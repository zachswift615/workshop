#!/bin/bash

# Workshop Release Script
# Automates version bumping, changelog updates, tagging, and PyPI publishing
#
# Usage:
#   ./release.sh [patch|minor|major|VERSION]
#
# Examples:
#   ./release.sh patch      # 1.0.5 -> 1.0.6
#   ./release.sh minor      # 1.0.5 -> 1.1.0
#   ./release.sh major      # 1.0.5 -> 2.0.0
#   ./release.sh 1.2.3      # Set to specific version
#   ./release.sh            # Interactive mode

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get current version from __init__.py (in workshop subdirectory)
CURRENT_VERSION=$(grep -E "^__version__ = " workshop/src/__init__.py | cut -d'"' -f2)

echo -e "${BLUE}📦 Workshop Release Automation${NC}"
echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}\n"

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${RED}❌ Error: You have uncommitted changes. Please commit or stash them first.${NC}"
    exit 1
fi

# Parse command line argument
BUMP_TYPE="${1:-}"

# Calculate new version
IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"

if [[ -n "$BUMP_TYPE" ]]; then
    # Non-interactive mode with parameter
    case $BUMP_TYPE in
        patch)
            NEW_VERSION="$major.$minor.$((patch + 1))"
            ;;
        minor)
            NEW_VERSION="$major.$((minor + 1)).0"
            ;;
        major)
            NEW_VERSION="$((major + 1)).0.0"
            ;;
        *)
            # Assume it's a specific version number
            NEW_VERSION="$BUMP_TYPE"
            ;;
    esac
    echo -e "${GREEN}Releasing version: ${NEW_VERSION}${NC}\n"
else
    # Interactive mode
    echo -e "${BLUE}Select version bump type:${NC}"
    echo "1) patch (x.x.N) - bug fixes"
    echo "2) minor (x.N.0) - new features, backward compatible"
    echo "3) major (N.0.0) - breaking changes"
    echo "4) custom - specify exact version"
    read -p "Enter choice [1-4]: " bump_type

    case $bump_type in
        1)
            NEW_VERSION="$major.$minor.$((patch + 1))"
            ;;
        2)
            NEW_VERSION="$major.$((minor + 1)).0"
            ;;
        3)
            NEW_VERSION="$((major + 1)).0.0"
            ;;
        4)
            read -p "Enter new version: " NEW_VERSION
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac

    echo -e "\n${GREEN}New version will be: ${NEW_VERSION}${NC}"
    read -p "Continue? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Setup for testing: Uninstall PyPI version and install editable local version
echo -e "\n${BLUE}🔧 Setting up test environment...${NC}"
echo -e "  Uninstalling PyPI version (if installed)..."
pip uninstall claude-workshop -y 2>/dev/null || echo "  (no existing installation found)"

echo -e "  Installing editable local version..."
if ! (cd workshop && pip install -e . -q); then
    echo -e "${RED}❌ Failed to install editable version. Aborting.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Editable version installed${NC}"

# Run tests before proceeding (in workshop subdirectory)
echo -e "\n${BLUE}🧪 Running tests...${NC}"
if ! (cd workshop && pytest); then
    echo -e "${RED}❌ Tests failed. Aborting release.${NC}"
    # Clean up editable install
    pip uninstall claude-workshop -y 2>/dev/null
    exit 1
fi
echo -e "${GREEN}✓ All tests passed${NC}"

# Clean up: Uninstall editable version before PyPI install
echo -e "\n${BLUE}🧹 Cleaning up test environment...${NC}"
pip uninstall claude-workshop -y
echo -e "${GREEN}✓ Editable version uninstalled${NC}"

# Get commits since last version tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -z "$LAST_TAG" ]]; then
    echo -e "${YELLOW}⚠️  No previous tags found. Using all commits.${NC}"
    COMMITS=$(git log --pretty=format:"- %s" --no-merges)
else
    echo -e "${BLUE}Getting commits since ${LAST_TAG}...${NC}"
    COMMITS=$(git log ${LAST_TAG}..HEAD --pretty=format:"- %s" --no-merges)
fi

# If no commits, abort
if [[ -z "$COMMITS" ]]; then
    echo -e "${RED}❌ No commits since last release. Nothing to release.${NC}"
    exit 1
fi

echo -e "\n${BLUE}Commits to include in changelog:${NC}"
echo "$COMMITS"

# Categorize commits
ADDED=$(echo "$COMMITS" | grep -iE "^- (add|new|feat|feature|implement)" || true)
FIXED=$(echo "$COMMITS" | grep -iE "^- (fix|bug|patch|resolve)" || true)
CHANGED=$(echo "$COMMITS" | grep -iE "^- (update|change|improve|enhance|refactor)" || true)
OTHER=$(echo "$COMMITS" | grep -viE "^- (add|new|feat|feature|implement|fix|bug|patch|resolve|update|change|improve|enhance|refactor)" || true)

# Build changelog entry
CHANGELOG_ENTRY="## [${NEW_VERSION}] - $(date +%Y-%m-%d)\n\n"

if [[ -n "$ADDED" ]]; then
    CHANGELOG_ENTRY+="### Added\n${ADDED}\n\n"
fi

if [[ -n "$FIXED" ]]; then
    CHANGELOG_ENTRY+="### Fixed\n${FIXED}\n\n"
fi

if [[ -n "$CHANGED" ]]; then
    CHANGELOG_ENTRY+="### Changed\n${CHANGED}\n\n"
fi

if [[ -n "$OTHER" ]]; then
    CHANGELOG_ENTRY+="### Other\n${OTHER}\n\n"
fi

# CHANGELOG is in root directory
CHANGELOG="CHANGELOG.md"

# Find the line number where to insert (after the header, before first version)
INSERT_LINE=$(grep -n "^## \[" "$CHANGELOG" | head -1 | cut -d: -f1)
if [[ -z "$INSERT_LINE" ]]; then
    # No existing versions, insert after header
    INSERT_LINE=$(grep -n "^# Changelog" "$CHANGELOG" | cut -d: -f1)
    INSERT_LINE=$((INSERT_LINE + 4))  # After header and description
fi

# Create temp file with new changelog
{
    head -n $((INSERT_LINE - 1)) "$CHANGELOG"
    echo -e "$CHANGELOG_ENTRY"
    tail -n +$INSERT_LINE "$CHANGELOG"
} > "${CHANGELOG}.tmp"

# Add comparison link at the bottom
if [[ -n "$LAST_TAG" ]]; then
    # Update comparison links
    sed -i.bak "s|\[Unreleased\].*|[${NEW_VERSION}]: https://github.com/zachswift615/workshop/compare/${LAST_TAG}...v${NEW_VERSION}|" "${CHANGELOG}.tmp"
    # Add new comparison link before the last one
    LAST_LINK_LINE=$(grep -n "^\[.*\]: https" "${CHANGELOG}.tmp" | tail -1 | cut -d: -f1)
    {
        head -n $LAST_LINK_LINE "${CHANGELOG}.tmp"
        echo "[${NEW_VERSION}]: https://github.com/zachswift615/workshop/compare/${LAST_TAG}...v${NEW_VERSION}"
        tail -n +$((LAST_LINK_LINE + 1)) "${CHANGELOG}.tmp"
    } > "${CHANGELOG}.tmp2"
    mv "${CHANGELOG}.tmp2" "${CHANGELOG}.tmp"
fi

mv "${CHANGELOG}.tmp" "$CHANGELOG"
rm -f "${CHANGELOG}.bak"

echo -e "\n${GREEN}✓ Updated CHANGELOG.md${NC}"

# Update version in __init__.py (in workshop subdirectory)
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" workshop/src/__init__.py
rm -f workshop/src/__init__.py.bak
echo -e "${GREEN}✓ Updated version in workshop/src/__init__.py${NC}"

# Update version in pyproject.toml (in workshop subdirectory)
sed -i.bak "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" workshop/pyproject.toml
rm -f workshop/pyproject.toml.bak
echo -e "${GREEN}✓ Updated version in workshop/pyproject.toml${NC}"

# Commit changes
git add CHANGELOG.md workshop/src/__init__.py workshop/pyproject.toml
git commit -m "Release v${NEW_VERSION}

$(echo -e "$CHANGELOG_ENTRY" | sed 's/^## \[.*\] - .*$//' | sed 's/^### //' | sed '/^$/d')

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

echo -e "${GREEN}✓ Committed version bump${NC}"

# Push to GitHub
git push
echo -e "${GREEN}✓ Pushed to GitHub${NC}"

# Create and push tag
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"
git push origin "v${NEW_VERSION}"
echo -e "${GREEN}✓ Created and pushed tag v${NEW_VERSION}${NC}"

# Build and publish to PyPI (in workshop subdirectory)
echo -e "\n${BLUE}📦 Building package...${NC}"
(cd workshop && python -m build)

echo -e "\n${BLUE}📤 Publishing to PyPI...${NC}"
if [[ -z "$TWINE_USERNAME" ]] || [[ -z "$TWINE_PASSWORD" ]]; then
    echo -e "${YELLOW}⚠️  TWINE_USERNAME and/or TWINE_PASSWORD not set.${NC}"
    echo "Please set them and run:"
    echo "  cd workshop && python -m twine upload dist/claude_workshop-${NEW_VERSION}*"
    exit 0
fi

(cd workshop && python -m twine upload "dist/claude_workshop-${NEW_VERSION}*")
echo -e "${GREEN}✓ Published to PyPI${NC}"

# Upgrade local installation (with retry for PyPI propagation)
echo -e "\n${BLUE}⬆️  Upgrading local installation...${NC}"
echo -e "${YELLOW}Waiting for PyPI to propagate new version...${NC}"

MAX_RETRIES=5
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 5
    if pip install --upgrade "claude-workshop==${NEW_VERSION}" 2>/dev/null; then
        echo -e "${GREEN}✓ Local installation upgraded${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}Retry $RETRY_COUNT/$MAX_RETRIES...${NC}"
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${YELLOW}⚠️  PyPI propagation taking longer than expected.${NC}"
    echo -e "You can manually upgrade later with:"
    echo -e "  pip install --upgrade claude-workshop==${NEW_VERSION}"
fi

echo -e "\n${GREEN}🎉 Release v${NEW_VERSION} complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo "  • View release on GitHub: https://github.com/zachswift615/workshop/releases/tag/v${NEW_VERSION}"
echo "  • View on PyPI: https://pypi.org/project/claude-workshop/${NEW_VERSION}/"

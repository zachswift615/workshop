# Release Process

This document describes how to release a new version of Workshop.

## Prerequisites

1. All changes committed to `main` branch
2. Tests passing locally (`pytest`)
3. PyPI credentials configured (see below)

## PyPI Credentials Setup

Set your PyPI credentials as environment variables:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...  # Your PyPI API token
```

Or add them to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) for persistence.

## Release Script

The `release.sh` script automates the entire release process:

```bash
# Interactive mode (prompts for version type)
./release.sh

# Non-interactive mode (specify version type)
./release.sh patch      # 1.0.5 -> 1.0.6
./release.sh minor      # 1.0.5 -> 1.1.0
./release.sh major      # 1.0.5 -> 2.0.0
./release.sh 1.2.3      # Set specific version
```

### What it does:

1. **Validates** - Checks for uncommitted changes
2. **Tests** - Runs full test suite (aborts if any fail)
3. **Version Bump** - Prompts for version type (patch/minor/major/custom)
4. **Changelog** - Auto-generates changelog entry from commits since last tag
5. **Commits** - Creates version bump commit
6. **Tags** - Creates git tag for the release
7. **Publishes** - Uploads to PyPI
8. **Upgrades** - Updates local installation

### Version Bump Types

- **Patch (x.x.N)** - Bug fixes, no new features
- **Minor (x.N.0)** - New features, backward compatible
- **Major (N.0.0)** - Breaking changes
- **Custom** - Specify exact version number

### Commit Message Categorization

The script automatically categorizes commits into changelog sections:

- **Added**: Commits starting with `add`, `new`, `feat`, `feature`, `implement`
- **Fixed**: Commits starting with `fix`, `bug`, `patch`, `resolve`
- **Changed**: Commits starting with `update`, `change`, `improve`, `enhance`, `refactor`
- **Other**: Everything else

**Tip**: Use conventional commit prefixes for better changelog organization.

## Manual Release (if script fails)

If the automated script fails, you can release manually:

```bash
# 1. Update version in 3 places
# - src/__init__.py: __version__ = "x.x.x"
# - pyproject.toml: version = "x.x.x"
# - CHANGELOG.md: Add new section

# 2. Run tests
pytest

# 3. Commit
git add -A
git commit -m "Release vx.x.x"
git push

# 4. Tag
git tag -a "vx.x.x" -m "Release vx.x.x"
git push origin "vx.x.x"

# 5. Build
python -m build

# 6. Publish
python -m twine upload dist/claude_workshop-x.x.x*

# 7. Upgrade local
pip install --upgrade claude-workshop==x.x.x
```

## Post-Release

After release:

1. Verify on PyPI: https://pypi.org/project/claude-workshop/
2. Create GitHub release: https://github.com/zachswift615/workshop/releases/new
3. Announce in relevant channels (if applicable)

## Troubleshooting

### "Tests failed" error
- Fix failing tests before releasing
- Run `pytest -v` to see which tests failed

### "TWINE credentials not set" warning
- Set `TWINE_USERNAME` and `TWINE_PASSWORD` environment variables
- Or manually run the twine command shown in the output

### "No commits since last release"
- Make sure you've committed changes
- Check `git log` to verify commits exist

### Tag already exists
- Delete the tag: `git tag -d vx.x.x && git push origin :refs/tags/vx.x.x`
- Then re-run the release script

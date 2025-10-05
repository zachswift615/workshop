"""
Project root detection using weighted heuristics.

This module provides smart project root detection that works even before git init,
in monorepos, and with various project types.
"""
from pathlib import Path
from typing import Tuple


def find_project_root() -> Tuple[Path, str, int]:
    """
    Find project root using weighted heuristics.

    Returns:
        (Path, reason, score) - The detected root, why it was chosen, and confidence score
    """
    current = Path.cwd().resolve()
    home = Path.home()

    # Don't ever search past home directory
    search_paths = []
    for parent in [current] + list(current.parents):
        if parent == home:
            break
        search_paths.append(parent)

    best_score = 0
    best_path = current
    best_reasons = []

    # Weighted indicators (higher = stronger signal of project root)
    indicators = {
        # Version control (highest weight - definitive project boundary)
        '.git': (15, "git repository"),
        '.svn': (15, "svn repository"),
        '.hg': (15, "mercurial repository"),

        # Package managers (strong indicators of project root)
        'package.json': (12, "Node.js project"),
        'Cargo.toml': (12, "Rust project"),
        'go.mod': (12, "Go module"),
        'pyproject.toml': (12, "Python project"),
        'pom.xml': (12, "Maven project"),
        'build.gradle': (12, "Gradle project"),
        'build.gradle.kts': (12, "Kotlin Gradle project"),
        'composer.json': (12, "PHP project"),
        'Gemfile': (12, "Ruby project"),
        'mix.exs': (12, "Elixir project"),
        'Package.swift': (12, "Swift package"),
        'stack.yaml': (12, "Haskell Stack project"),
        'Cargo.lock': (10, "Rust project"),
        'package-lock.json': (10, "Node.js project"),
        'yarn.lock': (10, "Yarn project"),
        'pnpm-lock.yaml': (10, "pnpm project"),
        'poetry.lock': (10, "Poetry project"),
        'Pipfile': (10, "Pipenv project"),

        # Build/config files (moderate indicators)
        'Makefile': (8, "Make-based project"),
        'CMakeLists.txt': (8, "CMake project"),
        'Dockerfile': (8, "Docker project"),
        'docker-compose.yml': (8, "Docker Compose project"),
        'docker-compose.yaml': (8, "Docker Compose project"),
        'webpack.config.js': (7, "Webpack project"),
        'vite.config.js': (7, "Vite project"),
        'rollup.config.js': (7, "Rollup project"),
        'tsconfig.json': (7, "TypeScript project"),
        '.eslintrc.js': (5, "ESLint project"),
        '.prettierrc': (5, "Prettier project"),

        # Documentation (weak but common)
        'README.md': (5, "documented project"),
        'README.rst': (5, "documented project"),
        'README.txt': (5, "documented project"),
        'README': (5, "documented project"),
        'LICENSE': (3, "licensed project"),
        'LICENSE.md': (3, "licensed project"),
        'LICENSE.txt': (3, "licensed project"),

        # Config files (very weak - could be anywhere)
        '.editorconfig': (2, "editor config"),
        '.gitignore': (2, "git config"),
    }

    # Search from current directory upward
    for path in search_paths:
        score = 0
        reasons = []

        for indicator, (weight, description) in indicators.items():
            if (path / indicator).exists():
                score += weight
                reasons.append(description)

        # Update best if this is better
        # Prefer closer directories if scores are equal
        if score > best_score or (score == best_score and path == current):
            best_score = score
            best_path = path
            best_reasons = reasons

    # Determine reason string
    if not best_reasons:
        reason = "current directory (no project indicators found)"
    elif len(best_reasons) == 1:
        reason = best_reasons[0]
    else:
        # Show top reason
        reason = f"{best_reasons[0]} (+{len(best_reasons)-1} more indicators)"

    # Threshold: require at least 8 points to override current directory
    # This prevents random directories with just a README from winning
    if best_score < 8 and best_path != current:
        return current, "current directory (low confidence in detection)", 0

    return best_path, reason, best_score


def validate_workspace_path(path: Path) -> Tuple[bool, str]:
    """
    Validate that a workspace path is acceptable.

    Args:
        path: Proposed workspace directory

    Returns:
        (is_valid, error_message)
    """
    # Resolve to absolute path
    path = path.expanduser().resolve()

    # Don't allow home directory itself
    if path == Path.home():
        return False, "Cannot use home directory as workspace"

    # Don't allow root
    if path == Path('/'):
        return False, "Cannot use root directory as workspace"

    # Check if parent exists (we'll create the workspace dir itself)
    if not path.parent.exists():
        return False, f"Parent directory does not exist: {path.parent}"

    # Check if it's writable (if it exists)
    if path.exists():
        if not path.is_dir():
            return False, f"Path exists but is not a directory: {path}"
        # Try to write a test file
        test_file = path / '.workshop_test'
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            return False, f"Directory is not writable: {e}"
    else:
        # Check parent is writable
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Clean up test directory if we created it
            if not any(path.iterdir()):
                path.rmdir()
        except (PermissionError, OSError) as e:
            return False, f"Cannot create workspace directory: {e}"

    return True, ""

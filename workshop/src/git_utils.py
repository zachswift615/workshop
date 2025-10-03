"""
Git utilities for Workshop - extracts git context
"""
import subprocess
from typing import Dict, Optional


def run_git_command(args: list) -> Optional[str]:
    """
    Run a git command and return output.

    Args:
        args: Git command arguments (e.g., ['branch', '--show-current'])

    Returns:
        Command output as string, or None if command fails
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_info() -> Dict[str, Optional[str]]:
    """
    Get current git context (branch, commit).

    Returns:
        Dict with 'branch' and 'commit' keys
    """
    return {
        "branch": run_git_command(['branch', '--show-current']),
        "commit": run_git_command(['rev-parse', '--short', 'HEAD'])
    }


def get_modified_files() -> list:
    """
    Get list of modified files in git.

    Returns:
        List of file paths
    """
    output = run_git_command(['status', '--porcelain'])
    if not output:
        return []

    files = []
    for line in output.split('\n'):
        if line.strip():
            # Parse git status format: "XY filename"
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])

    return files

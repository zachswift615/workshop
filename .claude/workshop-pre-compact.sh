#!/usr/bin/env python3
"""
Workshop PreCompact hook for Claude Code.
Captures important context before compaction to prevent information loss.

This script is called by Claude Code's PreCompact hook before context is compacted.
"""
import sys
import subprocess
from datetime import datetime


def capture_pre_compact_context(reason: str):
    """
    Capture important context before compaction.

    Args:
        reason: 'auto' for automatic compaction, 'manual' for /compact command
    """

    # Create a note about the impending compaction
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Record that compaction is happening
        subprocess.run([
            'workshop', 'note',
            f'Context compaction triggered ({reason}) - preserving conversation state',
            '-t', 'compaction',
            '-t', f'compaction-{reason}'
        ], check=False, capture_output=True)

        # Get current state and save it
        # This preserves goals and next steps that might be in the conversation
        result = subprocess.run(
            ['workshop', 'state'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout:
            # State exists and was captured
            print(f"✓ Workshop: Preserved context before {reason} compaction", file=sys.stderr)

    except Exception as e:
        # Silently fail - don't interrupt compaction
        pass


def main():
    """Main entry point."""
    import os

    # Get compaction reason from environment
    reason = os.environ.get('CLAUDE_PRECOMPACT_MATCHER', 'unknown')

    # Capture context
    capture_pre_compact_context(reason)

    # Print message to stderr (won't interfere with compaction)
    if reason == 'auto':
        print("📦 Workshop: Auto-saving context before compaction...", file=sys.stderr)
    else:
        print("📦 Workshop: Saving context before manual compaction...", file=sys.stderr)


if __name__ == '__main__':
    main()

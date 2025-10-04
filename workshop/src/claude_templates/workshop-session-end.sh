#!/usr/bin/env python3
"""
Workshop session end hook for Claude Code.
Parses transcript and stores session summary in Workshop.

This script is called by Claude Code's SessionEnd hook.
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any


def parse_jsonl_transcript(transcript_path: Path) -> List[Dict[str, Any]]:
    """Parse JSONL transcript file into list of message objects."""
    messages = []

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        messages.append(obj)
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        return []

    return messages


def extract_session_data(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract session data from parsed messages."""

    files_modified: Set[str] = set()
    commands_run: List[str] = []
    workshop_entries: Dict[str, int] = {
        'decisions': 0,
        'notes': 0,
        'gotchas': 0,
        'preferences': 0,
        'antipatterns': 0
    }
    user_requests: List[str] = []

    start_time = None
    end_time = None
    branch = ""

    for msg in messages:
        # Track timestamps
        if 'timestamp' in msg:
            timestamp = msg['timestamp']
            if start_time is None:
                start_time = timestamp
            end_time = timestamp

        # Get message content
        if 'message' not in msg:
            continue

        inner_msg = msg['message']
        role = inner_msg.get('role', '')
        content = inner_msg.get('content', [])

        # Extract user requests
        if role == 'user':
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '').strip()
                    if text and not text.startswith('<') and len(text) > 10:
                        # Skip system messages and very short messages
                        user_requests.append(text)

        # Extract tool uses (assistant actions)
        if role == 'assistant':
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue

                block_type = block.get('type')

                # Track file modifications
                if block_type == 'tool_use':
                    tool_name = block.get('name', '')
                    tool_input = block.get('input', {})

                    if tool_name == 'Edit':
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            files_modified.add(file_path)

                    elif tool_name == 'Write':
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            files_modified.add(file_path)

                    elif tool_name == 'Bash':
                        command = tool_input.get('command', '')
                        if command:
                            # Track workshop CLI commands
                            if 'workshop' in command:
                                if 'decision' in command:
                                    workshop_entries['decisions'] += 1
                                elif 'note' in command:
                                    workshop_entries['notes'] += 1
                                elif 'gotcha' in command:
                                    workshop_entries['gotchas'] += 1
                                elif 'preference' in command:
                                    workshop_entries['preferences'] += 1
                                elif 'antipattern' in command:
                                    workshop_entries['antipatterns'] += 1

                            # Track commands (filter out noise)
                            if not command.startswith('workshop context') and \
                               not command.startswith('workshop recent') and \
                               not command.startswith('workshop search') and \
                               not command.startswith('workshop why'):
                                # Truncate very long commands
                                cmd_display = command[:100] + '...' if len(command) > 100 else command
                                commands_run.append(cmd_display)

    # Try to get git branch
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except:
        pass

    return {
        'files_modified': sorted(list(files_modified)),
        'commands_run': commands_run,
        'workshop_entries': workshop_entries,
        'user_requests': user_requests,
        'start_time': start_time,
        'end_time': end_time,
        'branch': branch
    }


def generate_summary(session_data: Dict[str, Any]) -> str:
    """Generate a brief summary of the session."""
    parts = []

    files_count = len(session_data['files_modified'])
    if files_count > 0:
        parts.append(f"Modified {files_count} file{'s' if files_count != 1 else ''}")

    # Count total workshop entries
    total_entries = sum(session_data['workshop_entries'].values())
    if total_entries > 0:
        parts.append(f"recorded {total_entries} workshop entr{'ies' if total_entries != 1 else 'y'}")

    requests_count = len(session_data['user_requests'])
    if requests_count > 0:
        parts.append(f"{requests_count} user request{'s' if requests_count != 1 else ''}")

    if parts:
        return '; '.join(parts)
    else:
        return "Session activity recorded"


def calculate_duration(start_time: str, end_time: str) -> int:
    """Calculate session duration in minutes."""
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration = (end - start).total_seconds() / 60
        return int(duration)
    except:
        return 0


def store_session(session_data: Dict[str, Any], session_id: str, reason: str):
    """Store session in Workshop using CLI."""

    # Calculate duration
    duration = 0
    if session_data['start_time'] and session_data['end_time']:
        duration = calculate_duration(session_data['start_time'], session_data['end_time'])

    # Generate summary
    summary = generate_summary(session_data)

    # Build workshop CLI command
    # Note: We're adding a session entry directly
    # Since we don't have a `workshop session add` command yet,
    # we'll need to add it to the CLI

    # For now, store as a note with special metadata
    # TODO: Once session commands are implemented, use those instead

    try:
        # Store as a decision with session metadata
        subprocess.run([
            'workshop', 'decision',
            f'Session ended: {summary}',
            '-r', f'Duration: {duration}min; Files: {len(session_data["files_modified"])}',
            '-t', 'session',
            '-t', f'session-{session_id[:8]}'
        ], check=False)
    except Exception as e:
        # Silently fail - don't interrupt session end
        pass


def main():
    """Main entry point."""

    # Get transcript path from environment or command line
    if len(sys.argv) > 1:
        transcript_path = Path(sys.argv[1])
    else:
        # Default to CLAUDE_TRANSCRIPT_FILE environment variable
        import os
        transcript_file = os.environ.get('CLAUDE_TRANSCRIPT_FILE')
        if not transcript_file:
            sys.exit(0)  # Silently exit if no transcript
        transcript_path = Path(transcript_file)

    if not transcript_path.exists():
        sys.exit(0)

    # Get session ID and reason
    import os
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    reason = os.environ.get('CLAUDE_SESSION_END_REASON', 'unknown')

    # Parse transcript
    messages = parse_jsonl_transcript(transcript_path)
    if not messages:
        sys.exit(0)

    # Extract session data
    session_data = extract_session_data(messages)

    # Store session
    store_session(session_data, session_id, reason)


if __name__ == '__main__':
    main()

#!/bin/bash

# Workshop SessionStart Hook
# This imports new conversation history and displays workshop context at the beginning of each session

# Ensure PATH includes common locations for pyenv, homebrew, etc.
export PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

# Check if workshop is available
if ! command -v workshop >/dev/null 2>&1; then
    echo "Workshop CLI not found in PATH. Install with: pip install claude-workshop"
    exit 0
fi

# Auto-import new JSONL files (runs silently in background)
# This captures compaction summaries and new conversation data automatically
workshop import >/dev/null 2>&1 &

# Display workshop context as JSON for Claude to parse
# Capture context and escape it properly
# Try to find python3 in common locations
PYTHON=""
for p in python3 python /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
    if command -v "$p" >/dev/null 2>&1; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python not found. Cannot format workshop context."
    exit 0
fi

CONTEXT=$(workshop context 2>&1 | head -50 | "$PYTHON" -c "import sys, json; print(json.dumps(sys.stdin.read()))")

echo '{
  "role": "system_context",
  "message": "📝 Workshop Context Available",
  "details": "Use the `workshop` CLI to access project context. Key commands:\n\n- `workshop context` - View session summary\n- `workshop search <query>` - Search entries\n- `workshop note <text>` - Add a note\n- `workshop decision <text> -r <reasoning>` - Record a decision\n- `workshop gotcha <text>` - Record a gotcha/constraint\n\nWorkshop maintains context across sessions. Use it liberally to:\n- Record decisions and their reasoning\n- Document gotchas and constraints\n- Track goals and next steps\n- Save user preferences\n\nCurrent context:",
  "context": '"${CONTEXT}"'
}'

#!/bin/bash

# Workshop SessionStart Hook
# This imports new conversation history and displays workshop context at the beginning of each session

# Check if workshop is available
if ! command -v workshop &> /dev/null; then
    echo "Workshop CLI not found. Install with: pip install -e ./workshop"
    exit 0
fi

# Auto-import new JSONL files (runs silently in background)
# This captures compaction summaries and new conversation data automatically
workshop import &>/dev/null &

# Display workshop context as JSON for Claude to parse
echo '{
  "role": "system_context",
  "message": "📝 Workshop Context Available",
  "details": "Use the `workshop` CLI to access project context. Key commands:\n\n- `workshop context` - View session summary\n- `workshop search <query>` - Search entries\n- `workshop note <text>` - Add a note\n- `workshop decision <text> -r <reasoning>` - Record a decision\n- `workshop gotcha <text>` - Record a gotcha/constraint\n\nWorkshop maintains context across sessions. Use it liberally to:\n- Record decisions and their reasoning\n- Document gotchas and constraints\n- Track goals and next steps\n- Save user preferences\n\nCurrent context:",
  "context": '"$(workshop context 2>&1 | sed 's/"/\\"/g' | tr '\n' ' ')"'"
}'

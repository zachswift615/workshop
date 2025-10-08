@echo off
REM Workshop SessionStart Hook
REM This displays workshop context at the beginning of each Claude Code session

REM Check if workshop is available
where workshop >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Workshop CLI not found. Install with: pip install claude-workshop
    exit /b 0
)

REM Use Python to generate JSON with embedded workshop context
REM The Python display.py already handles UTF-8 encoding on Windows
python -c "import subprocess, json; ctx = subprocess.run(['workshop', 'context'], capture_output=True, text=True, encoding='utf-8').stdout.strip().replace('\"', '\\\"').replace('\n', ' '); print(json.dumps({'role': 'system_context', 'message': '📝 Workshop Context Available', 'details': 'Use the `workshop` CLI to access project context. Key commands:\\n\\n- `workshop context` - View session summary\\n- `workshop search <query>` - Search entries\\n- `workshop note <text>` - Add a note\\n- `workshop decision <text> -r <reasoning>` - Record a decision\\n- `workshop gotcha <text>` - Record a gotcha/constraint\\n\\nWorkshop maintains context across sessions. Use it liberally to:\\n- Record decisions and their reasoning\\n- Document gotchas and constraints\\n- Track goals and next steps\\n- Save user preferences\\n\\nCurrent context:', 'context': ctx}))"

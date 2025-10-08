@echo off
REM Workshop PreCompact Hook
REM Calls the Python script to capture context before compaction

REM Check if workshop is available
where workshop >nul 2>nul
if %ERRORLEVEL% NEQ 0 exit /b 0

REM Call the Python script (same logic as .sh version)
python "%~dp0workshop-pre-compact.sh"

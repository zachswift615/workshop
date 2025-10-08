@echo off
REM Workshop SessionEnd Hook
REM Calls the Python script to parse transcript and store session summary

REM Check if workshop is available
where workshop >nul 2>nul
if %ERRORLEVEL% NEQ 0 exit /b 0

REM Call the Python script (same logic as .sh version)
REM Pass transcript file path as argument
python "%~dp0workshop-session-end.sh" %*

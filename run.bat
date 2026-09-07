@echo off
REM Windows runner for Wellfound Job Agent - Now uses Microsoft Edge
REM Usage: run.bat [run|scrape|match|apply]
REM First time: run.bat scrape  (will open Edge, ask you to login)
REM Then: run.bat  (full pipeline)

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

setlocal
cd /d "%~dp0"

REM Use python from PATH (Python 3.11)
python -X utf8 -m wellfound_agent %*
if %errorlevel% neq 0 (
    echo.
    echo Try also: wellfound-agent %*
)
endlocal
pause

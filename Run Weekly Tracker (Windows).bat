@echo off
REM Double-click this file to run the weekly tracker — no typing commands
REM required. A window opens on its own, asks two quick questions, then
REM shows the progress bar and waits for a keypress before closing so the
REM summary (what was added, where it saved, time/cost) stays on screen
REM to read. This is the Windows counterpart to
REM "Run Weekly Tracker (Mac).command" / "Run Weekly Tracker (Mac).app".
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo  US-China Relations Tracker
echo ==========================================
echo.
echo What would you like to run?
echo   1) Last complete week (just press Enter for this)
echo   2) A specific date range instead
echo.
set /p choice="Enter 1 or 2: "
echo.

if "%choice%"=="2" (
    echo Enter dates as YYYYMMDD, e.g. 20260804.
    echo.
    set /p start_date="Start date: "
    set /p end_date="End date:   "
    echo.
    call run_week.bat --start "!start_date!" --end "!end_date!"
) else (
    call run_week.bat
)

echo.
echo Press any key to close this window...
pause >nul

@echo off
REM Double-click this file to run the weekly tracker: no typing commands
REM required. A window opens on its own, asks two quick questions, then
REM shows the progress bar and waits for a keypress before closing so the
REM summary (what was added, where it saved, time/cost) stays on screen
REM to read. This is the Windows counterpart to
REM "Run Weekly Tracker (Mac).command" / "Run Weekly Tracker (Mac).app".
REM
REM The actual questions/date-validation logic lives in
REM scripts\run_weekly_tracker_windows.ps1 (PowerShell, not batch) — see
REM that file's own header comment for why. -ExecutionPolicy Bypass only
REM affects this one invocation, not any system-wide setting, so it
REM doesn't need an administrator or any change to this computer's
REM normal security settings.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_weekly_tracker_windows.ps1"

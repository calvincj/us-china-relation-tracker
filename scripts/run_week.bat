@echo off
REM The simple, one-command way to run the tracker for a normal week — the
REM Windows counterpart to run_week.sh (see that file for the fuller
REM comments; kept in sync with it, same two things it does):
REM
REM Usage (run from the project's root folder):
REM   scripts\run_week.bat                                    (last complete week)
REM   scripts\run_week.bat --start 2026-08-04 --end 2026-08-10 (a specific week instead)
REM   scripts\run_week.bat -v                                  (show full detail, not just progress)
REM
REM What happens:
REM   1. First time only: loads the past trackers so nothing gets
REM      re-scraped/duplicated.
REM   2. Runs the scraper live in this window — a progress bar across all
REM      sources, then a short summary.
REM
REM For an unattended weekly scheduled task instead of running this by
REM hand, see README.md for a Windows Task Scheduler example that calls
REM this same script.

setlocal
cd /d "%~dp0.."

if not exist "output\tracker.db" (
    echo First run — loading past trackers so nothing gets duplicated...
    python code\seed_dedup_db.py
)

python code\scraper.py %*

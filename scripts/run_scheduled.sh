#!/usr/bin/env bash
# The "set it and forget it" runner — meant to be wired to cron or launchd
# so this runs on its own schedule with nobody manually typing a command.
# For running it yourself, by hand, use run_week.sh instead (it shows a
# live progress bar; this one logs quietly to a file since nobody's
# watching the terminal when a scheduler fires it).
#
# What it does:
#   1. Seeds output/tracker.db from input/past_trackers/*.docx the
#      FIRST time only (if output/tracker.db doesn't exist yet) so a
#      brand-new machine doesn't re-scrape/duplicate everything already
#      covered historically.
#   2. Runs every source in code/scraper.py, appending new entries to
#      output/tracker_output.docx (defaults to last complete week — see
#      code/scraper.py --help for --start/--end).
#   3. Writes a timestamped log to logs/ so a human (or cron's mail) can see
#      what happened without staring at a terminal.
#
# Usage:
#   ./scripts/run_scheduled.sh    # run once, now — same as run_week.sh minus the progress bar
#
# To actually make this run on its own every week, add a cron entry
# (crontab -e):
#   0 7 * * 1  cd "/path/to/us-china-relation-tracker" && ./scripts/run_scheduled.sh   # every Monday at 7am
# or, on macOS, a launchd plist is more reliable than cron for laptops that
# sleep overnight — see README.md for a StartCalendarInterval example. Once
# either is set up, this genuinely runs unattended — nobody needs to
# remember to type anything.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdir -p logs
LOG_FILE="logs/$(date +%Y-%m-%d_%H%M%S).log"

if [ ! -f output/tracker.db ]; then
    echo "[run_scheduled] output/tracker.db not found — seeding from input/past_trackers/ first" | tee -a "$LOG_FILE"
    python3 code/seed_dedup_db.py >> "$LOG_FILE" 2>&1
fi

echo "[run_scheduled] Starting scraper run at $(date)" | tee -a "$LOG_FILE"
python3 code/scraper.py --no-open >> "$LOG_FILE" 2>&1
STATUS=$?

echo "[run_scheduled] Finished with exit code $STATUS at $(date)" | tee -a "$LOG_FILE"
exit $STATUS

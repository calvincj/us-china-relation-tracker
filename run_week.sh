#!/usr/bin/env bash
# The simple, one-command way to run the tracker for a normal week.
#
# Usage:
#   ./run_week.sh                                        # last complete week (Tue-Mon)
#   ./run_week.sh --start 2026-08-04 --end 2026-08-10     # a specific week instead
#   ./run_week.sh -v                                      # show full detail, not just progress
#
# What happens:
#   1. First time only: loads the past trackers so nothing gets
#      re-scraped/duplicated.
#   2. Runs the scraper live in this terminal — a progress bar across all
#      sources, then a short summary.
#   3. Prints exactly where the finished, dated document was saved.
#
# For an unattended weekly cron/launchd job instead of running this by
# hand, use run_scheduled.sh (see README.md) — same underlying scraper,
# just logs to a file instead of showing a live progress bar.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -f output/tracker.db ]; then
    echo "First run — loading past trackers so nothing gets duplicated..."
    python3 code/seed_dedup_db.py
fi

python3 code/scraper.py "$@"

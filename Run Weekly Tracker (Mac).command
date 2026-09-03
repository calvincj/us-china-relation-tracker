#!/usr/bin/env bash
# Double-click this file (in Finder, not a terminal) to run the weekly
# tracker — no typing commands required. A terminal window opens on its
# own, asks two quick questions, then shows the progress bar and waits
# for a keypress before closing so the summary (what was added, where it
# saved, time/cost) stays on screen to read.
cd "$(dirname "$0")"

echo "=========================================="
echo " US-China Relations Tracker"
echo "=========================================="
echo ""
echo "What would you like to run?"
echo "  1) Last complete week (just press Enter for this)"
echo "  2) A specific date range instead"
echo ""
read -p "Enter 1 or 2: " choice
echo ""

if [ "$choice" = "2" ]; then
    echo "Enter dates as YYYYMMDD, e.g. 20260804."
    echo ""
    read -p "Start date: " start_date
    read -p "End date:   " end_date
    echo ""
    ./run_week.sh --start "$start_date" --end "$end_date"
else
    ./run_week.sh
fi

echo ""
echo "Press any key to close this window..."
read -n 1 -s

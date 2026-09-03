#!/usr/bin/env bash
# Double-click this file (in Finder, not a terminal) to run the weekly
# tracker: no typing commands required. A terminal window opens on its
# own, asks two quick questions, then shows the progress bar and waits
# for a keypress before closing so the summary (what was added, where it
# saved, time/cost) stays on screen to read.
cd "$(dirname "$0")"

# Accepts YYYYMMDD or YYYY-MM-DD, checks it's a REAL calendar date (not
# just 8 digits: catches something like 20261332), and prints the
# normalized YYYYMMDD form on success. Returns non-zero on anything
# invalid so the caller can ask again instead of crashing further down
# with a confusing Python traceback.
#
# The round-trip comparison (not just "did `date` parse this at all")
# matters: macOS's `date -j -f` silently ROLLS OVER an out-of-range day
# instead of rejecting it (e.g. "20260230" quietly becomes 20260302,
# "Feb 30" -> "Mar 2") rather than raising an error the way Python's own
# datetime.strptime does. Re-formatting the parsed result and comparing
# it back to the original catches exactly that case: a genuinely valid
# date round-trips to itself unchanged, an invalid one that got silently
# "corrected" won't match. Found live, 2026-09-03, testing this exact
# function against 20260230.
validate_date() {
    local raw="${1//-/}"
    if ! [[ "$raw" =~ ^[0-9]{8}$ ]]; then
        return 1
    fi
    local result
    result=$(date -j -f "%Y%m%d" "$raw" "+%Y%m%d" 2>/dev/null)
    if [ -n "$result" ] && [ "$result" = "$raw" ]; then
        echo "$result"
    else
        return 1
    fi
}

read_date() {
    local prompt="$1"
    local input normalized
    while true; do
        read -p "$prompt" input
        normalized=$(validate_date "$input")
        if [ -n "$normalized" ]; then
            echo "$normalized"
            return 0
        fi
        # >&2, not stdout: this function's whole stdout is captured by
        # the caller via `$(read_date ...)` to get the normalized date
        # back — anything else printed to stdout here would get
        # silently appended into that captured value instead of showing
        # up as an on-screen message. Found live, 2026-09-03: without
        # this, a retry message ended up concatenated INTO the date
        # string itself, which then broke scraper.py's own date parsing
        # with a confusing error instead of ever showing the user this
        # message at all.
        echo "That's not a valid date. Enter it as YYYYMMDD, e.g. 20260804." >&2
    done
}

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
    today=$(date "+%Y%m%d")
    start_date=$(read_date "Start date: ")
    while true; do
        end_date=$(read_date "End date:   ")
        if [ "$end_date" -gt "$today" ]; then
            echo "That end date is in the future. Enter a date up to today."
        else
            break
        fi
    done
    echo ""
    ./run_week.sh --start "$start_date" --end "$end_date"
else
    ./run_week.sh
fi

echo ""
echo "Press any key to close this window..."
read -n 1 -s

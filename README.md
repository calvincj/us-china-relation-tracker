# US-China Relations Tracker — automated scraper

Weekly scraper that watches PRC- and US-government press sources (plus,
optionally, a set of X/Twitter accounts) for US-China-relevant news and
appends new entries to `output/tracker_output.docx` in the same format as
the existing tracker (see `input/past_trackers/`).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your API keys — see .env.example for
                        # which ones are required vs. optional, and where
                        # to get each one
```

`GEMINI_API_KEY` is required to run at all. `X_API_KEY` is required too,
but only for the X/Twitter source specifically — leave it blank and
everything else still runs, just without X. Everything else in
`.env.example` is an optional fallback — the comments in that file
explain what each one unlocks and are written for someone who isn't a
programmer, so start there.

## First-time setup: seed the dedup database

Before the first live run, seed `output/tracker.db` from everything
already covered in `input/past_trackers/*.docx` so the scraper doesn't
re-process (and duplicate) old news:

```bash
python code/seed_dedup_db.py
```

## Running it yourself (the simple way)

**No terminal needed — Mac**: double-click `Run Weekly Tracker (Mac).app`
in this folder (it has its own icon, so it's easy to spot). It opens a
terminal window for you and asks:

```
What would you like to run?
  1) Last complete week (just press Enter for this)
  2) A specific date range instead
```

Press Enter for the normal weekly case. If you pick 2, it asks for a
start and end date as `YYYYMMDD` (e.g. `20260804`) — `YYYY-MM-DD` works
too if you prefer dashes. Either way, it
then shows progress and waits for a keypress before closing so you can
read the summary. (First time only, macOS might warn "unidentified
developer" — right-click the file, choose Open, confirm once, and it
won't ask again. If it ever refuses to open at all with a "damaged"-style
error — this can happen to an unsigned app after being copied around —
either run `codesign --force --deep -s - "Run Weekly Tracker (Mac).app"`
once from a terminal, or just double-click
`Run Weekly Tracker (Mac).command` instead, which does exactly the same
thing with no signing involved.)

**No terminal needed — Windows**: double-click
`Run Weekly Tracker (Windows).bat` in this folder. It asks the exact same
two questions as the Mac version above, in a Command Prompt window, and
waits for a keypress before closing so you can read the summary. (Needs
Python installed and on your `PATH` — if double-clicking does nothing or
flashes and closes, open Command Prompt, `cd` into this folder, and run
`"Run Weekly Tracker (Windows).bat"` from there instead, so any error
message stays visible.)

If you're comfortable with a terminal instead, from the project root (the
folder this README is in), one command:

```bash
./run_week.sh          # Mac/Linux
run_week.bat            # Windows
```

Either way, it seeds the dedup database on the very first run, then shows
a progress bar while it checks every source, and finishes with something
like:

```
Done — 9 new entries added for Aug 25-31, 2026.
Saved to: output/US-China Tracker Aug 25-31, 2026.docx
Took 16m 7s — 14,320 tokens, est. cost $0.0187.
```

**It defaults to last week automatically.** The tracker's week always
runs Tuesday through Monday — run `./run_week.sh` (or `run_week.bat`) on
a Monday and it covers last Tuesday through today; run it Tuesday (or any
day after) and it covers that exact same just-finished week, not a new
one. You never need to think about dates for a normal weekly run.

If you ever need a specific week instead (catching up after a trip, or
redoing one), say so explicitly:

```bash
./run_week.sh --start 2026-08-04 --end 2026-08-10   # Mac/Linux
run_week.bat --start 2026-08-04 --end 2026-08-10     # Windows
```

Want to see everything it's doing instead of just the progress bar
(useful if something looks wrong)? Add `-v`. Either way, the full detail
is always saved to `logs/` for later.

## Running it as one source, or fully unattended (the flexible way)

```bash
python code/scraper.py                    # run every source
python code/scraper.py --source fmprc_conf # run just one (see --help for the full list)
./run_scheduled.sh                         # Mac/Linux: seeds on first run, then runs everything, logs to logs/
```

`run_scheduled.sh` is the same underlying scraper as `run_week.sh`, just
quiet (everything logged to a file, nothing shown live) — it's meant to be
wired to cron or launchd so it runs completely on its own, on a schedule,
with nobody around to watch a progress bar or type a command (Windows:
see the Task Scheduler example below instead — it calls `run_week.bat`
directly, no separate quiet script needed there). Once one of
these is set up, it genuinely runs unattended — you don't run it, it runs
itself:

```
0 7 * * 1  cd "/path/to/us-china-relation-tracker" && ./run_scheduled.sh   # every Monday at 7am
```

or, on macOS, a `launchd` job survives sleep/reboot more reliably than cron.
Create `~/Library/LaunchAgents/com.tracker.weekly.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.tracker.weekly</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/us-china-relation-tracker/run_scheduled.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
</dict></plist>
```

then `launchctl load ~/Library/LaunchAgents/com.tracker.weekly.plist`.

On Windows, Task Scheduler is the equivalent — either use its GUI ("Create
Basic Task" → trigger: Weekly, Monday → action: Start a Program →
`run_week.bat` → "Start in" set to this project's folder), or the same
thing from Command Prompt:

```
schtasks /create /tn "US-China Tracker Weekly" /tr "\"C:\path\to\us-china-relation-tracker\run_week.bat\"" /sc weekly /d MON /st 07:00
```

(There's no quiet/logs-only Windows counterpart to `run_scheduled.sh` yet —
Task Scheduler runs `run_week.bat` in the background either way, and its
own history/log view shows what happened, so this hasn't been needed.)

**Rate limits mean a full run can take a while.** Gemini's request-per-minute
limit paces every Gemini call several seconds apart; a run across all
sources can take anywhere from a few minutes to over an hour depending on
how much is new. This is expected — see "Speed" below for what can and
can't be sped up.

## Checking cost and what happened

Every run prints its own time and cost automatically (see the "Took ..."
line above) — no separate command needed for a normal week. It also
prints, right below that, whether any source actually failed (a site
being down, a page that stopped loading — a real error, not just "0 new
items," which is a normal, healthy outcome) — so a real problem can't
silently scroll by in a log file nobody's watching:

```
⚠ 1 source(s) had errors this run:
  - State Council Information Office (scio): 2 error(s)
      [scio] Failed to fetch http://www.scio.gov.cn/...
```

or, when nothing went wrong: `No source errors this run.` Either way,
every run also ends with a reminder that Truth Social, YouTube, and Dept
of War aren't covered by this tool at all (see "What's covered / not
covered" below) — worth a manual check on weeks where one of those might
matter.

Every LLM/API call is also logged permanently to `output/usage_log.jsonl`
with a real dollar estimate, in case you ever want the ALL-TIME total
across every run this project has ever made (not just the most recent
one):

```bash
python3 -c "import sys; sys.path.insert(0, 'code'); import scraper as S; S.summarize_usage_log()"
```

Items an LLM judged "probably not relevant enough" — as opposed to a plain
keyword miss — are logged to `output/flagged_for_review.md` instead of
silently disappearing, so you can periodically skim it and manually add
back anything that got cut too aggressively.

## What's covered / not covered

See `input/notes/SOURCES.md` for the full source inventory (PRC + US
government + X, what's implemented vs. intentionally skipped and why).

Dept of War (war.gov) is intentionally **not** scraped. Its article pages
return a flat 403 for any non-browser client — confirmed to be an
infrastructure-level block (Akamai), not something caused by this
project's own scraping, and not something a code fix or a real headless
browser can get past. No reliable substitute source was found either
(checked the old defense.gov domain, various user-agents, the RSS feed's
own content depth, Wayback Machine, archive.today, DVIDS, GovInfo, and
the department's own X accounts). See `input/notes/SOURCES.md` and
`input/notes/NOTES.md` for the full investigation. The scraping code is
still in `code/scraper.py` (`scrape_wardept`), just disconnected from the
active run, in case this is ever revisited.

## Manual entries

`code/format_entry.py` formats a manually-pasted transcript/press release
into the same tracker style (useful for sources the scraper doesn't cover).
`input/notes/sample_qa.txt` is an example input you can try it on:

```bash
python code/format_entry.py input/notes/sample_qa.txt --out output/tracker_output.docx
```

`googledoc_autoformat_extension/Code.gs` does the same thing directly
inside a Google Doc (Extensions → Apps Script → paste it in) if you're
maintaining the tracker there instead of as a local .docx — it's fully
independent of everything else in this project, nothing here calls into
it and it calls into nothing here.

## Speed

A full run can take a while because Gemini's requests-per-minute limit
forces a real pause between calls. A few things help without sacrificing
accuracy:

- **The pipeline already avoids LLM calls where a plain keyword check is
  reliable** (screening obviously-irrelevant items for free, and detecting
  speaker structure in a transcript via regex before ever asking an LLM to
  parse it) — most of the runtime by now is actually spent on the calls
  that genuinely need judgment (relevance screening, translation,
  paragraph extraction).
- **The pipeline stops wasting time re-discovering an exhausted Gemini
  quota.** Once Gemini rate-limits once, it's skipped (no pause, no
  attempt) for a couple of minutes rather than re-tried — and re-failing —
  on every single subsequent call.
- **The 4-tier LLM fallback chain (Gemini → Groq → OpenRouter → Grok)
  already runs each item through whichever provider is fastest/available**,
  so a Gemini rate-limit doesn't stall a run — it just shifts that item to
  the next tier, which isn't rate-limited the same way.
- **Running multiple *sources* concurrently** (e.g. FMPRC and Treasury at
  the same time, since they don't depend on each other) is possible and
  would cut wall-clock time further, but isn't implemented yet — it needs
  care around the shared SQLite dedup database (concurrent writes) and
  around not spending Gemini's shared per-minute budget faster than one
  source already does alone. Worth adding if a full run's length becomes a
  real problem; see `input/notes/NOTES.md` for the tradeoffs.

## Project files

| File/folder | Purpose |
|---|---|
| `code/scraper.py` | Main pipeline — one `scrape_*` function per source, shared doc-writing/hyperlink helpers, `main()` dispatches by `--source` |
| `code/backtest.py` | Validates the pipeline against a past tracker's known entries (used during development, not part of normal operation) |
| `code/test_scraper.py` | Offline regression tests for the classification/label-parsing logic — no API keys or network needed, run with `python code/test_scraper.py` |
| `code/seed_dedup_db.py` | One-time (or repeatable) seeding of `output/tracker.db` from past trackers' embedded source links |
| `code/format_entry.py` | Manual paste-to-formatted-entry CLI tool |
| `Run Weekly Tracker (Mac).app` | Mac: the one to double-click — has its own icon (from `assets/tracker-icon.png`). Just opens a terminal and runs `Run Weekly Tracker (Mac).command` |
| `Run Weekly Tracker (Mac).command` | What the `.app` actually runs: asks last-week-or-custom-dates, then runs `run_week.sh` and waits for a keypress before closing. Works fine double-clicked directly too, just with the default plain-script icon |
| `Run Weekly Tracker (Windows).bat` | Windows: the one to double-click — same two questions, same progress bar, waits for a keypress before closing. Runs `run_week.bat` |
| `assets/tracker-icon.png` | Source image for the Mac `.app`'s icon — only needed again if you want to change the icon (see NOTES.md for how it was generated) |
| `run_week.sh` | Mac/Linux: the simple one-command way to run it by hand: seeds if needed, shows a live progress bar, ends with the dated output doc's location and the run's time/cost |
| `run_week.bat` | Windows counterpart to `run_week.sh` — same behavior, called by `Run Weekly Tracker (Windows).bat` or directly from Command Prompt |
| `run_scheduled.sh` | Mac/Linux: cron/launchd-friendly wrapper: seeds if needed, runs everything, logs to `logs/` instead of showing a progress bar — meant to run on its own on a schedule, unattended. No Windows counterpart yet — wire `run_week.bat` directly into Task Scheduler instead |
| `googledoc_autoformat_extension/Code.gs` | Same manual formatting as `format_entry.py`, as a Google Docs Apps Script menu — standalone, no dependency on anything else in this project |
| `input/notes/SOURCES.md` | Full source inventory + feasibility notes |
| `input/notes/NOTES.md` | Running log of decisions/assumptions/bugs found during development |
| `input/notes/US_OFFICIALS_CHINESE_NAMES.md` | Sourced reference for `KNOWN_NAME_ROMANIZATIONS` in `code/scraper.py` — which Chinese name maps to which US official's real English spelling, so the translator doesn't guess |
| `input/notes/sample_qa.txt` | Example transcript input for `format_entry.py` |
| `input/source_links/` | The original source-list doc this project was built from |
| `input/past_trackers/` | Historical tracker documents, used to check the scraper's work against known-correct entries |
| `output/` | Everything the pipeline generates: the dedup database, the output doc, cost logs, the review-flag list, the X account cache. Nothing in here is source code — safe to delete `tracker.db` and re-seed, or delete the rest, without touching how the scraper works |

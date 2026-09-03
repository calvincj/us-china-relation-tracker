# US-China Relations Tracker — automated scraper

This tool checks US and Chinese government websites (and some X/Twitter
accounts) every week for US-China-relevant news, and writes up new
entries in a Word document, in the same style as the existing tracker.

## Setup (only needs to be done once)

**Step 1.** Open Terminal (on a Mac) or Command Prompt (on Windows) in
this folder, and type this, then press Enter:

```
pip install -r requirements.txt
```

**Step 2.** Make a copy of the file named `.env.example` in this folder,
and rename the copy to `.env`.

- On a Mac, type this and press Enter:
  ```
  cp .env.example .env
  ```
- On Windows, type this and press Enter:
  ```
  copy .env.example .env
  ```

**Step 3.** Open the new `.env` file in any text editor. It has a spot
for each API key, with a link showing where to get it. Get a key from
https://aistudio.google.com/apikey and paste it in after
`GEMINI_API_KEY=` — this one is required, the tool won't run at all
without it. If you also want it to check X/Twitter accounts, get a key
from https://developer.x.com/ too and paste it in after `X_API_KEY=` —
without it, everything else still works, it just skips X. The rest of
the keys in the file are optional backups — read the notes inside the
file for what each one is for.

**Step 4.** Type this and press Enter:

```
python code/seed_dedup_db.py
```

This tells the tool about everything already covered in the past
tracker documents, so it won't repeat old news the first time it runs.

Setup is done. You won't need to repeat any of this again.

## Running it each week

### If you're on a Mac

1. Double-click **Run Weekly Tracker (Mac).app** in this folder.
2. A window opens and asks a question. Just press Enter to run last
   week's report — that's the normal, correct choice almost every time.
3. Wait. This can take anywhere from a few minutes to over an hour,
   depending on how much news there is that week. This is normal.
4. When it finishes, it tells you where the file was saved, and the
   Word document opens automatically.
5. Press any key to close the window.

The first time you open the app, macOS may show a warning that it's from
an "unidentified developer." If that happens: right-click the app,
choose **Open**, then click **Open** again to confirm. You only need to
do this once — it won't ask again after that.

### If you're on Windows

1. Double-click **Run Weekly Tracker (Windows).bat** in this folder.
2. A window opens and asks a question. Just press Enter to run last
   week's report — that's the normal, correct choice almost every time.
3. Wait. This can take anywhere from a few minutes to over an hour,
   depending on how much news there is that week. This is normal.
4. When it finishes, it tells you where the file was saved. Open the
   `output` folder in this project and double-click that file to read it
   (unlike on a Mac, it doesn't open automatically on Windows).
5. Press any key to close the window.

### Running a specific week instead of last week

If you ever need to redo a specific week, or catch up after time away:
when asked the question in step 2 above, type `2` and press Enter
instead. It will then ask for a start date and an end date. Type them as
year-month-day with no spaces or dashes — for example, August 4, 2026 is
`20260804`.

## What you'll see when it's done

A finished run ends with a short summary like this:

```
Done — 9 new entries added for Aug 25-31, 2026.
Saved to: output/US-China Tracker Aug 25-31, 2026.docx
Took 16m 7s — 14,320 tokens, est. cost $0.0187.
```

Right below that, it tells you if anything went wrong — for example, if
one of the websites it checks happened to be down that day:

```
1 source(s) had errors this run:
  - State Council Information Office: 2 error(s)
```

If everything worked, it just says `No source errors this run.`

Every run also ends with a reminder that Truth Social, YouTube, and the
Dept of War website are not covered by this tool at all (see below for
why) — worth checking those yourself by hand if a story from one of them
might matter that week.

## What this tool covers and doesn't cover

See `input/notes/SOURCES.md` for the complete list of every source this
tool checks, and which ones it doesn't.

It does **not** check Truth Social, YouTube, or the Dept of War website
(war.gov). Truth Social and YouTube were never built. The Dept of War
website actively blocks this kind of tool from reading it, and there was
no reliable substitute — see `input/notes/SOURCES.md` for the details.

## Adding an entry by hand

If you have a transcript or press release from a source this tool
doesn't cover, you can format it into the same tracker style yourself:

```
python code/format_entry.py input/notes/sample_qa.txt --out output/tracker_output.docx
```

(`input/notes/sample_qa.txt` in that example is just a sample file to
try it on — replace it with your own file.)

If you keep the tracker as a Google Doc instead of a Word file,
`googledoc_autoformat_extension/Code.gs` does the same formatting job
from inside Google Docs (Extensions → Apps Script → paste it in). It's
completely separate from everything else in this project.

## More technical details

Everything below this point is for whoever maintains or edits this
tool's code — not needed for running it week to week.

A full run can take a while because of how fast the AI service it uses
will accept requests. This is expected and not a sign anything is wrong.

| File/folder | Purpose |
|---|---|
| `code/scraper.py` | Main program — one function per source it checks |
| `code/backtest.py` | Checks the program's work against a real past tracker week (used for development, not normal use) |
| `code/test_scraper.py` | Automated tests for the main program — run with `python code/test_scraper.py` |
| `code/test_format_entry.py` | Automated tests for the manual add-an-entry tool — run with `python code/test_format_entry.py` |
| `code/seed_dedup_db.py` | The one-time setup script from Step 4 above |
| `code/format_entry.py` | The manual add-an-entry tool from above |
| `Run Weekly Tracker (Mac).app` | The Mac icon to double-click |
| `Run Weekly Tracker (Mac).command` | What the `.app` runs underneath — works fine double-clicked directly too |
| `Run Weekly Tracker (Windows).bat` | The Windows file to double-click |
| `run_week.sh` / `run_week.bat` | What the double-click launchers run underneath, for anyone who prefers typing the command directly in Terminal/Command Prompt |
| `run_scheduled.sh` | For running this automatically on a schedule on a Mac, with no one watching (see comments inside the file) |
| `input/notes/SOURCES.md` | Full list of every source checked, and every source considered but not used, with reasons |
| `input/notes/NOTES.md` | A running log of decisions and bugs found during development |
| `input/notes/US_OFFICIALS_CHINESE_NAMES.md` | Reference list used so the tool translates Chinese names for US officials correctly |
| `input/past_trackers/` | The historical tracker documents, used to check the tool's work against known-correct entries |
| `output/` | Everything the tool creates when it runs: the finished Word documents, its memory of what it's already covered, and its logs. Nothing in here is part of the program itself |

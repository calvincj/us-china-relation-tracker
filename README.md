# US-China Relations Tracker: automated scraper

This tool checks US and Chinese government websites (and some X/Twitter
accounts) every week for US-China-relevant news, and writes up new
entries in a Word document, in the same style as the existing tracker.

## Setup (only needs to be done once)

**Step 1.** Open Terminal (on a Mac) or Command Prompt (on Windows).

Then get to this project's folder: type `cd` followed by one space,
then drag this project's folder (the one this README is in) from
Finder or File Explorer into the Terminal/Command Prompt window. It
will automatically fill in the correct path for you. Press Enter.

**Step 2.** Type this, then press Enter:

```
pip install -r scripts/requirements.txt
```

**Step 3.** Make a copy of the file named `.env.example` in this folder,
and rename the copy to `.env`.

- On a Mac, type this and press Enter:
  ```
  cp .env.example .env
  ```
- On Windows, type this and press Enter:
  ```
  copy .env.example .env
  ```

**Step 4.** Open the new `.env` file in any text editor. It has a spot
for each API key, with a link showing where to get it. Get a key from
https://aistudio.google.com/apikey and paste it in after
`GEMINI_API_KEY=`. This one is required; the tool won't run at all
without it. If you also want it to check X/Twitter accounts, get a key
from https://developer.x.com/ too and paste it in after `X_API_KEY=`.
Without it, everything else still works, it just skips X. The rest of
the keys in the file are optional backups; read the notes inside the
file for what each one is for.

**Step 5.** Type this and press Enter:

```
python code/seed_dedup_db.py
```

This tells the tool about everything already covered in the past
tracker documents, so it won't repeat old news the first time it runs.

**Step 6 (optional, but recommended).** Type this and press Enter:

```
python code/scraper.py --check
```

This confirms your `.env` key actually works, in a few seconds, before
you commit to a real run that takes 10-15 minutes and costs real money.
If it says your setup looks good, you're ready. If something's wrong,
it'll tell you specifically what (a missing key, a rate limit, etc.)
instead of you finding out partway through a real run.

Setup is done. You won't need to repeat any of this again.

## Running it each week

### If you're on a Mac

1. Double-click **Run Weekly Tracker (Mac).app** in this folder.
2. A window opens and asks a question. Just press Enter to run last
   week's report. That's the normal, correct choice almost every time.
3. Wait. A normal run usually takes about 10 to 15 minutes. This is
   normal, even if nothing seems to be happening on screen.
4. When it finishes, it tells you where the file was saved, and the
   Word document opens automatically.
5. Press any key to close the window.

If you ever need to stop a run early, click into the window and press
Control+C.

The first time you open the app, macOS may show a warning that it's from
an "unidentified developer." If that happens: right-click the app,
choose **Open**, then click **Open** again to confirm. You only need to
do this once; it won't ask again after that.

### If you're on Windows

1. Double-click **Run Weekly Tracker (Windows).bat** in this folder.
2. A window opens and asks a question. Just press Enter to run last
   week's report. That's the normal, correct choice almost every time.
3. Wait. A normal run usually takes about 10 to 15 minutes. This is
   normal, even if nothing seems to be happening on screen.
4. When it finishes, it tells you where the file was saved. Open the
   `output` folder in this project and double-click that file to read it
   (unlike on a Mac, it doesn't open automatically on Windows).
5. Press any key to close the window.

If you ever need to stop a run early, click into the window and press
Control+C.

### Running a specific week instead of last week

If you ever need to redo a specific week, or catch up after time away:
when asked the question in step 2 above, type `2` and press Enter
instead. It will then ask for a start date and an end date. Type them as
year-month-day with no spaces or dashes; for example, August 4, 2026 is
`20260804`. If you type something that isn't a real date, or an end date
that's in the future, it will tell you and ask you to enter it again.

Running the same week more than once is safe. The finished document
always contains everything found for that whole week, not just whatever
was new since the last time you ran it, so re-running a week you've
already done (or one that overlaps a previous run) won't leave anything
out or duplicate anything.

## What you'll see when it's done

A finished run ends with a short summary like this:

```
Done: 9 new entries added for Aug 25-31, 2026.
Saved to: output/US-China Tracker Aug 25-31, 2026.docx
Took 13m 51s: 228,145 tokens + 15 X reads, est. cost $0.26.
```

Right below that, it tells you if anything went wrong; for example, if
one of the websites it checks happened to be down that day:

```
1 source(s) had errors this run:
  - State Council Information Office: 2 error(s)
      [scio] Failed to fetch list (likely cause: the website took too long to respond)
```

Each error line includes a plain-language guess at what actually
happened (a rate limit, a dead page, a network problem), not just the
raw technical detail. If everything worked, it just says `No source
errors this run.`

If a run's cost ever unexpectedly runs away (a real bug, not normal
behavior), it stops itself automatically once spending crosses $5 and
tells you so — everything found up to that point is still saved.

Every run also ends with a reminder that Truth Social, YouTube, and the
Dept of War website are not covered by this tool at all (see below for
why); worth checking those yourself by hand if a story from one of them
might matter that week.

## What this tool covers and doesn't cover

See `input/notes/SOURCES.md` for the complete list of every source this
tool checks, and which ones it doesn't.

It does **not** check Truth Social, YouTube, or the Dept of War website
(war.gov):

- Truth Social was never built.
- YouTube was never built either. There's a newer AI feature that might
  make this realistic now (it wasn't when this was last looked at); see
  `input/notes/SOURCES.md` for details if this becomes a priority.
- The Dept of War website actively blocks this kind of tool from
  reading it, and there was no reliable substitute found; see
  `input/notes/SOURCES.md` for the full investigation.

## Adding an entry by hand

If you have a transcript or press release from a source this tool
doesn't cover, you can format it into the same tracker style yourself:

```
python code/format_entry.py input/notes/sample_qa.txt --out output/tracker_output.docx
```

(`input/notes/sample_qa.txt` in that example is just a sample file to
try it on; replace it with your own file.)

If you keep the tracker as a Google Doc instead of a Word file,
`googledoc_autoformat_extension/Code.gs` does the same formatting job
from inside Google Docs (Extensions → Apps Script → paste it in). It's
completely separate from everything else in this project.

## More technical details

Everything below this point is for whoever maintains or edits this
tool's code, not needed for running it week to week.

A normal run takes about 10 to 15 minutes (measured across several real
runs). It could take longer on a week with an unusual amount of news,
since the AI service it uses only accepts requests at a limited rate.

Everything in this folder is organized so the only things at the top
level are the 3 double-click launchers, `README.md`, and `.env`/
`.env.example`. Everything else lives in one of these subfolders:

| File/folder | Purpose |
|---|---|
| `Run Weekly Tracker (Mac).app` | The Mac icon to double-click |
| `Run Weekly Tracker (Mac).command` | What the `.app` runs underneath; works fine double-clicked directly too |
| `Run Weekly Tracker (Windows).bat` | The Windows file to double-click; just launches the PowerShell script in `scripts/` |
| `code/scraper.py` | Main program: one function per source it checks |
| `code/backtest.py` | Checks the program's work against a real past tracker week (used for development, not normal use) |
| `code/test_scraper.py` | Automated tests for the main program; run with `python code/test_scraper.py` |
| `code/test_format_entry.py` | Automated tests for the manual add-an-entry tool; run with `python code/test_format_entry.py` |
| `code/seed_dedup_db.py` | The one-time setup script from Step 5 above |
| `code/format_entry.py` | The manual add-an-entry tool from above |
| `scripts/requirements.txt` | The dependency list from Step 2 above |
| `scripts/run_weekly_tracker_windows.ps1` | The actual questions/date-validation logic for Windows (written in PowerShell, not batch, for reliable calendar-date checking) |
| `scripts/run_week.sh` / `scripts/run_week.bat` | What the double-click launchers run underneath, for anyone who prefers typing the command directly in Terminal/Command Prompt |
| `scripts/run_scheduled.sh` | For running this automatically on a schedule on a Mac, with no one watching (see comments inside the file) |
| `input/notes/SOURCES.md` | Full list of every source checked, and every source considered but not used, with reasons |
| `input/notes/NOTES.md` | A running log of decisions and bugs found during development |
| `input/notes/US_OFFICIALS_CHINESE_NAMES.md` | Reference list used so the tool translates Chinese names for US officials correctly |
| `input/notes/sample_qa.txt` | Sample file for the "Adding an entry by hand" section above |
| `input/past_trackers/` | The historical tracker documents, used to check the tool's work against known-correct entries |
| `output/` | Everything the tool creates when it runs: the finished Word documents and its memory of what it's already covered. Nothing in here is part of the program itself |
| `logs/` | A timestamped log file from every run, in case something needs troubleshooting later |
| `assets/` | The icon used by the Mac app |
| `googledoc_autoformat_extension/` | The separate Google Docs version mentioned above |

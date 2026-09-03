# Autonomous work log — US-China Relations Tracker scraper

Started: 2026-08-04. Working autonomously per instructions; logging every
assumption/decision here instead of stopping to ask.

## 0. State found at start of this session

The repo already contained a substantial implementation from a prior session
(files dated mid/late June 2026, 2 git commits): `scraper.py`,
`format_entry.py`, `apps-script/Code.gs`, `requirements.txt`, `sample_qa.txt`,
`tracker_output.docx`. It covers 8 sources (FMPRC EN conf + remarks, MOFCOM EN,
State, White House, Treasury, USTR, war.gov/DoD) with Gemini-based
translation/summarization/Q&A-parsing and sqlite dedup.

Gaps found against the task brief, addressed below in order:

1. **Inline hyperlink-in-summary was completely missing.** The target format
   (confirmed by inspecting `past-trackers/U.S.-China Relations Tracker
   06.23.26 - Present.docx` XML) hyperlinks exactly one verb/phrase inside the
   plain-text summary sentence (e.g. "Foreign Ministry Spokesperson Lin Jian
   **addressed** reporters' questions on...") to the original source URL,
   styled `#1155CC` + single underline (Google-Docs-default link style),
   Times New Roman 12pt like the rest of the doc. `add_qa_entry`/
   `add_release_entry` in `scraper.py` wrote the summary as flat unlinked
   text. **Fixed** — see `add_hyperlink()`, the new `link_anchor` field
   returned by `generate_summary()`, and updated `add_qa_entry`/
   `add_release_entry` signatures (now take `url`).
2. **No dedup against past trackers.** `tracker.db` starts empty, so a first
   run would re-scrape/duplicate everything already sitting in
   `past-trackers/*.docx` and the in-progress `tracker_output.docx`. **Fixed**
   — added `seed_dedup_db.py` which walks every hyperlink target URL in those
   docs and inserts it into `seen_urls` before the first live run.
3. **Source inventory incomplete.** The links doc lists ~30 sources; the
   scraper only implements the 8 that are plain static-HTML/RSS/JSON gov
   pages. See `SOURCES.md` for the full inventory + feasibility tier. Not
   all gaps are closeable (see below).
4. **Chinese-only PRC pages not covered**: MFA leadership speeches/activity,
   MOFCOM Chinese press pages (weekly conf, daily spokesperson Chinese,
   leadership activity, special press conferences, daily news release),
   State Council (SCIO) press announcements, Ministry of National Defense
   (mod.gov.cn) weekly press conference. These are all static HTML + CJK,
   same pattern as the existing `scrape_fmprc`. Adding as many as time
   allows — tracked in SOURCES.md status column.
5. **X/Twitter, TruthSocial, WeChat, YouTube — out of scope for automation.**
   Per the brief's own expectation. X's API is paid-tier and login-walled for
   scraping; TruthSocial requires an authenticated/JS session; WeChat
   official-account content isn't publicly listable without an unofficial
   article-index mirror; YouTube would need transcript scraping of a channel
   with no reliable China-relevance pre-filter. **Decision: skip all four,
   documented in SOURCES.md and as a code comment block in scraper.py.**
   Per instructions, noting **RollCall Factbase**
   (https://www.rollcall.com/factbase/trump/) as the standing alternative
   mirror for Trump's Truth Social posts — it republishes his posts with
   timestamps and is plain static HTML, so it's a viable future source if
   this becomes a priority; not wired up yet (would still need a
   relevance/summary pass same as other sources).

## Assumptions made without asking

- Treating `tracker_output.docx` as a scratch/dev file, not the canonical
  live tracker doc (the real one presumably lives in Google Docs, per the
  Apps Script tool). Local `.docx` output is for review before copy/paste or
  before wiring an actual Google Docs API push.
- `apps-script/Code.gs` (the manual paste-formatter for Google Docs) is a
  different, deliberately-manual tool (Step in the brief is about the
  *scraper* pipeline). Did not add URL-hyperlinking there since manual pastes
  don't carry a source URL in scope automatically — flagging as a possible
  future enhancement (add an optional URL prompt) rather than doing it now.
- Kept Gemini 2.5 Flash / Groq llama-3.3-70b as the LLM backends already
  configured (valid API keys present in `.env`) rather than switching models.
- "Daily run only returns new news since last entry" implemented via the
  existing `tracker.db` seen-URL table (now seeded from past trackers), not
  by diffing docx content — this matches the existing architecture and is
  more robust than text-diffing Word docs.

## MOFCOM's other 4 Chinese index pages added (2026-08-05)

Per user request ("build" the MOFCOM daily-news-release module, "keep on
improving... getting all the news/press releases/statements present in
past trackers"). Checked each remaining MOFCOM `xwfb/*` Chinese index page
(`ldrhd` leadership activity, `bldhd` dept. leadership activity, `ztxwfbh`
special press conferences, `sjfzrfb` bureau/dept head announcements) —
all run the identical JS-CMS API-gateway pattern already reverse-engineered
for `rcxwfb`, just a different `pageId`. Generalized into
`_MOFCOM_SECTION_PAGE_IDS` + `scrape_mofcom_section()`, with 5 thin
per-section wrappers (`mofcom_daily`/`mofcom_leadership`/
`mofcom_dept_leadership`/`mofcom_bureau_heads`/`mofcom_special_conf`), all
reusing `process_mofcom_item()` entirely — this was purely a list-discovery
gap, not a parsing one. `ztxwfbh` came back genuinely empty when checked
live (valid — nothing published there recently — not a bug).

Live-verified `mofcom_daily`: correctly recovered and correctly classified
(as "release", matching ground truth) the exact "China's Position on the
Issue of So-called 'Overcapacity'" position paper that motivated adding
this source, preserving its full multi-section structure — plus a second,
previously-unseen entry (China-Vanuatu trade agreement negotiations).

Also attempted the Chinese-language State Council page
(`www.scio.gov.cn/xwfb/bwxwfb/`) — blocked: the entire `www.scio.gov.cn`
domain (not just this path) is currently returning HTTP 521 (Cloudflare:
origin down), on both HTTP and HTTPS, with or without cert verification.
`english.scio.gov.cn` (already covered) is unaffected, so this looks like
site-side downtime on the Chinese domain specifically rather than a
permanent block — worth retrying later, not implemented this session.

## Groq retired llama-3.3-70b-versatile (found 2026-08-05)

Coming back to this the next day: Gemini's daily quota had reset (confirmed
working again), but Groq calls started failing with **404 "model does not
exist"** — a different failure signature than the 429s from the day before.
Checked `client.models.list()` live: `llama-3.3-70b-versatile` is gone from
this account's available models entirely (Groq retired it, or a plan
change dropped access — either way, no amount of waiting fixes a 404 the
way it fixes a 429). Picked `openai/gpt-oss-120b` from what's currently
available (also tried `qwen/qwen3.8-27b`, which gave a good Chinese
translation too but is much smaller — went with the largest general-
purpose model available since our tasks span translation, summarization,
relevance classification, and structured JSON). Added a `GROQ_MODEL`
constant instead of the hardcoded string in two places, verified both the
plain-text (`_call_groq`) and structured-JSON (`_call_groq_json`) paths
against it directly. **If Groq starts failing again, check whether it's a
404 (model retired — check `models.list()` again) vs. a 429 (just the
daily quota, wait it out) before assuming the same fix applies.**

## Bug #6 (big one) — Groq's new model silently returned empty translations under its own reasoning-token budget

Re-ran the week-1 backtest with all prior fixes + the 5 new MOFCOM sources
in place: `queued` went from 1 to 8 (of 21 in-scope), `kind_match` 7/8. Dug
into the remaining 13 "not queued" cases — several were on textbook,
obviously-relevant content (He Lifeng's video call with **Treasury
Secretary Bessent** and **USTR Greer**; State/Treasury sanctioning six
Chinese companies over Iranian oil; a UFLPA entity-list addition; a White
House fact sheet on China's voter-data collection) — too clearly on-topic
to be `classify_relevance` correctly saying no.

Traced one (the He Lifeng/Bessent call) all the way down: `translate_to_
english()` was returning **only the page's title and breadcrumb nav**,
dropping the entire substantive paragraph, with no error raised. Root
cause: `GROQ_MODEL` (`openai/gpt-oss-120b`, picked earlier today after Groq
retired the previous model) is a **reasoning model** — it spends
completion tokens on an invisible chain-of-thought before the visible
answer. Confirmed directly via the API's own usage breakdown: a one-
sentence translation spent **290 of a 600-token budget on reasoning alone**,
hit `finish_reason: "length"` before emitting any visible text, and
`_call_groq()` returned that empty string as if it were a valid answer —
no exception, no warning, just silently wrong. Given the backtest run was
hitting Gemini's daily cap and falling back to Groq on nearly every call,
this one bug plausibly explains most of the 13 "not queued" results, not
just the one that got traced — **not a `classify_relevance`-strictness
problem after all, at least not primarily.**

Fixed in `_call_groq()`/`_call_groq_json()`: `reasoning_effort="low"` (cuts
the reasoning overhead for what are fundamentally straightforward
transform tasks — translate/extract/summarize — that don't need heavy
deliberation) plus `max_tokens` raised 600→4000 / 800→4000 for headroom,
and — the actually load-bearing part — **an empty response now raises
instead of returning `""`**, so a future exhaustion (a longer document,
a different model swap) fails loudly and gets retried next run instead of
silently producing a hollow translation that then fails every downstream
check for reasons that look like a relevance judgment but aren't.

Bonus, smaller fix same investigation: Groq's transliteration of recurring
Chinese-official names was imprecise ("Bessenet"/"Gill" for Bessent/Greer).
Added `KNOWN_NAME_ROMANIZATIONS`, injected into `translate_to_english()`'s
prompt only for names actually present in a given chunk (keeps the prompt
lean) — verified fixes the exact case above.

Re-ran the full backtest after the fix: **queued jumped from 8 → 13 of 21
in-scope entries (62%)**, `kind_match` 12/13 — confirming this was indeed
the dominant cause, not `classify_relevance` strictness.

## Bug #7 — the reasoning-token fix's OWN max_tokens bump broke a different Groq limit

Digging into the still-not-queued cases from that run: the "overcapacity"
position paper (the very entry that motivated building `mofcom_daily`) had
gone from correctly-queued (verified earlier) back to failing — this time
with a **413 "Request too large"**: `tokens per minute (TPM): Limit 8000,
Requested 8143`. Cause: fixing bug #6 by raising `max_tokens` 600→4000
made total requests (prompt + reserved completion) big enough to blow
Groq's per-minute token cap on this account tier, for long documents
specifically (this position paper is the longest content hit all session).
One fix surfaced the next limit down.

Fixed with `_call_groq_with_retry()`: prompt capped at 4000 chars (down
from the original 9000 — needed room under 8000 TPM alongside a reserved
completion budget), `max_tokens` dropped to 2000 (still enough per direct
testing to survive reasoning overhead and produce a real answer), and a
retry-once-at-1500-chars on an actual 413 as a safety net rather than just
failing the item. Also fixed a subtler bug this surfaced:
`_call_groq_json()` was truncating the FULL already-combined prompt
(content + "respond in this JSON schema" instructions appended at the
end) from the front — for a long `prompt`, that risked truncating away
the part that tells the model to answer in JSON at all. Restructured so
the schema-instructions suffix is appended AFTER truncating just the
content, always surviving intact.

Re-verified the exact 413 case directly: now queues successfully, still
correctly typed "release". Re-ran the full backtest: **queued 13→15 of 21
(71%)**, `kind_match` 14/15.

## Bug #8 — the truncation-window fix and the TPM-limit fix collided with each other

Investigated the 3 still-not-queued non-infra cases (the other 3 of 6 are
the known external blockers: scio's 521 outage ×2, war.gov's Akamai
block). Found the SAME root cause as bug #7's setup, one layer up:
`classify_relevance`/`extract_key_paragraphs` were being called with a
pre-truncated `plain[:2500]` at 2 call sites — so even the FREE keyword
pre-filter never saw content past character 2500. Confirmed live: a real
Treasury sanctions release only names the actual Chinese/Hong-Kong-based
shipping companies at character ~4300 (deep into Iran-sanctions
boilerplate). Fixed by passing the FULL text at both call sites and adding
`_relevance_snippet()` — a windowing helper that centers the LLM-facing
snippet on wherever a real China-specific mention actually is, rather than
just the first N characters.

That fix's first version anchored on the first `US_SOURCE_RELEVANCE_
KEYWORDS` match — which, for this same document, is the generic word
"Sanctions" at character 19 ("OFAC **Sanctions** Illicit Maritime..."),
long before the real China mention — so it still returned a
beginning-of-document prefix and missed the point entirely. Fixed with a
narrower `_CHINA_MENTION_RE` (`China\w*`/`Chinese`/`Beijing`/`Xi Jinping`
only) used to pick the anchor, falling back to the broader keyword only if
no direct China mention exists.

**Then, testing that fix live, hit a THIRD layered problem**: the
now-correctly-windowed snippet (sized up to 5000 chars for
`extract_key_paragraphs`) plus its instruction text could exceed 4000
characters — which is exactly `_call_groq`'s own prompt-truncation cap from
bug #7's fix. Once a call fell back to Groq, `_call_groq` re-truncated the
ALREADY-correctly-centered snippet from the front, cutting the China
mention right back out — one fix's output silently violating another
fix's input assumption. Fixed by shrinking `_relevance_snippet`'s default
to 3000 chars (comfortably under `_call_groq`'s 4000-char cap alongside
~300-500 chars of instruction overhead) and removing `extract_key_
paragraphs`'s own `max_chars=5000` override.

Re-verified live end-to-end: the Treasury sanctions release (the exact
case that surfaced all three layers) now correctly queues. Its
**companion** State Department release on the same action does NOT queue —
checked directly and this looks like a genuine, defensible borderline call
rather than a bug: State's version only says the sanctioned vessels
transported oil "to China and the United Arab Emirates" (China as one of
two destinations, no named Chinese entity), while Treasury's version
separately names the actual China-based/Hong-Kong-based shipping
companies. The past tracker includes both with independent summaries;
`classify_relevance`'s "must name China or a Chinese entity, not just
mention it in passing" bar reasonably rejects the thinner of the two.
Left as a documented edge case rather than loosened further, since the
same document pairs recur (a Treasury designation naming entities +
a State Department statement announcing the same action more briefly) and
recovering the Treasury side already captures the substance.

Also noted, not yet fixed: the Treasury entry's generated summary
("Secretary Bessent designated two firms tied to an IRGC-backed maritime
insurance scheme...") is accurate but frames the entry around the
Iran-sanctions angle rather than the China angle that's the actual reason
it belongs in a US-China tracker (ground truth's own summary leads with
"sanctioning six Chinese companies..."). `generate_summary()` gets the
FULL text, not the China-centered window, so on a multi-topic release it
can reasonably summarize the DOMINANT topic instead of the reason-for-
inclusion. Worth passing the relevance window (or an explicit "focus on
the China angle" instruction) into `generate_summary()` for release-type
entries — not done this session, flagging for next time.

Backtest history for this same week, tracked across every fix this
session: **0 → 1 → 8 → 13 → 15 of 21 in-scope entries recovered (71%)**,
plus the 3 remaining gaps are external/infra (2 site outages, 1 network
block) or a defensible judgment call, not bugs.

**One more re-run after that (v6) dropped to 2/21 — this is quota
exhaustion, not a regression.** Confirmed from the log: `openai/gpt-oss-
120b`'s daily cap turns out to be 200,000 tokens/day (not unlimited just
because it's larger than Gemini's 20 requests/day), and today's repeated
backtest runs plus all the individual debugging calls used up ~199,900 of
it. Every failure in that run is a 429 quoting `Used 198xxx-199xxx,
Limit 200000`, not a content-judgment rejection. Both Gemini (20 req/day)
and now Groq (200k tokens/day) are exhausted for the rest of today as of
this writing. The 15/21 (71%) figure from the run just before this one —
plus the Treasury fix verified individually afterward, which that run
predates — is the real current state; re-run the backtest fresh tomorrow
(or after upgrading either key off its free tier) to confirm it holds
without hand-verifying each case.

## Keyword pre-filter added (2026-08-04, per user feedback)

User feedback: "you don't have to use llm for everything, sometimes
keywords also help. just make sure 美元 doesn't necessarily imply US."
Directly addresses today's quota-exhaustion problem — most items on any
list page have nothing to do with China/US relations at all, and don't
need an LLM call to establish that.

- Added `US_SOURCE_RELEVANCE_KEYWORDS` (English: `RELEVANCE_KEYWORDS` plus
  explicit `China\w*`/`Beijing`/`Xi Jinping` tokens — the original list had
  no bare China-mention term, since it was designed to find the US side
  *within* inherently-China-focused FMPRC/MOFCOM content, not to screen
  US-originated press releases) and wired it into `classify_relevance()`
  itself as a free first check — every one of its 8 call sites (mofcom,
  scio, state, whitehouse, treasury, ustr, wardept, mfa_leadership) now
  skips the LLM call entirely when no keyword is present.
- Added `CHINESE_RELEVANCE_KEYWORDS` for the Chinese-translation paths
  (`fmprc`'s CJK branch, `mfa_leadership`, `mnd`'s non-bilingual fallback)
  so a raw Chinese page can be skipped before ever paying for a translation
  call, not just before the classification call.
- **Caught exactly the bug the feedback warned about, twice, while building
  it**: my first draft of `CHINESE_RELEVANCE_KEYWORDS` included bare
  `人民币` ("RMB/yuan") as a "finance/currency" keyword, and the English
  `RELEVANCE_KEYWORDS` already had bare `yuan`/`RMB`/`currency` — all of
  which show up on nearly *any* Chinese/English economic-statistics release
  as the unit a dollar figure is quoted in (e.g. "5.5万亿元人民币，约合8100亿美元"),
  regardless of subject. Caught it with a test case matching that exact
  shape before it shipped (`中国海洋经济...约合8100亿美元` — confirmed does NOT
  trigger the Chinese list; `China's GDP reached 18 trillion yuan...`
  — English list correctly still triggers on "China" but that's fine, the
  pre-filter's job is cheap recall not precision, the LLM still makes the
  final call). Removed bare `人民币`/`yuan`/`RMB`/`currency` from both lists,
  kept only the actual policy-relevance phrases (`汇率操纵`/"currency
  manipulation", `贸易逆差`/`贸易顺差`/"trade deficit"/"trade surplus").
- Live-verified: re-ran `mfa_leadership_activity` (same batch that had
  errored out on quota earlier) — 8 of the first 9 items were skipped with
  zero LLM calls logged, only the ones with an actual keyword hit went on
  to spend a translation call. Exactly the intended effect.
- Design note for future sources: this pre-filter intentionally errs toward
  recall (let borderline text through to the LLM) rather than precision
  (aggressively reject) — false negatives here permanently lose an item for
  free, false positives just cost one extra LLM call that the strict
  `classify_relevance` prompt will still correctly reject. Keep that
  asymmetry in mind before adding more keywords.

## Format fix + backtesting harness (2026-08-04, per user feedback)

User feedback: (1) date headings were repeating once per entry instead of
once per day, (2) asked whether pure statement/document releases (no
reporter Q&A) are handled correctly, and (3) asked for a real backtest —
run the scraper against a past week, diff against the known-correct past
tracker for that week, repeat for a few more weeks, and use the findings to
improve the scraper.

### Fix 1 — date heading appearing once per day, not once per entry

Confirmed against the past tracker's raw paragraphs that the SAME date
heading is never repeated back-to-back — multiple same-day entries sit
under one heading with no blank paragraph between them (spacing comes
entirely from each paragraph's own 8pt `space_after`, not a literal blank
paragraph, which the old code was also inserting).

Fixed by deferring all writes: `add_qa_entry`/`add_release_entry` split into
heading+body wrappers (`add_qa_entry_body`/`add_release_entry_body`, no
heading, no blank separator) plus a new `queue_entry()`/`PENDING_ENTRIES`/
`flush_pending_entries()` buffer. Every `scrape_*` function now queues
entries instead of writing straight to `doc`; `main()` flushes (sorts by
date, writes one heading per date, collapsing repeats via a module-level
"last date written" that persists across flushes) after each source
finishes, rather than after every single item. Trade-off documented inline:
this bounds crash-recovery loss to one source's pending items instead of
one item, and does NOT fully re-interleave different sources' entries into
one global chronological order (each source's own entries land correctly
grouped/sorted, but source A's block can still precede source B's even if
B's dates are earlier) — full global ordering would mean deferring every
write to the very end of the whole run, losing ALL progress on a kill
instead of one source's worth, not a good trade for a run that already
hits per-item errors routinely (mostly LLM quota, see below).
`format_entry.py` is unaffected — it still uses the (unchanged) `add_qa_entry`/
`add_release_entry` heading+body wrappers directly, since it's always
adding exactly one entry, not a batch.

Verified offline (no LLM cost): queued 2 same-day entries + 1 different-day
entry out of order, flushed, confirmed exactly 2 date headings in the
output with the right entries grouped under each.

### Fix 2 — content type (Q&A vs release) is a property of the page, not the source

Checked the past trackers directly and found both directions of the
"sources default to one content shape" assumption breaking: a MOFCOM
"position paper" release with ~10 "Section N.M (topic): text" paragraphs
and NO reporter Q&A at all (FMPRC/MOFCOM/MND were hardcoded to always parse
as Q&A), and conversely an SCIO press conference quoting 4 different
officials (Yan Dong, Lin Weilong, Han Yong, He Shaojun) with each rendered
as a plain bold-name-attributed excerpt, not a "Q:"/"A:" exchange (SCIO/
State/etc. were hardcoded to always extract as a release).

Added `content_type_from_paragraphs()`/`content_type_from_exchanges()`: 2+
labeled ("Name: text") paragraphs is Q&A only if at least one label looks
like it's ASKING (a generic term — reporter/press/question/journalist/
interviewer — or a wire-service/outlet-shaped label, "Times"/"Daily"/
"Agency"/etc. or a known abbreviation like AFP/Reuters/CCTV), not just
quoting several different named officials. `finalize_qa_item()`/
`finalize_release_item()` are the shared tails every `scrape_*` function
now calls, which re-check this and reroute (`exchanges_to_paragraphs()`
flattens a Q&A parse back into plain paragraphs when it turns out to
actually be a release, and vice versa `finalize_release_item()` builds
exchanges via the LLM classifier when raw release-sourced text turns out
to be a real Q&A). This was also a nice DRY cleanup — 8 near-duplicate
scrape function tails collapsed into 2 shared functions
(`finalize_qa_item`/`finalize_release_item`, plus `process_release_common`
for the classify_relevance-gated release sources).

### The backtesting harness (`backtest.py`) and what it found

`backtest.py` extracts every entry in a date range from a past tracker
(date, summary, source URL, and — read directly from the docx's run-level
bold+italic formatting, which is `add_qa_entry`'s exact "Q" speaker-label
signature and nothing else legitimately produces — whether the past
tracker rendered it Q&A-style or release-style), then re-fetches each URL
LIVE and runs it through the *exact same* `process_*_item()` function the
live scraper calls (not a re-implementation — literally the same code,
exposed by splitting each `scrape_*`'s per-item try-block into its own
`process_<source>_item()` function). Uses a throwaway in-memory sqlite
connection and only reads `PENDING_ENTRIES` after each call — never touches
the real `tracker.db`/`tracker_output.docx`.

Ran it against 2026-07-28..08-03 (this past week) against the "Present"
tracker. Ground truth: 34 entries, 13 of which are X/TruthSocial/YouTube
(confirms those really do make up a large minority of past coverage — ~38%
this week — even though they're out of scope for this scraper per
SOURCES.md). Of the 21 in-scope entries, the first pass queued **zero** —
which is itself the finding. Root causes, all fixed:

1. **FMPRC's CJK-ratio check used the raw page, not the article body.**
   FMPRC's English-mirror pages carry a language-switcher menu ("简体中文",
   "Русский", ...) whose handful of CJK characters was enough to tip a
   genuinely all-English article over the `cjk > 100` threshold, routing it
   into the Chinese-translation branch — where the Chinese keyword
   pre-filter then (correctly, given there's no real Chinese content)
   found nothing and dropped a real, already-covered article entirely
   (2026-07-28's Lin Jian/Xi-Lula phone call entry). Fixed: the CJK ratio
   is now measured on `extract_main_text()`'s output, not the raw page.
2. **`finalize_qa_item()` gave up entirely when `parse_qa()` found zero
   labeled paragraphs**, rather than trying the release path on the raw
   text. A plain document/position-paper release (no "Speaker: text"
   structure anywhere at all, e.g. the MOFCOM "Section N.M: text" position
   paper) legitimately produces zero exchanges from a Q&A-oriented parse,
   but is NOT irrelevant — it's just not Q&A-shaped. Fixed: empty exchanges
   now falls through to `extract_key_paragraphs()` on the raw text before
   giving up.
3. **The MFA leadership keyword pre-filter was too strict for what this
   source actually tracks.** Backtesting the Wang Yi/Global-Development-
   Initiative-anniversary entry (a real, already-covered entry) showed it
   has ZERO matches against the US-relevance keyword list, in Chinese or
   after translation — confirmed by pulling every mfa.gov.cn ground-truth
   entry across the full "Present" tracker: Wang Yi meeting the Iranian/
   Pakistani/Egyptian FM, Xi's CCP-105th-anniversary speech — none
   necessarily mention the US anywhere, all are tracked regardless. The
   actual editorial bar for this source is "substantive top-leadership
   diplomatic activity," not "explicitly mentions US-China relations."
   Fixed: dropped the keyword pre-filter AND the `classify_relevance()`
   gate for this source specifically, and added `extract_key_paragraphs
   (..., general=True)` — a broader extraction prompt ("most important
   paragraphs conveying substantive content, not protocol boilerplate")
   that doesn't require a US-China angle, which is now this source's only
   filter (drops pure scheduling/protocol notices, keeps everything with
   real content).
4. **A regex anchoring bug in the asker-detection itself.**
   `_ASKER_LABEL_RE.match(label)` — `.match()` anchors at position 0
   regardless of internal `^` markers, but the outlet-suffix branch
   (`times|daily|agency|...`) has no leading `^` because it's meant to
   match anywhere in the label. Net effect: "The New York Times" was never
   recognized as an outlet (it doesn't *start* with "times"), so a
   textbook FMPRC Q&A transcript (A Tarde / The New York Times / Antara
   asking, Lin Jian answering — the exact same 2026-07-28 entry from bug
   #1) was misclassified as a release by bug #2's fix. Fixed:
   `.search()` instead of `.match()`.

All four verified via stubbed-LLM structural tests (real fetch + real
parsing logic, `call_llm`/`call_llm_json`/`translate_to_english` monkey-
patched to canned values) rather than a live run, because — directly as a
result of the same afternoon's earlier testing — **both Gemini (20/day) and
Groq (100k tokens/day) free-tier quotas were fully exhausted by the time
these fixes were ready to test live** (confirmed: a bare `_call_groq("Say
OK")` 429'd). A full live re-run of this backtest is queued for whenever
quota resets:

```
python backtest.py --tracker "past-trackers/U.S.-China Relations Tracker 06.23.26 - Present.docx" \
                    --start 2026-07-28 --end 2026-08-03 --out backtest_week1.json
```

### Other weeks — ground-truth extraction only (no LLM cost, so unaffected by quota)

Ran `extract_ground_truth()` (free, offline) against two more historical
weeks to sanity-check the harness against older tracker eras and surface
anything structurally new before spending live-test budget on them:

- **Part 2 tracker, 2025-12-01..12-07** (18 entries): surfaced sources not
  currently in scope anywhere — `www.ft.com` (Financial Times, a news
  outlet, correctly out of scope), `www.news.cn` (Xinhua — a PRC state
  media outlet NOT in the current source list, worth considering),
  `us.china-embassy.gov.cn` (the Chinese Embassy's own website, distinct
  from its X account which is already correctly out of scope — also worth
  considering). Added to SOURCES.md as candidates, not implemented yet.
- **Part 3 tracker, 2026-05-01..05-07** (22 entries): same source mix as
  the current period (fmprc/mfa/mofcom/state/treasury), plus
  `daines.senate.gov` (a senator's site — one-off, not worth a dedicated
  scraper) and, again, a large YouTube/X share (8+5 of 22).
- Also confirmed `Part 2`'s actual date range is 2025-09-23..2026-02-02 (my
  first guess of March 2026 was outside its coverage — a harmless
  reminder to check a tracker's actual range before picking a backtest
  week, not a code issue).

### Bug #5 — MOFCOM's Chinese-language pages weren't handled at all (found from a real user-run backtest)

User ran the live backtest after the 4 fixes above and got `queued: 1 /
21 in-scope`. Reproducing it (quota was still mostly dead, so re-ran with
`call_llm`/`call_llm_json`/`translate_to_english` monkey-patched to
maximally permissive canned values, isolating structural/keyword-filter
behavior from real LLM-judgment strictness): 14/21 queued cleanly, 2 were
external HTTP errors unrelated to this code (a `scio.gov.cn` 521 and the
already-documented war.gov 403), and **2 MOFCOM entries were rejected even
with every LLM call maximally permissive** — a real structural bug, not an
LLM-strictness question.

Root cause: `process_mofcom_item()` only knew how to handle the English
mirror (`english.mofcom.gov.cn`, what `scrape_mofcom`'s own list-discovery
targets) — it ran the English keyword pre-filter
(`US_SOURCE_RELEVANCE_KEYWORDS`) against raw Chinese text for any
`www.mofcom.gov.cn` (Chinese-language) URL, which of course never matches
an English keyword, silently dropping it. This directly **contradicts a
documented assumption in `SOURCES.md`** — that MOFCOM's Chinese press
pages are "redundant with the English mirror already covered" — the real
past-tracker entry that surfaced this (a MOFCOM spokesperson Q&A on the US
DoD's Section 1286 sanctions list against Chinese research institutions)
was sourced directly from the Chinese page, not the English one. Fixed:
`process_mofcom_item()` now CJK-detects like `process_fmprc_item()` does,
translating + using `CHINESE_RELEVANCE_KEYWORDS` when the page turns out
to be Chinese. Also noted: MOFCOM's Chinese transcripts use generic 问/答
("Question"/"Answer") labels rather than named spokespersons, unlike
FMPRC — added "Answer" to the spokesperson set so `_build_exchanges` calls
it "A" rather than defaulting to "Q". `SOURCES.md` corrected.

Verified (with the same permissive stubs) that all 3 of this week's
Chinese-domain MOFCOM URLs now queue successfully; not yet re-verified
with real translation (still no quota) so the qa/release kind on those
specific 3 isn't trustworthy yet — the stub for `translate_to_english`
doesn't preserve the 问/答 structure, so they came back "release" via the
new empty-exchanges fallback rather than "qa"; real translation should fix
that, to be confirmed live.

**Open question for the next live run**: 14 (now 16, with MOFCOM fixed)
of 21 entries are structurally processable, but the user's real run only
queued 1 — meaning `classify_relevance()`/`extract_key_paragraphs()`'s
actual LLM judgment is rejecting most of the rest. Given the same pattern
already found and fixed once for `mfa_leadership` (a too-strict bar
mismatched against what the past tracker actually tracks), this is the
top suspect and the first thing to check once quota allows: which specific
ground-truth entries get a real "NO" from `classify_relevance` or a real
`NONE`/empty result from `extract_key_paragraphs`, and whether that bar
needs loosening the same way MFA leadership's did.

Next time quota is available: re-run the live backtest for this week to
confirm the 4 fixes actually recover the previously-missed entries
end-to-end (not just structurally), then run it against a Part-2/Part-3
week to validate against an older tracker era with different spokespersons
(Wang Wenbin/Hua Chunying/Zhao Lijian instead of Lin Jian/Mao Ning/Guo
Jiakun — already in `FMPRC_SPOKESPERSONS`, but never live-tested against
their actual old transcripts).

## Final validation pass (2026-08-04)

After all the fixes above, ran clean end-to-end tests source-by-source and
inspected the actual `tracker_output.docx` XML (not just the logs):

- **`--source mnd`** (the new bilingual MND module): 5 entries written,
  covering real China-Philippines (Zhongye Dao/South China Sea),
  China-Russia (Joint Sea 2026 exercise), and Taiwan (Lai Ching-te
  "independence" remarks) news from mid-July 2026. Confirmed in the raw
  XML: `left_indent` on every Q/A paragraph is exactly `457200` EMU (=
  0.5in, `Inches(0.5)`) — byte-for-byte the same indent value the past
  tracker uses — and every summary line has a real verb hyperlinked
  ("addressed" / "released") to the correct mod.gov.cn source URL. The two
  entries whose source page had an English half used it directly (no
  translation call); the rest correctly fell back to translating the
  Chinese. One cosmetic issue, not fixed: on a Groq-generated summary, word
  order came out "Ministry of National Defense spokesperson Chen Xi Senior
  Colonel released..." (title fragment out of order) — a natural-language
  quality wobble from the weaker fallback model, not a structural bug;
  worth a human glance same as the rest of the tracker presumably already
  gets.
- **`--source fmprc_conf`**: 2 entries, correct "addressed" → FMPRC-URL
  hyperlinks, correct Q/A structure.
- **`--source ustr`**: 0 entries across two clean runs (10 items each) —
  spot-checked by hand that the one item that looked promising (a
  forced-labor Section 301 action) genuinely never names China, so this is
  correct behavior, not a bug.
- Kicked off one full `python scraper.py` (all sources, no `--source`) run
  on top of the mnd output to produce a real first multi-source
  `tracker_output.docx`. **Result: 11 entries written, all correctly
  formatted with a real verb hyperlinked to its source** — but most sources
  wrote 0 new entries not because nothing qualified, but because **Groq's
  free tier also has a hard daily cap** (100,000 tokens/day for
  llama-3.3-70b-versatile) and it ran out mid-run (~12:40, after Gemini's
  20/day cap was already long gone from earlier testing). From that point,
  every source's LLM calls 429'd on both providers, so `mofcom`, `scio`,
  most of `mnd`, `whitehouse`, `treasury`, `ustr` (and the tail of
  `mfa_leadership_activity`) errored per-item and were **skipped, not
  written and not marked-seen** — each `scrape_*` function's per-item
  try/except catches this and moves on, so nothing broke and nothing got
  corrupted, but ~60 items that were fetched never got a chance to be
  judged relevant. Because they weren't `mark_seen`, **tomorrow's run will
  retry every one of them for free** — this is self-healing, not data loss.
  Final per-source outcome from this run:

  | Source | New items found | Written | Notes |
  |---|---|---|---|
  | fmprc_conf | 0 | 0 | already covered by earlier testing today |
  | fmprc_remarks | 5 | 3 | completed before quota ran out |
  | mfa_leadership_speeches | 10 | 2 | completed before quota ran out |
  | mfa_leadership_activity | 10 | 0 | quota ran out partway through |
  | mofcom | 10 | 0 | quota exhausted |
  | scio | 10 | 0 | quota exhausted |
  | mnd | 10 | 0 (5 from an earlier standalone test are in the doc) | quota exhausted |
  | state | 0 | 0 | — |
  | whitehouse | 18 | 0 | quota exhausted |
  | treasury | 10 | 0 | quota exhausted |
  | ustr | 10 | 0 | quota exhausted |
  | wardept | 10 | 0 | blocked at fetch (Akamai, see above) before reaching any LLM call |

  **Bottom line for whoever reads this**: the pipeline itself worked
  correctly end-to-end (confirmed via `mnd`/`fmprc_remarks`/
  `mfa_leadership_speeches` actually writing well-formatted, correctly
  hyperlinked entries) — today's numbers are low because I personally spent
  a large chunk of both providers' free daily quota on live-testing before
  this run even started, on top of the run's own real usage. **A quieter
  day should get much further.** If 12-sources'-worth of daily volume
  routinely exhausts a free Groq key, the fix is either: upgrade Groq to a
  paid tier, upgrade Gemini to a paid tier (its output quality/JSON
  reliability is better when it isn't 429ing constantly), or split the run
  across the day (e.g. `run_daily.sh` twice, morning/evening) so the token
  budget resets between halves.

## Live test results (2026-08-04)

Ran a cheap no-LLM diagnostic (fetch + parse list pages only) against every
implemented source before spending any LLM quota, then fixed what broke:

| Source | Result | Fix |
|---|---|---|
| `fmprc_conf` | ✅ 7 fresh links, incl. today's (Aug 4) entry | none needed |
| `fmprc_remarks` | ✅ 7 links | none needed |
| `mofcom` | ❌ was broken — the EN listing page migrated to a client-rendered CMS sometime after June; the static HTML has no article links anymore, just a `<script>` that calls an API-gateway endpoint. **Fixed**: found and wired up the JSON endpoint the page's own JS calls (`/api-gateway/jpaas-publish-server/front/page/build/unit`), which returns a `data.html` fragment with the real article links — no browser needed. Verified live, 15 links returned. | code fix applied |
| `state` | ⚠️ the primary WP JSON API (`/wp-json/wp/v2/press_releases`) now 404s — state.gov apparently dropped/moved that endpoint. The code's existing RSS fallback (`/rss-feed/press-releases/feed/`) still works and returned 10 items, so this source still functions end-to-end, just always via the fallback path now. Left as-is since the fallback already covers it; flagging in case the WP API 404 is worth investigating further. | none needed (fallback already covers it) |
| `whitehouse` | ✅ RSS returned 20 items | none needed |
| `treasury` | ✅ 22 links | none needed |
| `ustr` | ✅ 235 links matched (the regex matches broadly across the page, which is fine — code already slices to the first 10 unseen) | none needed |
| `wardept` | ❌ was broken from this sandbox — `war.gov/News/Releases/` (and individual article pages) return HTTP 403 "Access Denied" from Akamai, both via plain `curl`/httpx AND via headless Playwright (identical bare 403, no JS challenge to solve) — this is an IP/ASN-level block on this sandbox's outbound IP, not something any client-side fingerprint trick fixes. Found that `war.gov`'s RSS backend (`/DesktopModules/ArticleCS/RSS.ashx?ContentType=9\|11&Site=945`) is NOT behind that block and returns clean XML for both Releases (ContentType=9) and Speeches (ContentType=11 — this is where DASW Alvaro Smith's China-relations remarks live, an exact match for a past-tracker entry). **Rewrote `scrape_wardept` to use this RSS feed instead of Playwright** — removes the Playwright dependency entirely and is more robust. **Caveat**: individual article-page fetches (the actual content, not just the listing) were also 403'd from this sandbox for the same IP-reputation reason — the RSS discovery step now works, but confirm article-body fetches succeed once this runs from the user's normal network before trusting it unattended. | code fix applied + open caveat |

Net effect: dropped the `playwright` dependency entirely (removed from
`requirements.txt`) since the one source that needed it no longer does.

## Relevance-filter bug found + fixed during live testing (2026-08-04)

First live end-to-end run (`--source state`) surfaced a real content-quality
bug: `classify_relevance`'s prompt was loose enough to pass items with only a
tangential connection (a Cook Islands self-governance-anniversary greeting,
a Freedom Tech Excellence Program launch, a US-Italy critical-minerals
announcement — none mentioning China), and when the *next* stage
(`extract_key_paragraphs`) correctly found no China-relevant paragraphs, its
LLM refusal text (e.g. "I am sorry, but the provided text does not
contain...") was written into the document as if it were a real body
paragraph. Both are fixed:
- `classify_relevance` now requires an explicit, substantive PRC/Taiwan/
  Hong Kong/named-Chinese-entity connection, not just adjacent foreign-policy
  topics, and parses strictly off the first line of the reply.
- `extract_key_paragraphs` detects refusal-shaped responses (regex +
  explicit "reply NONE if nothing qualifies" instruction) and returns `[]`;
  every `add_release_entry` call site now skips (and marks-seen) the whole
  entry when `paras` comes back empty instead of writing something anyway.
- Re-ran `--source state` after the fix: all 9 items on today's feed were
  correctly rejected (0 written) — confirms both the original false
  positives and the new stricter gate.
- Ran `--source ustr` after the fix on genuinely China-relevant items
  (forced-labor Section 301 action, etc.) to confirm true positives still
  flow through correctly with the new gate — see result logged below.

**Operational note**: while testing this, a scratch `DELETE FROM seen_urls
WHERE date_seen > '2026'` (meant to un-seed 3 specific test URLs) matched
*every* row due to SQLite string comparison (`'2026-08-04T...' > '2026'` is
true for any 2026 timestamp) and wiped the whole 2248-row seed. Caught
immediately and re-seeded from `past-trackers/` (the source of truth, so no
actual data was lost) via `python seed_dedup_db.py`. No lasting effect, but
worth remembering: don't hand-edit `tracker.db` with ad hoc SQL — use
`seed_dedup_db.py` or `is_seen`/`mark_seen`.

## More bugs found via live testing (2026-08-04, continued)

- **`plain = BeautifulSoup(resp.text, "html.parser").get_text()` was pulling
  the whole page**, not the article body — on ustr.gov specifically, article
  pages open with several KB of *other* articles' headlines before the real
  body starts, which pushed the actual content out of the 2500-5000 char
  windows `classify_relevance`/`extract_key_paragraphs`/`generate_summary`
  truncate to. Concretely: a real USTR forced-labor Section 301 release was
  rejected as "not relevant" because char #2500 was still inside the
  headline list, never reaching the word "China". **Fixed** with a new
  `extract_main_text()` helper (tries `<article>`, then a
  content/article/entry/post/body/main selector, else falls back to the
  stripped-chrome full page) and swapped it into every "release"-type
  scraper (`mofcom`, `treasury`, `ustr`, `wardept`, `scio`, `mfa_leadership`).
  `state`/`whitehouse` were unaffected — they get body content straight from
  the WP-API/RSS `content` field, not a page fetch.
- **Gemini's free tier turned out to cap at 20 requests/DAY**
  (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), not just 15 RPM as
  the original code's comments assumed. A real daily run needs far more than
  20 LLM calls, so Gemini in practice only covers the first few items each
  day and Groq (llama-3.3-70b) does the rest via the fallback path. Working
  as designed for the plain-text `call_llm`, but `call_llm_json` (used by
  `generate_summary`'s anchor extraction and `parse_qa_with_llm`) had NO
  Groq fallback at all — it just retried Gemini 3x with growing backoff and
  then raised, which `generate_summary` degraded gracefully from (its own
  try/except) but `parse_qa_with_llm` did not (the whole entry would error
  out). **Fixed**: added `_call_groq_json()` (JSON-via-prompt against the
  same Pydantic schema) and wired it into `call_llm_json` on 429/quota,
  mirroring `call_llm`'s existing fallback shape.
- Confirmed end-to-end after both fixes: re-ran `--source ustr` clean (fresh
  `tracker_output.docx`, cleared test artifacts) — correctly rejected all 10
  items in that batch (verified by hand that the one "forced labor" release
  that looked promising genuinely never names China — broad 60-economy
  action, not a false negative). Re-ran `--source fmprc_conf` next: 2 items
  written with correct verb anchors ("addressed" → the FMPRC URL) — confirms
  the Q&A/hyperlink path also works, not just the release-entry path.
- Two more small bugs surfaced while eyeballing that fmprc_conf output
  (mixed in with an earlier, pre-fix scio test run still sitting in
  `tracker_output.docx` at the time):
  - `extract_key_paragraphs`'s "reply NONE if nothing qualifies" sentinel
    only matched an exact `"NONE"` reply; the model sometimes adds trailing
    commentary ("NONE (since only three relevant paragraphs exist)"), which
    slipped past the check and got written into the doc as a body
    paragraph. Fixed to match on `NONE` as a prefix instead of the whole
    string, in both the early-return check and the paragraph filter.
  - `translate_to_english` occasionally prepends a meta line ("Here is the
    translation of the Chinese text to English:") despite being told not
    to; the regex Q&A fallback parser can't distinguish that from real
    content, so it was ending up as a spurious CONT paragraph in the
    tracker doc. Added an explicit "no preamble" instruction to the prompt
    plus a defensive strip of a matching leading line if the model adds one
    anyway.
- Also confirmed (by hand-inspecting the stale pre-fix scio entries) that
  the fallback anchor heuristic in `generate_summary` — "first word of the
  summary" — produces junk when it's the actual fallback path taken (it
  picks the subject's name, e.g. "Chen", not a verb). This only fires when
  BOTH Gemini and the Groq JSON fallback fail, which shouldn't happen often
  now that `call_llm_json` has the Groq fallback; left as-is since after
  that fix the structured path (which returns a real verb anchor) succeeds
  first in every live retest since. Worth revisiting the plain-text
  fallback's anchor heuristic if it turns out to fire often in practice.

## Format fixes (2026-08-04)

- **Inline hyperlink on the summary line was entirely missing.** Confirmed
  against the past tracker's raw XML that exactly one verb/short-phrase in
  each plain-text summary sentence is hyperlinked to the source URL, styled
  `#1155CC` + single underline (Google-Docs default link style), Times New
  Roman 12pt. Added `add_hyperlink()` (hand-built OOXML `<w:hyperlink>`,
  python-docx has no native API for this) and `add_summary_para()`; extended
  `generate_summary()` to return `(summary, anchor)` via a structured
  Gemini JSON call (new `SummaryResponse` schema) where `anchor` is the
  verbatim substring to hyperlink, with a plain-text fallback if the model's
  anchor doesn't land. Wired `url=`/`anchor=` through all 7
  `add_qa_entry`/`add_release_entry` call sites. Verified offline against a
  synthetic doc that the generated XML matches the past tracker's structure
  byte-for-byte in the parts that matter (font/size/color/underline/rId).

## 2026-08-05 continued — cleared the remaining documented open items

Per user follow-up ("keep on improving, look back at the bugs you listed
and fix"). Went back through every "not yet fixed"/"worth investigating"
item logged above:

- **`generate_summary()`'s China-angle framing (was: "not done this
  session")** — fixed. It was truncating with a flat `text[:3500]`, the
  exact same blind spot bug #6/7/8 already fixed in `classify_relevance`/
  `extract_key_paragraphs` — for the Treasury sanctions release, the
  Chinese-company mention at character ~4300 was past that cutoff, so the
  summary-writing call never saw it and (correctly, given what it was
  shown) wrote a summary centered on the Iran-sanctions angle instead.
  Applied the same `_relevance_snippet()` windowing here, plus an explicit
  prompt instruction to lead with whichever angle is actually about China/
  Taiwan/Hong Kong when a document covers multiple topics, even if that's
  not the document's main subject.
- **`state.gov`'s primary WP-JSON API 404 (was: "flagging in case worth
  investigating")** — investigated and fixed. The custom post-type route
  was renamed server-side from `press_releases` to `state_press_release`
  (found by walking `state.gov/wp-json/`'s own route-discovery document).
  `scrape_state` was silently getting by on the RSS fallback this whole
  time; now hits the real API directly. Verified live: 10 items back,
  correct URLs/titles.
- **The MND word-order cosmetic issue** and **the `www.scio.gov.cn` 521
  outage** — re-checked; the former is inherent LLM prose-quality
  variance on the weaker fallback model (not a code bug, nothing to fix),
  the latter is still down as of this check (external, not our code).
  Left both as documented, unfixed by design.

## 2026-08-05 continued — user added OpenRouter + Cerebras keys as further fallback options

Discussed other LLM API options after today's Gemini/Groq quota exhaustion
(see the Anthropic Claude API skill's guidance, offered as the top
recommendation — no free-tier request-count wall, likely fixes the
reasoning-token/romanization issues too — user hasn't set that up yet).
User said they added `OPENROUTER_API_KEY` and `CEREBAS_API_KEY` to `.env`
— **checked `.env` directly and neither key is actually present** (file's
mtime is unchanged from June 26, before this session even started); the
edit likely wasn't saved. Flagged this back to the user rather than
building against keys that don't exist. Built the integration
anyway, ready to go the moment the keys land: `_call_openrouter`/
`_call_openrouter_json` and `_call_cerebras`/`_call_cerebras_json` (both
plain OpenAI-compatible `/chat/completions` calls via a shared
`_openai_compatible_chat`/`_openai_compatible_chat_json` helper), plumbed
into a new `_fallback_chain()`/`_call_fallback_chain()`/
`_call_fallback_chain_json()` that replaces the old Gemini-then-Groq-only
logic in `call_llm`/`call_llm_json` — now Gemini tries first, then Groq,
OpenRouter, and Cerebras in order, built dynamically from whichever keys
are actually present in `.env` (so adding/removing a key changes the
chain with zero code changes). Model choice: `google/gemma-4-31b-it:free`
on OpenRouter, `gemma-4-31b` on Cerebras — deliberately NOT `gpt-oss-120b`
(which Cerebras also hosts) to avoid a repeat of today's reasoning-token-
exhaustion bug; Gemma is a plain instruction-tuned model with no hidden-
reasoning failure mode.

Verified with placeholder keys that both endpoints are live and the
request shape is correct (both returned a clean 401 Unauthorized, proving
connectivity + correct URL/payload, not a network or code-path error) and
that the fallback chain builds in the right order (Groq → OpenRouter →
Cerebras). **Still waiting on the real keys to land in `.env` before any
of this can be functionally tested** — checked again after finishing the
code and `.env`'s mtime is still June 26; the user's edit has not been
saved. `.env.example` updated with both new variables and where to get
them.

## 2026-08-05 continued — keys landed; live-tested and fixed 2 more real issues

User saved the keys. Live-testing immediately found two more real, live-
only issues (exactly why "wire it up and test" beats "wire it up and
assume"):

1. **The chosen OpenRouter model was routed through the wrong upstream.**
   `google/gemma-4-31b-it:free` 429'd: "temporarily rate-limited upstream"
   — turns out OpenRouter serves that `:free` slug via Google AI Studio's
   shared free pool, i.e. the exact same contended resource sitting behind
   our own exhausted `GEMINI_API_KEY`. Adding a second entry point to a
   wall we'd already hit wasn't going to help regardless of key. Switched
   to `minimax/minimax-m3:free` (different upstream, GMICloud) — live-
   verified: correct translation, `reasoning_tokens: 0` in the usage
   breakdown for a plain prompt (has a reasoning field, didn't spend on
   it this time — the empty-response guard in `_openai_compatible_chat`
   stays as a safety net regardless).
2. **`_openai_compatible_chat`'s `resp.json()` broke on OpenRouter's
   response format.** OpenRouter prefixes the HTTP body with blank/
   keep-alive lines (an SSE-style anti-proxy-timeout pattern) even on a
   plain non-streaming request — a bug in the NEW code, not a provider
   quirk to route around. Fixed by locating the first `{` before parsing
   instead of trusting the whole body to be bare JSON.
3. **Cerebras needs account-level billing verification** — confirmed the
   key itself is valid (401 with a fake key earlier, 402 "Payment
   required" with the real one), so this isn't fixable in code. Left
   `CEREBRAS_MODEL` configured; the fallback chain already skips past a
   failing provider to the next one, so this costs nothing to leave as-is
   until the user resolves it on cloud.cerebras.ai.

**Verified end-to-end**: `_call_openrouter`/`_call_openrouter_json` both
work correctly against the real API (checked a live JSON call too — valid
summary+anchor back). Then verified the FULL chain through the actual
`call_llm()` entry point: Gemini 429'd (still exhausted from today) →
Groq presumably also still exhausted → OpenRouter served a correct
translation. The 3-tier fallback is live and functioning, not just
structurally plausible.

**Full backtest with the new tier live**: 14/21 (67%) — in the same 62-71%
band as every fixed-and-verified run today, not a regression. Checked one
of the 7 not-queued cases directly (the UFLPA entity-list release, clearly
China/Xinjiang-relevant, keyword match confirmed True) — re-running that
exact item standalone right after the backtest finished succeeded
immediately via the same Gemini→Groq→OpenRouter chain, meaning the
original miss was a transient hiccup (most likely OpenRouter's own
free-tier rate limit under the backtest's faster/denser call pattern) and
not a new logic bug. The remaining not-queued set is the same recurring
cast either way: 3 external site/network issues (`scio.gov.cn` 521 outage
x2, `war.gov` Akamai block) plus 1-2 borderline items that flip between
runs depending on which backend model ends up serving that particular
call — not something worth chasing further without a stable single
backend to calibrate against.

**Session total for today, all fixes combined**: 0 → 1 → 8 → 13 → 15 → 14
of 21 in-scope entries recovered across the day, with every structural bug
found via backtesting now fixed, a 4-tier LLM fallback chain in place
(Gemini → Groq → OpenRouter → Cerebras, degrading gracefully and
automatically as each hits its own limit), and 5 new MOFCOM source
modules added. Remaining gaps are external (2 site outages, 1 network
block, all outside this code's control) or normal LLM judgment variance
on 1-2 genuinely borderline items, not further bugs to fix.

## 2026-09-01 — weekly-cadence fix (per-source item caps were sized for daily use)

User clarified the final product: a **weekly** tracker (run ~once a week),
not a daily one. That changes a real assumption baked into the code: every
`scrape_*` function capped at `[:10]` new items per run, sized for a daily
cadence where nothing piles up between runs. At a weekly cadence, a busier
source (State, Treasury, USTR, MOFCOM) can easily publish more than 10
total items in 7 days — not all China-relevant, but enough that a real
China-relevant one could fall outside the most-recent-10 window and never
even get fetched, let alone judged.

Fixed: added `MAX_NEW_ITEMS_PER_RUN = 30` and replaced all 9 hardcoded
`[:10]` slices with it. Also bumped the underlying fetch sizes so there's
actually something to slice from: `parse_rss()`'s default `limit` 20→50,
State's WP-API `per_page` 20→50, war.gov's RSS `max` param 20→50 on both
feeds. Tried to do the same for MOFCOM's CMS API (its pagination widget
reports `count="510"` total items sitting behind a fixed `rows="15"` page
size) — adding `pageNo=2` to the query did NOT return a different page
(identical first result both times), so true pagination there needs a
different mechanism I haven't found yet. Not chased further: MOFCOM's
press-conference cadence is roughly 1-3/week in practice, well under the
15-per-page ceiling, so this isn't likely to actually cost real coverage
the way it would for a busier source — flagged as a known limitation
rather than fixed.

Pure code change, no LLM calls — free to make regardless of quota state.

## 2026-09-01 continued — new-week generalization test + 2 more real bugs found

Per user request: fresh quota day, test frugally, validate on weeks beyond
the one already extensively tested, remember the actual deliverable is a
**weekly** tracker.

**New-week test**: Part 2 tracker, 2025-12-01..12-07 (an earlier
administration period — different spokespersons, never tested before).
Of 18 ground-truth entries, 8 were actually dispatchable (mfa.gov.cn x3,
mofcom.gov.cn x3, whitehouse.gov x2 — the rest are X/YouTube/FT/Xinhua/
Embassy, out of scope or not yet built). **7/8 (87.5%) recovered** —
notably higher than the extensively-tuned week, which is itself a good
sign: the fixes generalize, they're not overfit to one week's specific
quirks.

**Bug #9 — PDF documents were being destroyed by HTML parsing.** The one
miss was `2025-National-Security-Strategy.pdf` — `extract_main_text()`
was called on `resp.text`, which for a `Content-Type: application/pdf`
response is httpx's attempt to decode raw PDF bytes as text: garbage
starting with `%PDF-1.6...FlateDecode...`. `classify_relevance`/
`extract_key_paragraphs` correctly said "no relevant content" about text
that was never readable — a false negative indistinguishable from a real
judgment call unless you actually check what text they were shown. The
real document is a 33-page, ~64k-character National Security Strategy
with 21 "China" mentions and substantial China-policy discussion — about
as core a document as this tracker could want. `pdfplumber` was already
available in the environment; added `extract_pdf_text()` +
`extract_text_from_response()` (a Content-Type-aware dispatcher — PDF via
pdfplumber, everything else via the existing `extract_main_text()`) and
swapped all 10 `extract_main_text(resp.text)` call sites to go through it.
Added `pdfplumber` to `requirements.txt`. Verified live: the PDF now
extracts real text and the entry queues correctly.

**Bug #10 — `generate_summary()` hallucinated a named official.** Once the
PDF fix let the real content through, the generated summary read "White
House National Security Advisor Jake Sullivan outlined strategies to
counter China's economic coercion..." — Sullivan is the *previous*
administration's NSA and appears **zero times** in the document (checked
directly: `Sullivan` count = 0, `Trump` count = 27). The model filled in a
plausible-sounding but fabricated attribution rather than reporting that
no specific individual is named. Fixed with an explicit prompt
instruction: don't invent/guess a person's name or title when the text
doesn't clearly name one — attribute to the institution instead. Re-
verified: now correctly says "The White House released the National
Security Strategy, warning that China has become rich and powerful...".

**Bug #11 (pure code, no LLM cost) — per-source item caps were sized for
daily use, not weekly.** All 9 `scrape_*` functions capped at the first 10
not-yet-seen items per run. At a **weekly** cadence (the actual intended
use, per this session's framing), a busier source can publish more than
10 total items in 7 days, so a real China-relevant item could sit past
the 10th slot and never get looked at. Added `MAX_NEW_ITEMS_PER_RUN = 30`
and replaced every hardcoded `[:10]`; also raised the underlying fetch
sizes (`parse_rss()` default 20→50, State's WP-API `per_page` 20→50,
war.gov's RSS `max` 20→50) so there's actually more to slice from.
MOFCOM's CMS API resisted a quick pagination attempt (`pageNo=2` returned
the same first page) — left at its native 15-per-page ceiling since that
source's real-world cadence (1-3 items/week) is well under it anyway; not
a likely coverage loss in practice, flagged as a known limitation rather
than chased further.

## Bug #12 (self-inflicted) — the PDF-dispatcher fix caused infinite recursion on itself

Immediately hit while starting the next backtest week (Part 1, Feb 2025):
`RecursionError: maximum recursion depth exceeded` on several
whitehouse.gov and state.gov pages. Cause: the earlier bulk find-and-
replace that swapped all 10 occurrences of `extract_main_text(resp.text)`
over to `extract_text_from_response(resp)` (for the PDF fix, bug #9) did a
blind literal-string replace — which also matched the identical string
sitting inside `extract_text_from_response()`'s OWN fallback branch and
docstring, turning `return extract_main_text(resp.text)` into
`return extract_text_from_response(resp)`: the function calling itself
forever. `py_compile` doesn't catch this (it's a runtime name/logic issue,
not a syntax error), so it silently shipped in the "COMPILE_OK" fix a few
minutes earlier and only surfaced on the next live page fetch. Fixed by
restoring the correct fallback call; verified against the exact page that
first surfaced it. **Lesson for future bulk replaces in this file:
literal-string `.replace()` across a whole module can rewrite a function's
own reference to what it's wrapping — grep the result for the new call
still appearing INSIDE the function that defines it, not just count
occurrences.**

Killed and restarting the in-progress Part 1 backtest run, since it had
already been using the broken code (loaded before the fix) for several
items.

## Bug #13 — Latin-only regex character classes + orphan speaker-label paragraphs (Part 1 week, kind-mismatches)

The re-run of the Part 1 (Feb 2025) backtest surfaced a 4/13 kind-mismatch
rate, all State Dept joint-press-availability transcripts. Root cause was
actually two stacked bugs found together on one live URL
(`state.gov/.../secretary-of-state-marco-rubio-and-guatemalan-president-
bernardo-arevalo-at-a-joint-press-availability/`):

1. **Unicode-unaware character classes.** `_QA_RE`, `_LABEL_RE`, the regex
   inside `split_single_paragraph`, and `add_release_entry_body`'s
   `speaker_re` all used `[A-Za-z0-9 \-'\.]`-style classes to match a
   speaker label's name portion. That silently fails to match accented
   Latin letters — "PRESIDENT ARÉVALO:" never matches `[A-Za-z0-9...]+`
   because of the "É". Fixed all four by widening to `\w` (Unicode-aware
   by default in Python 3 `str` patterns), matching the character class
   already used elsewhere for CJK-safe matching.
2. **Orphan speaker-label paragraphs** (the actual dominant cause once
   #1 was fixed and the mismatch persisted): this transcript's HTML puts
   each speaker label alone in its own `<p>` — literally just
   `"MODERATOR:"` or `"PRESIDENT ARÉVALO:"` with nothing after the colon
   — and the first line of that speaker's actual remarks lands in the
   NEXT paragraph. Every label regex in the file (`_LABEL_RE`, `_QA_RE`)
   requires `:\s+` (colon THEN whitespace THEN text) on one line, so a
   colon at the very end of a paragraph with no trailing text never
   matches at all — not misclassified, invisible. `content_type_from_
   paragraphs` therefore found zero labels and the whole two-person
   exchange defaulted to "release". Fixed with a new
   `_merge_orphan_speaker_labels()` pass (regex `^[A-Z][\w \-'\.]{1,40}:$`
   for "paragraph is ONLY a label") that joins such a paragraph with the
   one immediately following it, before either `content_type_from_
   paragraphs` or `parse_qa_from_plaintext` ever see the list — wired into
   `finalize_release_item` right after the initial paragraph split.
   Continuation lines after that still fall through to `_build_exchanges`'s
   existing `CONT` handling, so no further change was needed there.
   Also added "moderator" to `_ASKER_LABEL_RE`'s asker-term list — a
   moderator introducing speakers and (implicitly) posing the "floor is
   yours" framing is a real facilitator/asker role in these transcripts,
   just not a journalist.

Verified against the exact failing URL: now correctly classified `qa`,
5 exchanges built (MODERATOR intro + PRESIDENT ARÉVALO remarks, correctly
split into A/CONT), summary correctly leads with the Taiwan/China content
buried in the transcript rather than the migration/border-security framing
that opens it.

## Part 1 week (2025-02-01..02-07) re-run after bug #13 — 12/13 kind-match, up from 9/13

Full re-run: 30 ground-truth entries, 13 with no scrapable domain (X/
TruthSocial, out of scope), 17 dispatchable. Of those: **13 queued, 12 of
13 correctly kind-matched** (up from 4 kind-mismatches pre-fix), 4 not
queued. Investigated each of the remaining 5 gaps live:

- **1 real kind-mismatch, defensible**: `state.gov/secretary-marco-rubio-
  with-rich-edson-of-fox-news/` — a Fox News interview. Our code sees a
  reporter asking questions and a Cabinet official answering and correctly
  calls that `qa` by definition; the past tracker rendered it as `release`
  (bold name + quote, no Q:) — an editorial/formatting choice on the past
  tracker's part more than a factual misclassification. Left as-is rather
  than special-cased.
- **1 not-queued, external/unfixable**: `fmprc.gov.cn/.../t20250202_
  11548196.html` now redirects to FMPRC's own "page does not exist /
  system maintenance" placeholder (verified live — the fetched body is
  literally 系统维护 / "您访问的页面不存在或已删除"). This is an 18-month-old
  page; FMPRC has apparently reorganized or pruned this URL since. Nothing
  to fix in our code — the source page is genuinely gone.
- **1 not-queued, external/unfixable**: `whitehouse.gov/fact-sheets/2025/
  02/fact-sheet-president-donald-j-trump-withdraws-from-anti-american-un-
  organizations/` now serves a **completely different** fact sheet at the
  same URL (verified live — the page title and body are about the
  Women's Sports executive order, not UN organizations). whitehouse.gov
  appears to have reassigned/overwritten this URL slug at some point.
  Also unfixable from our side — the historical content simply isn't
  there anymore to fetch.
- **1 not-queued, real gap, LLM-judgment not a code bug**:
  `whitehouse.gov/.../national-security-presidential-memorandum-nspm-2/`
  — a long Iran-sanctions memorandum with exactly one embedded mention
  ("...Iranian crude to the People's Republic of China") deep in a
  sub-clause. Confirmed the text IS fetched correctly and the relevance
  snippet DOES include that exact sentence (windowing is fine) — the
  LLM call itself (routed to OpenRouter's fallback model, since Groq's
  daily token cap was exhausted by this point in testing) judged the
  single passing mention not "China-relevant" enough to extract a
  paragraph. This is a real recall miss, but it's a prompt-strictness/
  model-quality tradeoff (a stricter bar avoids false positives on every
  document that name-drops China in one sanctions sub-clause; a looser
  bar catches cases like this one) rather than a fixable logic error —
  flagging as a known limitation rather than tuning further at the edge
  of today's quota.

**Recall on this week, dispatchable items: 13/17 queued (76%), 12/13 of
those correctly kind-classified (92%).** Combined with bug #13's fix,
this is a clean, final number for this test week — no further known code
bugs in it.

## 2026-09-01 continued — three simplifications per user request, cut LLM calls per item ~in half

User asked for three changes, all aimed at reducing LLM dependency/cost
and error surface:

1. **`generate_summary()` disabled for now.** Added `ENABLE_LLM_SUMMARY`
   (currently `False`) and a single choke point, `get_summary_and_anchor()`,
   that every finalize_*/process_release_common call site now goes through
   instead of calling `generate_summary()` directly — flipping it back on
   is a one-line change, not a re-edit of 4 call sites. While disabled,
   the "summary" is just the bare URL (`add_summary_para()` already
   handles `summary == anchor` by hyperlinking the whole line). Also
   tightened `generate_summary()`'s own fallback prompt from "1-2
   sentences" to "ONE concise sentence" (the structured/primary prompt
   already said "ONE sentence") for whenever it's switched back on.
2. **`parse_qa_from_plaintext()` flipped to regex-first, LLM-as-last-
   resort.** Previously tried the LLM (`parse_qa_with_llm`, which
   reproduces/retypes the whole transcript in JSON) FIRST and only fell
   back to the regex-based `_build_exchanges()` (which slices the
   ORIGINAL text verbatim at each detected label boundary — a formatter,
   not a rewriter) on an exception. User reported occasional errors
   downstream (piping LLM-reconstructed text through the Google Docs
   formatting step) and asked why we're not just formatting the existing
   text. After bug #13's fixes this session (Unicode-safe labels, orphan-
   label merging, "moderator" recognized), the regex parser is reliable
   enough to be primary — verified live: the Rubio/Arévalo transcript
   (74 exchanges) now goes through 1 LLM call total (`classify_relevance`)
   instead of ~4 (classify + parse_qa + generate_summary + anchor retry).
3. **Chinese release-paragraph selection is now keyword-only, not an LLM
   judgment call.** New `_CHINESE_US_MENTION_RE` (美国/中美/美方/华盛顿/白宫/
   驻美/访美/对美/赴美 — deliberately narrower than `CHINESE_RELEVANCE_
   KEYWORDS`, matching the user's own manual rule: "does this paragraph
   name the US," not "is this on some China-policy-adjacent topic") and
   `select_relevant_chinese_paragraphs()` operate on the ORIGINAL Chinese
   text before translation, so only matched paragraphs get translated at
   all (one combined translation call, not a per-page extraction-judgment
   call). Wired into `finalize_qa_item`'s existing "no Q&A structure
   found" release-fallback branch via a new `raw_zh_text` parameter,
   threaded through from `process_fmprc_item`/`process_mofcom_item`/
   `process_mnd_item`'s Chinese branches. Deliberately NOT applied to MFA
   leadership sources, which already have a correctly-tuned, intentionally
   BROADER bar ("substantive leadership activity," not "mentions the US")
   from an earlier fix — this would have regressed that.

**Bug found immediately while verifying #2+#3 together, fixed same pass**:
tested against the known MOFCOM "China's Position on So-Called
Overcapacity" position paper. `_build_exchanges()` (now running first,
per #2) matched the page's own translated metadata boilerplate ("Category:
News", "Source: Xinhua News Agency", "Type: Reprint") as if they were real
speaker labels — they fit `_QA_RE`'s "Label: text" shape exactly as well
as an actual speaker. `content_type_from_exchanges()` correctly still
called this "release" (none of those labels look like an asker), but the
existing `exchanges_to_paragraphs()` tail has no relevance filter at all,
so ALL 53 translated paragraphs (i.e. essentially the entire document)
got dumped into the tracker instead of a curated few — worse than either
the old LLM-extraction behavior or the new keyword-filtered one. Fixed
with `_METADATA_LABEL_RE`, a small denylist checked inside
`_build_exchanges()` itself (Category/Source/Type/Author/Date/Tags/Editor/
Reprint, English and Chinese) — a match on one of these is skipped
entirely rather than treated as a label. Re-verified on the exact same
URL: now correctly falls through to the new keyword-based release path
(regex found zero real exchanges once metadata is excluded → LLM Q&A
fallback failed due to quota → `select_relevant_chinese_paragraphs()`
kicked in) and produced 9 targeted paragraphs instead of 53, using only
one translation call and zero extraction-judgment calls.

Net effect verified live on two real pages: the Rubio/Arévalo Q&A
transcript now costs 1 LLM call instead of ~4, and the MOFCOM position
paper costs 1 translation call (on 9 keyword-matched paragraphs) instead
of a full-page LLM extraction call — both with a bare-URL summary instead
of a generated one, per change #1.

Also fixed the 4th (last) occurrence of the Latin-only speaker-label regex
from bug #13 that was missed in that pass — the pattern inside
`split_single_paragraph` (line ~1636) still had `[A-Za-z0-9 \-'\.]`; widened
to `[\w \-'\.]` to match.

## 2026-09-01 continued — added per-call token-usage logging

Per user request ("curious, would like to optimize token usage"): every
LLM call now logs one `[usage] <label> via <provider>: prompt=N
completion=M total=T reasoning=R` line. New `_log_usage()` helper, called
from `call_llm`/`call_llm_json` (Gemini's `usage_metadata`, including
`thoughts_token_count` — see below), `_call_groq`/`_call_groq_json` (via a
shared `_log_groq_usage()`, including `completion_tokens_details.
reasoning_tokens`), and `_openai_compatible_chat`/`_openai_compatible_chat_json`
(OpenRouter/Cerebras — same `usage` shape in the raw JSON body). Threaded
a `label` parameter (e.g. "classify_relevance", "translate",
"generate_summary", "extract_key_paragraphs", "parse_qa_with_llm") through
every layer of the fallback chain so each log line says which code path
spent the tokens, not just which provider served it — the whole point was
to see where tokens actually go, not just a raw total.

**Immediate finding**: Gemini burns invisible "thinking" tokens too, not
just Groq's `gpt-oss-120b`. A live `classify_relevance` call logged
`prompt=827 completion=37 total=1222 reasoning=358` — 358 of 395
non-prompt tokens (91%) went to Gemini's own hidden chain-of-thought for
what's fundamentally a one-word YES/NO classification. This was invisible
before today; worth revisiting (e.g. a `thinking_budget=0`/low-effort
config for Gemini, mirroring the `reasoning_effort="low"` fix already
applied to Groq) if it turns out to be consistent across calls rather than
a one-off.

## 2026-09-01 continued — Part 3 week (2026-05-01..05-07), first live test: 8/8 queued, then bug #14 found+fixed

First live backtest on Part 3 (a week not previously live-tested, only
ground-truth-extracted). Of 22 entries, 14 are X/YouTube (out of scope),
leaving 8 dispatchable — **8/8 queued (100%)**, 7/8 correctly kind-matched.

**Bug #14 — same orphan-label problem as bug #13, but in the Q&A parsing
path, and with an added single-letter-label wrinkle.** The one mismatch:
a real MOFCOM Q&A ("MOFCOM Spokesperson Answers Reporters' Questions on
Blocking US Sanctions Against 5 Chinese Enterprises") was classified
`release` instead of `qa`. Root cause, found live: MOFCOM's Chinese Q&A
pages use a standalone "问："/"答：" label alone on its own line (content
starts on the NEXT line) — translated straight through as "Q:"/"A:" alone
on their own lines. Two stacked issues:

1. `parse_qa_from_plaintext()` never called `_merge_orphan_speaker_labels()`
   at all — that merge (added for bug #13) was only wired into
   `finalize_release_item`'s release-path paragraph prep, not into the
   actual Q&A parsing entry point every FMPRC/MOFCOM/MND page goes through
   first. Fixed by calling it there too.
2. Even after merging, `_ORPHAN_LABEL_RE`/`_QA_RE`/`_LABEL_RE`/`speaker_re`/
   `split_single_paragraph`'s pattern all required **at least 1 character**
   between the leading capital letter and the colon (`{1,40}`/`{1,50}`) —
   which a bare "Q:" or "A:" (zero characters between "Q"/"A" and ":")
   never satisfies. This is the standard journalism Q/A shorthand, and
   exactly what a translated 问：/答： becomes in practice — not an edge
   case. Fixed by widening all five to `{0,40}`/`{0,50}`.
3. Once matched, a bare "A:" still wasn't recognized as an ANSWER role:
   `_build_exchanges`'s `is_sp` check only tested whether a known
   spokesperson term (e.g. "Answer") was a SUBSTRING of the label — true
   for a label like "MOFCOM Spokesperson", never true for "A" alone (there's
   no substring relationship between "answer" and "a"). Fixed by also
   directly recognizing a bare "a" (case-insensitive) as an answer role,
   mirroring `_ASKER_LABEL_RE`'s existing bare-"q" recognition on the
   other side.

All three verified against the exact failing case: now correctly produces
2 exchanges (Q, then A — correctly typed), classified `qa`, **using ONLY
the regex path — zero LLM calls for structure**, exactly the point of
this session's change #2. (The live backtest run itself still went
through the LLM fallback for this one item, since it ran before this fix
was in place — the fix is verified standalone and logged here rather than
re-run against live quota, which was nearly exhausted by this point.)

## Token usage breakdown, Part 3 backtest (12 LLM calls total, before bug #14's fix)

Aggregated from `[usage]` log lines across the whole run:

| Call type | calls | prompt | completion | reasoning | total |
|---|---|---|---|---|---|
| translate | 4 | 2200 | 1870 | 1075 | 5122 |
| parse_qa_with_llm | 2 | 2136 | 1027 | 1240 | 4403 |
| extract_key_paragraphs | 4 | 2698 | 1594 | 434 | 4292 |
| classify_relevance | 2 | 1627 | 91 | 27 | 1718 |
| **Total** | **12** | | | | **15535** |

| Provider | calls | prompt | completion | reasoning | total |
|---|---|---|---|---|---|
| OpenRouter | 6 | 5042 | 2531 | 0 | 7573 |
| Gemini | 2 | 1193 | 739 | 2292 | 4224 |
| Groq | 4 | 2426 | 1312 | 484 | 3738 |

Notable: `translate` is the single biggest cost center by call type (one
per Chinese-sourced item that needs translating at all — unavoidable, it's
real work). `parse_qa_with_llm` still fired twice this run (both before
bug #14's regex fix landed) — after that fix, this specific pair of calls
should drop to zero, cutting ~4400 tokens and 2 full LLM round-trips from
a comparable future run. Gemini's reasoning overhead is stark relative to
its own total: 2292 of 4224 tokens (54%) went to invisible thinking for
only 2 calls — confirms the earlier single-sample finding wasn't a fluke;
worth a `thinking_budget=0`-equivalent config if the google-genai SDK
exposes one for gemini-2.5-flash, next time there's Gemini quota to test
against. OpenRouter reports zero reasoning tokens across all 6 of its
calls, consistent with earlier findings that `minimax/minimax-m3:free`
doesn't spend on hidden reasoning for these prompt shapes.

## 2026-09-01 continued — fixed Gemini's invisible-thinking cost (flagged earlier, not yet fixed until now)

User asked directly whether the Gemini reasoning-token finding had
actually been fixed yet — it hadn't, only diagnosed. Fixed now:
`gemini-2.5-flash` is a "thinking" model by default, same invisible-
chain-of-thought shape as `GROQ_MODEL`'s issue (bug #6), but unlike
`gemini-2.5-pro` (which requires a minimum thinking budget), flash
supports `thinking_budget=0` to disable it outright. Added
`_GEMINI_THINKING_CONFIG = types.ThinkingConfig(thinking_budget=0)` and
wired it into both `call_llm`'s and `call_llm_json`'s
`GenerateContentConfig` — mirrors the `reasoning_effort="low"` fix
already applied to Groq. Verified live: a plain YES/NO classification
that previously would have logged `reasoning=300+` now logs
`prompt=26 completion=1 total=27` — no reasoning line printed at all
(zero). No visible quality regression on a first spot-check (still
correctly answered YES); worth a normal eye on relevance/summary quality
over the next few live runs same as any other change, but this class of
task (classify/translate/extract short verbatim spans) doesn't call for
deliberation in the first place.

Also answered a related question about existing English-first-then-
Chinese logic across sources, since it came up in the same conversation:
MND already skips translation entirely when its bilingual same-page
English half is present (`process_mnd_item`, pre-existing). FMPRC treats
its English listing as the sole source for daily conferences (Chinese
FMPRC listing skipped at the source level, not per-item). MOFCOM
deliberately does NOT cross-reference its English mirror against its
Chinese sections before translating — this was tried once already (the
original "Chinese pages are redundant with English" assumption in
SOURCES.md) and backtesting disproved it, dropping a real past-tracker
entry that only existed on the Chinese side. Flagged as a possible future
optimization (a cautious date/title-matched skip, not a blanket "English
exists somewhere this week" skip) but not implemented, given the
documented regression risk — left for the user to decide if it's worth
pursuing.

## 2026-09-01 continued — Part 1 week (June 9-15, 2025), first live test: 6/7 queued, 2 kind-mismatches, 2 more real bugs found+fixed

New week, never tested before. Of 21 ground-truth entries, 14 are X/
TruthSocial (out of scope), leaving 7 dispatchable: **6/7 queued, 1
not-queued, 4/6 kind-matched, 2/6 kind-mismatched**.

**Not-queued (defensible judgment call, not a bug)**: a state.gov
Philippines-Independence-Day statement from Rubio, ground truth says
"release." The text mentions "South China Sea" exactly once, in passing
("...work together to uphold international law in the South China
Sea..."), with no explicit mention of China/Chinese entities anywhere.
Live-checked `classify_relevance` directly: it correctly said NO per its
own (deliberately tightened, 2026-08-04) instruction that a topically-
adjacent mention without naming China isn't automatically substantive —
the same guard that fixed the Cook-Islands/US-Italy false positives
earlier. The past tracker's human editor evidently used a looser bar here
(South China Sea mentions are implicitly China-relevant even unnamed).
Flagging as a real, known editorial-calibration gap rather than "fixing"
it — loosening the gate risks reintroducing the false positives it was
tightened to prevent.

**Kind-mismatch #1 (not a bug, content-shape limitation)**: an MND page
(Jiang Bin on US M1A2 tank transfers to Taiwan), ground truth "qa," got
"release." Checked the actual source page: it's a **third-person news
article** ("China Military Online") reporting ON a press-conference
exchange — "When being asked to comment on these, the Chinese defense
spokesperson first pointed out that...", not a verbatim transcript with
any "Reporter: .../Spokesperson: ..." structure at all. There is no real
Q&A structure in the source to extract — the past tracker's "qa"
rendering is itself a manual re-narration by a human editor, not
something recoverable from this page's actual content. Release is the
honest classification of what's actually on the page.

**Kind-mismatch #2 (bug #15, found + fixed)**: a real MOFCOM regular
press conference (He Yadong on rare-earth exports / the first US-China
trade-consultation meeting), ground truth "qa," got "release." Root
cause: MOFCOM's *regular* press-conference pages (as opposed to its
spokesperson-remarks pages already handled) wrap each speaker name in
Chinese brackets — "【何亚东】：" — which `translate_to_english` carries
straight through as English square brackets ("[He Yadong]:") instead of
stripping them. Every label regex in the file requires a label to START
with a plain letter (`^[A-Z]...`), so a leading "[" made the whole label
invisible — third distinct label-shape bug this session, same "not
misclassified, unrecognized" failure mode as bugs #13/#14. Fixed with a
new `_BRACKETED_LABEL_RE`/`_unbracket_label()` (handles both "[...]" and
full-width "【...】", in case a translation leaves the original CJK
brackets in place) wired into both `parse_qa_from_plaintext` and
`finalize_release_item`'s paragraph prep, before `_merge_orphan_speaker_
labels`. (First version of the fix had its own bug — hardcoded ": " even
when nothing followed on the same line, which broke `_ORPHAN_LABEL_RE`'s
`:$` anchor for the still-orphaned case; fixed to only add the space when
there's real trailing content.)

Fixing the bracket issue surfaced a SECOND real bug on the same page:
once labels were recognized, "He Yadong" (the actual named spokesperson)
still wasn't typed "A" — the `is_sp` check only matches a *role word*
("Spokesperson"/"Minister"/...) as a substring of the label, which never
matches a bare personal name. Unlike FMPRC (which has a maintained
`FMPRC_SPOKESPERSONS` name list), MOFCOM's regular-conference spokesperson
rotates too often to maintain a name list for. Fixed with a general
heuristic in `_build_exchanges`: a real press conference has exactly one
answerer and many different askers, so whichever non-asker-shaped label
repeats 2+ times is almost certainly the answerer — a `Counter`-based
second pass retypes all of that label's turns to "A". Verified live on
the real page: He Yadong's 5 turns all correctly promoted to "A", each
single-appearance reporter label ("CGTN Reporter", "Kyodo News Reporter",
etc.) correctly left as "Q", overall `content_type_from_exchanges` now
returns "qa" — matching ground truth. This heuristic is a safe *addition*
for existing named-spokesperson sources (FMPRC/MND): it only fires on a
label the substring check didn't already resolve, so it's a no-op
wherever the existing logic already worked.

Not re-run through the full live backtest after this fix — Groq's daily
token cap was within ~1 request of hitting its limit again by this point
(199583/200000) and Gemini was rate-limiting on nearly every call.
Verified directly against the real, exact failing page content instead
(same standalone-verification approach used throughout this session)
rather than spend the day's last live-quota margin re-confirming one
already-diagnosed item.

## 2026-09-01 continued — flag-for-review side channel, per user feedback

User feedback, prompted directly by the Philippines-Independence-Day
not-queued case above: "always good to have more than less — leave a
note for a human reviewer to judge if [it] should [be] kept." Added
`flag_for_review(url, title, reason)` — appends a checklist entry
(date, title, url, and the model's own stated reason) to a new
`flagged_for_review.md`, created on first use. The item is still excluded
from `tracker_output.docx` and still `mark_seen()`'d (this is a side
channel, not a second inclusion path) — the point is a human can
periodically skim this file and manually add back anything cut too
aggressively, rather than a rejection just vanishing into the logs.

Wired into every point where an LLM (not a free keyword check) actually
renders a "not relevant enough" judgment: both `classify_relevance`
rejection sites (`process_release_common`, `process_mofcom_item`'s
English-mirror branch) and both `extract_key_paragraphs`-empty rejection
sites (`finalize_qa_item`'s release-fallback, `finalize_release_item`'s
release path). Deliberately NOT wired into the free keyword-prefilter
skips (`classify_relevance`'s "no US-China-relevant terms found" path) or
`filter_relevant_exchanges`'s keyword-only checks — those have no LLM
judgment to second-guess in the first place, so flagging them would just
be noise. Verified live against the exact Philippines/South-China-Sea
case from this session: correctly still excluded from the tracker, but
now logged with the model's own verbatim reasoning
("NO — The release only references the Philippines and U.S. relations,
without explicitly mentioning China...") for a human to weigh in on.

## 2026-09-01 continued — user linked billing to Gemini; corrected a wrong claim + fixed a real self-inflicted pacing bug

User linked a card to their Gemini API account (~$10) specifically to get
past the free tier's 20-requests/day wall, after I'd quoted third-party
aggregator numbers suggesting Tier 1 gives 2,000 RPM / uncapped RPD. Their
own AI Studio dashboard immediately after linking showed **RPM=4, TPM=
7.77K, RPD=30** — nowhere close to those figures. Correcting the record:
those third-party numbers describe a HIGHER usage tier reached only after
sustained spend/usage history, not what a freshly-linked account gets
immediately — I should have flagged that uncertainty harder the first
time rather than presenting aggregator numbers as settled fact for an
account that had just linked billing. Real gain from linking: RPD went
20 → 30 (modest, not "uncapped"), plus of course removing any dollar-cap
concern (Gemini is priced cheaply enough that this workload's actual
spend is trivial regardless — see below).

**Found a real bug while updating for the corrected numbers**: `GEMINI_
SLEEP` (the pacing delay between Gemini calls) was `4` seconds — a
holdover comment claimed this was "under the free tier's 15 RPM cap," but
RPM=4 (confirmed on this account, both before and evidently after linking
billing) needs one request every **15 seconds**, not 4. This means the
pipeline has likely been self-inflicting a chunk of its own Gemini 429s
all session, independent of the daily quota — every burst of 2+ Gemini
calls within the same 15s window would 429 regardless of RPD headroom.
Fixed: `GEMINI_SLEEP = 16`.

**Added persistent, USD-denominated usage tracking**, per user request to
"keep track of token usage and how much that'd be in USD" across
continued testing (not just a one-off log-parsing exercise like the Part
3 breakdown earlier). `_log_usage()` now also appends a structured JSON
record per call to `usage_log.jsonl` (provider, label, prompt/completion/
reasoning/total tokens, and a computed `usd` field), and a new
`summarize_usage_log()` aggregates it by label and by provider with a
grand-total USD figure — callable any time, not just parsed ad hoc from
free-text logs. Pricing table (`_USD_PER_MILLION`): Gemini real money
($0.30/M input, $2.50/M output, thinking tokens billed at the output
rate per Google's own pricing page — checked live today), Groq and
OpenRouter priced at literal $0.0 since both are actually free right now
(this account's Groq key is the free tier; `OPENROUTER_MODEL` is a
`:free` slug) — not "unknown," genuinely free regardless of volume.
Cerebras omitted (never successfully billed a call all session — 402
Payment Required throughout). `usage_log.jsonl` and `flagged_for_review.md`
added to `.gitignore` (generated runtime output, not source).

## 2026-09-01 continued — resumed backtest campaign after the pacing fix; two clean(ish) weeks

User updated the Present tracker with more recent weeks (now spans
2026-06-23..08-31, up from 08-03 — 288 ground-truth entries, up from 202)
and flagged that some newer entries were done by a less-experienced peer
intern and "may not be perfect" — a reminder to sanity-check any new
"mismatch" against the actual source before assuming it's a scraper bug,
not just trust the ground truth blindly.

**July 7-13, 2026**: 12/12 dispatchable queued, 12/12 kind-matched, zero
mismatches, zero flagged-for-review items. Full usage: 14 calls, all
served by Gemini (first time all session a whole week needed zero
fallback — the GEMINI_SLEEP fix above), zero reasoning tokens, $0.0114.

**June 23-29, 2026**: 17/18 dispatchable queued, 17/17 kind-matched, 1
not-queued. Investigated the miss (an SCIO release on Japan/Philippines
maritime talks that also covers a US assessment) rather than accept the
number at face value: both `classify_relevance` and `extract_key_
paragraphs` independently return correct/positive results on this exact
text when called directly, and re-running the real `process_scio_item`
end-to-end on the real URL queues it correctly. This was a **transient**
failure during the original run (most likely a brief simultaneous 429
across fallback tiers) — `process_scio_item`'s except block already
doesn't `mark_seen()` on an exception, so the item isn't lost, just
deferred to the next real run. Confirms the existing "self-healing, not
data loss" design works as intended; no code change needed.

## 2026-09-01 continued — bug #16: a single outlet citation could flip an ordinary press release to "qa"

**June 30-July 6, 2026**: 12/13 dispatchable queued (before fixes), 2 real
kind-mismatches + 1 external miss (war.gov — confirmed live, still 403
Forbidden from this sandbox, the same standing Akamai IP-block; not a
code bug).

Both kind-mismatches were the SAME root cause, and NOT a regression from
today's earlier {0,40}/bracket/orphan-label fixes (verified: the specific
labels involved were already long enough to match under the old {1,40}
quantifier too) — a pre-existing gap that these two backtests happened to
be the first to surface:

- A USTR press release that opens with a "media coverage" roundup ("Fox
  News:", "Bloomberg:", "CNBC:") followed by one-off reaction quotes from
  EIGHT different named officials/trade-association presidents — got
  flipped to "qa" because a single outlet name ("Bloomberg"/"CNBC", both
  literal entries in `_KNOWN_OUTLETS_RE`) was, under the old rule, enough
  on its own regardless of anything else in the document.
- Xi Jinping's 105th-CCP-anniversary speech — the page's own title line
  ("Xi Jinping: [Speech title]", a common Chinese-article convention of
  attributing a title to its author) parses as a "Label: text" match,
  which combined with something else in the (very long, heavily-quoted)
  speech was enough to trip the same old any-hit rule.

**Root cause**: `_classify_by_labels`'s rule was "does ANY label look
asker-shaped" — true, but not sufficient. The actual discriminator: a
real press conference has ONE (rarely two, for a joint briefing) person
actually answering, no matter how many different outlets/reporters ask;
a "roundup of individual reactions" cites MANY different people
symmetrically, none of them a repeat answerer. **Fixed**: require an
asker-shaped label AND that the labels which DON'T look asker-shaped
resolve to only 1-2 distinct names, not 3+. Verified against every real
case from this whole session: MOFCOM's He Yadong (1 distinct answerer →
qa), the Rubio/Arévalo transcript (1 distinct answerer, Arévalo — his
whole turn is one long CONT-continued block, so he never even repeats as
a separate label, and the fix still holds him correctly since the bar is
"how many DISTINCT non-asker names," not "does one repeat" → qa), a
synthetic FMPRC-shaped transcript (1 distinct answerer, multiple
wire-service askers → qa), and both real failures above (8 and several+
distinct non-asker names respectively → release).

**Fixing this surfaced a second, adjacent gap**: verifying against
MOFCOM's real page, "CGTN Reporter" and "CNBC Reporter" (outlet name +
role-word compound labels — an entirely ordinary transcript-label shape)
matched NEITHER of `_ASKER_LABEL_RE`'s two branches — not the exact-match
branch (the whole label isn't literally just "reporter"), and not the
outlet-suffix branch either, since "cgtn"/"cnbc" aren't in that keyword
list. They were being miscounted as additional non-asker "answerers,"
which would have wrongly flipped this real transcript back to "release"
under the new stricter rule. Fixed by adding reporter/journalist/
correspondent/interviewer/anchor to the SUFFIX-matching branch too (they
were previously only recognized as a bare, whole-label exact match), so
"<any outlet name> Reporter/Correspondent/..." is recognized regardless
of whether that specific outlet happens to be in the keyword list.

All four cases (USTR, Xi speech, MOFCOM, Rubio/Arévalo) re-verified live
end-to-end after both fixes — all correctly classified, zero regressions.

## 2026-09-01 continued — X (Twitter) source built; X_API_KEY/xAI mix-up sorted out

User asked to implement the previously-"blocked" X sources (18 accounts,
see SOURCES.md), having put $5 into an account and added `X_API_KEY`.

**Built `scrape_x`/`process_x_tweet`** using X's official API v2 (moved to
pay-per-use pricing in Feb 2026 — ~$0.005/post read, ~$0.01/user read,
confirmed live via docs.x.com — which is what actually makes this
affordable now; the old subscription tiers, Free with no read access at
all or Basic at ~$200/month, were why this was "blocked" in the first
place). Cost discipline built in from the start, since every read is
billed by X itself: `X_STATE_PATH` (`x_accounts_state.json`) caches each
account's username→user-ID resolution forever (a real, billed "user
read," paid once, not every run) and each account's highest-seen tweet ID
(`since_id`, X's own recommended incremental-poll param) so an
already-processed tweet is never re-billed on a later run, on top of our
own `is_seen()` dedup. Only SOURCES.md's "normal" tier (11 accounts)
polls by default; the 7 "less important" accounts are listed but off
(`X_INCLUDE_LESS_IMPORTANT`) to control cost. A tweet is short enough to
skip the heavier release-entry machinery entirely — `process_x_tweet`
classifies the tweet text directly and queues a single-paragraph release
entry, no `extract_key_paragraphs` call needed.

**Found and fixed a real billing-accuracy bug during the very first live
test**: the first test call 401'd, but `_log_x_cost` fired anyway before
checking the response status — would have overstated real spend by
logging a charge for a failed, unbilled request. Fixed to only log cost
after confirming a 200 response; removed the one phantom entry already
written to `usage_log.jsonl`.

**The 401 itself turned out to be a real mix-up, not a bug**: `X_API_KEY`
in `.env` started with `xai-...` — the prefix for **xAI** (Grok) API
keys, not X/Twitter's. X and xAI are separate products/companies (both
under Musk, hence the confusion) with entirely separate auth systems; no
code change would have made an xAI key authenticate against `api.x.com`.
Diagnosed via full response-header/body inspection (safe to do repeatedly
— confirmed a failed 401 isn't billed by X) rather than guessing at fixes.

**User's call, given the choice**: keep the $5 of xAI credit as a 5th LLM
fallback tier (Grok) instead of pursuing real X access immediately.
Implemented `_call_xai`/`_call_xai_json` reusing the existing
`_openai_compatible_chat(_json)` plumbing (extended with an `extra_body`
param specifically to carry `reasoning_effort: "none"` — grok-4.3 is a
reasoning model by default, same invisible-token-spend shape as
`GROQ_MODEL`/gemini-2.5-flash, both already fixed this session — xAI's
own docs confirm this parameter disables it outright). Wired into
`_fallback_chain` as: Groq → OpenRouter → XAI → Cerebras (XAI ahead of
Cerebras, which has never once successfully billed a call all session).
Added real pricing to `_USD_PER_MILLION` ($1.25/M input, $2.50/M output,
confirmed live via docs.x.ai) — genuine money, unlike Groq/OpenRouter's
$0 free tiers.

User then separately sorted out the real X/Twitter credential: renamed
the xAI key to `GROK_API_KEY` and obtained an actual X API Bearer token
for a NEW `X_API_KEY`. `_xai_api_key()` updated to read `GROK_API_KEY`
(not falling back to `X_API_KEY` anymore, now that the two are correctly
separate real credentials). `scrape_x`'s code is complete and ready — not
yet live-verified against a real Bearer token, since at time of writing
`.env` still showed the OLD xai- key under `X_API_KEY` (the user's
described edit hadn't actually saved to disk yet); to be verified live
once that lands.

**Update**: user saved `.env` with both keys correctly separated. Verified
both live: `_call_xai` returns a correct response with real usage/cost
logged ($0.000241 for a trivial smoke-test prompt); `_x_get_user_id`
against the real `X_API_KEY` returns `200 OK` and a real numeric user ID
for @WhiteHouse ($0.01 correctly billed and logged). Ran a small,
deliberately-controlled end-to-end test (5 tweets, not the full 11-account
run) before scaling up: fetched 5 recent @WhiteHouse tweets ($0.025),
correctly classified all 5 as not China-relevant (energy/manufacturing/
Iran content), correctly queued zero. Full X source is live and working.

## 2026-09-01 continued — Aug 4-10, 2026 week: 11/13 queued, both misses genuine (0 new bugs)

11/13 dispatchable queued, 11/11 kind-matched, 2 not-queued — investigated
both rather than accept the number:

- A White House polysilicon-tariff fact sheet: zero literal "China"
  mentions anywhere in the page (checked directly — only "foreign
  governments"/"adversarial nations"), despite polysilicon tariffs being
  widely understood as China-directed. `classify_relevance` correctly
  said NO per its own explicit-mention bar, and — this is the real
  finding — **the new flag_for_review() system caught it exactly as
  designed**, its first real catch this session: sitting in
  `flagged_for_review.md` with the model's own reasoning for a human to
  weigh in on, not silently dropped.
- A MOFCOM item (a national-security trade investigation into imported
  printing/copying equipment) that ground truth frames as "in the
  broader context of ongoing trade tensions with the U.S." — but the
  source text itself never names the US/America anywhere (only generic
  "外国"/"foreign"), so `CHINESE_RELEVANCE_KEYWORDS`'s free pre-filter
  correctly (given what's actually on the page) skips it before any LLM
  call happens at all. This is a real, accepted limitation, not a bug:
  the free pre-filter's entire cost-saving purpose is to reject items
  with no explicit connecting keyword without spending an LLM call, and
  this ground-truth judgment relies on broader real-world context (this
  probe being understood as targeting US-based suppliers) that isn't
  recoverable from keyword matching, or arguably even from an LLM call on
  this text alone. Loosening the filter to catch cases like this risks
  reintroducing the exact cost problem the filter exists to solve. Left
  as-is — flagged here for the record, not fixed.

## 2026-09-01 continued — Aug 11-17, 2026 week: 10/13 queued before fixes; 2 real bugs found+fixed, 1 genuine limitation

10/13 dispatchable queued, 10/10 kind-matched, 3 not-queued:

**Bug #17 (real, fixed) — a whitehouse.gov "release" that's just a stub
page pointing at a PDF was never actually read.** "The Great
Transshipment Scam" (a real 25-page OTMP report, past-tracker entry) —
the fetched page text was only 107 characters: "Releases | The Great
Transshipment Scam | The White House | ... | Download". The real content
lives at a separate PDF URL the stub page links to
(`.../wp-content/uploads/2026/08/The-Great-Transshipment-Scam.pdf`),
never followed. `classify_relevance`/`extract_key_paragraphs` correctly
found nothing relevant in text that was never the real report — same
failure shape as bug #9 (PDF-as-HTML) but one layer up: this time the
PDF link exists but was never even fetched. Fixed with a new
`_resolve_pdf_stub()`: if the extracted page text is suspiciously short
(<300 chars) and the page has a `.pdf` link, follow it and extract THAT
instead. Wired into both `process_whitehouse_item_by_url` and
`scrape_whitehouse`'s RSS loop. Verified live: now correctly fetches the
real PDF, finds 4 relevant paragraphs, queues as `release`. Written
generally enough to reuse if another source turns out to have the same
stub-page-plus-PDF pattern.

**Bug #18 (real, fixed) — a bare "AI" keyword matched inside "AIrcraft"
and wasted an LLM call.** Investigating a not-queued UAS/drone import
proclamation revealed `US_SOURCE_RELEVANCE_KEYWORDS.search()` matched
"AI" at position 51 — inside "Unmanned **AI**rcraft Systems". Root cause:
`RELEVANCE_KEYWORDS`'s pattern was `\b(?:...)` — a word boundary
required only BEFORE the alternation, never AFTER. A short alternative
like bare "AI" only needs to start at a word boundary (true for the "A"
that begins "Aircraft") — with no trailing `\b` required, matching just
the first two letters of a much longer, unrelated word was good enough.
Same risk for "chip" inside a longer word, etc. This didn't cause a WRONG
inclusion here (`classify_relevance`'s own LLM judgment still correctly
said no further down the pipeline, and this document genuinely never
mentions China anywhere in 24K characters) — but it's a real, silent
cost bug: the free keyword pre-filter's whole point is to skip an LLM
call for free when there's truly no signal, and a phantom match defeats
that. Fixed by extracting the alternatives into `_RELEVANCE_ALTERNATIVES`
(previously `RELEVANCE_KEYWORDS.pattern` itself, hackily string-surgered
via `.rstrip(")")` to build `US_SOURCE_RELEVANCE_KEYWORDS` — fragile, and
would have broken outright if a trailing `\b` had simply been appended to
the old pattern string) and compiling BOTH patterns from it with a proper
`\b(?:...)\b` — closed on both ends. Verified: "aircraft" no longer
matches; genuine matches ("tariff", "export control", "artificial
intelligence", bare "AI" in "the AI race", "U.S.") all still do.

**Genuine limitation, not fixed**: an MND Q&A (spokesperson Chen Xi on
Japan's "neo-militarism" defense budget) that ground truth frames as
relevant "including due to the U.S-Japanese alliance relevance" — checked
all 9 paragraphs of the actual bilingual page content directly, and NONE
of them mention the US/America/any US official anywhere; the entire
exchange is about Japan and WWII-era history. Same category as this
session's other implicit-context judgment calls (South China Sea,
polysilicon) — the ground truth's US-alliance framing is a real-world-
context inference beyond what's actually stated in the source, not
something recoverable from this text by any classifier, keyword or LLM.
Not fixed; documented for the record.

## 2026-09-01 continued — Aug 18-24, 2026 week: clean sweep

10/10 dispatchable queued, 10/10 kind-matched, zero mismatches, zero
not-queued. All of today's fixes (regex-first Q&A parsing, bracket/
orphan-label handling, the {0,40} quantifier, the distinct-non-asker-name
heuristic, the PDF-stub follow, the keyword-boundary fix) holding up
clean on a week none of them were tuned against specifically.

## 2026-09-01 continued — Aug 25-31, 2026 week: last untested week in the Present tracker, both misses external

9/11 dispatchable queued, 9/9 kind-matched, 2 not-queued — both
`www.scio.gov.cn` (Chinese domain) URLs, both confirmed live returning
HTTP 521 (Cloudflare: origin server down) — the exact same documented,
site-side outage from SOURCES.md, not a code bug. Nothing to fix.

**This closes out the Present tracker's full range (2026-06-23..08-31,
all 8 weeks now tested)**: 0 → 1 → 8 → 13 → 15 → 14 (original week,
earlier sessions) plus 12/12, 17/18, 12/13, 11/13, 10/13, 10/10, 9/11
across the 7 newly-added weeks this session — with every kind-mismatch
found either fixed (bugs #13-#18) or confirmed external/genuine judgment
call. No further known code bugs against this tracker file.

## 2026-09-01 continued — first real (non-backtest) run + bug #19: topic keywords ≠ US relevance within a Q&A block

User asked for a real, non-backtest run: wipe `tracker_output.docx` and
actually run `python3 scraper.py` to see genuine output, "don't cross
check with existing tracker." Backed up both `tracker_output.docx` and
the real `tracker.db` (2,325 seeded URLs from all 4 past-tracker files)
before touching either. Since the real `tracker.db` already has this
whole week marked seen (from the past-tracker's own hyperlinks, now
extending through Aug 31), a run against it would find nothing new — used
a fresh empty dedup DB for this demo instead, swapping the real one back
afterward.

**Learned mid-run (user caught it, not me): an empty dedup DB doesn't
bound output to "one week."** `scraper.py` has no date-range concept —
it processes whatever's "new" (not yet in the dedup DB) up to 30 items
per source. In real operation that stays close to a week because
everything older is already marked seen; with an empty DB, a source with
a deep list-page backlog (MFA leadership speeches) just dumps its entire
visible history. Stopped the run once this became clear. Because entries
only flush to the doc after each *source* fully completes, only FMPRC's
two sources (12 entries, genuinely Aug 24-31 — that particular list page
only ever shows recent days) made it into the file; MFA leadership
speeches' 17+ queued-but-unflushed entries were safely discarded, nothing
corrupted.

**User then read the actual output and found two real issues by direct
inspection** — exactly the kind of check `backtest.py` can't do (it only
verifies known ground-truth URLs classify correctly; it doesn't catch
over-inclusion of things that were never in the ground truth to begin
with):

**Bug #19 (real, fixed) — `filter_relevant_exchanges` used the broad
topic-keyword list, not an actual US-mention check.** Two exchanges in
the generated output had nothing to do with the US at all: a Beijing
Daily/Lin Jian exchange about humanoid robots ("cooperation on
artificial intelligence...with all other countries") and an NHK/Lin Jian
exchange about Japan ("erroneous remarks and actions on Taiwan made by
those running the Japanese government") — a purely China-Japan dispute.
Both got included because `filter_relevant_exchanges` checked the broad
`RELEVANCE_KEYWORDS` list (Taiwan, artificial intelligence, semiconductor,
etc.) rather than an actual US-mention — and a single FMPRC daily
conference covers many different bilateral stories, so a shared topic
keyword without the US actually being part of that specific exchange is
common, not rare. Confirmed directly: `RELEVANCE_KEYWORDS.search()` hit
"artificial intelligence" and "Taiwan" respectively, both false signals
for these two exchanges specifically. Root issue: `RELEVANCE_KEYWORDS`
mixes "explicit US reference" terms with "topic the US also cares about"
terms, and `filter_relevant_exchanges` — unlike `classify_relevance`,
which has an LLM judgment downstream to catch a loose keyword hit — has
NO downstream check, so a loose keyword list there directly causes
over-inclusion. Fixed with a new `_EXPLICIT_US_MENTION_RE` (just the "US
references"/"US officials" terms — U.S./United States/America/Washington/
named officials, no topic words at all) used specifically in
`filter_relevant_exchanges`; `RELEVANCE_KEYWORDS` itself is unchanged and
still used (via `_RELEVANCE_ALTERNATIVES`) for `US_SOURCE_RELEVANCE_
KEYWORDS`'s free whole-document pre-filter, where looseness is fine.
Verified: both false-positive blocks now correctly dropped; a synthetic
Trump/tariff block with explicit "U.S."/"United States" still correctly
kept. Matches the user's own stated rule for this judgment call from
early in the project: an explicit US mention, not a shared topic.

**Investigated a claimed miss, found it wasn't a bug**: user also noted a
real SCIO item (China responding to US Iran sanctions, naming Bessent
explicitly) was missing from the output. Traced it: this is a genuine
SCIO article, and `scio` runs late in `main()`'s source order — the
killed run never got that far (stopped 3 sources in, well before `scio`).
Verified live: `process_scio_item` on the real URL queues it correctly on
its own. Not a bug — an artifact of stopping the demo run early, nothing
to fix.

Both of the day's earlier-tested weeks (and today's live-fetched
conferences) were re-verified live against these two specific findings
before reporting back — the Aug 25, 2026 FMPRC conference (which
legitimately DOES discuss Bessent/Iran explicitly, a different exchange
within the same conference than the SCIO article) correctly keeps that
block and correctly drops nothing it shouldn't under the new filter.

## 2026-09-01 continued — repo reorganization, .env rewrite, gitignore, and a real speed fix

User asked for four things: (1) reorganize the folder / remove unnecessary
files, (2) rewrite `.env`/`.env.example` comments for a non-programmer
(which keys are required vs. optional, and where to get each), (3) update
`.gitignore` accordingly, (4) look into speeding up a run without losing
accuracy.

**Reorganization**: introduced `data/` (everything the pipeline generates
at runtime — `tracker.db`, `tracker_output.docx`, `usage_log.jsonl`,
`flagged_for_review.md`, `x_accounts_state.json`) and `reference/`
(standalone reference material — the original source-list docx,
`sample_qa.txt`). `DATA_DIR = "data"` added to `scraper.py`, with
`os.makedirs(DATA_DIR, exist_ok=True)` at import time so the directory
exists before any of the path constants below it are ever used, regardless
of which script (`scraper.py`/`backtest.py`/`format_entry.py`/
`seed_dedup_db.py`) imports them first — `DB_PATH`/`DOC_PATH`/
`FLAGGED_REVIEW_PATH`/`USAGE_LOG_PATH`/`X_STATE_PATH` all rebuilt as
`os.path.join(DATA_DIR, ...)`. `format_entry.py`/`seed_dedup_db.py` needed
no code changes at all — they import these constants by name rather than
hardcoding the paths, so they picked up the new location automatically.
`run_daily.sh`'s hardcoded `tracker.db` existence check updated to
`data/tracker.db`. Removed `.DS_Store` and `__pycache__/` (regenerable
junk). Also found and untracked `~$acker_output.docx` — a Microsoft Word
lock/temp file that had somehow actually been committed to git at some
point; added `~$*.docx` to `.gitignore` and `git rm --cached` it (staged,
not committed — the user's next commit will finalize the removal).
Verified nothing broke: all four entry points still compile and run
(`scraper.py --help`, `format_entry.py --help`), and the real `tracker.db`
(2,325 seeded URLs, restored from the demo-run swap earlier today) loads
correctly from its new location.

**`.env`/`.env.example` rewrite**: previous version documented only 4 of
what are now 5 real keys (missing `GROK_API_KEY`/`X_API_KEY` entirely) and
assumed programmer-level context. Rewrote for a non-coder: explicit
REQUIRED/OPTIONAL section headers, plain numbered sign-up steps per key,
which exact field to copy (the X API mixup from earlier today — grabbing
"API Key" instead of "Bearer Token" — is called out explicitly), a direct
warning that `GROK_API_KEY` (xAI) and `X_API_KEY` (X/Twitter) are
different products despite the similar name and shared owner, and realistic
cost framing for the two paid ones (Grok, X) instead of just calling them
"optional." Edited the real `.env` file's comments to match WITHOUT ever
reading or displaying its actual secret values — used `sed`/a small Python
script matching only on the `KEY=` prefix to insert comment lines above
each key, then verified via a value-redacted diff and a live `load_dotenv()`
check that all 5 keys still load with unchanged values.

**`.gitignore`**: collapsed the individual runtime-file entries into one
`data/` line (now that they all live there), added `~$*.docx` for the Word
lock-file issue found above.

**Bug #20 (speed, no accuracy change) — `call_llm`/`call_llm_json` slept
16s before EVERY Gemini attempt, even ones already known-doomed.** Once
Gemini's daily quota is exhausted (routine by midday in every session
today), every subsequent LLM call still paid the full `GEMINI_SLEEP` tax
before attempting Gemini, immediately 429ing, and falling to the fallback
chain anyway — across a real ~150-call run that's 40+ minutes of pure
sleep "confirming" something already learned minutes earlier. Added a
Gemini cooldown tracker (`_gemini_on_cooldown()`/`_start_gemini_cooldown()`,
a module-level `time.monotonic()` timestamp): on any 429, skip straight to
the fallback chain — no sleep, no attempt — for 120 seconds, rechecking
periodically rather than disabling Gemini outright for the rest of the run
(in case it was a transient RPM blip rather than the daily cap; RPM clears
in seconds, and `GEMINI_SLEEP` already paces correctly for that case, so a
429 despite proper pacing is far more likely the daily cap — but this
doesn't assume that, it just checks back every 2 minutes rather than never).
Zero accuracy impact — this only changes how fast the code discovers what
it was already going to discover, not which provider ends up serving a
call or what that provider is asked. Verified the state-transition logic
directly (`_gemini_on_cooldown()` false initially, true immediately after
`_start_gemini_cooldown()`, ~120s remaining).

**True parallelism (running multiple sources concurrently) was explained
to the user but NOT implemented this session.** The real bottleneck
(Gemini's per-account RPM) is shared across any number of threads — more
threads can't call Gemini faster than the account's limit allows, so
concurrency's actual benefit is letting each source's non-Gemini work
(HTTP fetches, HTML parsing, Groq/OpenRouter/Grok calls — all separate,
higher-limit accounts) overlap in wall-clock time instead of one source
blocking the next. Real, but requires: a single shared rate limiter/lock
around actual Gemini calls (so concurrent threads don't collectively
exceed the true account-wide RPM — a per-thread sleep alone would NOT
prevent that), thread-safe SQLite access (a shared connection isn't safe
across threads without care — separate connections + WAL mode, or a
lock), and safe concurrent appends to `PENDING_ENTRIES`/the shared
`Document` object. Deliberately not attempted today, right after a long
day of careful correctness fixes across this same file — the risk of a
subtle race-condition bug (e.g. two threads' entries interleaving under
the same date heading, or a lost SQLite write) outweighs the wall-clock
win for a first pass. Flagged in README.md's new "Speed" section as a
real, well-scoped follow-up if run length becomes a recurring problem.

## 2026-09-01 continued — one more reorganization pass: separate code from everything else

User feedback on the first reorganization: still too many `.py` files
sitting loose at the project root for someone unfamiliar with code, and
`data`/`reference` as folder names didn't say what was actually inside.
Second pass:

- **`code/`**: `scraper.py`, `backtest.py`, `format_entry.py`,
  `seed_dedup_db.py` — every Python file, moved out of the root entirely.
  `run_daily.sh` and `README.md` stay at the root as the actual "how do I
  use this" surface a non-programmer interacts with; they now invoke
  `python code/scraper.py` etc.
- **`docs/`**: `NOTES.md`, `SOURCES.md` moved here. `README.md` stays at
  the root (GitHub/most tools expect it there and render it automatically).
- **`data/` → `generated-output/`**: same contents, name says what's
  actually in it.
- **`reference/` → `reference-materials/`**: same contents, ditto.

`DATA_DIR` in `scraper.py` renamed from `"data"` to `"generated-output"` —
this is the only code change the whole move required, since `DATA_DIR`
(like every other relative path in this project — `past-trackers/`, etc.)
resolves against the current working directory at runtime, not the
script's own file location. Moving `scraper.py` itself into `code/`
doesn't change this: as long as these scripts are invoked from the
project root (e.g. `python code/scraper.py`, not `cd code && python
scraper.py`), every relative path still resolves exactly where it did
before. `format_entry.py`/`seed_dedup_db.py`/`backtest.py` needed zero
code changes beyond their own docstrings/help text — they import
`scraper`'s path constants by name, and Python resolving `import scraper`
from a sibling file in the same directory (`code/`) works unchanged.
`run_daily.sh` didn't need its `cd "$(dirname "${BASH_SOURCE[0]}")"` line
touched either, since the script itself stayed at the root — only its
internal `python3 seed_dedup_db.py`/`python3 scraper.py` calls needed the
`code/` prefix added.

Verified thoroughly before calling it done: compiled all four scripts,
then actually ran each one's real entry point from the project root
exactly as documented in the new README (`--help` for three of them,
`--dry-run` for `seed_dedup_db.py`, which correctly reported 2,374 known
URLs and 111 new ones against the real seeded database at its new
location) — not just a compile check, an actual invocation of the
documented command for each.

Left `docs/NOTES.md`'s own past entries referring to the OLD `data`/
`reference` names as-is — this file is a dated work log describing what
was true at each point in time, not a living reference document; rewriting
history in it to match today's naming would defeat its purpose. Only
`docs/SOURCES.md` (a living reference, not a log) had its `reference/`
mention updated to `reference-materials/`.

## 2026-09-01 continued — third and final reorganization pass

User asked one more round of clarity fixes, plus a real question: is
`apps-script/` used for anything besides the standalone Google Docs tool?
Checked directly rather than assume — grepped every `.py` file for any
mention of `apps-script`/`Code.gs` (found exactly one, a comment crediting
where a design idea came from, not an import or a call) and grepped
`Code.gs` for any mention of a `.py` file (found none) and read
`appsscript.json` (a standard Google Apps Script manifest — OAuth scopes
for accessing Google Docs directly from within Google's own environment,
nothing project-specific). Confirmed: fully standalone, paste-into-a-
Google-Doc tool with zero functional connection to the Python pipeline in
either direction.

Renamed accordingly:
- `apps-script/` → `googledoc_autoformat_extension/` (name now says what
  it actually is)
- `references/` → `input/` (top-level parent)
- `references/past-trackers/` → `input/past_trackers/` (hyphen → underscore,
  matching this project's other multi-word folder names)
- `references/docs/` → `input/notes/`

Updated every live reference across `scraper.py`, `backtest.py`,
`seed_dedup_db.py`, `run_daily.sh`, `README.md`, and `docs/SOURCES.md`
(now `input/notes/SOURCES.md`) — including the one apps-script comment in
`scraper.py` itself, since that's living code documentation, not a dated
log entry, unlike this file. Verified for real again, not just compiled:
`seed_dedup_db.py --dry-run` correctly found all 2,374 known URLs at
`input/past_trackers/` against `output/tracker.db`, and `scraper.py`'s
`DB_PATH`/`DOC_PATH` constants resolve to the new `output/` location.

This file (`input/notes/NOTES.md`) still has old-name mentions in its own
earlier, dated entries above (`data/`, `reference/`, `docs/`,
`apps-script/`) — left alone on purpose, same reasoning as the previous
pass: a work log describes what was true at each point in time, and
rewriting it to match today's names would erase that.

## 2026-09-01 continued — bug #21: mark_seen() could commit before its entry was ever durably written

User asked "what else needs improvement," which surfaced a real,
previously-undiscussed correctness gap while thinking through their
"which week" question: every `process_*_item()` function called
`mark_seen(conn, url)` immediately upon deciding an item was relevant —
in the same breath as `queue_entry()`, which only appends to the
in-memory `PENDING_ENTRIES` buffer. That buffer isn't written to disk
until `flush_pending_entries()` runs, once per SOURCE (not once per item)
— see the PENDING_ENTRIES design comment from 2026-08-04 explaining why
per-source batching exists (collapsing repeated date headings). A crash
or kill between "mark_seen() committed to tracker.db" and "this source's
flush actually ran" permanently marks the item seen — so it's never
retried — while its real content never made it into the doc: silent,
PERMANENT data loss. This is a different, worse failure mode than the
per-item exception handling already in place elsewhere (an exception
raised INSIDE a process_*_item, before reaching queue_entry+mark_seen,
correctly leaves the item unmarked and eligible for retry — see the SCIO
transient-failure investigation earlier today). The demo-run kill earlier
today (mfa_leadership_speeches' 17 queued-but-unflushed entries) happened
to be harmless only because that demo used a throwaway dedup database
discarded right after — against the REAL `tracker.db`, the exact same
kill would have permanently lost those 17 items with no trace.

**Fixed**: moved `mark_seen()` out of every individual `process_*_item()`
call site's "queued" path (5 call sites: `finalize_qa_item`'s two return
points, `finalize_release_item`'s two, and `process_x_tweet`) and into
`flush_pending_entries()` itself, AFTER `doc.save()` succeeds — so an item
is only ever marked seen once its content is confirmed durably written,
not merely "decided to be written." `flush_pending_entries()`'s signature
changed to take `conn` (previously just `doc`) — its one real call site,
in `main()`'s `run()` wrapper, already had `conn` in scope. The "not
relevant, skip" `mark_seen()` calls (11 of the original 17) were left
completely unchanged — there's no pending write to protect for those,
marking a skip immediate is already safe. `format_entry.py`'s own
doc-writing path is unaffected — it calls `add_qa_entry`/`add_release_entry`
directly, bypassing `queue_entry`/`flush_pending_entries`/`mark_seen`
entirely (it's a one-off manual tool with no dedup concept).

Verified precisely, not just compiled: queued a synthetic entry, confirmed
`is_seen()` is `False` immediately after (proving a crash here would now
correctly leave it retryable), then called `flush_pending_entries()` and
confirmed `is_seen()` flips to `True` only after. Re-ran the exact same
check against a real live FMPRC item end-to-end (through the "release,
not really Q&A" reroute branch specifically, since that one has its own
separate return point) — same result, real content, real translation.

## 2026-09-01 continued — bug #22: the same mark_seen/flush ordering mistake, again, in X's since_id bookkeeping

Kept looking per user's "any other bugs? keep going" — found the SAME
architectural mistake as bug #21, in a different subsystem. `scrape_x()`
was updating and saving `output/x_accounts_state.json`'s `since_id`
per-account, IMMEDIATELY after that account's tweets were processed —
but `scrape_x()` covers all 11 accounts as ONE "source," flushed once
after the whole function returns. A crash between "since_id saved for
account N" and "the eventual flush" would permanently exclude account N's
tweets from ever being fetched again (X's `since_id` API parameter
excludes anything at or before it) — worse than bug #21's version, since
here we'd have ALREADY PAID X real money to read those tweets with
nothing to show for it, not just risked a doc write. `is_seen()` still
protects against actual DUPLICATE entries either way (it's the real
dedup, `since_id` is purely a cost-optimization to avoid re-billing
already-checked tweets) — the risk here was tweets becoming permanently
unreachable, not double-counted.

**Fixed**: `scrape_x()` now stages each account's prospective new
`since_id` in a module-level `_PENDING_X_SINCE_IDS` dict instead of
saving immediately; `flush_pending_entries()` persists it to
`x_accounts_state.json` right after its own doc.save() (or immediately,
if there were zero doc entries this flush — a run where every tweet was
correctly judged irrelevant still deserves its since_id advanced, so
future runs don't needlessly re-fetch/re-bill the same rejected tweets).

Verified by actually reproducing the crash, not just simulating it: ran
a real live `scrape_x()` across all 11 accounts, killed the process
mid-way through the first account (@ChineseEmbinUS) after real tweets had
already been read and billed ($0.15 for 30 tweet reads) and several had
already been queued. Diffed `x_accounts_state.json` before/after: the
account's `user_id` (cached separately, immediately, by `_x_get_user_id`
— a real, safe-to-save-eagerly cost optimization with no data at risk)
was present, but `since_id` was correctly ABSENT — confirming the exact
crash this fix targets leaves no trace of the risky state, exactly as
intended, under a genuine kill rather than a synthetic test.

## Bug #23 — classify_relevance()'s "does this mention China" bar is meaningless for a Chinese-government account's own posts

Found investigating that same live 11-account run's actual output before
killing it: a Chinese Embassy tweet — "China's digital publishing
industry continues to grow, with AI tools supporting content creation…" —
got queued despite having ZERO mention of the US anywhere. Several more
in the same run: Xinjiang disaster relief, desertification control,
"smart farming" in Turpan vineyards — all generic PRC soft-power content,
none involving the US. Re-tested the exact wording directly:
`classify_relevance` returned YES, reasoning only that the text "directly
referenc[es] China."

**Root cause**: `classify_relevance`'s prompt ("Reply YES only if this
explicitly and substantively involves China... OR a direct US-China
policy action") was written for US-ORIGIN sources (state.gov,
whitehouse.gov, FMPRC/MOFCOM Q&A blocks) where "does this mention China"
is a meaningfully rare, relevant signal. Applied to a PRC-government
account's OWN feed, that first clause is satisfied by nearly everything
they post — their tweets are trivially "about China" by construction.
Exact same category of mistake as bug #19 (a shared topic isn't the same
as actual relevance), just discovered in a third place.

**Fixed**: added `_PRC_X_ACCOUNTS` (the 3 PRC-government accounts:
ChineseEmbinUS, SpoxCHN_LinJian, SpoxCHN_MaoNing) and branched
`process_x_tweet` — for these three specifically, skip `classify_relevance`
entirely and require `_EXPLICIT_US_MENTION_RE` (the same narrow "explicit
US/named-official mention" pattern built for bug #19) instead. Cheaper
too: a free regex check instead of an LLM call for the vast majority of
these accounts' output, which is generic PRC content with no US angle at
all. Verified against the exact three tweets from the live run: the
digital-publishing and Turpan-farming tweets (no US mention) now
correctly excluded with zero LLM calls; a synthetic tweet mentioning
"Washington"/"US-China trade" still correctly included.

## 2026-09-01 continued — built code/test_scraper.py, an offline regression suite; it immediately found 3 more real bugs

Per user request ("I want this to be a product with no bugs") — the
highest-leverage next step wasn't more live testing, it was converting
today's ad hoc verification snippets (written once, checked, thrown away)
into a real, permanent test suite. Built `code/test_scraper.py` using
Python's built-in `unittest` (no new dependency — matches this project's
"keep setup simple" convention), covering every pure-logic function
behind today's bugs #13-#19: `_classify_by_labels`, `_build_exchanges`,
`_merge_orphan_speaker_labels`, `_unbracket_label`,
`RELEVANCE_KEYWORDS`/`_EXPLICIT_US_MENTION_RE`,
`select_relevant_chinese_paragraphs`/`_CHINESE_US_MENTION_RE`, and the
mark_seen/flush ordering fix (#21/#22). No network access, no LLM calls,
no API keys needed, runs in 0.02s — deliberately scoped to only the parts
that are pure functions of their input; `backtest.py` remains the tool
for anything needing a live fetch or an LLM judgment.

**It found 3 more real bugs on its very first run** — exactly the point
of building it:

- **`_unbracket_label` never actually handled genuinely untranslated
  Chinese punctuation**, despite explicitly trying to: `_BRACKETED_LABEL_RE`
  accepted both `[`/`【` for the bracket but only the ASCII `:` for the
  colon, never the fullwidth `：` (a different Unicode character,
  U+FF1A vs U+003A) that would plausibly survive alongside untranslated
  brackets. Fixed to accept either.
- **Bug #18's own fix broke ordinary plurals.** Adding a trailing `\b` to
  `RELEVANCE_KEYWORDS` (to stop "AI" matching inside "AIrcraft") also
  silently stopped "tariff" from matching inside "tariffs" — a boundary
  exists between "tariff" and its own "s" suffix, same mechanism, just
  now working against a legitimate plural instead of a false positive.
  "tariffs"/"sanctions"/"chips"/"semiconductors"/"export controls" are at
  least as common as their singular forms in real headlines. Fixed by
  adding `s?`/`(?:y|ies)`/`(?:es)?` to every affected term
  (tariff, trade war, sanction, export control, import duty, chip,
  semiconductor, technology transfer, exchange rate policy, trade
  deficit, trade surplus, forced transfer). A regression traded for a
  fix, caught only by writing the test — the live testing that found the
  original AI/aircraft bug never happened to hit a plural-form document
  afterward to notice.
- **Bug #16's fix had its own latent regression**, and this was the
  interesting one: testing `_classify_by_labels` against a REAL
  historical case referenced earlier this session — an FMPRC transcript
  with "A Tarde"/"The New York Times"/"Antara" asking and Lin Jian
  answering (the exact transcript that motivated the `.search()` vs.
  `.match()` fix on 2026-08-04) — failed. "A Tarde" and "Antara" are both
  real foreign wire/outlet names not in `_KNOWN_OUTLETS_RE`'s necessarily-
  incomplete curated list, so they got miscounted as additional
  "answerers," pushing the non-asker-name count to 3 and wrongly flipping
  a genuinely correct transcript to "release" under the distinct-count-
  only rule. Fixed the rule's SHAPE, not just patched around this one
  case: "release" now requires BOTH 3+ distinct non-asker names AND none
  of them repeating — a repeating name (Lin Jian, 3x) still correctly
  signals "this is the answerer" regardless of how many other one-off
  names (recognized outlets or not) sit alongside them, while the USTR
  media-roundup case (8 distinct names, zero repeats) still correctly
  fails both conditions. This is a case where "spot-check the 3-4 cases
  you have on hand" (what live-testing verification naturally does) isn't
  enough — a case NOT actively being tested that day silently broke, and
  only a suite that keeps EVERY past case alive as a permanent test would
  have caught it before it shipped.

All 32 tests pass after the three fixes above. Re-verified the real USTR
case live end-to-end one more time (not just via the synthetic test data)
to be thorough after rewriting `_classify_by_labels`'s core logic —
correctly still "release".

- **`translate_to_english`'s chunk size (5500) was arbitrary and
  undocumented**, found via code review, not live testing: `grep -n
  "5500"` across NOTES.md turned up no reason it was ever set to that
  number, while every real call site (4 of 5 — the FMPRC/Treasury/State/
  MND item processors) truncates its input to exactly 7000 chars before
  ever calling this function. That meant almost every real Chinese
  document translated by this pipeline (most exceed 5500 chars once
  truncated to 7000) was being needlessly split into 2 chunks: an extra
  LLM call every time, and — worse — each chunk is translated
  independently and joined with `"\n\n".join(...)` with no merge logic
  across the boundary, so a split landing right after an orphan "问："/
  "答：" label (content starting in the NEXT chunk) would silently
  orphan that label from its content across the join — the same failure
  shape as bugs #13/#14, just one layer up. gemini-2.5-flash's real
  context window (~1M tokens) makes chunking at 7000 chars (~2000
  tokens) pointless. Raised the chunk size to 10,000 — comfortably above
  every current caller's max input, so none of them chunk in practice —
  while keeping the loop (not removing it) so a future caller passing
  something longer still degrades safely instead of hitting an unbounded
  single request.

  **Caught a self-introduced bug while making this exact fix**: the
  first edit dropped the `parts = []` initialization before the loop
  (`parts.append(translated)` referencing a name that was never bound),
  which would have crashed on every single real call — this function had
  no test coverage (it needs a live LLM call, so it's excluded from
  `test_scraper.py` by design) and the crash was only caught because the
  fix was live-verified against a real document instead of just
  compiled. `python3 -m py_compile` had already passed clean, since a
  `NameError` on an unbound local is only a runtime error, not a syntax
  one — compiling clean is not evidence a function works. Fixed by
  adding `parts = []` back before the loop.

  Verified live end-to-end against the real MOFCOM "China's Position on
  the So-called 'Overcapacity' Issue" position paper (11,812 raw chars,
  well over 5500 once truncated to 7000): the usage log shows exactly
  ONE `translate` call (`usd=$0.0149`, `total=10112` tokens) for the
  7000-char input, where the old 5500-char chunk size would have produced
  two. All 38 offline tests still pass after both changes.

- **Continued the "go through everything" review pass** into the
  remaining areas flagged earlier as unreviewed
  (`_relevance_snippet`/`extract_main_text`/`KNOWN_NAME_ROMANIZATIONS`/
  the WP-API `item_url` theoretical type gap/the X malformed-JSON
  theoretical gap/MFA leadership date parsing). Findings:
  - `_relevance_snippet`, `extract_main_text`, `extract_pdf_text`,
    `KNOWN_NAME_ROMANIZATIONS`, `RELEVANCE_KEYWORDS`/
    `_EXPLICIT_US_MENTION_RE`'s `\b` boundaries, and MFA leadership's
    URL-date regex (`t(\d{8})_`, degrading to `utcnow()` if absent) all
    checked out — no bugs found, already correctly reasoned and
    documented from earlier fixes this session.
  - **`item_url()` hardened**: its `guid` fallback only ever actually
    fires for a WP-API item missing "link" (RSS items always carry a
    resolved "link" string — `parse_rss` already folds its own guid
    fallback in). A WP-API item's raw `guid` field is
    `{"rendered": "..."}`, a dict, not a string — the old
    `item.get("link", item.get("guid", ""))` would have returned that
    dict as if it were a URL, silently poisoning dedup/sqlite/doc
    hyperlinks downstream. Every real source currently used happens to
    include "link", so this was never hit live — hardened anyway (now
    unwraps a dict guid's "rendered" key) rather than left as a latent
    trap for the day a future source omits it. Added
    `TestItemUrl` (5 cases) to `test_scraper.py` — 43 tests total, all
    passing.
  - **The X malformed-JSON gap (`_x_get_recent_tweets`/
    `_x_get_user_id`'s unguarded `resp.json()`) needs no fix**: traced
    `main()`'s `run()` wrapper and confirmed every source function,
    `scrape_x` included, already runs inside a per-source
    `try/except Exception` that logs and moves on, followed
    unconditionally by `flush_pending_entries()` — so a malformed X
    response would be caught, logged, and safely flushed around, not
    crash the whole scraper or lose already-queued entries from other
    accounts processed earlier in the same run. Confirmed rather than
    fixed: there was nothing to fix.

## 2026-09-02 — forward-looking note: multi-user web service would need de-globalizing pending state

User is considering a future dashboard/web service (Google login, users
supply their own API keys, pick a week, get a progress bar and a
downloadable doc). Evaluated feasibility rather than building it — verdict:
straightforward as a product (auth, encrypted key storage, and a job queue
are standard patterns), and it wouldn't change per-run token cost or
runtime at all, since those are dominated by Gemini's RPM pacing regardless
of what triggers the run.

One real prerequisite found while evaluating: this file currently relies on
several **module-level mutable globals** that assume one run/one process/
one user at a time — `PENDING_ENTRIES`, `_LAST_WRITTEN_DATE`,
`_PENDING_X_SINCE_IDS`, `_gemini_retry_after`. Fine for the current cron/CLI
usage; a real bug risk the moment two users' jobs could ever execute
concurrently in the same worker process (e.g. user A's pending entries
getting flushed into user B's doc, or B's run seeing A's Gemini cooldown
state). Not fixed yet — flagging here so it's addressed BEFORE multi-tenant
use, not discovered as a race-condition bug after.

## 2026-09-02 continued — one-command weekly run for a non-technical user

User's actual near-term need isn't a web dashboard (evaluated separately,
above) but just making the existing CLI trivially easy for their boss to
run by hand. Added:

- **`default_week_range()`**: the tracker's week is Tuesday-through-Monday
  (established earlier this session). Formula: `end` = the most recent
  Monday on or before today (today itself if today IS Monday), `start` =
  the Tuesday 6 days before. One formula, no special-casing — verified
  directly that Monday and every day of the following week (Tue-Sun) all
  resolve to the identical completed week, per the user's explicit spec
  ("run on Monday" and "run on Tuesday" should give the same range).
  4 new tests in `test_scraper.py` lock this in (`TestDefaultWeekRange`,
  including a `subTest` loop over all 5 remaining weekdays) — 48 tests
  total, all passing.
- **`--start`/`--end` CLI flags** (YYYY-MM-DD), defaulting to the above.
  Deliberately used ONLY for the human-facing week label (progress bar
  header, dated doc filename, final summary) — NOT as a hard filter on
  which items get processed. The pipeline is already purely incremental
  (only touches URLs `is_seen()` hasn't marked), so a normal run already
  only picks up last week's new items on its own; adding a real date
  filter on top would risk silently dropping genuine backlog content if a
  run is ever skipped/delayed — worse than an occasionally-imprecise
  label. If a real backfill-by-date feature is wanted later, it needs a
  deliberate per-source design (some list pages carry a visible date,
  most don't until the item page itself is fetched), not just plumbing
  these two flags into is_seen()'s check.
- **Quiet-by-default console output**: previously every INFO log line
  (there can be 100+ in a full run) printed straight to the terminal,
  which would have buried a progress bar entirely on the same screen.
  Split logging into a FileHandler (still full INFO detail, always, to a
  new timestamped file under `logs/`) and a StreamHandler capped at
  WARNING by default — added `-v`/`--verbose` to restore full on-screen
  detail for actual debugging. Nothing about what's captured changed,
  only what's printed live.
- **Progress bar**: `tqdm`, one tick per source (18 total on a full run),
  description set to that source's human-readable name from `SOURCES`.
  Added `tqdm>=4.66.0` to requirements.txt — first new dependency in a
  while, deliberately minimal (no compiled extension, pure-Python).
- **Dated output copy**: after a run, `output/tracker_output.docx` (the
  ongoing master doc — kept as-is for dedup/history continuity) now also
  gets copied to `output/US-China Tracker <week label>.docx` — e.g. `US-
  China Tracker Aug 25-31, 2026.docx` — so a non-technical user has an
  obviously-labeled file to open/share for that week specifically,
  without needing to know which entries in the ever-growing master doc
  are new. `_format_week_for_filename()` handles a week that spans two
  months correctly (e.g. "Aug 25-Sep 1, 2026").
- **`run_week.sh`**: the actual one-liner — `./run_week.sh`. Seeds the
  dedup DB on first use, otherwise just runs `code/scraper.py` with
  whatever args are passed through. Kept `run_daily.sh` unchanged in
  spirit (still the quiet, log-to-file wrapper for an unattended cron/
  launchd job) — the two scripts now cleanly split "someone watching the
  terminal" vs. "nobody's watching, check the log later."

Live-verified end-to-end against a real single-source run
(`python code/scraper.py --source scio`, 2026-09-02): confirmed the
console stayed quiet (progress bar + eventual summary only) while
`logs/2026-09-02_104228.log` captured full INFO detail including real
new items being queued — file-vs-console split works as intended.

## 2026-09-02 continued — auto-shown run cost/time, run_daily.sh -> run_scheduled.sh, README cleanup

- **Auto-shown cost/time**: every run now ends with a third summary line,
  `Took <duration> — <N> tokens [+ M X reads], est. cost $X.XXXX.` —
  no more needing a separate `summarize_usage_log()` call to see what a
  given run cost. Added `_summarize_run_usage(since_ts)` (filters
  USAGE_LOG_PATH — a running log across the pipeline's ENTIRE history —
  down to just this run's own records by timestamp) and
  `_format_duration()` (47s / 16m 7s / 1h 05m). 6 new tests
  (`TestFormatDuration`, `TestSummarizeRunUsage`) — 54 total, all passing.
  `summarize_usage_log()` itself is untouched and still useful for an
  ALL-TIME total across every run ever made, now documented as such in
  README rather than as the only way to see cost at all.
- **`run_daily.sh` renamed to `run_scheduled.sh`** per direct user
  question ("is run_daily.sh like if I turn it on, then it runs without
  me ever giving it instructions?") — yes, once wired to cron/launchd it
  runs completely unattended, and the old name didn't communicate that
  ("daily" was already misleading — it's a weekly script). Updated every
  reference (README's two mentions incl. the launchd plist's
  ProgramArguments, run_week.sh's own comment, one scraper.py docstring
  mention) — NOT touching this file's own historical NOTES.md mentions,
  per this file's standing convention of preserving old names in past log
  entries.
- **README: removed the "Folder guide" table** (per user request — it's
  no longer needed now that `run_week.sh` is the one thing a
  non-technical user needs to know about) and added an explicit line that
  `X_API_KEY` is required specifically for the X source (previously only
  `.env.example`'s own comments said this — the README's Setup section
  still said "only GEMINI_API_KEY is required," which was correct for
  "runs at all" but read as contradicting `.env.example`'s "Required"
  section once the user put X_API_KEY there).

## 2026-09-02 continued — double-clickable launcher, no terminal needed

User's actual goal behind considering Claude Code as an interface was
"feels easier for my boss than the terminal" — evaluated that specifically
and recommended against it (adds a Claude-usage cost on top of the
already-tracked scraper cost, doesn't meaningfully lower the bar over
typing one already-simple command, and is less predictable run to run
than a deterministic script). The actual blocker (unfamiliarity with a
terminal) has a much cheaper fix: **`Run Weekly Tracker.command`** — a
double-clickable macOS launcher (Finder recognizes the `.command`
extension + execute bit, opens Terminal.app automatically, runs it). It
just `cd`s to its own folder and calls `run_week.sh`, then waits for a
keypress before closing so the summary stays readable. No new dependency,
no new cost, same underlying tested code path.

Not live-tested via an actual Finder double-click (can't drive Finder
from this environment) — verified instead via `bash -n` (syntax) and by
inspection that `cd "$(dirname "$0")"` is the standard, well-established
idiom for making a script self-locating regardless of where it's
double-clicked from. Flagged the one real caveat in README: if this file
is ever transferred to another Mac via AirDrop/email/download (setting
the com.apple.quarantine flag), the FIRST double-click may show an
"unidentified developer" warning — right-click → Open once clears it
permanently. Not an issue if the file is simply part of a cloned/copied
project folder placed directly on the target machine.

## 2026-09-02 continued — progress bar looked "frozen" on a slow source; real bug, not perception

User reported "Run Weekly Tracker.command" looked like it stopped, pasted
terminal output ending mid-percentage on "MFA leadership speeches
(Chinese): 11%". Checked `ps aux` — the process was still genuinely
running (confirmed alive), and its log file showed real, fresh content
(Xi Jinping's Sept 1 SCO summit speeches) being translated normally at
Gemini's paced rate. Not a hang, not a crash — a real UX gap: the
progress bar (added earlier today) only advances once per SOURCE, so a
source with several long new items sitting through Gemini's per-call
pacing can hold the same percentage for minutes at a stretch, which
reasonably reads as frozen to someone watching it.

Fixed at the actual choke point: `queue_entry()` — the one function every
`process_*_item()` across every source calls when something gets queued —
now prints `[N] found: <url>` via `tqdm.write()` (prints cleanly above the
active bar without corrupting it; a harmless plain print when no bar is
active, e.g. from backtest.py or a test) the instant each item is found,
independent of --verbose (this is a reassurance signal for a non-technical
user, not debug detail, so it always shows). New module-level
`_RUN_ITEM_COUNT`, reset to 0 at the top of main(). Compiled clean, all 54
tests still pass. Not re-verified against a fresh live run yet (the
in-progress run the user reported was already using the old in-memory
code and can't pick this up until its next invocation) — should confirm
the per-item lines actually appear next real run.

## 2026-09-02 continued — datetime.utcnow() deprecation warnings were also the "two bars" bug

User asked to suppress the `datetime.utcnow()` DeprecationWarning
cluttering the console, and separately asked whether the progress bar
could always be just one bar — turned out to be the SAME root cause.
`datetime.utcnow()` is deprecated as of newer Python versions and prints
a warning straight to stderr on every call; that warning text landing
mid-redraw of tqdm's `\r`-based single-line bar is exactly what split one
continuously-updating bar into what visually looked like two separate
bar lines in the user's pasted terminal output. Fixing the warning fixed
both complaints from one change.

Fix: added `_utcnow()` — gets the correct instant via the non-deprecated
`datetime.now(timezone.utc)`, then immediately strips tzinfo back off
before returning. Deliberately NOT switching to real timezone-aware
datetimes throughout: every date this pipeline stores/sorts/compares
(PENDING_ENTRIES's sort key, every process_*_item()'s date fallback,
item_date()'s strptime results) is naive, and introducing even one
timezone-aware datetime into that mix would raise `TypeError: can't
compare offset-naive and offset-aware datetimes` the moment a fallback-
dated item and a normally-dated item land in the same sort — a real,
easy-to-miss risk of an otherwise "obviously correct" modernization.
Replaced all 14 `datetime.utcnow()` call sites via `sed` (verified none
were missed via a full-file grep afterward). Live-verified: ran
`--source ustr` for ~8s and confirmed zero DeprecationWarning output and
a clean single bar line, vs. the interrupted double-line output from the
user's terminal-pasted evidence.

Also confirmed directly for the user: re-running against the same default
week is fully safe regardless of what's already in `tracker.db` —
dedup is URL-keyed and permanent, so a rerun only ever processes genuinely
unseen items; nothing gets duplicated no matter how many times the same
nominal week is targeted.

**Real gap surfaced by this exact exchange, not yet fixed**: the run the
user terminated was labeled "Aug 25-31, 2026" (correct default per
default_week_range() for a Wednesday) but was queuing MFA leadership
items dated September 1st — because, as documented when `--start`/`--end`
were added, the week range is used ONLY for the human-facing label/
filename, not as an actual filter on what gets processed (deliberately —
see that section above). This is fine in the steady-state weekly cadence
this was designed for (new-since-last-run ≈ last week's items), but
becomes visibly wrong the moment there's a real gap since the last run
(exactly what happened here, following a long multi-day testing session)
— the dated output file ends up mislabeled with a range narrower than
its actual contents. Flagged to the user as an open design question
(hard-filter by date vs. dynamically label from the actual min/max dates
queued vs. leave as an approximate label) rather than picking one
unilaterally, since it changes real behavior.

## 2026-09-02 continued — dated filename now labeled from actual content, not the requested week

Per user's choice (asked directly rather than picking unilaterally): the
dated doc filename and final "Done — N entries added for ..." summary now
derive their date range from what was ACTUALLY queued this run, not
week_start/week_end (which remain just the requested/expected range,
still shown in the header printed before the run starts). Added
`_extend_date_range(entries, current_min, current_max)` — a pure function
(not inline in main()'s closure) so it's directly testable — called once
per source right before its flush, extending a running (actual_min_date,
actual_max_date) across the whole run. Falls back to the originally
expected week_label only when a run finds nothing new at all (no real
content to derive a range from). When the actual range differs from what
was expected, the final summary now also prints an explicit note
("Expected X, but found content outside that range too — probably a gap
since the last run.") rather than silently relabeling with no
explanation. 4 new tests (`TestExtendDateRange`) — 58 total, all passing.

## 2026-09-02 continued — interactive date prompt in the double-click launcher

Added an interactive prompt to `Run Weekly Tracker.command` specifically
(not `run_week.sh`/`run_scheduled.sh` — those stay non-interactive since
a terminal/cron invocation shouldn't ever block waiting on stdin):

```
What would you like to run?
  1) Last complete week (just press Enter for this)
  2) A specific date range instead
```

Choosing 2 prompts for start/end dates with the format spelled out in
plain language + a worked example (year-month-day, two digits each, dash-
separated — "August 4th 2026 is: 2026-08-04") rather than just "YYYY-MM-DD"
on its own, per the user's explicit ask to make the expected input
genuinely easy to understand for someone non-technical. Blank/anything-
but-"2" defaults to the normal last-week case — verified via an isolated
branch-logic test (printf-piped "1", blank, and "2" inputs) that all three
select the correct path before ever touching a real scraper.py invocation.

Also hardened `main()`'s `--start`/`--end` parsing: a malformed date used
to raise a raw `ValueError` traceback; now caught and reported as a plain
"Couldn't understand that date. Use YYYY-MM-DD, like 2026-08-04" message
via `parser.error()`. This was already a latent gap (nothing stopped
`--start` from being typed wrong from the terminal either) but became a
real, expected-not-rare failure mode the moment a plain-language prompt
started inviting direct date entry from someone who might type "08/04/2026"
or a 2-digit year. Live-verified with a deliberately malformed date
(`2026-13-99`) fed through the actual `.command` file end-to-end — friendly
message shown, no traceback. Compiled clean, all 58 tests still pass (no
new tests for the bash prompt itself — it has no pure-function logic to
unit test; verified via the branch-logic simulation described above
instead, consistent with this file's approach to shell-script changes).

## 2026-09-02 continued — MFA leadership free pre-filter (length-OR-keyword, NOT keyword-only), plus header wording fix

User asked directly for a keyword pre-filter on MFA leadership speeches/
activity to stop it from full-translating every single item (the slowest
source in a run). A PURE keyword filter is unsafe there though — this
source's own existing comment already documents why (backtest.py, real
past-tracker verification): its actual editorial bar is "substantive
top-leadership diplomatic activity," not "mentions a topic," and the
2026-07-28 Wang Yi/Global Development Initiative entry is a real,
already-covered case that matches ZERO terms in `CHINESE_RELEVANCE_
KEYWORDS` (no US/trade/tech/territorial keyword anywhere in it). A
keyword-only gate would have silently dropped it.

Implemented length-OR-keyword instead: skip translate_to_english() only
when the item is BOTH short (`< _MFA_LEADERSHIP_MIN_SUBSTANTIVE_CJK` = 300
CJK chars, deliberately conservative — a real speech/statement runs far
longer) AND has no `CHINESE_RELEVANCE_KEYWORDS` hit. A short item that DOES
hit a keyword still gets translated; a long item with no keyword hit
(the Wang Yi/GDI shape) still gets translated too — only obvious one-line
protocol/scheduling notices get skipped for free. Pulled the actual
predicate into its own pure function, `_mfa_leadership_should_skip_
translate(plain_cn, cjk_count)`, so it's directly testable — 3 new tests
(short+no-keyword skipped, short+keyword NOT skipped, long+no-keyword NOT
skipped, the last one modeling the exact real Wang Yi/GDI shape) — 61
total, all passing.

Live-verified against the exact two real URLs from the user's own
just-terminated run (t20260902_12014342, t20260901_12014173): both would
still translate under the new filter (cjk=486/no-keyword and
cjk=1317/keyword-hit respectively — neither is short-AND-keywordless), so
this fix doesn't regress the very items the user was watching get found
live.

**Separately**: user also saw those two items' dates (Sept 1-2) as "out of
the time range" against the run's stated "Aug 25-31" target, and
understandably reacted with confusion — but they'd interrupted the run
before it reached the FINAL summary, which (per the actual-content-
labeling fix from earlier today) would have correctly relabeled the
output as covering the real Aug 25-Sep 2 range. The confusion was really
about the STARTING header line reading like a hard promise rather than a
best-guess target. Reworded it: "targeting Aug 25-31, 2026 (finds
whatever's new since the last run — if it's been a while, that may
include earlier or later dates too; the final saved filename below will
reflect what was actually found)" — makes the non-binding nature explicit
up front instead of only becoming clear at the end of a run someone may
not watch all the way through.

## 2026-09-02 continued — MFA leadership reverted to pure keyword filter (ground truth was wrong)

User corrected the length-OR-keyword hybrid from earlier today: the
2026-07-28 Wang Yi/Global Development Initiative past-tracker entry that
justified NOT using a pure keyword filter was itself a human coding
error in the original tracker (confirmed directly by the user) — it
never should have been included, since it has no actual US-China
relations content. That removes the only real evidence this source
needed different treatment. Reverted `_mfa_leadership_should_skip_
translate()` to a plain `CHINESE_RELEVANCE_KEYWORDS` gate, matching
FMPRC/MOFCOM/MND exactly — dropped the length floor and
`_MFA_LEADERSHIP_MIN_SUBSTANTIVE_CJK` entirely. Updated all 3 tests to
match (a long document with no keyword hit is now correctly expected to
be SKIPPED, the opposite of before). Live re-verified against the same
two real URLs from the user's earlier run: the Sept 2 item (no keyword
hit) now correctly gets skipped without translating; the Sept 1 item
(hits 美国/关税等) still translates. 61 tests still pass.

**Lesson for later**: ground truth from a manually-compiled tracker isn't
infallible — this is the second time this session a "real past-tracker
entry" turned out to be human error rather than a genuine edge case (the
first being the "may not be perfect" newer-intern entries flagged
2026-09-01). Worth treating a single surprising ground-truth data point
with more skepticism before designing code specifically to preserve it,
especially when the design cost is "translate everything, always" on the
project's slowest call.

## 2026-09-02 continued — Run Weekly Tracker.app: custom icon, git-portable

User added `global-business.png` to the project root and asked for it to
become the launcher's icon, "or turn it into an app" (referencing the
earlier evaluation that a plain Finder "Get Info → paste icon" customization
does NOT survive `git clone` — it's stored in extended attributes/resource
fork metadata, not file content, so git never tracks it).

- Moved the image to `assets/tracker-icon.png` (512×512 PNG, already a
  clean square source — ideal for macOS icon generation).
- Generated a full `.icns` via `sips` (resizing to the 10 required icon
  slot sizes: 16/32/128/256/512, each ×1 and ×2) + `iconutil -c icns`.
- Built `Run Weekly Tracker.app` via `osacompile` from a small AppleScript
  (`tell application "Terminal" to do script ...`) that resolves its own
  bundle's containing folder at runtime and tells Terminal to run
  `Run Weekly Tracker.command` there — deliberately a thin wrapper, not a
  reimplementation, so `Run Weekly Tracker.command` stays the single
  source of truth for the actual interactive logic (the app doesn't need
  updating if that logic ever changes). Replaced the bundle's default
  `applet.icns` with the generated one — Info.plist's `CFBundleIconFile`
  already pointed at that exact filename, so no plist edit was needed.
- **Codesigning caveat, found live**: `osacompile` ad-hoc-signs the
  bundle; after replacing the icon, tried REMOVING the signature entirely
  (`codesign --remove-signature`) on the theory that no signature is
  safer than a signature that could go stale after a git transfer —
  this actually broke the app outright (`Launchd job spawn failed`, real
  live test). Reverted to re-signing ad-hoc instead
  (`codesign --force --deep -s -`), which is proven working (launched
  Terminal and ran the script correctly, live-tested twice). Documented
  the residual risk in README: if the ad-hoc signature ever goes stale
  after being copied/cloned to another Mac (a "damaged app" error), the
  fix is one command (re-run the same codesign command) or simply use
  `Run Weekly Tracker.command` directly, which has no signing involved
  at all and is kept fully functional as a fallback for exactly this
  reason.
- **Confirmed git-portability directly** (the actual question asked):
  `git add -n "Run Weekly Tracker.app"` lists all 8 real files inside the
  bundle, `applet.icns` (the custom icon) included — a normal `git add`/
  `commit`/`push`/clone WILL carry the custom icon over correctly, unlike
  a plain Finder-pasted icon.
- Live-tested the full double-click flow twice via `open "Run Weekly
  Tracker.app"` (Finder-double-click's actual underlying mechanism) —
  confirmed it opens Terminal, cd's to the right folder, and shows the
  interactive prompt correctly; killed the test process and closed the
  window each time before it did any real scraping.

## 2026-09-02 continued — the custom icon wasn't actually showing; found + fixed the real cause

User reported not seeing the custom icon on Run Weekly Tracker.app after
the previous fix. Diagnosed properly instead of guessing: wrote a small
AppleScript using NSWorkspace's `iconForFile:` to export exactly what
macOS resolves as this file's icon to a PNG, then viewed it directly —
confirmed it was still the generic default AppleScript "scroll" icon, not
the replaced applet.icns.

Root cause: `osacompile`'s bundle ships a compiled asset catalog
(`Contents/Resources/Assets.car`) containing the DEFAULT AppleScript
icon, and the bundle's Info.plist had BOTH the legacy `CFBundleIconFile`
key (which we'd correctly pointed at our replaced applet.icns) AND the
modern `CFBundleIconName` key — which resolves against the asset catalog
and takes precedence when both are present. Our icon swap only ever
touched the legacy path, so it silently lost to the untouched catalog.

Fixed: `/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName"` on
Info.plist, and deleted the now-unreferenced Assets.car outright. Re-signed
ad-hoc again (any Info.plist/Resources edit invalidates the existing
signature). Re-ran the same NSWorkspace icon-export check — now correctly
shows the actual globe+briefcase image. Re-verified the app still launches
and runs correctly via `open` (twice).

**Process-cleanup lesson from this verification pass**: killing the
`Run Weekly Tracker.command` bash wrapper's PID does NOT kill its child
`python3 code/scraper.py` process — `kill` only signals the exact PID
given, not descendants. Left 2 orphaned live scraper.py processes running
briefly during this round of testing (each caught and killed within
~10-20s, trivial extra cost) before noticing via `ps aux`. Lesson: when
killing a test run of `Run Weekly Tracker.command`/`.app` for verification
purposes, always `ps aux | grep scraper.py` and kill THAT pid directly,
not just the wrapper's.

If a Finder window already open still shows a stale icon after this fix,
that's Finder's own icon cache, not a real remaining bug — closing and
reopening the folder window (or `killall Finder`) forces a redraw.

## 2026-09-02 continued — REAL hard date filtering + per-week doc rendering (major fix)

User correctly pushed back hard on the "label only, don't filter" design
from earlier today: "I don't want all the tuesday and wednesday stuff...
I just want last tuesday to monday... I think your underlying logic may
still be wrong, cuz when I asked for 'Aug 25-31, 2026', it looked up a
Sept 1 MFA leadership link again." They also clarified the actual desired
semantics: "if you'd already scraped it, then just give me the doc" —
i.e. a genuinely date-SCOPED document, not just a differently-labeled
copy of everything ever scraped.

Investigating this surfaced a bigger problem than the missing filter:
**the "dated" per-week file was never actually a per-week extract at
all** — it was `shutil.copyfile(DOC_PATH, ...)`, a straight copy of the
ENTIRE cumulative master document (which accumulates every entry from
every run, forever) under a week-labeled filename. Confirmed via
`get_or_create_doc()` — it loads and appends to the same file indefinitely.
A real design gap, not just a missing filter.

### The fix (three parts, working together)

1. **`queue_entry()` now HARD-filters by a run's target range.** New
   module globals `_RUN_TARGET_START`/`_RUN_TARGET_END`, set by `main()`
   from `week_start`/`week_end` (None outside a main()-driven run, so
   backtest.py/format_entry.py are unaffected). An item outside range is
   dropped WITHOUT being marked seen — left for a future run whose target
   actually covers its date, not lost.
2. **A new durable `entries` table in tracker.db** (url, date, kind,
   summary, anchor, exchanges_json, paragraphs_json), written by
   `flush_pending_entries()` right after `doc.save()` succeeds — same
   durability timing/reasoning as `mark_seen()`. This is what makes a
   per-week document reconstructable independent of the master doc.
3. **`render_doc_for_range(conn, start, end)`** builds a FRESH document
   from the `entries` table, not a copy of the master doc. This is what
   actually delivers "if you already got those dates, just give me the
   doc" — an entry shows up whether it was queued THIS run or a previous
   one, so re-running an already-covered week is fast (nothing new to
   queue) and still produces the complete, correct document.

**MFA leadership got an extra optimization**: since its date is parseable
straight from the URL (no fetch needed), the range check now happens
BEFORE fetching at all — an out-of-range item costs nothing, not even a
network request, let alone a translate call.

Removed as obsolete: `_extend_date_range()` and its tests, the "(Expected
X, but found content outside range too...)" summary note, the `shutil`
import — all existed only to cope with the old "label, don't filter"
design and are no longer needed now that the label is correct by
construction. Header wording reverted to a plain "covering X" — it's a
real guarantee again, not a hedge.

### A second, more serious bug found while verifying this live

Checking real URLs against the new code surfaced that one had already
been marked seen — timestamped from EARLIER TODAY. Tracing it back found
a real, ongoing bug in `test_scraper.py` itself: `flush_pending_entries()`
always calls `doc.save(S.DOC_PATH)` — the module constant, not a path
derived from the `doc` object passed in — so `TestMarkSeenFlushOrdering`'s
two tests, which pass a throwaway in-memory `Document()` thinking that
isolated them, were actually **silently overwriting the real
`output/tracker_output.docx` on every single test run**, all session.
(The sibling assertion in the same test class correctly patched
`S.X_STATE_PATH` for the exact same reason — this exact lesson just
hadn't been applied to `S.DOC_PATH` too.)

Confirmed real damage: `output/tracker_output.docx` had been reduced to
the test's synthetic one-entry fixture, and 40 real URLs from today's
actual live verification runs (17 SCIO entries, several FMPRC Q&A
entries, one MFA leadership item) were marked seen with no recoverable
content — the exact "seen but content lost" failure class bug #21 was
built to prevent, just via test contamination instead of a crash.

**Fixed and recovered**:
- Patched both tests to save `S.DOC_PATH` to a `tempfile.TemporaryDirectory()`
  path for the test's duration (matching the existing `X_STATE_PATH`
  pattern) and restore it in `tearDown()`.
- Deleted the 40 contaminated `seen_urls` rows (all timestamped
  2026-09-02) so a future run re-fetches and correctly re-processes them
  under the NOW-FIXED code (writing to both the real doc and the new
  `entries` table this time).
- Reset `output/tracker_output.docx` to a clean empty document (its
  contents were synthetic test junk, not recoverable real data).
- Verified the fix holds: ran the full test suite and confirmed via
  `stat`'s mtime that the real `tracker_output.docx` was untouched.

### Live end-to-end verification (real data, real network calls)

- `--source mfa_leadership_speeches --start 2026-08-25 --end 2026-08-31`:
  30 unseen items on the list page (spanning back to Nov 2025) — every
  single one outside the target range was skipped WITHOUT a fetch
  (confirmed in the log), including the two real Sept 1/2 items that
  started this whole investigation. Two genuinely in-range items (Aug 28,
  30) WERE fetched and correctly judged "no topic keyword." 7 seconds,
  $0. A second identical run afterward took 2s (Aug 28/30 now correctly
  marked seen from the first run) — confirms the "already scraped, fast"
  behavior.
- `--source fmprc_conf --start 2026-08-25 --end 2026-08-31`: 5 real Q&A
  entries found and queued (Aug 25/26/27/28/31). Directly inspected the
  resulting `output/US-China Tracker Aug 25-31, 2026.docx` paragraph by
  paragraph — real Lin Jian/Guo Jiakun Q&A content, correctly dated,
  correctly hyperlinked, zero Sept content of any kind. This is the
  first real, direct confirmation that the per-week doc is both complete
  AND correctly scoped, not just passing a synthetic test.

All 63 offline tests pass throughout.

## 2026-09-02 continued — API pacing double-check (Gemini + X, real money now)

User asked to double-check wait times after noting things "seem a bit
slow" — now real money on the line for both Gemini and X.

**Checked today's logs for actual rate-limit trouble**: zero 429s, zero
Gemini cooldown triggers across every log from today. GEMINI_SLEEP
(16s/call) is working exactly as designed — not accidentally degraded,
not silently falling back to a slower provider. The slowness IS the
pacing, by design, for a confirmed RPM=4 account (verified against the
real AI Studio dashboard 2026-09-01, not a third-party aggregator
figure — see that constant's own comment).

**Found one real, fixable inefficiency**: `scrape_x()` slept
`REQUEST_SLEEP` (2s) after EVERY account in its loop (11-18 accounts
depending on X_INCLUDE_LESS_IMPORTANT), on top of whatever Gemini
pacing individual tweets needed. That sleep constant exists for
politeness toward the actual GOVERNMENT WEBSITES this pipeline scrapes
via fetch()/httpx — but `_x_get_user_id()`/`_x_get_recent_tweets()` call
httpx directly, never through fetch(), and X's v2 API has its own much
more generous published per-15-min rate limits that 11-18 sequential
calls in one run never comes close to. Removed it — saves ~20-35s per
run for zero real benefit, since it was never actually protecting
against anything. Compiled clean, 63 tests still pass (no test coverage
lost — this constant's removal has no pure-function logic to test, and
X's live calls were never part of the offline suite's scope anyway).

**Asked the user to check one thing I can't verify myself**: whether
their Gemini tier has genuinely increased since 2026-09-01's RPM=4
reading — Google auto-upgrades tiers based on cumulative spend/usage
history (this is exactly the mechanism third-party aggregators were
describing when they over-reported "Tier 1: 2000 RPM" back on 08-04),
and today involved a lot of real paid Gemini usage across all this
session's live verification. If RPM is now genuinely higher,
GEMINI_SLEEP can be safely lowered — but this needs a real dashboard
check, not a guess, given real billing is on the line; the same
methodology that got the RPM=4 figure in the first place (checking
aistudio.google.com's own account limits page directly) is the right
way to recheck it, not inferring from behavior or assuming an aggregator
figure.

## 2026-09-02 continued — GEMINI_SLEEP: 16s -> 1s, real tier upgrade confirmed

User checked their AI Studio dashboard directly (as asked) and reported
back real, current numbers: **RPM=1000, TPM=1M, RPD=10,000** — a huge
jump from the RPM=4 reading checked just one day earlier (2026-09-01).
This is the auto-upgrade-with-usage-history mechanism the 08-04 entry
predicted but couldn't yet confirm (that's what third-party aggregators
were describing when they over-reported "Tier 1: 2000 RPM" on a freshly-
linked account) — now real, confirmed directly from the account's own
dashboard after a day of genuine paid usage.

At RPM=1000, RPM itself isn't a binding constraint at any pace this
pipeline could plausibly run at. Lowered `GEMINI_SLEEP` from 16 to 1 —
not zero, kept as a small deliberate safety margin against TPM (a real
translate call can run ~10K tokens; several back-to-back with zero
pacing at a busy moment could plausibly approach the 1M/min ceiling) and
against any unlisted burst-rate protection. `_gemini_on_cooldown()`'s
429-triggered backoff is untouched and remains the real safety net
regardless of this nominal pace.

Live-verified immediately, not just compiled: `--source
mfa_leadership_speeches --start 2026-09-01 --end 2026-09-07` — real
run, 3 genuine Gemini calls (2 translate + 1 extract_key_paragraphs,
7,895 tokens, $0.0121), zero 429s, zero cooldown triggers, completed in
35s total. Under the old 16s pacing, those same 3 calls' pacing alone
would have been 48s before any real latency — a meaningful, now-confirmed-
safe speedup.

Also removed `scrape_x()`'s unconditional 2s `REQUEST_SLEEP` between
every account (11-18 per run) — never protected against a real X-side
limit (X's calls bypass fetch() entirely, going straight through httpx;
X's own v2 API limits are far more generous than what this workload
could ever threaten) — saves another ~20-35s/run for free.

Net effect on run time: dramatically faster for any run touching
multiple new Gemini-requiring items, on top of the X fix. Re-check the
actual AI Studio dashboard again if this ever changes (tiers can move in
either direction) — never infer a new pacing value from behavior or a
third-party number, per this exact lesson twice now.

## 2026-09-02 continued — GEMINI_SLEEP: 1s -> 0.5s, and the honest remaining bottleneck

User clarified their speed concern wasn't about billing safety, it was
"you made it too slow" — pushed to check whether 1s was still overly
conservative. Checked a real run's own log: small `classify_relevance`
calls (~200-250 tokens, the majority of any run) were STILL spaced
~1-2s apart at 1s sleep — meaning the sleep itself, not real network/
generation latency, was still the dominant cost for the common case.
Cut `GEMINI_SLEEP` to 0.5s. Math: TPM=1M/min (16,667 tok/sec) is the
only real constraint left at RPM=1000; 0.5s allows ~20K tok/sec if
EVERY call were a maximal ~10K-token translate back-to-back — modestly
over TPM in that specific worst case, but real runs mix in far more
small calls than that, and `_gemini_on_cooldown()`'s existing 429-
triggered backoff is the real safety net if that edge case is ever hit
(a brief graceful fallback to Groq/OpenRouter, not a crash or overspend).

Live-verified against a genuinely large real backlog (`--source scio
--start 2026-09-01 --end 2026-09-07`, which hadn't been targeted in a
while and had candidates going back to March 2026): 30+ real Gemini
calls, zero 429s, zero cooldown triggers (confirmed by grepping the
log — the one "429" match was just a coincidental token count in a
usage line, not an actual rate-limit error). 7 real entries queued,
correctly date-filtered (a May 8 item was correctly left unseen for a
future run targeting that date), $0.0163, 26,697 tokens.

**Being straight about what this run's 2m21s actually breaks down to**,
since further Gemini tuning won't move this number much: the dominant
cost for a source with a real backlog is `REQUEST_SLEEP` (2s per HTTP
fetch, for politeness toward the actual government website) plus real
page-load time across every candidate URL — NOT Gemini's pacing, which
is now a small fraction of total time. `REQUEST_SLEEP` is a different
dial protecting against a different risk (getting blocked by .gov
servers) and hasn't been touched — reducing it wasn't asked for and
would trade a real reliability risk for speed, unlike the Gemini/X
pacing fixes today which had no real downside once the actual current
limits were confirmed.

## 2026-09-02 continued — X redesigned around search, not per-account timeline polling

Implemented the search-based redesign discussed after the $1.735/94%-of-
run-cost X finding. Researched X's actual current pricing model first
(docs.x.com + several 2026 pricing summaries, cross-checked): confirmed
"a search that returns 20 posts is billed as 20 post reads" — same
per-post rate as the old timeline endpoint, but a search query can
combine a keyword filter AND multiple accounts into ONE call, so X only
returns (and bills for) posts that already match, instead of paying for
every post from every account and discarding most after the fact.

- New `build_x_search_query(accounts, terms)` — pure function, `(terms)
  (from:a OR from:b ...)`, X's real search syntax. Tested directly,
  including a regression test that the two REAL groups this pipeline
  builds stay under "recent search"'s 512-char query limit (passed: ~300
  and ~150 chars respectively).
- New `_x_search_recent(query, since_id, max_results=100)` replaces
  `_x_get_user_id()` + `_x_get_recent_tweets()` entirely — hits
  `GET /2/tweets/search/recent` with `expansions=author_id&user.fields=
  username` to get each result's author back without a separate lookup
  call. A genuinely nice side effect: search's `from:` operator takes a
  plain USERNAME, not a numeric user ID, so the whole username->user-ID
  resolution step (a separately-billed "user read" per account) is gone
  — one less cost, one less cache to maintain. `_X_USD_PER_USER_READ`
  removed as dead.
- `scrape_x()` now builds exactly 2 queries per run instead of up to 18:
  non-PRC accounts filtered by `_X_CHINA_SEARCH_TERMS` (their bar:
  mentions China), PRC accounts filtered by `_X_US_SEARCH_TERMS` (their
  bar: mentions the US — same asymmetry as `_PRC_X_ACCOUNTS`'s existing
  logic elsewhere, just applied one layer earlier). Both keyword lists
  deliberately mirror RELEVANCE_KEYWORDS/CHINESE_RELEVANCE_KEYWORDS'
  actual terms rather than inventing a new list — same accepted
  recall tradeoff already trusted elsewhere in this pipeline, not a new
  one.
- `since_id` tracking moved from per-account to per-SEARCH-GROUP (a
  combined query has one shared result stream, not one per account) —
  `x_accounts_state.json` now nests both under `_search_groups`. Updated
  `flush_pending_entries()`'s persistence accordingly (same after-
  doc.save() safety timing as before, see bug #22). Cleaned the old
  per-username `user_id`/`since_id` entries out of the real state file
  — dead under the new design, would only have confused future
  debugging.

**Live-verified with two real, back-to-back runs** (real money, watched
carefully): first run (no `since_id` yet under the new schema, so it
searched the ~7-day default window) — **20 total X reads** across both
groups combined, **$0.10**, 7 real entries correctly queued with
usernames correctly resolved via the expansion (RapidResponse47,
WhiteHouse, PressSec, ChineseEmbinUS all correctly attributed). Compare
to the OLD design's first-ever run: 329 reads, $1.645, unfiltered. A
~16x reduction on directly comparable "first activation" runs, and no
recall loss beyond the keyword-filter tradeoff already accepted
everywhere else in this pipeline.

Second run immediately after: **0 new reads, $0.0000, 0s** — confirms
`since_id` correctly prevents re-billing already-seen content under the
new per-group tracking, matching the old design's steady-state
guarantee.

Updated `TestMarkSeenFlushOrdering.test_x_since_id_staged_not_saved_
until_flush` to check the new nested `_search_groups` shape (was
checking a bare top-level username key, which no longer exists). Added
`TestBuildXSearchQuery` (3 tests, including the 512-char-limit
regression test against the real production account lists). 66 tests
total, all passing.

## 2026-09-02 continued — re-enabled per-entry summaries, verified against real past trackers first

User asked to re-enable `generate_summary()` (disabled since 2026-09-01)
plus the verb-hyperlink convention — explicitly asked to check the real
past trackers FIRST rather than trust this file's own prior documentation
of the convention.

Directly inspected `input/past_trackers/*.docx`'s actual OOXML hyperlink
structure (not just visible text) across two different tracker files:
confirmed a SINGLE verb or short verb phrase is hyperlinked within one
plain-text sentence — "Lin Jian **addressed** reporters' questions on...",
"Bessent **testified** before...", "**posted** on X about...",
"**issued** a press release on...". Real word counts: 13-19 words median
across 8 sampled real entries. This matches `generate_summary()`'s
existing prompt and `add_summary_para()`'s existing rendering logic
almost exactly (both were originally built to match this same
convention, before being disabled) — no rendering-code changes needed,
just flip `ENABLE_LLM_SUMMARY = True`.

**Tightened the prompt anyway**, live-verified need: the first real entry
generated after re-enabling (a G20/FATF Treasury statement) came out to
~40 words — noticeably longer than the 13-19 word real median, since the
old prompt only said "no fluff" with no concrete length target. Added an
explicit "roughly 15-25 words" target plus "cut a long topic list to the
2-3 most important items" to both the primary (structured JSON) and
fallback (plain-text) prompts. Re-ran generate_summary() directly against
the SAME real Treasury text to compare: 26 words, anchor "released" (a
verb straight from the prompt's own example list) — a real, measured
improvement (40 -> 26 words), landing right at the edge of the target
range rather than needing further tuning that would fight normal LLM
length variance for a soft target.

Note: the Treasury entry queued during the FIRST verification run (before
the prompt tightening) is already written into the real output doc with
the longer ~40-word wording — not retroactively rewritten, since it's a
quality nuance, not a correctness bug, and rewriting already-real
production content wasn't asked for. Every entry generated from here
forward uses the tightened prompt.

Cost/time impact, now that this is live rather than estimated: one real
`generate_summary` call added `usd=$0.0022` / a few seconds to that one
Treasury entry (5,078 tokens total for the whole item, translate+summary
combined) — consistent with the ~$0.0006/entry estimate given before
re-enabling, and cheaper in wall-clock terms than originally estimated
since GEMINI_SLEEP is down to 0.5s today (was 16s when that estimate was
made). All 66 tests still pass — no test coverage for generate_summary()
itself (needs a live LLM call, explicitly out of scope for
test_scraper.py per its own stated design, same as translate_to_english).

## 2026-09-02 continued — simplified the date prompt, dropped dashes entirely

Two rounds of feedback on Run Weekly Tracker.command's date prompt:
1. Removed condescending hand-holding: "(the earlier one)"/"(the later
   one)" on the start/end date prompts, and "that's year, then month,
   then day" spelled out in the format explanation — user was direct
   that this read as talking down to them.
2. Dropped the dash requirement entirely: typing "2026-08-04" for every
   date felt unnecessarily fussy. Added `_parse_user_date(s)` — accepts
   plain `YYYYMMDD` (e.g. `20260804`) via a regex-gated `strptime`, still
   falls back to `date.fromisoformat()` for anyone who types dashes
   anyway (the CLI's `--start`/`--end` flags keep working exactly as
   before for existing scripts/habits — this is additive, not a breaking
   change). Updated the prompt text, the friendly ValueError message,
   argparse's `--help` text, and the README to all mention the no-dash
   format as primary. 3 new tests (`TestParseUserDate`) — 69 total, all
   passing.

**Caught my own mistake while verifying this**: tried to live-test the
updated `.command` file's date-parsing UX with a quick piped-input +
timeout kill, but the backgrounding didn't kill the process in time —
it actually launched a REAL full-scale run (all 18 sources, not just a
UX check) targeting Aug 18-24 with real API calls starting. Caught via
`ps aux` within seconds, killed immediately (`kill -9` both the bash
wrapper AND the python child — remembering today's earlier lesson that
killing just the wrapper leaves an orphaned child). Verified no lasting
effect: `entries` table still shows 0 rows for Aug 18-24 (the flush-
after-each-source design means a kill this early, before any single
source finished, saves nothing) — that week is still genuinely
untouched and available for the user's own real blind test later, not
accidentally spent by my own verification slip.

## 2026-09-02 continued — real crash: XML-invalid control character in LLM output

User's own real Aug 18-24 blind-test run crashed mid-flush, 3/18 sources
in, with a hard `ValueError: All strings must be XML compatible: Unicode
or ASCII, no NULL bytes or control characters` from lxml, inside
`add_summary_para()`'s `_run(p, after)` call while writing MFA leadership
activity's 5 queued entries. Root cause: `generate_summary()`'s LLM
output apparently contained a stray control character — the first real-
world exercise of that path since `ENABLE_LLM_SUMMARY` was turned back
on earlier today; this exact failure mode was never possible while
summaries were disabled (the bare-URL fallback has no free-form LLM text
in it at all).

Tried to reproduce the EXACT original text by regenerating summaries for
the same 5 URLs — LLM output isn't deterministic, none of the 5 came
back with a bad character this time, so the precise original trigger is
unrecoverable. Fixed at the actual root instead of chasing one exact
string: added `_xml_safe()` (strips anything outside XML 1.0's valid
text-content ranges — tab/newline/CR plus most of Unicode, which is
exactly the C0-control-character class this crash came from) and applied
it at BOTH real text-insertion points — `_run()` (used by nearly every
paragraph write) AND `add_hyperlink()` (found on inspection to build its
own raw `<w:t>` XML element directly, bypassing `_run()` entirely — the
anchor text itself is also LLM-generated and could just as easily carry
a bad character). Fixing only one of the two would have left the other
just as crash-prone.

Live-verified with an actual reproduction (a string containing a real
NULL byte and a real vertical-tab control character) through both
`_run()` and `add_hyperlink()` directly — confirmed no crash, bad
characters cleanly stripped, everything else preserved (including CJK
text, tabs, newlines). 6 new tests (`TestXmlSafe`) — 75 total, all
passing.

**Confirmed the crash-safety design held**: since the crash happened
INSIDE the paragraph-building loop, BEFORE `doc.save()` is ever called,
none of the 5 MFA leadership activity items got marked seen and nothing
was written to the `entries` table — verified directly (`is_seen()`
false for all 5, zero `entries` rows for Aug 18-24). The user's Aug
18-24 blind test is still completely untouched and ready to re-run now
that the actual bug is fixed — this wasn't a case of losing that test
run's progress, the crash-then-safe-abort behaved exactly as the
mark_seen/flush ordering work earlier today was designed to handle.

## 2026-09-02 continued — big feedback batch from a real Aug 18-24 run: 9 items

User's real Aug 18-24 test surfaced a substantial, concrete list of real
issues. Worked through them one by one (their batch had already finished
before starting, confirmed via `ps aux`):

1. **Other per-item terminal prints** — checked: none exist. The `[N]
   found: url` print removed last time was the ONE mechanism, inside the
   shared `queue_entry()` every source funnels through — already fully
   fixed for White House/Treasury/everything, nothing left to find.

2. **war.gov: stop after the first 403.** Added `_LAST_FETCH_STATUS` — a
   lightweight module-level side channel `fetch()` sets on any definitive
   HTTP error, so a caller can check WHICH status code a `None` return
   meant without changing `fetch()`'s simple `Optional[Response]`
   contract for its ~15 other call sites. Wired into `scrape_wardept`'s
   loop: break immediately on a 403 instead of repeating the same
   Akamai-block failure on the remaining ~29 items. Live-verified: real
   run against war.gov now stops after item 1, 6s total instead of what
   would have been ~30 wasted requests. 2 new tests
   (`test_last_fetch_status_*`).

3. **war.gov warnings — root cause, no further fix available.** Confirmed
   (again, directly) this is Akamai's TLS/connection-fingerprint bot
   detection, not a header/cookie issue — already investigated exhaustively
   earlier today (tried browser-matching headers, a cookie warm-up; even
   the homepage 403s for a non-browser client). No further fix exists
   short of real browser rendering (Playwright), which this project
   deliberately doesn't use. Item #2 above is the actual improvement
   available: stop wasting requests once it's confirmed blocked for this
   run, rather than "fix" an unfixable block.

4. **Auto-open the finished doc.** Added `subprocess.run(["open",
   dated_path])` at the end of a successful run (macOS only, `check=False`
   so a failure here never makes the run itself look failed) — new
   `--no-open` flag, which `run_scheduled.sh` now passes (nobody's
   watching an unattended cron run to see a doc pop open).

5. **Keep the date heading for a day with nothing found.** Checked the
   real past trackers first: confirmed a quiet day (e.g. "Sunday, August
   2, 2026") DOES get its own heading with nothing under it, immediately
   followed by the next day's heading — not silently skipped. Rewrote
   `render_doc_for_range()` to walk every day in [start, end], not just
   the dates that have `entries` rows — a quiet day is real information
   ("nothing happened"), different from "we didn't check." Updated the
   test that previously asserted an empty range renders a fully empty
   doc (that assumption was the OLD, now-wrong behavior).

6. **Can date-range filtering happen at the source, not just via the
   cap? Checked honestly, source by source**: only `state.gov` uses a
   real WordPress REST API (`wp-json/wp/v2/...`), which DOES support
   `before`/`after` date params natively — that's the one place true
   server-side date filtering is straightforward to add. Every other
   affected source is either RSS (war.gov, whitehouse.gov — no date
   filtering possible at all, just "latest N in feed order") or a raw
   HTML list page (ustr, treasury, mofcom, fmprc, mnd, mfa leadership —
   no query-param filtering, though some may support deeper pagination
   we don't currently walk). Not implemented yet — flagging as a real,
   scoped follow-up (add before/after to state's WP-API call; for
   RSS/HTML sources, the only lever is walking further back through
   pagination when the target range is old, a bigger change).

7. **"Latin America" false positive.** A real one: "America" matched
   inside "Latin America" (a region, not the US), and — critically —
   this specific regex (`_EXPLICIT_US_MENTION_RE`) has NO LLM judgment
   downstream to catch it; `filter_relevant_exchanges` and PRC accounts'
   tweet-relevance check both decide directly off this match. Added
   `(?<!Latin )(?<!South )(?<!Central )` negative lookbehinds (each
   fixed-width, as Python's `re` requires) before `America[n]?` in both
   `_RELEVANCE_ALTERNATIVES` and `_EXPLICIT_US_MENTION_RE`. Live-verified
   6 real cases directly (all 3 region names correctly excluded, "The
   American ambassador," "Washington," and "United States" all still
   correctly matched) before writing tests. Left the X search query's
   own keyword list alone — X's query syntax has no equivalent to a
   substring-level lookbehind, only whole-tweet `-exclude`, which is a
   blunter/lossier tool, and this exact failure hasn't been observed on
   X specifically.

8. **Raw markup leaking into body text.** A real White House/Ford entry
   came out as literal `**Ford Motor Company** <a href="...">
   **announced**</a> **it will reshore...` in the finished doc. Re-fetched
   the actual live source page directly to check: the RAW extracted text
   has NONE of this markup at all (clean plain text) — confirming
   `extract_key_paragraphs()`'s LLM call added the markdown bold and a
   fabricated HTML anchor itself, despite being told to preserve exact
   text, not something carried through from the page. Fixed at the same
   choke points as the earlier XML-safety fix (`_run()`/`add_hyperlink()`)
   rather than just this one call site, so it's caught regardless of
   which LLM call produces it: `_strip_stray_markup()` strips markdown
   `**bold**`/`__bold__` markers and HTML tags matching a recognized tag
   name allowlist (a, b, i, u, strong, em, span, p, br, div, ul, ol, li,
   h1-h6) — deliberately NOT a blanket `<[^>]+>`, which would also eat a
   genuine "<5% target" comparison in real economic text. Live-verified
   against the exact real bad string, and confirmed the "<5%" case is
   correctly preserved. 3 new tests.

9. **Irrelevant "pleasantry" paragraphs slipping through.** A real
   example: "Kim Sung-han stated that the ROK and China are close
   neighbors, and their relationship has a long history..." — entirely
   generic diplomatic pleasantry, no concrete substance, from a Wang
   Yi/Kim Sung-han (ROK National Security Director) meeting readout via
   MFA leadership's `general=True` extraction path. Confirmed via live
   re-test against the actual source URL that a first prompt-strengthening
   attempt (explicitly calling out generic friendship language as a
   pleasantry, with a concrete negative example) did NOT fix it —
   the model still included it. Root cause: `extract_key_paragraphs()`
   asked for exactly `n` (default 4) paragraphs, which can pressure a
   model to pad the count with a marginal paragraph rather than return
   fewer genuinely-substantive ones. Changed the prompt to "UP TO n...
   return FEWER than n if that's all that's genuinely substantive — do
   not pad the count." Re-verified against the same real source TWICE
   (LLM output isn't deterministic) — both times correctly returned only
   2 paragraphs, pleasantry excluded both times. No offline test possible
   (needs a live LLM call, same as generate_summary/translate_to_english)
   — verified live instead, twice, for repeatability.

All 83 offline tests pass throughout. Every fix in this batch was
verified against REAL content from the user's own actual run (or, for
generate_summary re-verification, the exact real source URL), not
synthetic reproductions alone, except where noted (control-character/
markup fixes used a constructed reproduction of the real observed text
since the exact original LLM output wasn't recoverable — but the
underlying real page content was still checked directly to confirm the
markup was NOT present in the source).

## 2026-09-02 continued — raised the item cap for real, and added bold source/speaker labels

**Cap question, answered with real data, not a guess**: checked which
source actually needs a higher cap by fetching USTR's live list page
directly — **128 genuinely unseen items**, nowhere close to the old
30-item ceiling. war.gov also hit 30 in the earlier log, but raising its
cap is moot given the Akamai block (item #2/3 from the last batch — it
stops after the first 403 regardless of how many items are queued).
Raised `MAX_NEW_ITEMS_PER_RUN` 30 -> 150 globally rather than per-source:
safe because every OTHER source sits comfortably under 30 in normal
weekly operation, so this changes nothing for them — it only matters for
a source that's actually hit the ceiling.

**Bold source/speaker labels — confirmed against the real trackers
before implementing, per usual.** Direct inspection found this is a
UNIVERSAL convention, not just for X: every release-type body paragraph
in the real tracker is bold-prefixed with who's speaking — an X account
("Chinese Embassy:", "Rapid Response 47:", "President Trump:") or a
plain institutional label when there's no named speaker at all ("State
Council Press Release: A senior official..."). Also confirmed: only the
FIRST body paragraph gets the label; a multi-paragraph quote from the
same release has no repeated label on paragraph 2+.

Implementation:
- `queue_entry()` gained a `source_label` parameter, threaded into
  `PENDING_ENTRIES` and (new) the `entries` table — required an actual
  schema migration (`ALTER TABLE entries ADD COLUMN source_label TEXT`
  wrapped in try/except, since `CREATE TABLE IF NOT EXISTS` is a no-op
  against a table that already has real rows on the user's machine).
- `add_release_entry_body()` bold-prefixes `source_label` onto the FIRST
  paragraph ONLY, and ONLY if that paragraph doesn't already have its
  own natural "Name: text" shape (a Q&A-shaped release fallback that
  extracted a real speaker label verbatim) — never stacks two labels on
  one paragraph.
- `finalize_release_item()`/`finalize_qa_item`'s release-fallback branch
  now pass their existing `source_name` straight through as the label —
  it was already the right clean string ("Treasury Department", "State
  Council Information Office", "USTR", ...), just never used this way
  before.
- New `_X_ACCOUNT_DISPLAY_NAMES` dict maps every configured X username to
  a real display name matching the tracker's own convention ("Chinese
  Embassy", "Rapid Response 47", "President Trump", "Secretary Bessent",
  ...) — covers all 18 accounts (11 normal + 7 less-important), with a
  test asserting every configured account has a real entry (not a
  silent username fallback for one that was simply forgotten).

Live-verified both paths against real content: a real Treasury G20/FATF
item correctly rendered "Treasury Department: 1 The statement was
agreed..." as the first body paragraph's bold prefix; a real Chinese
Embassy tweet (fetched live via a direct search bypassing since_id)
correctly rendered "Chinese Embassy: 🌏📚 #China's digital publishing
industry..." — both exactly matching the real tracker's shape. 4 new
tests. 87 total, all passing.

## 2026-09-02 continued — the cap was the wrong fix entirely; real fix has no cap needed

User pushed back twice on the "just raise the cap" approach, correctly:
first that a permanent global raise pays real ongoing cost for what's
actually a one-time backlog problem (reverted 150 -> 30, added
`--max-items` as an explicit one-time-catch-up override instead — see
above), then asked the sharper question: **why is there a cap at all,
if the list is sorted by date — why not just read the date and stop?**

Checked directly rather than assuming: fetched USTR's real list page and
inspected the HTML around a listing entry. It's a Drupal "views" listing
— every row already carries `<time datetime="2026-08-20T12:00:00Z">`
directly alongside the link, confirmed strictly newest-first across 5+
sampled rows. This means the date is available for FREE, straight from
the one list-page fetch we already make — no need to visit each article
just to learn its date, and no need for an arbitrary item-count cap to
bound a date-scoped request at all.

Rewrote `scrape_ustr()`: parse `(date, url, title)` triples directly from
each `views-row`, walk them in their natural (already newest-first)
order, and `break` the instant an item's date falls before this run's
`_RUN_TARGET_START` — everything after that point is guaranteed even
older. `MAX_NEW_ITEMS_PER_RUN` still applies as a safety ceiling for the
OTHER case (no target range set at all), but it's no longer what decides
whether an old week's content gets reached. Also threaded the
already-known date through to `process_ustr_item()` (new `known_date`
param) so it stops needlessly re-deriving the same date via a regex
search over the full fetched page text.

**Live-verified against the exact real case that started this
whole thread**: `--source ustr --start 20260818 --end 20260824` —
**one page fetch, 2 seconds total**, log shows `"Reached 2026-08-13,
before this run's target start (2026-08-18) — stopping"` — correct
whether-or-not that specific week actually had new content (it had two
in-range items, already seen from earlier testing). Compare to the
original problem: this exact same request under the OLD design either
missed content behind the 128-item backlog entirely (cap=30) or paid to
fetch up to 150 full article pages regardless of the target range
(cap=150) — this fix costs the SAME single list fetch whether the
target range is last week or six months ago, and correctly reaches
arbitrarily old content with no backlog-size cap at all.

**Scope note**: this fix is specific to sources whose LIST page exposes
a real per-item date (confirmed for USTR; state.gov's WP-API also
already returns `date` per item in its listing JSON, so the same
principle applies there for free too). Sources without a list-level
date (raw HTML with no visible date, like FMPRC/MOFCOM/MND/MFA
leadership's Chinese pages) still need the fetch-then-check-date
approach already in place elsewhere — the cap (or `--max-items` for a
deliberate catch-up) remains the right tool for those. Not yet checked
whether Treasury or other sources share USTR's exact page structure —
flagged as a reasonable follow-up if the user wants it extended further.

## 2026-09-02 continued — checked every source for the same date-in-listing trick; Treasury fixed, war.gov re-confirmed still blocked

**war.gov**: re-checked directly (homepage AND article page) — still a
flat 403 from both, no change since the earlier investigation. This is a
persistent Akamai block, not something that resolves on its own; nothing
new to do here beyond the existing stop-after-first-403 fix.

**Checked every other source for USTR's exact trick** (a real per-item
date sitting right in the list page's HTML, letting the walk stop early
with zero extra fetches):

- **Treasury: confirmed identical structure, fixed and verified live.**
  Same pattern as USTR almost exactly — `<time datetime="...">` in the
  same small container div as each link. Found and fixed a real
  complication along the way: the original broad href match
  (`/news/press-releases/`) also matched nav-menu category links (no
  date at all) AND, worse, pagination controls ("Page 2", "Next page")
  that inherited a BOGUS date from an unrelated ancestor div once a
  `<time>` tag was searched for loosely — these could have looked like
  fake very-recent items. Fixed by requiring the link to match a real
  content slug shape (two letters + digits, e.g. "sb0620") instead of a
  bare substring, which cleanly excludes both. Live-verified against the
  same Aug 18-24 request: 2 seconds, one page fetch, naturally exhausted
  all 10 available items (all within/after the target range) without
  needing the early-break — same correct outcome either way.
- **State: already optimal, no fix needed.** Its WP-API call already
  requests `date` as one of the returned `_fields` in the SAME initial
  listing response — the date has been available for free all along,
  just not yet used for early-stopping the walk (lower priority to wire
  up since State hasn't shown a real backlog in live testing).
- **White House: already optimal, no fix needed.** RSS feeds carry a
  `<pubDate>` per item in the feed itself by spec — same situation as
  State, date already free, not yet wired into an early-stop.
- **FMPRC: partially already exploiting this, differently.** Its list
  page ALSO shows a plain-text date next to each link, but
  `process_fmprc_item` already derives the date from the URL pattern
  itself (`t20260902_...`) rather than the surrounding HTML — the same
  trick already used for MFA leadership. Not yet wired into an early-
  stop for the LIST WALK itself, but hasn't shown a real backlog in live
  testing (2 and 1 new items in the most recent real run) — lower
  priority than Treasury/USTR were.
- **MOFCOM (5 variants), MND, MFA leadership: not yet checked.** All
  Chinese-language raw HTML sources, none have shown a real backlog
  in live testing so far — flagged as a real, scoped follow-up if the
  user wants full coverage, but not urgent given no confirmed problem
  there yet (unlike USTR/Treasury, which had real, measured evidence:
  128 and use of the exact-cap signal respectively).

All 87 tests still pass throughout.

## 2026-09-02 continued — Wang Yi's title, fixed on the second attempt

User: for Wang Yi, just use "Foreign Minister," not the full "Member of
the Political Bureau of the CPC Central Committee Wang Yi." First
prompt attempt (a single "don't use the CPC title" instruction, one
example) wasn't specific enough — re-verified live against the same
real source and it swapped one overly-formal title for ANOTHER
("Director Wang Yi", picking up his separate "Director of the Office of
the Central Commission for Foreign Affairs" title instead). Root cause:
Wang Yi genuinely holds several simultaneous real titles, and the
instruction needed to say WHICH one to always use, not just which one to
avoid.

Rewrote both `generate_summary()` prompts (primary + fallback) with an
explicit, named rule: Wang Yi is ALWAYS "Foreign Minister Wang Yi", Li
Qiang always "Premier Li Qiang", Han Zheng always "Vice President Han
Zheng", regardless of which title the source text happens to lead with
— plus a general fallback rule for any other Chinese official (drop
Party/Commission structure, keep the actual government role). Live-
verified against the exact same real source 3 times in a row: all 3
correctly returned "Foreign Minister Wang Yi held a strategic
dialogue..." — consistent, not a one-off lucky generation.

## 2026-09-02 continued — Dept of War (war.gov) dropped from active dispatch

Final decision after the deeper investigation the user asked for
earlier today (see the "Dept of War Still blocked" and substitute-site
entries above): **`wardept` is removed from `SOURCES` and from `main()`'s
source-dispatch list.** User's instruction, verbatim: "cool, drop then!
and note in readme."

Recap of why, for anyone reading this later without the full thread:
- war.gov's article pages (and homepage) return a flat 403 for every
  client tested — plain httpx/curl, a real headless-Playwright browser
  (no JS challenge presented, so this is an IP/ASN-level or fingerprint
  block enforced before any page logic runs, not something a smarter
  client-side technique can solve), several spoofed user-agents
  (Googlebot, Bingbot among them), and the old `defense.gov` domain.
  Reproduced independently from two separate networks — not caused by
  this project's own request volume.
- Confirmed pre-existing since at least 2026-08-04 (before the RSS-
  backend workaround was even built), so this isn't a new block that
  our own scraping triggered.
- robots.txt allowing the path is irrelevant — robots.txt is an
  honor-system opt-out that only cooperative crawlers choose to respect;
  it has no technical relationship to Akamai's bot-management layer,
  which is what's actually returning the 403 and doesn't consult
  robots.txt at all.
- Exhaustively checked for a substitute before giving up: DVIDS (related
  but not the same releases), the RSS feed's own item descriptions (too
  short to substitute for full article text), Wayback Machine (incomplete
  per-article coverage), archive.today (no meaningful coverage), and the
  department's own X accounts (@DOWResponse, @SecWar — real and active,
  but not a systematic feed of these specific releases). No viable
  substitute found.

What changed in `code/scraper.py`:
- `SOURCES` dict: `"wardept"` entry removed, replaced with a comment
  explaining the removal and pointing here.
- `main()`: the `run("wardept", scrape_wardept, ...)` dispatch line
  removed, replaced with a comment.
- `scrape_wardept()` itself: left fully intact (RSS-based discovery,
  stop-after-first-403 handling all still there and functional), just
  given a DISABLED header comment explaining it's unreachable now and
  why — reversible with one line if war.gov's policy ever changes.

Also updated: `README.md` (new paragraph under "What's covered / not
covered" explaining the exclusion) and `input/notes/SOURCES.md` (moved
the Dept of War row into the "blocked" category, matching the existing
TruthSocial/WeChat/YouTube convention, with the same reasoning folded
into the "Why ... are marked blocked" section).

Verification: `python3 -m py_compile code/scraper.py` clean; full test
suite still green afterward (see below) — nothing in the test suite
asserted `wardept` needed to be present in `SOURCES`, so removing it
broke nothing.

## 2026-09-02 continued — "U.S. dollars" false positive, same shape as Latin America

User: Chinese pieces that just mention a figure in US dollars aren't
necessarily about US-China at all — same category of bug as the Latin
America fix earlier today.

Root cause, once traced through: `CHINESE_RELEVANCE_KEYWORDS` already
deliberately excludes bare 美元 ("US dollar") for exactly this reason —
see the comment above its definition, added earlier in the project's
history. But that protection is Chinese-text-only. A Chinese release
quoting a USD-equivalent figure (e.g. "8100亿美元") gets translated to
English before the English-side keyword checks run, and the translation
comes out as "810 billion U.S. dollars" — at which point
`RELEVANCE_KEYWORDS`/`US_SOURCE_RELEVANCE_KEYWORDS`/
`_EXPLICIT_US_MENTION_RE` all matched on "U.S." alone, since none of them
knew "U.S." was just naming a currency unit here. So the Chinese-side
fix was real but got silently undone one step later, post-translation —
never live-tested against a translated example specifically, which is
why it wasn't caught until now.

Fix: added a negative lookahead to the shared "U\.S\b|United States"
alternative in both `_RELEVANCE_ALTERNATIVES` (feeds `RELEVANCE_KEYWORDS`
and `US_SOURCE_RELEVANCE_KEYWORDS`) and `_EXPLICIT_US_MENTION_RE`
directly — `U\.S(?!\.?\s*dollars?\b)\b` and
`United States(?!\s+dollars?\b)` — so "U.S. dollar(s)"/"United States
dollar(s)" no longer counts as a US mention, while a real US mention
elsewhere in the same sentence (e.g. "The United States announced a $2
billion aid package") still matches normally. Live-verified against
several realistic translated sentences plus a genuine-US-mention control
case; all came back correct. Added 4 new tests (`TestRelevanceKeywordBoundaries`/
`TestExplicitUsMention`) covering both the false positive and the
still-must-match control case — 91 tests total, all green.

## 2026-09-03 — Aug 25-31 re-run investigation: a seeding bug + 3 real relevance bugs

User deleted `output/` and asked for a fresh Aug 25-31 run (to see clean
results), then, after comparing it against the real ground-truth entries
in `input/past_trackers/U.S.-China Relations Tracker 06.23.26 -
Present.docx`, reported it was "missing so many things" and asked
whether the 30-item cap was the cause (it wasn't) and to investigate and
fix both missing entries and wrongly-included ones.

**Root cause of almost all the missing content: a seeding/dedup
contamination bug, not a scraper bug.** `seed_dedup_db.py` (correctly,
for normal use) seeds `seen_urls` from every hyperlink in
`input/past_trackers/*.docx`, including
`"...06.23.26 - Present.docx"` — but that file is the CONTINUOUSLY
UPDATED current tracker, so it already contains the Aug 25-31 week's own
ground-truth entries. Re-seeding it before a "run this exact week fresh"
exercise marked that week's own real source URLs (5 FMPRC daily
conferences, the Wang Yi/Perdue MFA-leadership meeting, several X posts)
as already-seen, so the live run skipped almost all of them — it wasn't
that the scraper couldn't find them, it was that the dedup layer told it
they were already covered. Confirmed directly: every one of those URLs
had a `seen_urls.date_seen` timestamp matching the exact moment
`seed_dedup_db.py` ran, not a real scrape.

This is specific to a debugging/comparison re-run of an ALREADY-PUBLISHED
week — normal production use (a genuinely new week) is unaffected, since
nothing in `seen_urls` could yet cover it. Fixed for this exercise with a
one-off seeding pass that walks each past-tracker doc in date-heading
order and skips marking anything seen on/after the target week's start
date (31 URLs excluded from the Present doc) — not a permanent
`seed_dedup_db.py` change, since normal seeding SHOULD cover the most
recent published week; this gap only bites when deliberately
re-running/comparing a week that's already in the current tracker.
Verified the real fix with `backtest.py` (which uses its own in-memory
sqlite connection, immune to this whole class of contamination) run
against the same week — see below.

**Bug 1 — MFA leadership: `general=True` let through an entry with ZERO
US mentions.** The Aug 26 output included "Foreign Minister Wang Yi and
Indian NSA Doval reached an 8-point consensus on the China-India boundary
question" — fetched the real source article and confirmed it: 0
occurrences of "United States"/"America"/"Washington"/"U.S." anywhere in
it. It's purely a China-India border story. Traced the cause: the free
keyword pre-filter (`CHINESE_RELEVANCE_KEYWORDS`) matched on "西藏"
(Tibet) — the article mentions Tibet only in the context of Indian
pilgrims visiting Mount Kailash, nothing to do with the US — and once
past that gate, `process_mfa_leadership_item` calls
`finalize_release_item(..., general=True)`, whose whole point (per its
2026-08-04 docstring) is to skip requiring any US connection at all,
because "substantive Chinese leadership activity" was believed to be
this source's real editorial bar. That belief rested entirely on one
past-tracker example (2026-07-28, Wang Yi/Global Development Initiative)
— which the user already confirmed elsewhere in this file was itself a
human coding error in the original tracker, not a real editorial
exception. That correction was applied to the keyword PRE-FILTER
(reverted to a plain keyword gate) back on 2026-09-02, but nobody had
gone back and fixed the EXTRACTION step's matching `general=True`
looseness — so the exact same invalidated premise kept living on one
layer downstream, and surfaced the moment an item passed the keyword
gate on an incidental, non-US topic word.

Fixed by retiring `general=True` for MFA leadership and giving
`finalize_release_item()` a `raw_zh_text` parameter (mirroring
`finalize_qa_item()`'s existing, already-correct pattern for
fmprc/mofcom/mnd's own no-exchanges-found fallback): when set, the
non-Q&A branch runs `select_relevant_chinese_paragraphs()` — the narrow,
explicit "does this paragraph literally name the US" keyword check —
instead of the LLM judgment call, and only translates the paragraphs that
actually pass. `general` itself is left in place (default `False`,
documented as deprecated) rather than ripped out, since removing a
parameter is a larger, riskier diff than just not passing it anymore.
Live-verified against both the real false positive (now correctly
produces zero US-mentioning paragraphs, gets skipped) and the real
ground-truth entry from the SAME week (Wang Yi meeting US Ambassador
Perdue — still correctly passes, since that article obviously does name
the US). 91 tests still pass (no new unit test added here specifically —
`finalize_release_item`'s LLM-calling paths aren't unit-tested by this
suite's existing convention, same as `classify_relevance` below).

**Bug 2 — `classify_relevance()`: two more real false positives, live-
reproduced.** (a) A White House release "President Trump Is Finally
Ending Canada's Free Ride" — entirely about US-Canada trade grievances —
got a YES purely because it names China ONCE, as a rhetorical aside
("Canada is joined only by the People's Republic of China in choosing
retaliation over negotiation"). (b) A Treasury annual "Portfolio Holdings
of Foreign Securities" statistical report got a YES because its data
table happens to include rows for "China, mainland," "Taiwan," and "Hong
Kong" among ~60 countries ranked by U.S. investment — zero actual prose
discussion of China anywhere in the release; `extract_key_paragraphs`
then compounded this by extracting raw table rows as if they were
"paragraphs" (literally "Treasury Department: 10\nTaiwan\n668\n668\n*\n0"
— unreadable, not prose). Both are the same underlying failure the
2026-08-04 tightening already targeted once (a Cook Islands greeting, a
US-Italy critical-minerals release) — an incidental keyword hit read as
substantive by the LLM.

Fixed by adding two explicit, named NO cases to `classify_relevance`'s
prompt: (1) China named once as a comparison inside a story that's
actually about a different country's bilateral relationship with the US,
(2) China/Taiwan/HK appearing only as one row in a multi-country
statistical table with no actual discussion. Also added a closing
framing question ("would a human editor writing this tracker actually
consider this release to be ABOUT US-China relations, or does it just
happen to contain the word 'China' somewhere?") since that's the
generalizable version of every one of these false positives so far.
Live re-verified against all 4 cases: both false positives now correctly
return NO with a correct one-sentence reason; two real control cases (the
genuine Treasury Iran/Hong-Kong-sanctions entry already in ground truth,
and a Venezuela-oil-deal release with a real, substantive paragraph about
displacing Chinese firms) still correctly return YES — the fix didn't
just get narrower, it stayed correctly permissive where the content
actually is substantive.

**Not a bug — confirmed a real, unfixable structural limit:** the X
source uses `/2/tweets/search/recent`, which only searches the last ~7
days by design (a paid "full-archive search" tier is a different product,
not a client fix). Re-running an Aug 25-31 week from Sep 3 means the
Aug 25-27 X posts (2 RapidResponse47 tweets, 1 SpoxCHN_LinJian tweet)
are permanently outside that window by the time the re-run happens — no
amount of dedup or code fixing recovers them; only running closer to the
actual week (as a normal weekly cron run would) avoids this. Confirmed
via `backtest.py`, which correctly reports these as "no_domain_match"
(x.com isn't in its dispatch table at all — it tests the web-scraped
sources only) rather than attempting and failing them.

**Not a bug — already-documented, still true:** both ground-truth items
hosted on the Chinese `www.scio.gov.cn` domain (Vice Minister Ling Ji's
remarks, and MND spokesperson Zhang Xiaogang's press conference mirrored
there) still return HTTP 521 (Cloudflare: origin down) exactly as
recorded in SOURCES.md from 2026-08-05 — re-confirmed live today via
`backtest.py`, unrelated to any of today's fixes.

**Real, narrow, unfixed gap — MOFCOM's `xwfbzt` special-topic pages.**
The Huang Ling item's ground-truth URL
(`mofcom.gov.cn/xwfbzt/2026/swbzklxxwfbh2026n8y27r/index.html`) is
in a URL namespace (`/xwfbzt/`, "special topic") distinct from the
already-covered `ztxwfbh` special-PRESS-CONFERENCE index
(`/xwfb/ztxwfbh/index.html`) — confirmed `process_mofcom_item` handles
the page fine once it has the URL (backtest.py: `queued=True`), so this
is a DISCOVERY gap only. Checked `/xwfbzt/index.html` for a walkable
listing: it's a general topic-hub page (RCEP, e-commerce, consumer
promotion campaigns, etc.), not a dated feed of individual press
conferences — no obvious mechanism to enumerate these one-off pages.
Given this is a single sighting so far (like the Xinhua/embassy-website
candidates in SOURCES.md's "found via backtesting" section), logged
there rather than built — worth another look if it recurs.

**Verification, live results:** ran `backtest.py` against the real Aug
25-31 ground truth (19 URLs) after all fixes: 9 queued correctly
(5 FMPRC + Wang Yi/Perdue MFA leadership + the MOFCOM special conference
+ 2 SCIO English releases), 0 fetch/process errors, 0 kind mismatches; 8
correctly out-of-scope for backtest.py (X/TruthSocial/YouTube, handled by
the separate live X pipeline or already known-unscrapable); 2 correctly
still-blocked (the www.scio.gov.cn 521s, unrelated to today). Then
re-seeded `output/tracker.db` excluding the target week (see above) and
re-ran the real `code/scraper.py --start 2026-08-25 --end 2026-08-31`
end-to-end to produce the actual corrected output doc.

**Two more real bugs found by actually reading that corrected output doc
(not just trusting the fixes above worked):**

**Bug 3 — a literal asterisk divider leaked into body text.** FMPRC's own
raw pages use a bare line of repeated asterisks
("**************************************************") as a visual
divider between two reporters' unrelated topics within the same press
conference transcript. `parse_qa()`'s paragraph-to-exchange conversion
(`_build_exchanges`) had no way to recognize this as a non-content
separator — it doesn't match "Label: text", so it fell through to the
generic CONT-paragraph branch and got written into the tracker as if it
were more of the PRECEDING answer (found in the real Aug 31 Guo Jiakun
trade-surplus entry). Fixed by adding `_SEPARATOR_LINE_RE` (a line made
of one character — `*`/`-`/`_`/`=`/`~` — repeated 4+ times) and skipping
it in `_build_exchanges`, in the same place empty/too-short paragraphs
are already skipped. Live-verified against the real page (0 leaked
separators in the resulting 31 exchanges, down from 1). Added 3 tests
(the real asterisk case, three other divider characters, and a control
case confirming a real short hyphenated phrase like "well-known" is
NOT treated as a divider) — 94 tests total, all green.

**Bug 4 — a real official's Chinese name mistranslated as a phonetic
guess.** The same Wang Yi/Perdue meeting entry rendered the US
Ambassador to China's name as "David Pond" instead of "David Perdue."
Root cause: FMPRC's official Chinese name for him is 庞德伟, which isn't a
transliteration his real English name would predict — `translate_to_
english()` has no way to know the real name without help, so it guessed
phonetically. This is the exact same failure shape `KNOWN_NAME_
ROMANIZATIONS` already exists to fix for Bessent/Greer/etc. (added
2026-08-05, itself found the same way — a real live translation getting
a recurring official's name wrong). Added `"庞德伟": "Perdue"` to that
glossary. Live-verified against the exact real article: now correctly
translates the headline and body as "U.S. Ambassador to China Perdue."
No new unit test (the glossary itself isn't independently tested by this
suite — it's exercised implicitly wherever `translate_to_english` is,
which needs a live model call).

Both bugs prompted one more full clean re-run (fresh wipe + re-seed
excluding the target week, same as above) to hand back a genuinely
correct final output doc rather than a hand-patched one.

## 2026-09-03 continued — user re-checked the corrected output against ground truth again, found more real gaps

User was NOT satisfied that entries were still missing after the fixes
above and asked for another full pass, itemizing exactly which
ground-truth entries were still absent. Investigated each one
individually rather than assuming the earlier fixes covered everything.

**SCIO pagination — real, fixable discovery bug.** Two real ground-truth
SCIO English releases (Aug 26 Iran-sanctions statement, Aug 28 Global-
South-development piece) were missing. `classify_relevance` correctly
said YES for both when tested directly — the bug was upstream: `scrape_
scio()` only ever fetched PAGE 1 of each of its two list_urls. Checked
for pagination and found it (`node_8020819_2.html`, `_3.html`, ... — up
to 10 checked, real content at least that deep) — both missing items
were sitting in plain sight on page 2. `node_8020819` in particular is a
fast-moving general feed: 30 items on page 1 covered as little as
~5 days, so page 1 alone isn't enough once a run is even a few days
behind. Fixed by adding pagination with the same date-aware early-stop
already used for Treasury/USTR (date comes straight from each item's own
URL, `/pressroom/YYYY-MM/DD/content_...html` — no extra fetch needed).
`process_scio_item` gained a `known_date` param, matching the existing
pattern on `process_ustr_item`/`process_treasury_item`. Live-verified:
both target URLs now found within 2 pages of `node_8020819`.

**MOFCOM's regular weekly press conference index — a real, sourced-but-
never-wired-up gap.** The Huang Ling item
(`.../xwfbzt/2026/swbzklxxwfbh2026n8y27r/index.html`) turned out to be
from MOFCOM's own REGULAR weekly press conference feed
(`/xwfb/lxxwfbh/index.html`) — the exact URL SOURCES.md already flagged
months ago as "listing page not yet built," just never connected to the
fact that it was reachable. Confirmed the page runs the identical CMS
API-gateway pattern as every other MOFCOM section (found its
`AuthorizedRead` script's `queryData`: same `webId`/`tplSetId`/`tagId`
as the rest, distinct `pageId`). One real wrinkle:
`_fetch_mofcom_cms_list`'s existing "skip any href containing 'index'"
guard (there to filter out a section's own nav-root link) silently
discarded EVERY real link on this page, because every real content page
here is itself a per-date directory whose canonical URL ends in its own
"index.html" (e.g. ".../swbzklxxwfbh2026n8y27r/index.html"). Added a
`skip_index_hrefs` parameter (default True, preserves existing behavior
for the other 5 sections) rather than changing the shared helper's
default. Date comes straight from the URL slug itself
(`swbzklxxwfbh2026n8y27r` = month 8, day 27) via a new regex, same
early-stop pattern as SCIO/Treasury/USTR. New source: `scrape_mofcom_
lxxwfbh`, wired into `SOURCES`/`main()` as `mofcom_lxxwfbh`.
`process_mofcom_item` gained a `known_date` param too.

**A genuinely non-obvious, high-impact bug found chasing down why the
new MOFCOM source was still unreliable even once discovery worked:**
testing `process_mofcom_item` on the Huang Ling URL repeatedly showed it
succeeding roughly half the time and silently producing ZERO relevant
exchanges the other half — worth chasing since Q&A parsing being
"randomly" unreliable is exactly the kind of thing that would erode
trust in the whole product. Traced it through three layers:

1. A real translation rendered one reporter's outlet as "International
   Market News Agency (IMNA) Reporter:" (47 characters) — alone on its
   own line, content on the next line (the standard orphan-label shape
   `_merge_orphan_speaker_labels` exists to handle). But `_ORPHAN_LABEL_
   RE` (and `_QA_RE`, `_LABEL_RE`, one inline regex in `parse_qa_with_
   llm`'s length-based dispatch) capped a label at `{0,40}` characters —
   too short for this real outlet name — AND used `\w` as the character
   class, which doesn't include parentheses at all, so even a SHORTER
   parenthetical label would have failed too. Fixed both: raised the cap
   to `{0,60}` (a deliberate generous bump, not a one-off patch for this
   exact outlet — real outlet names vary this much) and added `()` to
   every one of these regexes' character classes.
2. Even after that fix, the same item still failed intermittently.
   Traced further: the translation sometimes rendered the abbreviation
   as "the US government" (no periods) instead of "the U.S. government"
   — both are completely normal, common English spellings, but
   `_EXPLICIT_US_MENTION_RE`'s only US-abbreviation alternative was the
   strictly-dotted `U\.S\b`. A bare "US" mention was invisible to it.
   This is NOT a narrow, one-off gap — `_EXPLICIT_US_MENTION_RE` and
   `RELEVANCE_KEYWORDS`/`US_SOURCE_RELEVANCE_KEYWORDS` (all built from
   the same `_RELEVANCE_ALTERNATIVES`) are used everywhere across this
   pipeline to decide relevance, several with NO downstream LLM check to
   catch a miss (`filter_relevant_exchanges`, PRC-account X-tweet
   relevance). Any real content whose only US-identifying text happened
   to use "US" instead of "U.S." — extremely common, especially in LLM
   translation output — was silently, invisibly failing this check this
   entire time, with no error, no log flag, nothing to suggest anything
   was wrong. Likely a meaningful, previously invisible contributor to
   "the product doesn't consistently deliver."

   Fixed by adding `(?-i:US)` (bare, undotted "US") as a new alternative
   to both `_RELEVANCE_ALTERNATIVES` and `_EXPLICIT_US_MENTION_RE`, with
   the same dollar-amount exclusion as the dotted form. The `(?-i:...)`
   scoped-flag syntax is required, not optional: both patterns compile
   with `re.IGNORECASE` (needed for "america", "washington", etc.), and
   under plain case-insensitivity a bare `US\b` alternative would also
   match the lowercase pronoun "us" ("let us know," "join us") — `(?-i:
   US)` turns case-sensitivity back ON for just that one alternative.
   Live-verified: matches "the US government," "US Treasury," etc.;
   correctly does NOT match "let us know"/"join us"/"contact us"; dollar-
   exclusion still applies to the bare form too ("US dollars" still
   excluded). Re-ran the exact real failing MOFCOM URL 5 times after
   this fix: 5/5 correctly found and kept the tariff Q&A block, up from
   roughly half before.

Added 7 new tests across `TestRelevanceKeywordBoundaries`/
`TestExplicitUsMention` (bare-US matches, lowercase-pronoun non-matches,
dollar-exclusion-still-works) and `TestBuildExchanges`/
`TestMergeOrphanSpeakerLabels` (the long parenthetical label case) — 101
tests total, all green.

**FMPRC Aug 25 — confirmed a genuine, unfixable site-side gap, not a
missed pagination depth.** Checked FMPRC's own list pages 1-3 (`lxjzh/`,
`index_2.html`, `index_3.html`) directly: page 1 covers Aug 26-Sep 3,
page 2 jumps straight to Aug 5-14 — Aug 15-25 isn't linked from ANY of
these pages as of today. The article itself still exists at its known
URL (confirmed via direct fetch), it's just not currently reachable
through the site's own crawlable index at any checked depth — a genuine,
site-side data-availability gap (likely a delayed-translation artifact
on FMPRC's end), not something any amount of our own pagination-chasing
can recover. Matches the exact shape of the already-documented X 7-day-
window limitation: harmless for a normal on-time weekly run, only bites
a catch-up run for an already-stale week.

**Built a proper, sourced Chinese-name glossary per user request**, not
just the one-off Perdue fix: `input/notes/US_OFFICIALS_CHINESE_NAMES.md`
— every name verified against a real FMPRC/MFA/Xinhua/mainland-media
source (not guessed from phonetics, which is exactly the failure mode
that started this). Added Hegseth (赫格塞斯 — caught and corrected a
plausible-but-WRONG guess, 海格塞斯, before it ever shipped), Gabbard
(加巴德), Ratcliffe (拉特克利夫), Leavitt (莱维特), Miller (米勒), plus
Biden/Sullivan/Blinken for older `backtest.py` weeks. Left Steven Cheung
out, flagged as unverified — he has a real documented Chinese-heritage
family name rather than a media-assigned transliteration, and it's
unclear which (if either) PRC state media would use; better to leave a
gap than guess wrong twice in one glossary. `KNOWN_NAME_ROMANIZATIONS`
in `code/scraper.py` updated to match.

**Verification**: full re-seed (excluding target week, same script as
before) + full clean `code/scraper.py --start 2026-08-25 --end
2026-08-31` re-run planned after all of the above, this time invoked via
`./run_week.sh` per direct user request ("do it thru terminal so I can
see progress of run too and costs") rather than a bare `python3` call —
same underlying pipeline, just the interface the user actually asked
for going forward.

Final `./run_week.sh` re-run confirmed everything above works in the
real pipeline (not just isolated tests): MOFCOM's new `mofcom_lxxwfbh`
source correctly found and queued the Huang Ling tariff item; the
Wang Yi/Perdue entry rendered "Perdue" correctly everywhere, including
in an X repost; no false positives resurfaced. 14 entries, $0.27,
14m47s. Remaining gaps all confirmed structural/out-of-scope, not code
bugs: FMPRC's Aug 25 conference (dropped from FMPRC's own crawlable list
entirely, confirmed checking 3 pages deep), 2 items on the still-down
`www.scio.gov.cn` domain, 2 X posts already outside the 7-day search
window by the time this catch-up run happened, and Truth Social/YouTube
(never in scope).

## 2026-09-03 continued — explained HTTP 521, added an end-of-run failure report + standing reminder

User asked why `www.scio.gov.cn` returns "HTTP 521, Cloudflare" and
whether that means we're being blocked — explained it isn't: 521 is
Cloudflare's own "Web Server Is Down" code, meaning Cloudflare (sitting
in front of the origin as a reverse proxy) can't even reach the real
server behind it. That's a statement about the SITE's infrastructure
being down, not about us — a genuine block usually shows up as a 403, a
CAPTCHA, or a JS challenge page instead, which is a categorically
different signal. Nothing to fix on our end; this resolves itself
whenever MOFCOM's own hosting comes back.

User also asked for two things to be visible automatically at the end of
every run: (1) which sources actually failed (not just "0 new items,"
a real fetch/HTTP error), and (2) a standing reminder to manually check
Truth Social/YouTube/Dept of War, since nothing in this tool covers them
and it's easy to forget that when everything else IS covered.

Implemented via a small `_SourceErrorCapture(logging.Handler)`,
temporarily attached to `log` for the duration of each source's `run()`
call in `main()` — collects every ERROR-level message logged during that
window (a real fetch failure, an HTTP error, an unhandled exception)
into a plain list, with zero changes needed to any individual
`scrape_*`/`process_*_item` function (every real failure already calls
`log.error(...)` somewhere; this just listens for it). Deliberately only
ERROR+, not INFO's routine "0 new items"/"skipping" — those are healthy,
not failures, and would drown out real signal. At the end of a run,
prints either `No source errors this run.` or a per-source breakdown
(display name, key, error count, first 3 unique messages, "...and N
more" if there's more) — visible in the terminal without needing `-v` or
opening `logs/` at all, since the console handler caps at WARNING by
default and this prints via `print()`, not logging. The standing
Truth-Social/YouTube/Dept-of-War reminder prints unconditionally, every
run, right after. Added `TestSourceErrorCapture` (2 tests: captures
ERROR+, ignores INFO/skips) — 103 tests total, all green.

## 2026-09-03 continued — classify_relevance's "does this involve China" question is meaningless for a Chinese-government source

User spotted a real false positive by eye: a generated entry —
"The Ministry of Science and Technology issued ethical guidelines for
artificial intelligence (AI) medical imaging research and clinical
application" — with no US mention anywhere. Investigated rather than
just deleting the one entry, since a single spotted bug usually means a
whole class of the same bug.

Root cause: `classify_relevance()`'s prompt asks "does this explicitly
and substantively involve China" — exactly the right question for a
US-origin source (state/treasury/ustr/whitehouse), where that's a
genuinely rare, meaningful signal. Applied to SCIO — a CHINESE
government source — it's a trivial, nearly-always-true question: of
course a State Council Information Office release "involves China."
Tested 4 real SCIO releases from the same week directly against the
unmodified prompt: it correctly said NO to a healthcare-access report
and a housing-policy circular, but YES to an AI-ethics guideline and a
bare manufacturing-PMI reading — all four are equally domestic-only,
zero US mention in any of them. The LLM was applying the SAME prompt
inconsistently because the prompt itself doesn't ask the right question
for this direction.

The obvious fix (require an explicit US mention, matching MFA
leadership's fix from earlier today) turned out to be too strict: a
real, already-confirmed ground-truth SCIO entry (Aug 28, "China to
continue contributing to world development... rejecting the so-called
'China squeeze' narrative") has ZERO explicit US mention anywhere, yet
is substantively about US-China economic friction — it's rebutting a
US-driven "China squeeze"/decoupling narrative without ever naming the
US by name. A strict explicit-mention gate would have wrongly excluded
this real entry — the same trap as the (since-invalidated) Wang Yi/GDI
counter-evidence, except this one IS genuinely valid ground truth, not a
human coding error.

Fixed by giving `classify_relevance()` a `chinese_origin: bool = False`
parameter with a SEPARATE prompt for that direction: asks whether the
release involves the US/US-China relations/Taiwan/HK, OR responds to a
US-driven narrative even implicitly (naming "China squeeze"/
"decoupling"/"de-risking"/"overcapacity" as concrete examples) — versus
ordinary domestic Chinese policy/regulation/statistics with no such
angle. Wired to `chinese_origin=True` at both real call sites that
needed it: `process_scio_item` (via `process_release_common`) and
`process_mofcom_item`'s English-mirror branch (found the identical bug
there too while auditing every `classify_relevance()` call site — same
issue, just less visible since a wrong NO there gets masked by
`finalize_qa_item`'s no-exchanges fallback never running). Left the
THIRD real call site (`process_x_tweet`'s non-PRC-account branch)
unchanged — that one screens US-GOVERNMENT X accounts, where "does this
involve China" is exactly the right question already; the PRC-account
branch right next to it already has its own correct, separate handling
(a narrow `_EXPLICIT_US_MENTION_RE` check, no classify_relevance call at
all — this exact same "does this involve China is trivial for a
PRC-government voice" lesson was already learned there once).

Live-verified against all 6 known cases (the 2 false positives, the 2
already-correct NOs, and both real ground-truth YESes including the
zero-explicit-mention "China squeeze" one): 6/6 correct, re-checked 3x
on the AI-ethics case for consistency (all 3 correctly NO). 103 tests
still pass (no new unit test — `classify_relevance` isn't unit-tested by
this suite's existing convention, same as its base-case prompt).

## 2026-09-03 continued — auditing a Sep 1-3 run surfaced 3 more real bugs

User asked to keep going: audit the Aug 25-31 fix more (validating
against ground truth again) and also run — for the first time — Sep 1-3,
which has no manually-compiled ground truth yet (too recent), so this
required the same manual, fetch-and-verify-by-hand rigor used all day
rather than backtest.py's automated comparison. Re-ran backtest.py for
Aug 25-31 first to confirm the chinese_origin fix didn't regress anything
(still 9/19 queued, 0 errors, 0 kind mismatches) — then ran a real
`./run_week.sh --start 2026-09-01 --end 2026-09-03` and read every single
entry in the output doc against its actual source.

**Bug 5 — the chinese_origin fix was still too loose for bare Taiwan/HK
mentions.** Two real entries surfaced: "China Coast Guard patrols waters
east of Taiwan Island" and "China completes marine geophysical survey in
waters east of Taiwan Island" — both routine PRC sovereignty-assertion
notices, confirmed ZERO mentions of the US anywhere in either. The
chinese_origin prompt from earlier today explicitly listed "Taiwan, Hong
Kong" as an automatic YES trigger regardless of any US connection —
live-tested, confirmed both got YES purely for containing the word
"Taiwan." This is the exact same failure shape `filter_relevant_
exchanges` already learned to avoid on 2026-09-01 (a Taiwan-only
China-Japan exchange with zero US involvement) — a shared topic isn't
the same as US-China relations. Fixed by requiring Taiwan/HK content to
specifically connect to the US (arms sales, a US policy action, a US
official's statement) to count, with explicit NO examples (a coast guard
patrol notice, a marine survey, a routine sovereignty assertion) added
to the prompt. Re-verified all 5 known cases (the 2 new false positives,
the AI-ethics false positive, and both real China-squeeze/Iran-sanctions
YESes) — 5/5 correct. Re-ran `backtest.py` for Aug 25-31 again — still
9/19, unaffected (Aug 25-31's one Taiwan entry, the Zhang Xiaogang F-16
item, explicitly names the US directly anyway).

**Bug 6 — a real LLM hallucination, not just a wrong title.** A Treasury
G20 Finance Ministers statement (~18,500 characters, confirmed zero
mentions of "Yellen," "Bessent," or even the word "Secretary" anywhere)
got summarized as "Treasury Secretary Janet Yellen and other G20 Finance
Ministers assembled in Asheville..." — Yellen hasn't been Treasury
Secretary since January 2025. `generate_summary()`'s prompt already has
an explicit "do not invent a name" instruction (added earlier in this
project's history) — the model violated it anyway, almost certainly
pattern-matching "G20 Finance Ministers meeting" to whichever name is
most strongly associated with that event type in training data. Fixed
with a second, PROGRAMMATIC layer rather than trying to word the prompt
even more strongly: `_hallucinated_officials(summary, source_text)`
checks a fixed list of real recurring officials' surnames (Bessent,
Greer, Lutnick, Rubio, Vance, Navarro, Yellen, Perdue, Hegseth, Gabbard,
Ratcliffe, Leavitt, Miller, Biden, Sullivan, Blinken — "Trump" excluded,
he's named constantly as an adjective, "Trump tariffs," which isn't the
failure mode this catches) against the ORIGINAL source text; if a name
in the summary isn't found anywhere in the source, `get_summary_and_
anchor()` retries ONCE with an explicit correction naming the specific
wrong name, and if the retry is still bad, keeps the retry anyway
(better odds) and flags the URL for human review rather than silently
shipping a specific, factually wrong claim. Live-verified against the
exact real article: first attempt named Yellen (caught), retry correctly
produced "The Treasury Department participated in the G20 Finance
Ministers and Central Bank Governors meeting..." with no invented name.
Added `TestHallucinatedOfficials` (4 tests) — 107 tests total.

**Bug 7 — a genuine source-side duplicate, not a code bug, but worth
guarding against anyway.** Two entries in the Sep 1-3 output covered the
identical headline ("Trump Administration Launches Foundry School...")
under two DIFFERENT state.gov URLs, 2 days apart. Traced directly via
state.gov's own WP-API: two separate post IDs (702682, published Sep 1;
702743, published Sep 3) for the same title, with slugs differing by
exactly one missing hyphen ("workforce-behind" vs "workforcebehind") —
State's own web team appears to have republished rather than edited in
place. Since the URLs are genuinely different strings, normal is_seen()
dedup can't catch this. Added a second, narrower net: `queue_entry()`
now also tracks a same-run `_url_dedup_slug()` fingerprint (the URL path
with every non-alphanumeric character stripped, so "workforce-behind"
and "workforcebehind" collapse to the same string) — a second occurrence
of an already-queued slug THIS RUN is dropped with a warning, logged the
same way the existing date-range filter already silently drops an
out-of-range item. Deliberately same-run only (not persisted against the
`entries` table) since this specific case surfaced within a single run —
a persistent, across-runs version isn't built yet; would need a real
case spanning two separate runs to justify the extra complexity. Added
`TestUrlDedupSlug` + `TestQueueEntryRepublishDuplicateGuard` (4 tests) —
111 tests total, all green.

Not investigated further this round (ran out of scope for one sitting,
not because they looked wrong): the MOFCOM English-mirror
`classify_relevance` fix's downstream effects on the 5 Chinese-language
MOFCOM sections (mofcom_daily/leadership/dept_leadership/bureau_heads/
special_conf/lxxwfbh) — these route through the CJK branch
(`select_relevant_chinese_paragraphs`, already narrow/correct), not the
classify_relevance branch, so they were never exposed to this bug in the
first place; confirmed by re-reading the code path, not just assumed.

**Applying the fixes to the already-generated Sep 1-3 output**: since all
6 bad entries (4 Taiwan-only false positives — the CCG patrol, marine
survey, and 2 Zhang Han/Taiwan Affairs Office items found applying the
same Bug-5 check — plus the Yellen hallucination and the Foundry School
duplicate) were already scraped, summarized, and written to `entries`
BEFORE these fixes existed, simply re-running would NOT have caught
them — is_seen() would just skip everything already recorded, unaffected
by any code change since. Fixed by direct, targeted surgery instead of a
wasted re-run: deleted the 4 Taiwan-only rows and the duplicate Foundry
School row from `entries` (ids 21, 23, 24, 26, 30), updated the Yellen
row (id 33) with the corrected, already-verified retry summary, then
re-rendered `output/US-China Tracker Sep 1-3, 2026.docx` straight from
the corrected `entries` table via `render_doc_for_range()` — no live
re-scrape needed, since that function already reads purely from the DB.
Confirmed the corrected doc reads clean end to end.

**One more thing spotted while re-reading the corrected doc, flagged but
NOT auto-fixed**: the Sep 2 FMPRC daily conference's own Q&A already
covers a reporter's question about Ronald Sakolsky's China visit, and a
SEPARATE, later SCIO article (dated Sep 3, a different URL, a different
source module) covers the same underlying quote as its own feature
piece — real content overlap, but NOT the same failure shape as the
Foundry School case (that was one story, one source, republished under
a near-identical URL; this is one underlying quote covered by two
genuinely different sources, each contributing at least one detail the
other doesn't — the SCIO piece includes Sakolsky's own direct quote,
which the FMPRC Q&A doesn't). Building a reliable cross-SOURCE semantic-
duplicate detector is a meaningfully harder, fuzzier problem than the
exact-slug fix above, with real risk of false-positively merging two
genuinely different stories that just share a topic — not attempted
without a clearer, more clearly-wrong case to design against. Left as-is
for now; worth watching for recurrence.

## 2026-09-03 continued — the bare-Taiwan/HK loophole was in BOTH prompts, not just the Chinese-origin one

User asked directly why the "Foundry School" entry got included — it's a
workforce-training program (Pax Silica) whose only connection to
anything China-adjacent is naming Taiwan ONCE as one of four listed
program participants (Republic of Korea, Japan, Taiwan, India).
Confirmed via the real full source text (fetched by post ID once the
slug had aged out of the WP-API's default 50-item window): zero mentions
of "China"/"Chinese" anywhere in the entire ~3,300-character release.

Root cause: earlier today's Bug-5 fix (Taiwan/HK must connect to the US
to count) was only applied to the `chinese_origin=True` prompt branch
(for SCIO/MOFCOM). The ORIGINAL prompt — used for every US-origin source
(state/treasury/ustr/whitehouse) — still had the exact same unconditional
"Taiwan, or Hong Kong" trigger, unpatched. Live-confirmed the bug
directly: the Foundry School text got a YES from `classify_relevance
(chinese_origin=False)` with the reasoning "explicitly mentions Taiwan as
a participant... which is a substantive involvement in US-China
relations given the sensitive nature of Taiwan's international
participation" — exactly the shape of reasoning already known to be
wrong. Fixed by adding a third named NO case to the original prompt:
Taiwan/HK appearing only as one of several listed countries/participants
in an unrelated multilateral program, with no discussion of political
status or a China-specific angle. Live-verified: the Foundry School text
now correctly gets NO; a genuine control case (a real US arms-sale-to-
Taiwan story with China's explicit objection) still correctly gets YES.
Re-ran `backtest.py` for Aug 25-31 again — still 9/19, unaffected.

Also found and removed a SECOND instance of the identical pattern while
checking for others: a Pacific Islands Forum readout (Deputy Secretary
Landau, $150M in Pacific aid) whose only Taiwan/China-adjacent content
was "Taiwan as a key partner of Palau" in a hospital-infrastructure
partnership alongside Australia/Japan/New Zealand/South Korea — zero
China mention. (Couldn't re-fetch the exact original full article a
second time — it had changed/depublished on state.gov's own site by the
time of this check — so this one is confirmed against the already-
extracted paragraph text rather than a fresh full-article fetch; same
strong pattern match as Foundry School either way.) Scanned the rest of
the Aug 25-31 and Sep 1-3 output for any other Taiwan/HK mention: none
found beyond the ones already verified legitimate (an explicit Taiwan
arms-sale story, an explicit Hong Kong sanctions-target company).

Removed both bad entries (Foundry School, Pacific Islands Forum) from
`entries` directly and re-rendered `output/US-China Tracker Sep 1-3,
2026.docx` again. 111 tests still pass (no new test — this is the same
`classify_relevance` prompt-tuning category already established as not
unit-tested).

## 2026-09-03 continued — added a Windows launcher, renamed both by platform

User asked whether "the app thing" works on Windows — it doesn't; `.app`
bundles are a macOS-only concept, and `Run Weekly Tracker.command`/
`run_week.sh` are bash, which Windows has no native way to run either.
User asked for a Windows equivalent, then to rename both by platform so
the ambiguity (which one's for which OS?) can't come up again.

Added `run_week.bat` (direct counterpart to `run_week.sh` — same
seed-if-needed-then-run logic, `%*` forwards `--start`/`--end`/`-v`
straight through) and `Run Weekly Tracker (Windows).bat` (counterpart to
the interactive `.command` launcher — same two-question prompt, calls
`run_week.bat`, `pause` at the end to keep the window open for reading
the summary, matching the Mac version's exact wording via `echo` +
`pause >nul` instead of `pause`'s own default text).

Renamed `Run Weekly Tracker.app` → `Run Weekly Tracker (Mac).app` and
`Run Weekly Tracker.command` → `Run Weekly Tracker (Mac).command`. The
`.app` internally hardcodes the exact filename of the `.command` file it
opens (confirmed via `osadecompile` on its compiled AppleScript) — so the
rename needed a real fix, not just a `mv`: recompiled `main.scpt` with
the updated filename via `osacompile`, installed it into the existing
bundle (preserving the already-fixed custom icon setup — verified
`Assets.car` still absent and `CFBundleIconName` still unset via
PlistBuddy, both preconditions for the custom `.icns` to actually
resolve, per the icon investigation earlier in this project's history),
then re-signed ad-hoc (`codesign --force --deep -s -`) since modifying a
signed bundle's contents invalidates its existing signature — the same
lesson already learned once when the icon was first fixed.

Updated README.md throughout: parallel Mac/Windows instructions in
"Running it yourself," a Windows Task Scheduler example (GUI + `schtasks`
one-liner) alongside the existing cron/launchd one, and the project-files
table. Updated 2 stale comment cross-references in `code/scraper.py` to
the new Mac filename. 111 tests still pass (no test coverage needed or
attempted for the shell/batch launchers themselves — matches this
project's existing convention of verifying shell-script changes via
direct execution/inspection rather than unit tests, since they have no
pure-function logic to test).

## 2026-09-03 continued — verified GitHub is complete, removed genuinely dead code, found a real bug in format_entry.py

User asked for a general pass: confirm everything needed to run is
really on GitHub, clean up unnecessary comments, and keep looking for
bugs.

**GitHub completeness**: did a real fresh `git clone` into a scratch
directory (not just `git ls-files`), copied in a real `.env`, ran `pip
install -r requirements.txt`, `python code/seed_dedup_db.py`, and
`python code/scraper.py --source ustr` end to end — all worked
correctly, including the error-report and Truth-Social-reminder features
from earlier today. Confirms the repo is genuinely self-contained, not
just superficially. Also fixed a stale `.gitignore` comment referencing
`run_daily.sh`, a name the launcher hasn't had since early in the
project (it's `run_scheduled.sh` now).

**Removed genuinely dead code**: `extract_key_paragraphs()`'s
`general=True` branch and `finalize_release_item()`'s `general`
parameter — confirmed via a real usage search that NO caller passes
`general=True` anymore (MFA leadership switched to `raw_zh_text` earlier
today; see the classify_relevance chinese_origin entry above). This
wasn't just "an unnecessary comment" — the whole branch was unreachable,
and leaving working-but-buggy code reachable via a parameter is a real
landmine for a future re-introduction of the exact bug already found and
fixed once. Deleted the branch, simplified both function signatures,
and rewrote `extract_key_paragraphs()`'s docstring to explain what
`general=True` used to do and why it was retired, since the history is
still worth knowing even with the code gone. Also fixed a real, now-
stale comment found in the same area: `select_relevant_chinese_
paragraphs()`'s docstring still said "Not used for MFA leadership
sources" — false as of today's earlier fix, corrected to say it's used
by every Chinese-source caller including MFA leadership now.

**Fixed two more stale entries in `input/notes/SOURCES.md`**: the
MOFCOM weekly-press-conference row still said "not added — listing page
not yet built," contradicting the `mofcom_lxxwfbh` source built earlier
today for exactly that URL — updated to ✅. The "Candidates found via
backtesting" table still listed MOFCOM's `/xwfbzt/` pages as an
unresolved discovery gap for the same reason — removed that row, noted
it as resolved.

**Real bug found in `code/format_entry.py`** (the manual add-an-entry
tool — separate from the main scraper, never covered by test_scraper.py
at all): tested it end-to-end on its own sample file
(`input/notes/sample_qa.txt`) as part of "make sure it all works," and
found `classify_qa_with_llm()` silently produces WRONG speaker
assignments. Root cause: the function numbers paragraphs 1-N in its
prompt, asks the model to classify each, then assumes the model's
returned JSON array's POSITION lines up with the input list
(`labels[i]`) — with no check. When the model finds one paragraph
awkward to classify (in the real case, a bare "June 18, 2026" masthead
date line with no real speaker) and quietly omits it from its response,
every SUBSEQUENT label silently shifts by one position: the reporter's
real question got labeled as Lin Jian's answer, and Lin Jian's real
answer got the wrong treatment too — reproduced 3 times in a row on the
same real input, not a one-off. This is exactly the failure mode
`code/scraper.py`'s own Q&A parsing already learned to avoid (see
`parse_qa_from_plaintext`'s "regex-first, LLM-as-last-resort" docstring)
— `format_entry.py` never got that lesson applied to it since it's a
separate, standalone tool.

Fixed by having the model echo back an explicit `"paragraph"` number on
every returned object, then matching responses back to input paragraphs
by that number (a dict lookup) instead of by list position — a paragraph
the model omits now safely falls back to a plain CONT/no-speaker default
(inert, doesn't corrupt anything downstream) instead of shifting every
later paragraph's real label onto the wrong text. Also strengthened the
prompt itself to explicitly require every paragraph number to appear
exactly once. Live-verified 3 times after the fix: consistent, correct
speaker assignment every time.

While fixing this, also noticed the masthead date line itself ("June 18,
2026") was rendering as its own stray, contentless paragraph in the
finished entry once the misalignment bug no longer masked it — its date
was already being extracted separately for the entry's own heading, so
the raw line was pure redundancy. Added `_is_pure_date_line()` and
filtered it out of the paragraphs sent to Q&A classification.

Added `code/test_format_entry.py` — this file had ZERO test coverage
before today. 17 tests covering the pure functions (`preprocess_text`,
`detect_content_type`, `detect_language`, `extract_date`,
`_is_pure_date_line`, and the paragraph-number-matching logic itself
with a fake response) — not `classify_qa_with_llm`'s actual LLM
judgment, matching test_scraper.py's own established convention of only
unit-testing pure functions. 111 + 17 = 128 tests total across both
files, all green.

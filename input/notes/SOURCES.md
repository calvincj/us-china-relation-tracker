# Source inventory — US-China Relations Tracker

Extracted from `input/source_links/US-China Relations Tracker Links.docx` (hyperlink targets
pulled from the doc's XML, not retyped by hand). Status reflects this
session's work; `scraper.py --source <key>` keys are given where implemented.

Legend — **Approach**: `static` = requests/httpx + BeautifulSoup;
`playwright` = JS-rendered, needs headless browser; `blocked` = not
programmatically scrapable without paid API / login / unofficial mirror.

## PRC Government

| Source | URL | Lang | Tier | Approach | Status |
|---|---|---|---|---|---|
| MFA daily press conferences | https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/ | EN | normal | static | ✅ `fmprc_conf` |
| MFA daily press conferences | https://www.mfa.gov.cn/web/wjdt_674879/fyrbt_674889/ | ZH | normal | static | skipped — same conferences as the EN page above, EN is authoritative and already covered |
| MFA spokesperson remarks | https://www.fmprc.gov.cn/eng/xw/fyrbt/fyrbt/ | EN | normal | static | ✅ `fmprc_remarks` |
| MFA leadership speeches | https://www.mfa.gov.cn/web/ziliao_674904/zyjh_674906/ | ZH | normal | static + translate | ✅ `fmprc_leadership_speeches` (added this session) |
| MFA leadership activity | https://www.mfa.gov.cn/web/wjdt_674879/wjbxw_674885/ | ZH | normal | static + translate | ✅ `fmprc_leadership_activity` (added this session) |
| MOFCOM weekly press conferences | https://www.mofcom.gov.cn/xwfb/lxxwfbh/index.html | ZH | normal | static | ✅ `mofcom_lxxwfbh` (added 2026-09-03) — found via a real Aug 27, 2026 ground-truth entry (Spokesperson Huang Ling on a proposed U.S. tariff hike) that turned out to live at `/xwfbzt/YYYY/swbzklxxwfbhYYYYnMyDr/index.html`, a per-date directory this index links to; date is parsed straight from that URL slug for the same early-stop pattern as Treasury/USTR/SCIO |
| MOFCOM daily spokesperson remarks | https://www.mofcom.gov.cn/xwfb/xwfyrth/index.html | ZH | normal | static + translate | ✅ `mofcom` (article-level handling only, added 2026-08-04 — **correction**: this was previously marked "redundant with the English mirror," which backtest.py disproved — a real past-tracker entry was sourced directly from this Chinese page, with content not confirmed present on the English mirror. `process_mofcom_item` now CJK-detects and translates when it hits one of these URLs; list-page discovery for this specific index still only happens via the English mirror below, so Chinese-only items that never got mirrored won't be found yet — that's the next gap to close here) |
| MOFCOM daily spokesperson remarks | https://english.mofcom.gov.cn/News/PressConference/index.html | EN | normal | static | ✅ `mofcom` |
| MOFCOM leadership activity | https://www.mofcom.gov.cn/xwfb/ldrhd/index.html | ZH | normal | static + translate | ✅ `mofcom_leadership` (added 2026-08-05) |
| MOFCOM dept. leadership activity | https://www.mofcom.gov.cn/xwfb/bldhd/index.html | ZH | normal | static + translate | ✅ `mofcom_dept_leadership` (added 2026-08-05) |
| MOFCOM special press conferences | https://www.mofcom.gov.cn/xwfb/ztxwfbh/index.html | ZH | normal | static + translate | ✅ `mofcom_special_conf` (added 2026-08-05) — live-checked and currently empty (no items published recently), which is a valid state, not a bug |
| MOFCOM announcements | https://www.mofcom.gov.cn/xwfb/sjfzrfb/index.html | ZH | normal | static + translate | ✅ `mofcom_bureau_heads` (added 2026-08-05) |
| MOFCOM daily news release | https://www.mofcom.gov.cn/xwfb/rcxwfb/index.html | ZH | normal | static + translate | ✅ `mofcom_daily` (added 2026-08-05) — live-verified: correctly recovered and correctly classified as "release" the exact "China's Position on So-called Overcapacity" position paper that motivated adding this source in the first place |
| State Council (SCIO) ministry press announcements | http://www.scio.gov.cn/xwfb/bwxwfb/ | ZH | normal | static + translate | attempted 2026-08-05, blocked — the whole `www.scio.gov.cn` domain (not just this path) returns HTTP 521 (Cloudflare: origin server down) on both HTTP and HTTPS, with or without cert verification; `english.scio.gov.cn` (already covered via `scio`) works fine, so this looks like site-side downtime specific to the Chinese domain rather than a permanent block — worth retrying later |
| State Council press announcements | http://english.scio.gov.cn/pressroom/node_8020819.html | EN | normal | static | ✅ `scio` (added this session) |
| State Council press announcements | http://english.scio.gov.cn/pressroom/node_8020805.html | EN | normal | static | ✅ `scio` (same module, second listing page) |
| Ministry of National Defense weekly press conf. (mid-month) | http://www.mod.gov.cn/gfbw/xwfyr/yzxwfb/index.html | ZH | normal | static + translate | ✅ `mnd` (added this session) |
| Ministry of National Defense weekly press conf. (end-of-month) | http://www.mod.gov.cn/gfbw/xwfyr/lxjzh_246940/index.html | ZH | normal | static + translate | ✅ `mnd` (same module, second listing page) |
| Chinese Embassy in the US — X | https://x.com/ChineseEmbinUS | EN | normal | static (X API search) | ✅ `x` — see "X (Twitter)" below |
| Lin Jian — X | https://x.com/SpoxCHN_LinJian | EN | normal | static (X API search) | ✅ `x` |
| Mao Ning — X | https://x.com/SpoxCHN_MaoNing | EN | normal | static (X API search) | ✅ `x` |
| MFA WeChat | (official account, no listing URL) | ZH | **less important** | blocked | ❌ |
| MOFCOM WeChat | (official account, no listing URL) | ZH | **less important** | blocked | ❌ |

## US Government

| Source | URL | Lang | Tier | Approach | Status |
|---|---|---|---|---|---|
| @RapidResponse47 — X | https://x.com/RapidResponse47 | EN | normal | static (X API search) | ✅ `x` |
| White House news | https://www.whitehouse.gov/news/ | EN | normal | static (RSS) | ✅ `whitehouse` |
| Donald Trump — TruthSocial | https://truthsocial.com/@realDonaldTrump | EN | normal | blocked | ❌ — **RollCall Factbase** (https://www.rollcall.com/factbase/trump/) mirrors his Truth Social posts as plain static HTML with timestamps; viable fallback if this becomes a priority, not wired up yet |
| White House YouTube channel | https://www.youtube.com/@WhiteHouse | EN | normal | blocked | ❌ |
| News interviews w/ Trump/Vance/Rubio/Bessent re: China | (no single feed) | EN | normal | blocked | ❌ — no canonical source list; would require broad media monitoring, out of scope for a scraper |
| JD Vance — X | https://x.com/JDVance | EN | normal | static (X API search) | ✅ `x` |
| Steve Cheung — X | https://x.com/StevenCheung47 | EN | normal | static (X API search) | ✅ `x` |
| White House — X | https://x.com/WhiteHouse | EN | normal | static (X API search) | ✅ `x` |
| Karoline Leavitt — X (@PressSec) | https://x.com/PressSec | EN | normal | static (X API search) | ✅ `x` |
| Scott Bessent — X | https://x.com/SecScottBessent | EN | normal | static (X API search) | ✅ `x` |
| Donald Trump — X | https://x.com/realDonaldTrump | EN | normal | static (X API search) | ✅ `x` |
| Marco Rubio — X | https://x.com/SecRubio | EN | normal | static (X API search) | ✅ `x` |
| State Department press releases | https://www.state.gov/press-releases/ | EN | normal | static (WP API/RSS) | ✅ `state` |
| Dept. of War press releases | https://www.war.gov/News/ | EN | normal | blocked | ❌ — see "Why X / TruthSocial / WeChat / YouTube / Dept of War are marked blocked" below |
| Treasury press releases | https://home.treasury.gov/news/press-releases | EN | normal | static | ✅ `treasury` |
| USTR press releases | https://ustr.gov/about-us/policy-offices/press-office/press-releases | EN | normal | static | ✅ `ustr` |
| USTR — X | https://x.com/USTradeRep | EN | **less important** | blocked | ❌ not in the active `x` search groups (`X_INCLUDE_LESS_IMPORTANT = False`) |
| DoW Rapid Response — X | https://x.com/DOWResponse | EN | **less important** | blocked | ❌ same as above |
| John Ratcliffe — X | https://x.com/CIADirector | EN | **less important** | blocked | ❌ same as above |
| Pete Hegseth — X | https://x.com/SecWar | EN | **less important** | blocked | ❌ same as above |
| Stephen Miller — X | https://x.com/StephenM | EN | **less important** | blocked | ❌ same as above |
| Tulsi Gabbard — X | https://x.com/DNIGabbard | EN | **less important** | blocked | ❌ same as above |
| Howard Lutnick — X | https://x.com/howardlutnick | EN | **less important** | blocked | ❌ same as above |

## X (Twitter) — now implemented, search-based

Superseded 2026-09-02: unauthenticated scraping of x.com is still blocked
(JS challenge + login wall) and against X's ToS, but the paid `X_API_KEY`
read API turned out to be affordable once redesigned around search rather
than per-account timeline polling — a single `/2/tweets/search/recent`
call can combine a keyword filter with MULTIPLE accounts in one query,
billed once per post actually returned rather than once per account
polled regardless of hits (an ~16x cost reduction measured on a real
first-activation run). All 11 "normal"-tier accounts across both tables
above are covered by the `x` source (2 queries per run — one PRC-account
group, one US-account group); the other 7 "less important"-tier accounts
are implemented identically but not polled by default
(`X_INCLUDE_LESS_IMPORTANT = False`, to control cost) — flip it to add
them. (18 accounts total, matching the original links doc.)

**Real limitation, not a bug**: `/2/tweets/search/recent` only searches
the last ~7 days by design — a paid "full-archive search" tier is a
separate product, not something a client-side fix works around. A normal
weekly run is well within that window, so this doesn't affect regular
production use — it only bites a DELAYED re-run of an old week (e.g.
re-generating an Aug 25-31 week's output from September 3), where the
earliest days in the window have already aged out of what
`/search/recent` can return by the time the re-run happens. Confirmed
live 2026-09-03 — see NOTES.md.

## Why TruthSocial / WeChat / YouTube / Dept of War are marked blocked
- **TruthSocial**: same shape of problem (auth-gated JS app, no public API).
  **RollCall Factbase** is the documented workaround for Trump's posts
  specifically — it's a static-HTML mirror already used by researchers for
  this exact purpose. Not implemented yet; flagged as the clear next step if
  Truth Social coverage becomes a priority.
- **WeChat official accounts**: articles aren't listable without either the
  account owner's API credentials or an unofficial mirror/aggregator; both
  MFA's and MOFCOM's WeChat are marked "less important" in the source doc
  itself, so this is a low-cost thing to defer.
- **YouTube channel**: originally assessed 2026-08 as needing custom
  transcript-scraping infrastructure + a relevance filter over an entire
  channel's uploads with no dedicated "China" playlist — higher effort
  than the direct press-release/spokesperson text sources for
  comparatively thin incremental coverage (White House press conferences
  are already covered in text form via `whitehouse`). **Worth
  re-assessing, 2026-09-03**: Gemini's API added a "video understanding"
  feature (confirmed via ai.google.dev/gemini-api/docs/video-understanding,
  live-checked today) that can take a plain YouTube URL directly as
  input alongside a text prompt — no transcript-scraping step needed at
  all, Gemini reads the video itself. Real constraints found in the docs:
  public videos only (fine, the WhiteHouse channel is public), free-tier
  cap of 8 hours of YouTube video processed per day, and the feature is
  explicitly labeled "in preview... pricing and rate limits are likely to
  change." Discovery (which new videos exist) would still need the
  channel's own public RSS feed
  (`https://www.youtube.com/feeds/videos.xml?channel_id=...`) — that part
  doesn't need Gemini at all. Not built — this needs a real decision from
  the user given the "preview, may start costing money" caveat, not an
  autonomous build. Flagged, not implemented.
- **Dept of War (war.gov)**: removed from active dispatch 2026-09-02 after
  thorough investigation. Every article page (and the homepage) returns a
  flat 403 for any non-browser client — confirmed identical against plain
  httpx/curl, a real headless-Playwright browser (no JS challenge shown, so
  it's an infrastructure/IP-level block rather than a fingerprinting one
  that a smarter client could solve), the old `defense.gov` domain, and
  several spoofed user-agents (including Googlebot/Bingbot) — and
  reproduced independently from two separate networks, so it isn't
  self-inflicted by this project's own request volume; it's also been
  consistent since at least 2026-08-04, before the RSS-backend workaround
  was even built. robots.txt permitting the path doesn't matter here —
  robots.txt is an honor-system opt-out for cooperative crawlers, unrelated
  to the enforcing bot-management layer (Akamai) actually returning the
  403. No reliable substitute was found either: DVIDS carries related but
  not the same content, the RSS feed's own descriptions are too short to
  stand in for full article text, Wayback Machine's per-article coverage is
  incomplete, archive.today has no meaningful coverage of this site, and
  the department's own X accounts (@DOWResponse, @SecWar) aren't a
  systematic feed of these specific releases. The scraping code
  (`scrape_wardept`, RSS-based discovery + stop-after-first-403 handling)
  is left in `code/scraper.py`, just disconnected from `SOURCES`/`main()`,
  in case the block is ever lifted.

## Candidates found via backtesting, not yet implemented

Backtesting `backtest.py` against older past-tracker weeks (not in the
original links doc, but appearing in real past-tracker entries) surfaced:

| Source | URL | Notes |
|---|---|---|
| Xinhua (news.cn) | http://www.news.cn/ | PRC state media wire service; appeared in a Dec 2025 ground-truth entry. Worth a `scrape_xinhua` module if it recurs — not yet assessed for scrape feasibility. |
| Chinese Embassy in the US (own site) | https://us.china-embassy.gov.cn/ | Distinct from its X account (already correctly out of scope) — this is the embassy's own website, static HTML in principle. Not yet assessed. |

Both are one-off sightings so far (one ground-truth week each) — worth
re-checking after a few more backtest weeks before committing to
building either. (A third candidate that was here, MOFCOM's `/xwfbzt/`
special-topic pages, has since been resolved — see `mofcom_lxxwfbh` in
the PRC Government table above.)

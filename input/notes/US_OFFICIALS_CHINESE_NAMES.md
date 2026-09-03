# US officials — Chinese name reference

Why this exists: `translate_to_english()` has no way to know that a
Chinese official's name for a US person (assigned by Xinhua/FMPRC/state
media, not always phonetically predictable) maps to a specific English
spelling — it just translates what it sees. For most names this works
fine, but a name with unusual or non-obvious phonetics can come out
wrong: a real live run on 2026-09-03 rendered 庞德伟 (Ambassador David
Perdue's actual Chinese name) as "David Pond," a plausible-looking guess
that's simply incorrect. `KNOWN_NAME_ROMANIZATIONS` in `code/scraper.py`
is a glossary hint fed into every translation prompt specifically to
prevent this — this file is the maintained, sourced reference for that
dict. **Update both together** — this table is the paper trail for where
each spelling came from; the dict in `scraper.py` is what the code
actually uses.

Every name below was verified against a real Chinese-government or
mainland-media source (not guessed from English-to-Chinese phonetics —
that's exactly the failure mode this file exists to prevent). Add a row
here (and the matching line to `KNOWN_NAME_ROMANIZATIONS`) whenever a new
official starts appearing regularly, or whenever a translation gets a
name wrong the way Perdue's did.

## Current administration

| Full name | Role | Chinese name | Verified against |
|---|---|---|---|
| Donald Trump | President | 特朗普 | Universal across FMPRC/Xinhua; in `CHINESE_RELEVANCE_KEYWORDS` already |
| JD Vance | Vice President | 万斯 | Universal across FMPRC/Xinhua |
| Marco Rubio | Secretary of State | 鲁比奥 | Universal across FMPRC/Xinhua |
| Scott Bessent | Treasury Secretary | 贝森特 | Universal across FMPRC/MOFCOM |
| Howard Lutnick | Commerce Secretary | 卢特尼克 | Universal across FMPRC/MOFCOM |
| Peter Navarro | Senior Counselor for Trade | 纳瓦罗 | Universal across FMPRC |
| Jamieson Greer | US Trade Representative | 格里尔 | Multiple real MOFCOM articles, e.g. [mofcom.gov.cn](https://www.mofcom.gov.cn/xwfb/bldhd/art/2026/art_18048c71ff4445b6adfbe9e45f824220.html) ("王文涛部长会见美国贸易代表格里尔") |
| David Perdue | Ambassador to China | 庞德伟 | Real FMPRC article, [mfa.gov.cn](https://www.mfa.gov.cn/web/wjdt_674879/wjbxw_674885/202608/t20260827_12011229.shtml) ("外交部长王毅...会见美国驻华大使庞德伟") — the specific case that surfaced this whole gap |
| Pete Hegseth | Secretary of War (Defense) | 赫格塞斯 | Real MFA press-conference transcript, [mfa.gov.cn](https://www.mfa.gov.cn/fyrbt_673021/202501/t20250116_11536633.shtml) ("美国候任国防部长赫格塞斯") — NOT 海格塞斯, a plausible-looking wrong guess this project made and then corrected before shipping it |
| Tulsi Gabbard | Director of National Intelligence | 加巴德 | Real mfa.gov.cn reference (from her time in Congress; same surname transliteration carries over) |
| John Ratcliffe | CIA Director | 拉特克利夫 | mfa.gov.cn — referenced as "约翰·拉特克利夫" |
| Karoline Leavitt | Press Secretary | 莱维特 (full: 卡罗琳·莱维特) | Widely used across mainland Chinese media (Sina, CLS, Guancha) reporting on her briefings. **Note**: multiple reports as of Aug 2026 say she is stepping down from this role around end of August — worth a quick check if a `@PressSec`-labeled entry seems to name someone else |
| Stephen Miller | Deputy Chief of Staff for Policy | 米勒 (full: 斯蒂芬·米勒) | Mainland Chinese media (Sina, ifeng) — note Taiwan/HK sources sometimes render the given name as 史蒂芬 instead of 斯蒂芬; 斯蒂芬 is the mainland/Xinhua-style convention this project should match |

## Not added — flagged, not verified

| Full name | Role | Why not added |
|---|---|---|
| Steven Cheung | White House Communications Director | He has an actual, documented Chinese-heritage family name (张振熙 per public bio sources) rather than a media-assigned phonetic transliteration — unclear which one (if either) PRC state media would actually use if it ever named him directly. He's also a comparatively minor, rarely-directly-quoted official in this tracker's actual source material so far. Left out rather than guess; add a verified row here first if he starts showing up misnamed. |

## Carried over from the prior (Biden) administration

Still relevant because `backtest.py` runs against older past-tracker
weeks that predate this administration.

| Full name | Role (at the time) | Chinese name | Verified against |
|---|---|---|---|
| Joe Biden | President | 拜登 | Universal across FMPRC/Xinhua; already in `CHINESE_RELEVANCE_KEYWORDS` |
| Antony Blinken | Secretary of State | 布林肯 | Universal across FMPRC/Xinhua; already in `CHINESE_RELEVANCE_KEYWORDS` |
| Jake Sullivan | National Security Advisor | 沙利文 | Real mfa.gov.cn article, ("美国总统国家安全事务助理沙利文将访华") |
| Janet Yellen | Treasury Secretary | 耶伦 | Universal across FMPRC/Xinhua |

## How to extend this

1. When a name looks wrong in a generated tracker entry (a title/summary
   naming someone in a way that doesn't match how they're normally
   referred to in English), check the ORIGINAL Chinese source article for
   that entry and note the exact Chinese characters used for that person.
2. Search for that exact Chinese name alongside their real English name
   or title on a real Chinese-government domain (`site:mfa.gov.cn`,
   `site:mofcom.gov.cn`, `site:xinhuanet.com`) to confirm it's the
   REAL, actually-used name — not a one-off typo or an unrelated person
   who happens to share characters.
3. Add a row here with the source, and the matching line to
   `KNOWN_NAME_ROMANIZATIONS` in `code/scraper.py`.

Do not add a name here from phonetic guessing alone — that's the exact
failure mode this file exists to catch. If a name can't be verified
against a real source, leave it out and flag it in the "not verified"
table above instead, the way Steven Cheung's is.

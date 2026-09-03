#!/usr/bin/env python3
from __future__ import annotations
"""
Backtest the scraper's per-item pipeline against known ground truth.

For a date range already covered by a past tracker, this:
  1. Extracts every entry in that range (date, summary, source URL, and
     whether the past tracker rendered it as Q&A-style or release-style —
     inferred from actual italic-run usage in the docx, not guessed).
  2. Re-fetches each URL LIVE and runs it through the exact same
     process_*_item() function scraper.py's live scrapers call — not a
     re-implementation, the literal same code path.
  3. Reports, per entry: did we produce anything at all, did we agree on
     Q&A-vs-release, and a content_type_from_* explanation if not.

This does NOT touch output/tracker.db or output/tracker_output.docx — it
uses a throwaway in-memory sqlite connection and only reads
scraper.PENDING_ENTRIES after each call (never flushes it to a real doc).

Usage (run from the project root, not from inside code/):
    python code/backtest.py --tracker "input/past_trackers/U.S.-China Relations Tracker 06.23.26 - Present.docx" \\
                             --start 2026-07-28 --end 2026-08-03
    python code/backtest.py --tracker "input/past_trackers/Trump II Administration U.S.-China Tracker Part 2.docx" \\
                             --start 2026-03-01 --end 2026-03-07 --out backtest_part2_week.json
"""

import argparse
import json
import re
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

from docx import Document

import scraper as S

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
R_ID_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(\d{1,2}), (\d{4})$"
)


# ── Ground-truth extraction ──────────────────────────────────────────────────

def extract_ground_truth(tracker_path: str, start: datetime, end: datetime) -> list[dict]:
    """Every entry in [start, end] from a past-tracker docx: date, summary,
    source URL + anchor text, body paragraphs, and whether the entry was
    rendered Q&A-style (has an italic run anywhere in its body — only
    add_qa_entry's "Q" lines ever use italic) or release-style."""
    doc = Document(tracker_path)
    rels = doc.part.rels
    entries: list[dict] = []
    current_date: datetime | None = None
    current: dict | None = None

    def close_current():
        if current is not None:
            entries.append(current)

    for p in doc.paragraphs:
        text = p.text.strip()
        m = DATE_RE.match(text)
        if m:
            try:
                current_date = datetime.strptime(text, "%A, %B %d, %Y")
            except ValueError:
                current_date = None
            continue

        if current_date is None or not (start <= current_date <= end):
            continue

        links = p._p.findall(".//w:hyperlink", NS)
        indent = p.paragraph_format.left_indent
        is_summary_line = bool(links) and (indent is None or indent == 0)

        if is_summary_line:
            close_current()
            r_id = links[0].get(R_ID_ATTR)
            url = rels[r_id].target_ref if r_id in rels else None
            anchor_text = "".join(
                t.text or "" for hl in links for t in hl.findall(".//w:t", NS)
            )
            current = {
                "date": current_date, "summary": text, "url": url,
                "anchor": anchor_text, "body": [], "has_qa_label": False,
            }
        elif current is not None and indent:
            current["body"].append(text)
            for run in p.runs:
                # bold+ITALIC TOGETHER on the same run is add_qa_entry's
                # exact "Q" speaker-label signature (see add_qa_entry_body).
                # Plain italic alone is NOT a reliable signal — e.g. a
                # publication name ("the U.S. journal *Science*") gets
                # italicized as ordinary prose styling and would produce a
                # false positive if italic alone were the check. Found this
                # exact false positive testing against a real MOFCOM
                # document-release entry — see NOTES.md, 2026-08-04.
                if run.bold and run.italic:
                    current["has_qa_label"] = True

    close_current()
    # Only entries with a real http(s) URL are backtestable — X/TruthSocial
    # links and internal doc references (if any) are out of scope.
    return [e for e in entries if e["url"] and e["url"].startswith("http")]


def ground_truth_kind(entry: dict) -> str:
    return "qa" if entry["has_qa_label"] else "release"


# ── URL → live pipeline dispatch ─────────────────────────────────────────────

def dispatch(entry: dict, model, conn) -> dict:
    """Run the URL through the same process_*_item() the live scraper would
    use, based on domain. Returns a result dict; never raises."""
    url = entry["url"]
    host = urlparse(url).netloc
    title = entry["summary"][:80]
    date = entry["date"]

    result = {"url": url, "date": date.isoformat(), "matched_source": None,
              "queued": False, "kind": None, "error": None}

    try:
        if "fmprc.gov.cn" in host:
            client = S.make_client()
            result["matched_source"] = "fmprc"
            result["queued"] = S.process_fmprc_item(url, title, "backtest", model, conn, client)
        elif "mfa.gov.cn" in host:
            client = S.make_client()
            result["matched_source"] = "mfa_leadership"
            result["queued"] = S.process_mfa_leadership_item(url, title, "backtest", model, conn, client)
        elif "mofcom.gov.cn" in host:
            client = S.make_client(verify_ssl=False)
            result["matched_source"] = "mofcom"
            result["queued"] = S.process_mofcom_item(url, title, model, conn, client)
        elif "mod.gov.cn" in host:
            client = S.make_client(verify_ssl=False)
            result["matched_source"] = "mnd"
            result["queued"] = S.process_mnd_item(url, title, model, conn, client)
        elif "scio.gov.cn" in host:
            client = S.make_client()
            result["matched_source"] = "scio"
            result["queued"] = S.process_scio_item(url, title, model, conn, client)
        elif "state.gov" in host:
            client = S.make_client()
            result["matched_source"] = "state"
            result["queued"] = S.process_state_item_by_url(url, title, date, model, conn, client)
        elif "whitehouse.gov" in host:
            client = S.make_client()
            result["matched_source"] = "whitehouse"
            result["queued"] = S.process_whitehouse_item_by_url(url, title, date, model, conn, client)
        elif "home.treasury.gov" in host:
            client = S.make_client()
            result["matched_source"] = "treasury"
            result["queued"] = S.process_treasury_item(url, title, model, conn, client)
        elif "ustr.gov" in host:
            client = S.make_client()
            result["matched_source"] = "ustr"
            result["queued"] = S.process_ustr_item(url, title, model, conn, client)
        elif "war.gov" in host or "defense.gov" in host:
            client = S.make_client()
            result["matched_source"] = "wardept"
            result["queued"] = S.process_wardept_item(url, title, model, conn, client)
        else:
            result["matched_source"] = None  # x.com, truthsocial.com, media.defense.gov (PDFs/images), etc.
    except Exception as exc:
        result["error"] = str(exc)

    if result["queued"] and S.PENDING_ENTRIES:
        result["kind"] = S.PENDING_ENTRIES[-1]["kind"]

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracker", required=True, help="Path to a past-tracker .docx")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default=None, help="Write detailed JSON results here")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of entries tested (for a quick pass)")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end   = datetime.strptime(args.end, "%Y-%m-%d")

    ground_truth = extract_ground_truth(args.tracker, start, end)
    S.log.info(f"Ground truth: {len(ground_truth)} entries with a real source URL in [{args.start}, {args.end}]")

    if args.limit:
        ground_truth = ground_truth[: args.limit]

    model = S.init_llm()
    conn  = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY, date_seen TEXT)")
    conn.commit()

    results = []
    counts = {"total": 0, "no_domain_match": 0, "fetch_or_process_error": 0,
              "queued": 0, "not_queued": 0, "kind_match": 0, "kind_mismatch": 0}

    for entry in ground_truth:
        counts["total"] += 1
        S.PENDING_ENTRIES.clear()
        r = dispatch(entry, model, conn)
        r["ground_truth_kind"] = ground_truth_kind(entry)
        r["ground_truth_summary"] = entry["summary"]

        if r["matched_source"] is None:
            counts["no_domain_match"] += 1
        elif r["error"]:
            counts["fetch_or_process_error"] += 1
        elif r["queued"]:
            counts["queued"] += 1
            if r["kind"] == r["ground_truth_kind"]:
                counts["kind_match"] += 1
            else:
                counts["kind_mismatch"] += 1
        else:
            counts["not_queued"] += 1

        results.append(r)
        S.log.info(
            f"[{r['matched_source'] or 'SKIP'}] queued={r['queued']} "
            f"kind={r['kind']}/{r['ground_truth_kind']} url={entry['url'][:90]}"
        )

    S.PENDING_ENTRIES.clear()

    print("\n" + "=" * 70)
    print(f"BACKTEST: {args.tracker}  [{args.start} .. {args.end}]")
    print("=" * 70)
    for k, v in counts.items():
        print(f"  {k:24} {v}")
    print("=" * 70)

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"tracker": args.tracker, "start": args.start, "end": args.end,
                       "counts": counts, "results": results}, f, indent=2, default=str)
        print(f"Detailed results written to {args.out}")


if __name__ == "__main__":
    main()

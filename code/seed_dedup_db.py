#!/usr/bin/env python3
from __future__ import annotations
"""
Seed output/tracker.db's seen_urls table from every source URL already
embedded as an inline hyperlink in the past trackers (and, if present, the
in-progress output/tracker_output.docx).

Why: output/tracker.db starts empty, so a first live run of scraper.py
would treat every item currently sitting on each source's list page as
"new" — even items already written up in input/past_trackers/*.docx
— and duplicate them. Each past-tracker entry already carries its source
URL as the hyperlink target on the summary line, so we can read those
back out and pre-mark them seen without re-scraping or re-summarizing
anything.

Usage (run from the project root, not from inside code/):
    python code/seed_dedup_db.py                  # seed from input/past_trackers/*.docx
    python code/seed_dedup_db.py --dry-run         # show counts, don't write
    python code/seed_dedup_db.py --also output/tracker_output.docx
"""

import argparse
import glob
import logging

from docx import Document

from scraper import DB_PATH, init_db, is_seen, mark_seen

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
R_ID_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def extract_hyperlink_urls(path: str) -> set[str]:
    """Every unique external hyperlink target embedded in the doc's paragraphs."""
    doc = Document(path)
    rels = doc.part.rels
    urls: set[str] = set()
    for para in doc.paragraphs:
        for hyperlink in para._p.findall(".//w:hyperlink", NS):
            r_id = hyperlink.get(R_ID_ATTR)
            if r_id and r_id in rels:
                target = rels[r_id].target_ref
                if target.startswith("http"):
                    urls.add(target)
    return urls


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "docs", nargs="*",
        default=sorted(glob.glob("input/past_trackers/*.docx")),
        help="Doc(s) to seed from (default: everything in input/past_trackers/)",
    )
    parser.add_argument("--also", action="append", default=[], help="Extra doc path(s) to include, e.g. output/tracker_output.docx")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing to output/tracker.db")
    args = parser.parse_args()

    doc_paths = list(args.docs) + list(args.also)
    if not doc_paths:
        log.error("No docs found to seed from.")
        return

    conn = init_db()
    total_found = 0
    total_new = 0

    for path in doc_paths:
        try:
            urls = extract_hyperlink_urls(path)
        except Exception as exc:
            log.error(f"Failed to read {path}: {exc}")
            continue

        already = sum(1 for u in urls if is_seen(conn, u))
        new = len(urls) - already
        total_found += len(urls)
        total_new += new
        log.info(f"{path}: {len(urls)} hyperlinked URLs ({new} not yet in {DB_PATH})")

        if not args.dry_run:
            for u in urls:
                mark_seen(conn, u)

    verb = "would mark" if args.dry_run else "marked"
    log.info(f"Done. {verb} {total_new} new / {total_found} total URLs as seen across {len(doc_paths)} doc(s).")


if __name__ == "__main__":
    main()

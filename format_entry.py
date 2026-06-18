#!/usr/bin/env python3
from __future__ import annotations
"""
Manual entry formatter for the US-China tracker Word doc.

Paste or pipe a Q&A transcript or press release and get a properly
formatted entry appended to tracker_output.docx — matching the
exact style of the existing tracker docs.

Usage:
    python format_entry.py                       # paste via stdin
    python format_entry.py transcript.txt        # read from file
    python format_entry.py clip.txt --out out.docx
    python format_entry.py clip.txt --type qa    # override detection
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from scraper import (
    DOC_PATH,
    add_qa_entry,
    add_release_entry,
    get_or_create_doc,
    init_llm,
)

# Gemini free tier: 15 RPM. A manual run makes 2-3 calls, so 2s between
# calls keeps us safely under the rolling-window limit.
_GEMINI_SLEEP = 2.0
_GEMINI_MODEL = "gemini-2.5-flash"


def _call_gemini(client, prompt: str, retries: int = 2) -> str:
    time.sleep(_GEMINI_SLEEP)
    for attempt in range(retries + 1):
        try:
            resp = client.models.generate_content(model=_GEMINI_MODEL, contents=prompt)
            return resp.text.strip()
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "quota" in err or "resource_exhausted" in err:
                wait = 20 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s…")
                time.sleep(wait)
            elif attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise


# ── Text preprocessing ────────────────────────────────────────────────────────

def preprocess_text(text: str) -> list[str]:
    """
    Split raw pasted text into individual speaker-turn paragraphs.
    Handles both normal newline-separated transcripts and single-block
    pastes where multiple 'Speaker: text' entries run together inline.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    if len(lines) >= 3:
        return lines

    # 1-2 lines: likely a single pasted block — split on sentence-end + new Speaker:
    combined = ' '.join(lines)
    parts = re.split(
        r'(?<=[.?!])\s+(?=[A-Z][A-Za-z0-9 \-\'\.]{1,40}:\s)',
        combined,
    )
    if len(parts) >= 2:
        return [p.strip() for p in parts if p.strip()]

    return [combined.strip()] if combined.strip() else []


_SPEAKER_RE = re.compile(r'^[A-Z][A-Za-z0-9 \-\'\.]{1,40}:\s+')


def detect_content_type(paragraphs: list[str]) -> str:
    """'qa' if 2+ paragraphs begin with a Speaker: prefix, else 'release'."""
    hits = sum(1 for p in paragraphs if _SPEAKER_RE.match(p))
    return "qa" if hits >= 2 else "release"


def detect_language(text: str) -> str:
    cjk = sum(1 for c in text if '一' <= c <= '鿿')
    return "chinese" if cjk > 50 else "english"


def extract_date(text: str) -> datetime | None:
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y-%m-%d')
        except ValueError:
            pass
    m = re.search(
        r'\b(January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b',
        text,
    )
    if m:
        try:
            return datetime.strptime(m.group(0), '%B %d, %Y')
        except ValueError:
            pass
    return None


# ── LLM helpers ───────────────────────────────────────────────────────────────

def translate_to_english(client, text: str) -> str:
    return _call_gemini(
        client,
        "Translate the following Chinese text to English.\n"
        "Preserve speaker labels, paragraph breaks, and official titles exactly.\n\n"
        f"Text:\n{text}",
    )


def generate_summary(client, text: str) -> str:
    """One-sentence tracker-style summary."""
    return _call_gemini(
        client,
        "You are writing for the Brookings Institution US-China Relations Tracker.\n\n"
        "Write exactly ONE sentence summarizing the following content.\n\n"
        "Style rules:\n"
        "- Start with the official's title and name, or the institution name\n"
        "- Use active verb phrases: 'addressed reporters' questions on', "
        "'released a statement on', 'held a press briefing on', "
        "'answered questions about', 'issued a readout on'\n"
        "- Name the specific topic (tariffs, Taiwan, semiconductors, trade talks, etc.)\n"
        "- Do NOT start with 'The' — start directly with the name or title\n"
        "- Output ONE sentence only\n\n"
        "Examples of the exact style:\n"
        "  Foreign Ministry Spokesperson Lin Jian addressed reporters' questions on "
        "US tariff increases and China's position on trade negotiations.\n"
        "  State Department Spokesperson Matthew Miller held a press briefing covering "
        "US policy on Taiwan and export controls on advanced semiconductors.\n"
        "  USTR released a statement on the outcome of the Section 301 tariff review "
        "for Chinese technology products.\n\n"
        f"Content:\n{text[:6000]}",
    )


def classify_qa_with_llm(client, paragraphs: list[str]) -> list[dict]:
    """
    Ask Gemini to classify each paragraph as Q, A, or CONT and extract the speaker.

    Q    — question from a media outlet, journalist, or reporter
    A    — response/statement from a government official, spokesperson, minister,
           ambassador, press secretary, or department
    CONT — continuation of the previous A; same speaker, no new label

    A can follow A (multi-paragraph answers are common).
    Documents with no Q at all (press releases, white papers) are valid — everything A/CONT.
    """
    if not paragraphs:
        return []

    numbered = "\n".join(f"[{i + 1}] {p}" for i, p in enumerate(paragraphs))

    result = _call_gemini(
        client,
        "You are parsing a government press conference or official document for the "
        "Brookings Institution US-China Relations Tracker.\n\n"
        "Classify each numbered paragraph as exactly one of:\n"
        '  "Q"    — question from a media outlet, journalist, or reporter\n'
        '  "A"    — response or statement from a government official, spokesperson,\n'
        "           minister, ambassador, press secretary, or department\n"
        '  "CONT" — continuation of the previous A paragraph: no new speaker label,\n'
        "           the same official is still speaking\n\n"
        "Classification guide:\n"
        "  A:    State Department, Treasury, USTR, White House, MFA, MOFCOM, "
        "Lin Jian, Mao Ning, Wang Yi, any US Secretary/Ambassador/Spokesperson, "
        "any government official or ministry\n"
        "  Q:    Reuters, AFP, CNN, Bloomberg, AP, BBC, any reporter or media outlet\n"
        "  CONT: paragraph has NO speaker label (no 'Name: ' prefix) — continuing "
        "the previous official's answer\n\n"
        "Additional rules:\n"
        "- A can follow A (an official may give multiple consecutive paragraphs)\n"
        "- If NO questions exist at all (white paper, statement, readout), classify "
        "everything as A or CONT — that is correct\n"
        "- The 'speaker' field is the name/outlet before the colon, or null for CONT\n\n"
        "Return ONLY a valid JSON array — one object per paragraph, in order:\n"
        '[{"type":"Q","speaker":"Reuters"},{"type":"A","speaker":"Lin Jian"},'
        '{"type":"CONT","speaker":null},...]\n\n'
        f"Paragraphs:\n{numbered}",
    )

    # Strip markdown code fences if Gemini wraps in ```json ... ```
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip(), flags=re.MULTILINE)

    try:
        labels = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'\[.*\]', cleaned, re.DOTALL)
        try:
            labels = json.loads(m.group(0)) if m else []
        except Exception:
            labels = []

    exchanges = []
    for i, para in enumerate(paragraphs):
        label = labels[i] if i < len(labels) else {"type": "A", "speaker": None}
        ex_type = str(label.get("type", "A")).upper()
        if ex_type not in ("Q", "A", "CONT"):
            ex_type = "A"
        speaker = (label.get("speaker") or "").strip()

        # Strip the speaker prefix from the paragraph text
        if speaker:
            m2 = re.match(re.escape(speaker) + r'\s*:\s*', para, re.IGNORECASE)
            text = para[m2.end():].strip() if m2 else para.strip()
            if text == para.strip():
                # Speaker name didn't match literally — strip any generic prefix
                m2 = _SPEAKER_RE.match(para)
                text = para[m2.end():].strip() if m2 else para.strip()
        else:
            # CONT — but if the paragraph actually has a label, trust the label
            m2 = _SPEAKER_RE.match(para)
            if m2 and ex_type == "CONT":
                speaker = m2.group(0).rstrip(': ').strip()
                text = para[m2.end():].strip()
                ex_type = "A"
            else:
                text = para.strip()

        if not text:
            continue

        exchanges.append({"type": ex_type, "speaker": speaker, "text": text})

    return exchanges


def extract_body_paragraphs(client, text: str, n: int = 5) -> list[str]:
    """For press releases / white papers: pick the n most relevant verbatim paragraphs."""
    result = _call_gemini(
        client,
        f"You are selecting content for the Brookings Institution US-China Relations Tracker.\n\n"
        f"From the text below, extract the {n} most informative verbatim paragraphs "
        "relevant to US-China relations (trade, tariffs, technology, Taiwan, diplomacy).\n\n"
        "Rules:\n"
        "- Copy paragraphs verbatim — no paraphrasing or summarizing\n"
        "- Prefer paragraphs with specific policy details, numbers, or direct quotes\n"
        "- Preserve any speaker labels ('Name: text') exactly as written\n"
        f"- Separate each selected paragraph with the literal separator: |||\n"
        "- Output ONLY the paragraphs separated by |||, nothing else\n\n"
        f"Text:\n{text[:8000]}",
    )
    parts = [p.strip() for p in result.split("|||") if p.strip()]
    return parts[:n] if parts else [text[:500]]


# ── UI helpers ────────────────────────────────────────────────────────────────

def read_input(filepath: str | None) -> str:
    if filepath:
        return Path(filepath).read_text(encoding='utf-8')
    print('Paste text, then Ctrl+D:')
    return sys.stdin.read()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Format a text entry into a tracker-style Word doc'
    )
    parser.add_argument('file', nargs='?', help='Text file (default: stdin)')
    parser.add_argument(
        '--out', default=DOC_PATH,
        help=f'Output .docx path (default: {DOC_PATH})',
    )
    parser.add_argument(
        '--type', choices=['qa', 'release'],
        help='Override content-type detection',
    )
    args = parser.parse_args()

    raw_text = read_input(args.file)
    if not raw_text.strip():
        print('No text received — exiting.')
        sys.exit(1)

    # ── Init Gemini ──────────────────────────────────────────────────────────
    try:
        client = init_llm()
    except RuntimeError as exc:
        print(f'\nError: {exc}')
        print('Add GEMINI_API_KEY=your_key_here to your .env file.')
        sys.exit(1)

    # ── Translate if Chinese ─────────────────────────────────────────────────
    lang = detect_language(raw_text)
    working_text = raw_text
    if lang == 'chinese':
        print('Translating…')
        working_text = translate_to_english(client, raw_text[:10_000])

    # ── Preprocess and detect ────────────────────────────────────────────────
    paragraphs = preprocess_text(working_text)
    content_type = args.type or detect_content_type(paragraphs)
    date = extract_date(working_text) or datetime.now()

    print(f'type: {content_type}  |  date: {date.strftime("%Y-%m-%d")}  |  paragraphs: {len(paragraphs)}')

    # ── Generate summary ─────────────────────────────────────────────────────
    print('Generating summary…')
    summary = generate_summary(client, working_text)
    print(f'\n  {summary}\n')

    # ── Build entry ──────────────────────────────────────────────────────────
    doc = get_or_create_doc(args.out)

    if content_type == 'qa':
        print('\nClassifying Q&A exchanges…')
        exchanges = classify_qa_with_llm(client, paragraphs)
        if not exchanges:
            print('No exchanges found — check input text formatting.')
            sys.exit(1)
        q_count = sum(1 for e in exchanges if e['type'] == 'Q')
        a_count = sum(1 for e in exchanges if e['type'] == 'A')
        print(f'  {len(exchanges)} total  ({q_count} Q  {a_count} A)')
        add_qa_entry(doc, date, summary, exchanges)
    else:
        print('\nExtracting key paragraphs…')
        paras = extract_body_paragraphs(client, working_text, n=5)
        print(f'  {len(paras)} paragraphs extracted.')
        add_release_entry(doc, date, summary, paras)

    doc.save(args.out)
    print(f'\n✓  Written to: {args.out}')


if __name__ == '__main__':
    main()

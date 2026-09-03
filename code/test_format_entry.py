#!/usr/bin/env python3
from __future__ import annotations
"""
Offline regression tests for format_entry.py's pure logic — no API keys
or network needed, runs in under a second. Same philosophy as
test_scraper.py: this deliberately does NOT test classify_qa_with_llm's
actual LLM judgment (that needs a live key and is non-deterministic) —
only the pure functions around it.

Usage (run from the project root, not from inside code/):
    python3 code/test_format_entry.py
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import format_entry as F


class TestPreprocessText(unittest.TestCase):
    """Splits raw pasted text into speaker-turn paragraphs — handles both
    normal newline-separated transcripts and a single pasted block with
    multiple 'Speaker: text' entries running together inline."""

    def test_newline_separated_paragraphs_pass_through(self):
        text = "Reuters: What is your comment?\n\nLin Jian: We oppose this."
        self.assertEqual(
            F.preprocess_text(text),
            ["Reuters: What is your comment?", "Lin Jian: We oppose this."],
        )

    def test_single_block_splits_on_sentence_end_before_new_speaker(self):
        text = "Reuters: What is your comment? Lin Jian: We oppose this."
        result = F.preprocess_text(text)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].startswith("Reuters:"))
        self.assertTrue(result[1].startswith("Lin Jian:"))

    def test_single_unlabeled_line_stays_one_paragraph(self):
        self.assertEqual(F.preprocess_text("Just one plain line."), ["Just one plain line."])


class TestDetectContentType(unittest.TestCase):
    def test_two_or_more_labeled_paragraphs_is_qa(self):
        paragraphs = ["Reuters: Question one?", "Lin Jian: Answer one."]
        self.assertEqual(F.detect_content_type(paragraphs), "qa")

    def test_fewer_than_two_labels_is_release(self):
        paragraphs = ["Lin Jian: A statement with no question at all."]
        self.assertEqual(F.detect_content_type(paragraphs), "release")

    def test_unlabeled_paragraphs_are_release(self):
        paragraphs = ["Just prose with no speaker label.", "More prose."]
        self.assertEqual(F.detect_content_type(paragraphs), "release")


class TestDetectLanguage(unittest.TestCase):
    def test_english_text(self):
        self.assertEqual(F.detect_language("This is plain English text."), "english")

    def test_chinese_text(self):
        # Needs more than 50 CJK characters to clear detect_language's own
        # threshold (see test_short_chinese_phrase_inside_english_stays_
        # english below for why that threshold exists) — a realistic
        # full transcript opener, not just one short sentence.
        text = "外交部发言人林剑主持例行记者会，介绍近期中美关系最新进展，并回答记者提出的有关贸易、台湾问题以及双边合作等多项问题，重申中方一贯立场。"
        self.assertEqual(F.detect_language(text), "chinese")

    def test_short_chinese_phrase_inside_english_stays_english(self):
        # A handful of CJK characters (e.g. a quoted term) shouldn't tip
        # the whole document into "chinese" — the 50-char threshold exists
        # for exactly this.
        self.assertEqual(F.detect_language("The term 一带一路 refers to the Belt and Road Initiative."), "english")


class TestExtractDate(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(F.extract_date("Published 2026-06-18 in Beijing."), datetime(2026, 6, 18))

    def test_long_form_date(self):
        self.assertEqual(F.extract_date("June 18, 2026\n\nSome content."), datetime(2026, 6, 18))

    def test_no_date_returns_none(self):
        self.assertIsNone(F.extract_date("No date anywhere in this text."))


class TestIsPureDateLine(unittest.TestCase):
    """Real bug, live 2026-09-03: a masthead-style leading date line
    ("June 18, 2026") with no real speaker was left in `paragraphs` and
    sent to classify_qa_with_llm() like any other line, producing a
    stray, contentless paragraph in the finished tracker entry once the
    misalignment bug above it was fixed. Its date is already pulled out
    separately by extract_date() for the entry's own heading, so the
    line itself is redundant once that's done."""

    def test_bare_long_form_date_is_pure(self):
        self.assertTrue(F._is_pure_date_line("June 18, 2026"))

    def test_bare_iso_date_is_pure(self):
        self.assertTrue(F._is_pure_date_line("2026-06-18"))

    def test_date_within_a_real_sentence_is_not_pure(self):
        # Must not strip a real content paragraph just because it
        # contains a date — only a paragraph that IS just the date.
        self.assertFalse(F._is_pure_date_line(
            "On June 18, 2026, the ministry issued a statement."
        ))

    def test_speaker_labeled_paragraph_is_not_pure(self):
        self.assertFalse(F._is_pure_date_line("Lin Jian: We firmly oppose this."))


class TestClassifyQaWithLlmParagraphMatching(unittest.TestCase):
    """The paragraph-NUMBER-keyed matching classify_qa_with_llm() uses to
    interpret the model's response — see that function's own docstring
    for the real bug (a silently dropped paragraph shifted every later
    label by one position, swapping who said what) this replaced. Tests
    only the matching/fallback logic here with a fake response, not an
    actual LLM call."""

    def test_missing_paragraph_number_falls_back_to_cont(self):
        # Simulates the model's response omitting paragraph 1 entirely —
        # the exact real failure shape. paragraph 1 must fall back to a
        # safe CONT/no-speaker default, and paragraph 2's real label must
        # NOT shift onto paragraph 1's text.
        labels_list = [{"paragraph": 2, "type": "A", "speaker": "Lin Jian"}]
        labels_by_num = {
            entry["paragraph"]: entry
            for entry in labels_list
            if isinstance(entry.get("paragraph"), int)
        }
        self.assertEqual(labels_by_num.get(1, {"type": "CONT", "speaker": None})["type"], "CONT")
        self.assertEqual(labels_by_num.get(2)["speaker"], "Lin Jian")


if __name__ == "__main__":
    unittest.main(verbosity=2)

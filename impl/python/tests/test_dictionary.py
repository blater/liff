from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from liff import (
    AUTHOR,
    TITLE,
    DEFAULT_DICTIONARY,
    Dictionary,
    Found,
    MatchKind,
    Random,
)


ROOT_DIR = Path(__file__).resolve().parents[3]


class GeneratedDictionaryTests(unittest.TestCase):
    def test_generated_data_exactly_matches_source(self) -> None:
        with (ROOT_DIR / "liff.json").open(encoding="utf-8") as source_file:
            source = json.load(source_file)

        self.assertEqual(source["schema_version"], 1)
        self.assertEqual(source["title"], TITLE)
        self.assertEqual(source["author"], AUTHOR)
        self.assertEqual(source["source"], "liff-corrected.txt")
        self.assertEqual(len(DEFAULT_DICTIONARY.entries), 550)

        expected_entries = list(source["entries"].items())
        self.assertEqual(len(DEFAULT_DICTIONARY.entries), len(expected_entries))
        for actual, (word, expected) in zip(
            DEFAULT_DICTIONARY.entries, expected_entries, strict=True
        ):
            with self.subTest(word=word):
                self.assertEqual(actual.word, word)
                self.assertEqual(actual.part_of_speech, expected["part_of_speech"])
                self.assertEqual(actual.definition, expected["definition"])
                self.assertEqual(
                    [
                        {
                            "target": reference.target,
                            "relation": reference.relation,
                            "label": reference.label,
                        }
                        for reference in actual.references
                    ],
                    expected["references"],
                )

    def test_every_reference_resolves_exactly(self) -> None:
        for entry in DEFAULT_DICTIONARY.entries:
            for reference in entry.references:
                outcome = DEFAULT_DICTIONARY.search(reference.target)
                self.assertIsInstance(outcome, Found)
                assert isinstance(outcome, Found)
                self.assertEqual(outcome.kind, MatchKind.EXACT)
                self.assertEqual(outcome.entry.word, reference.target)

    def test_entries_are_immutable(self) -> None:
        entry = DEFAULT_DICTIONARY.entries[0]
        with self.assertRaises(FrozenInstanceError):
            entry.word = "CHANGED"  # type: ignore[misc]

    def test_injected_random_index_and_empty_dictionary(self) -> None:
        entries = DEFAULT_DICTIONARY.entries
        self.assertEqual(DEFAULT_DICTIONARY.random_with(lambda _: 0), entries[0])
        self.assertEqual(
            DEFAULT_DICTIONARY.random_with(lambda length: length - 1), entries[-1]
        )
        self.assertIsNone(DEFAULT_DICTIONARY.random_with(lambda length: length))
        self.assertIsNone(Dictionary(()).random_with(lambda _: 0))

    def test_random_request_has_no_score(self) -> None:
        outcome = DEFAULT_DICTIONARY.resolve(Random())
        self.assertIsInstance(outcome, Found)
        assert isinstance(outcome, Found)
        self.assertEqual(outcome.kind, MatchKind.RANDOM)
        self.assertIsNone(outcome.score)
        self.assertIn(outcome.entry, DEFAULT_DICTIONARY.entries)


if __name__ == "__main__":
    unittest.main()

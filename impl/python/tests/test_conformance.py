from __future__ import annotations

import json
import unittest
from pathlib import Path

from liff import Confidence, DidYouMean, Found, MatchKind, NotFound
from liff.core import (
    DEFAULT_DICTIONARY,
    candidate_score,
    damerau_levenshtein,
    glob_matches,
    similarity_score,
)
from liff.normalize import normalize, normalize_glob


IMPL_DIR = Path(__file__).resolve().parents[2]


def load_fixture(name: str) -> dict:
    with (IMPL_DIR / name).open(encoding="utf-8") as source:
        return json.load(source)


class SearchConformanceTests(unittest.TestCase):
    def test_shared_search_cases(self) -> None:
        contract = load_fixture("search-cases.json")
        self.assertEqual(contract["schema_version"], 1)

        for case in contract["cases"]:
            with self.subTest(query=case["query"]):
                outcome = DEFAULT_DICTIONARY.search(case["query"])
                if case["outcome"] == "found":
                    self.assertIsInstance(outcome, Found)
                    assert isinstance(outcome, Found)
                    self.assertEqual(outcome.entry.word, case["word"])
                    self.assertEqual(outcome.kind.value, case["kind"])
                    if "score" in case:
                        self.assertEqual(outcome.score, case["score"])
                elif case["outcome"] == "did_you_mean":
                    self.assertIsInstance(outcome, DidYouMean)
                    assert isinstance(outcome, DidYouMean)
                    actual = [
                        {
                            "word": suggestion.entry.word,
                            "confidence": suggestion.confidence.value,
                            "score": suggestion.score,
                        }
                        for suggestion in outcome.suggestions
                    ]
                    self.assertEqual(actual, case["suggestions"])
                elif case["outcome"] == "not_found":
                    self.assertIsInstance(outcome, NotFound)
                else:
                    self.fail(f"unknown outcome {case['outcome']!r}")


class AlgorithmConformanceTests(unittest.TestCase):
    def test_shared_algorithm_cases(self) -> None:
        contract = load_fixture("algorithm-cases.json")
        self.assertEqual(contract["schema_version"], 1)

        for case in contract["normalization"]:
            with self.subTest(normalization=case["input"]):
                self.assertEqual(normalize(case["input"]), case["output"])
        for case in contract["glob_normalization"]:
            with self.subTest(glob_normalization=case["input"]):
                self.assertEqual(normalize_glob(case["input"]), case["output"])
        for case in contract["edit_scores"]:
            with self.subTest(edit_score=(case["left"], case["right"])):
                self.assertEqual(
                    damerau_levenshtein(case["left"], case["right"]),
                    case["distance"],
                )
                self.assertEqual(
                    similarity_score(case["left"], case["right"]), case["score"]
                )
        for case in contract["candidate_scores"]:
            with self.subTest(candidate_score=(case["query"], case["candidate"])):
                self.assertEqual(
                    candidate_score(case["query"], case["candidate"]), case["score"]
                )
        for case in contract["glob_matches"]:
            with self.subTest(glob=(case["pattern"], case["candidate"])):
                self.assertEqual(
                    glob_matches(case["pattern"], case["candidate"]), case["matches"]
                )
        for case in contract["ordering"]:
            with self.subTest(ordering=case["input"]):
                self.assertEqual(sorted(case["input"]), case["ascending"])


if __name__ == "__main__":
    unittest.main()

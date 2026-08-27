import unittest

from generated.liff_dictionary import ENTRIES, lookup


class GeneratedPythonDictionaryTests(unittest.TestCase):
    def test_dictionary_is_complete(self) -> None:
        self.assertEqual(len(ENTRIES), 550)

    def test_lookup_is_case_insensitive_and_trims_whitespace(self) -> None:
        self.assertEqual(lookup("  sutton AND cheam  ").word, "SUTTON and CHEAM")

    def test_reference_target_can_be_looked_up(self) -> None:
        banteer = lookup("BANTEER")
        self.assertEqual(banteer.references[0].target, "ARAGLIN")
        self.assertEqual(lookup(banteer.references[0].target).word, "ARAGLIN")


if __name__ == "__main__":
    unittest.main()

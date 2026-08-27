from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from liff import DEFAULT_DICTIONARY
from liff.cli import main, run


def invoke(*arguments: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    status = run(arguments, stdout, stderr)
    return status, stdout.getvalue(), stderr.getvalue()


class CLITests(unittest.TestCase):
    def test_process_entry_point_propagates_status(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(sys, "argv", ["liff", "xyzzy"]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main()
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(stdout.getvalue(), 'No definition found for "xyzzy".\n')
        self.assertEqual(stderr.getvalue(), "")

    def test_no_arguments_prints_random_entry(self) -> None:
        status, output, stderr = invoke()
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        word, definition = output.rstrip("\n").split("\n", 1)
        entry = next(entry for entry in DEFAULT_DICTIONARY.entries if entry.word == word)
        self.assertEqual(definition, entry.definition)

    def test_found_searches_print_entry(self) -> None:
        cases = [
            (("banteer",), "BANTEER\nA lusty and raucous old ballad"),
            (("banteeer",), "BANTEER\nA lusty and raucous old ballad"),
            (("glutt",), "GLUTT LODGE\n"),
            (("bilb",), "BILBSTER\n"),
            (("bil*",), "BILBSTER\n"),
            (("b?lbster",), "BILBSTER\n"),
            (("symonds", "yat"), "SYMOND'S YAT\n"),
        ]
        for arguments, prefix in cases:
            with self.subTest(arguments=arguments):
                status, output, stderr = invoke(*arguments)
                self.assertEqual(status, 0)
                self.assertEqual(stderr, "")
                self.assertTrue(output.startswith(prefix), output)

    def test_ambiguous_and_large_glob_output(self) -> None:
        status, output, _ = invoke("high")
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n",
        )

        status, output, _ = invoke("b*")
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            "Did you mean?\n"
            "BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n"
            "BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n"
            "and 44 others\n",
        )

        status, output, _ = invoke("*")
        self.assertEqual(status, 1)
        self.assertEqual(len(output.rstrip("\n").split("\n")), 12)
        self.assertTrue(output.endswith("and 540 others\n"))

    def test_exactly_eleven_suggestions_are_all_printed(self) -> None:
        status, output, _ = invoke("bo*")
        self.assertEqual(status, 1)
        self.assertNotIn("and ", output)
        self.assertEqual(len(output.rstrip("\n").split("\n")), 12)

    def test_not_found_help_and_invalid_usage(self) -> None:
        status, output, stderr = invoke("xyzzy")
        self.assertEqual((status, output, stderr), (1, 'No definition found for "xyzzy".\n', ""))

        status, output, stderr = invoke("--help")
        self.assertEqual(status, 0)
        self.assertTrue(output.startswith("Usage: liff"))
        self.assertEqual(stderr, "")

        status, output, stderr = invoke("--unknown")
        self.assertEqual(status, 2)
        self.assertEqual(output, "")
        self.assertTrue(stderr.startswith("Usage: liff"))


if __name__ == "__main__":
    unittest.main()

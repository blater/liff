"""Thin command-line adapter for the Liff core package."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import NoReturn, TextIO

from .core import DEFAULT_DICTIONARY, Dictionary
from .model import DidYouMean, Found, Random, Search


HELP = """Usage: liff [WORD ...]

With no word, print a random definition. With a word, search the dictionary.
Quoted patterns may use * to match any sequence and ? to match one character."""
FULL_SUGGESTION_LIMIT = 11
TRUNCATED_SUGGESTION_LIMIT = 10


def run(
    arguments: Sequence[str],
    stdout: TextIO,
    stderr: TextIO,
    dictionary: Dictionary = DEFAULT_DICTIONARY,
) -> int:
    """Run one CLI request and return its process exit status."""

    if len(arguments) == 1 and arguments[0] in ("-h", "--help"):
        print(HELP, file=stdout)
        return 0
    if any(argument.startswith("-") for argument in arguments):
        print(HELP, file=stderr)
        return 2

    query = " ".join(arguments)
    request = Random() if not arguments else Search(query)
    outcome = dictionary.resolve(request)

    if isinstance(outcome, Found):
        print(outcome.entry.word, file=stdout)
        print(outcome.entry.definition, file=stdout)
        return 0
    if isinstance(outcome, DidYouMean):
        print("Did you mean?", file=stdout)
        displayed = (
            len(outcome.suggestions)
            if len(outcome.suggestions) <= FULL_SUGGESTION_LIMIT
            else TRUNCATED_SUGGESTION_LIMIT
        )
        for suggestion in outcome.suggestions[:displayed]:
            print(suggestion.entry.word, file=stdout)
        if displayed < len(outcome.suggestions):
            print(f"and {len(outcome.suggestions) - displayed} others", file=stdout)
        return 1

    print(f'No definition found for "{query}".', file=stdout)
    return 1


def main() -> NoReturn:
    """Run from process arguments for the zipapp entry point."""

    raise SystemExit(run(sys.argv[1:], sys.stdout, sys.stderr))

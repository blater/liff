"""Pure dictionary indexing and lookup operations."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .dictionary_generated import ENTRIES
from .model import (
    Confidence,
    DidYouMean,
    Entry,
    Found,
    MatchKind,
    NotFound,
    Outcome,
    Random,
    Request,
    Search,
    Suggestion,
)
from .normalize import normalize, normalize_glob


PERFECT_SCORE = 1000
QUALIFYING_SCORE = 700
LOW_SUGGESTION_COUNT = 2
TOKEN_PREFIX_SCORE = 900
PARTIAL_PREFIX_SCORE = 750
PREFIX_MIN_CODE_POINTS = 4


@dataclass(frozen=True, slots=True)
class _IndexedEntry:
    entry: Entry
    normalized: str


@dataclass(frozen=True, slots=True)
class _ScoredCandidate:
    entry: Entry
    score: int


@dataclass(frozen=True, slots=True, init=False)
class Dictionary:
    """An indexed immutable dictionary and its lookup operations."""

    _entries: tuple[Entry, ...]
    _index: tuple[_IndexedEntry, ...]
    _exact: Mapping[str, Entry]

    def __init__(self, entries: tuple[Entry, ...]) -> None:
        owned = tuple(entries)
        index = tuple(
            sorted(
                (_IndexedEntry(entry, normalize(entry.word)) for entry in owned),
                key=lambda indexed: indexed.normalized,
            )
        )
        for left, right in zip(index, index[1:], strict=False):
            if left.normalized == right.normalized:
                raise ValueError("dictionary contains duplicate normalized headwords")
        exact = MappingProxyType(
            {indexed.normalized: indexed.entry for indexed in index}
        )
        object.__setattr__(self, "_entries", owned)
        object.__setattr__(self, "_index", index)
        object.__setattr__(self, "_exact", exact)

    @property
    def entries(self) -> tuple[Entry, ...]:
        """Return every entry in canonical source order."""

        return self._entries

    def resolve(self, request: Request) -> Outcome:
        """Resolve a random or search request."""

        if isinstance(request, Random):
            entry = self.random()
            return NotFound() if entry is None else Found(entry, MatchKind.RANDOM, None)
        if isinstance(request, Search):
            return self.search(request.query)
        raise TypeError(f"unsupported request: {type(request).__name__}")

    def random(self) -> Entry | None:
        """Return a uniformly selected entry, or ``None`` when empty."""

        return self.random_with(secrets.randbelow)

    def random_with(self, choose_index: Callable[[int], int]) -> Entry | None:
        """Select using a deterministic index chooser test seam."""

        if not self._entries:
            return None
        index = choose_index(len(self._entries))
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]

    def search(self, query: str) -> Outcome:
        """Search for an exact, glob, or confidence-qualified headword."""

        if "*" in query or "?" in query:
            return self._search_glob(query)

        normalized_query = normalize(query)
        if not normalized_query:
            return NotFound()

        exact = self._exact.get(normalized_query)
        if exact is not None:
            return Found(exact, MatchKind.EXACT, PERFECT_SCORE)

        ranked = sorted(
            (
                _ScoredCandidate(
                    indexed.entry,
                    candidate_score(normalized_query, indexed.normalized),
                )
                for indexed in self._index
            ),
            key=lambda candidate: (-candidate.score, candidate.entry.word),
        )
        qualified_count = 0
        while (
            qualified_count < len(ranked)
            and ranked[qualified_count].score >= QUALIFYING_SCORE
        ):
            qualified_count += 1

        if qualified_count == 1:
            best = ranked[0]
            return Found(best.entry, MatchKind.HIGH_CONFIDENCE, best.score)
        if qualified_count == 0:
            return NotFound()

        suggestions = [
            Suggestion(candidate.entry, Confidence.MEDIUM, candidate.score)
            for candidate in ranked[:qualified_count]
        ]
        suggestions.extend(
            Suggestion(candidate.entry, Confidence.LOW, candidate.score)
            for candidate in ranked[
                qualified_count : qualified_count + LOW_SUGGESTION_COUNT
            ]
        )
        return DidYouMean(tuple(suggestions))

    def _search_glob(self, query: str) -> Outcome:
        pattern = normalize_glob(query)
        if not pattern:
            return NotFound()

        matches = tuple(
            indexed.entry
            for indexed in self._index
            if glob_matches(pattern, indexed.normalized)
        )
        if not matches:
            return NotFound()
        if len(matches) == 1:
            return Found(matches[0], MatchKind.GLOB, PERFECT_SCORE)
        return DidYouMean(
            tuple(
                Suggestion(entry, Confidence.MEDIUM, PERFECT_SCORE)
                for entry in matches
            )
        )


def similarity_score(left: str, right: str) -> int:
    """Return the integer OSA similarity score for normalized strings."""

    maximum = max(len(left), len(right))
    if maximum == 0:
        return PERFECT_SCORE
    retained = max(0, maximum - damerau_levenshtein(left, right))
    return retained * 1000 // maximum


def candidate_score(query: str, candidate: str) -> int:
    """Return edit similarity with the normative prefix floors."""

    edit_score = similarity_score(query, candidate)
    if len(query) < PREFIX_MIN_CODE_POINTS:
        return edit_score
    if candidate.startswith(query + " "):
        return max(edit_score, TOKEN_PREFIX_SCORE)
    if candidate.startswith(query):
        return max(edit_score, PARTIAL_PREFIX_SCORE)
    return edit_score


def glob_matches(pattern: str, candidate: str) -> bool:
    """Return whether a normalized glob matches a normalized headword."""

    previous = [False] * (len(candidate) + 1)
    previous[0] = True
    for pattern_character in pattern:
        current = [False] * (len(candidate) + 1)
        if pattern_character == "*":
            current[0] = previous[0]
        for index, candidate_character in enumerate(candidate, start=1):
            if pattern_character == "*":
                current[index] = previous[index] or current[index - 1]
            elif pattern_character == "?":
                current[index] = previous[index - 1]
            else:
                current[index] = (
                    previous[index - 1]
                    and pattern_character == candidate_character
                )
        previous = current
    return previous[len(candidate)]


def damerau_levenshtein(left: str, right: str) -> int:
    """Return optimal-string-alignment Damerau-Levenshtein distance."""

    previous_previous = [0] * (len(right) + 1)
    previous = list(range(len(right) + 1))

    for left_index, left_character in enumerate(left):
        row = left_index + 1
        current = [0] * (len(right) + 1)
        current[0] = row
        for right_index, right_character in enumerate(right):
            column = right_index + 1
            substitution_cost = int(left_character != right_character)
            current[column] = min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + substitution_cost,
            )
            if (
                row > 1
                and column > 1
                and left_character == right[right_index - 1]
                and left[left_index - 1] == right_character
            ):
                current[column] = min(
                    current[column], previous_previous[column - 2] + 1
                )
        previous_previous = previous
        previous = current

    return previous[len(right)]


DEFAULT_DICTIONARY = Dictionary(ENTRIES)


def resolve(request: Request) -> Outcome:
    """Resolve a request against the process-wide generated dictionary."""

    return DEFAULT_DICTIONARY.resolve(request)

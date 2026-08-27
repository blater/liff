"""Immutable public model for the Liff core API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class Reference:
    """A structured cross-reference embedded in a definition."""

    target: str
    relation: str
    label: str


@dataclass(frozen=True, slots=True)
class Entry:
    """One immutable dictionary entry."""

    word: str
    part_of_speech: str | None
    definition: str
    references: tuple[Reference, ...]


class MatchKind(str, Enum):
    """Reason an entry was returned as a definitive result."""

    RANDOM = "random"
    EXACT = "exact"
    GLOB = "glob"
    HIGH_CONFIDENCE = "high_confidence"


class Confidence(str, Enum):
    """Effective tier of a suggested candidate."""

    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class Found:
    """A definitive random, exact, glob, or fuzzy result."""

    entry: Entry
    kind: MatchKind
    score: int | None


@dataclass(frozen=True, slots=True)
class Suggestion:
    """One ordered candidate in an ambiguous result."""

    entry: Entry
    confidence: Confidence
    score: int


@dataclass(frozen=True, slots=True)
class DidYouMean:
    """An ordered ambiguous result."""

    suggestions: tuple[Suggestion, ...]


@dataclass(frozen=True, slots=True)
class NotFound:
    """No candidate met the applicable matching policy."""


Outcome: TypeAlias = Found | DidYouMean | NotFound


@dataclass(frozen=True, slots=True)
class Random:
    """Request uniform random selection."""


@dataclass(frozen=True, slots=True)
class Search:
    """Request a headword search."""

    query: str


Request: TypeAlias = Random | Search

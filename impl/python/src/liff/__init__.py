"""Typed, reusable access to the generated Meaning of Liff dictionary."""

from .core import (
    DEFAULT_DICTIONARY,
    LOW_SUGGESTION_COUNT,
    PARTIAL_PREFIX_SCORE,
    PERFECT_SCORE,
    PREFIX_MIN_CODE_POINTS,
    QUALIFYING_SCORE,
    TOKEN_PREFIX_SCORE,
    Dictionary,
    resolve,
)
from .dictionary_generated import AUTHOR, TITLE
from .model import (
    Confidence,
    DidYouMean,
    Entry,
    Found,
    MatchKind,
    NotFound,
    Outcome,
    Random,
    Reference,
    Request,
    Search,
    Suggestion,
)

__all__ = [
    "AUTHOR",
    "TITLE",
    "Confidence",
    "DEFAULT_DICTIONARY",
    "Dictionary",
    "DidYouMean",
    "Entry",
    "Found",
    "LOW_SUGGESTION_COUNT",
    "MatchKind",
    "NotFound",
    "Outcome",
    "PARTIAL_PREFIX_SCORE",
    "PERFECT_SCORE",
    "PREFIX_MIN_CODE_POINTS",
    "QUALIFYING_SCORE",
    "Random",
    "Reference",
    "Request",
    "Search",
    "Suggestion",
    "TOKEN_PREFIX_SCORE",
    "resolve",
]

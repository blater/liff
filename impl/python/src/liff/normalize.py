"""Deterministic ASCII-only normalization of UTF-8 Python strings."""

from __future__ import annotations


def normalize(value: str) -> str:
    """Normalize a search query or canonical headword."""

    return _normalize(value, preserve_globs=False)


def normalize_glob(value: str) -> str:
    """Normalize a glob pattern while preserving ``*`` and ``?``."""

    return _normalize(value, preserve_globs=True)


def _normalize(value: str, *, preserve_globs: bool) -> str:
    output: list[str] = []
    separator_pending = False

    for character in value:
        if character in ("'", "’"):
            continue
        is_ascii_alphanumeric = (
            "a" <= character <= "z"
            or "A" <= character <= "Z"
            or "0" <= character <= "9"
        )
        is_glob = preserve_globs and character in ("*", "?")
        if is_ascii_alphanumeric or is_glob:
            if separator_pending and output:
                output.append(" ")
            lowered = (
                chr(ord(character) + ord("a") - ord("A"))
                if "A" <= character <= "Z"
                else character
            )
            if lowered != "*" or not output or output[-1] != "*":
                output.append(lowered)
            separator_pending = False
        else:
            separator_pending = True

    return "".join(output)

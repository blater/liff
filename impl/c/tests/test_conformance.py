#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(binary: Path, *arguments: str, expected_status: int = 0) -> str:
    result = subprocess.run(
        [str(binary), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != expected_status:
        raise AssertionError(
            f"{binary.name} {arguments!r}: status {result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )
    return result.stdout


def test_search_cases(driver: Path, root: Path) -> None:
    contract = json.loads((root / "impl/search-cases.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == 1
    for case in contract["cases"]:
        lines = run(driver, "search", case["query"]).splitlines()
        if case["outcome"] == "found":
            kind, word, score = lines[0].split("\t")[1:]
            assert kind == case["kind"]
            assert word == case["word"]
            if "score" in case:
                assert int(score) == case["score"]
        elif case["outcome"] == "did_you_mean":
            heading = lines.pop(0).split("\t")
            assert heading == ["did_you_mean", str(len(case["suggestions"]))]
            actual = []
            for line in lines:
                word, confidence, score = line.split("\t")
                actual.append(
                    {"word": word, "confidence": confidence, "score": int(score)}
                )
            assert actual == case["suggestions"]
        else:
            assert lines == ["not_found"]


def test_algorithm_cases(driver: Path, root: Path) -> None:
    contract = json.loads((root / "impl/algorithm-cases.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == 1
    for case in contract["normalization"]:
        assert run(driver, "normalize", case["input"]) == case["output"]
    for case in contract["glob_normalization"]:
        assert run(driver, "normalize-glob", case["input"]) == case["output"]
    for case in contract["edit_scores"]:
        assert int(run(driver, "distance", case["left"], case["right"])) == case["distance"]
        assert int(run(driver, "similarity", case["left"], case["right"])) == case["score"]
    for case in contract["candidate_scores"]:
        assert int(run(driver, "candidate", case["query"], case["candidate"])) == case["score"]
    for case in contract["glob_matches"]:
        assert bool(int(run(driver, "glob", case["pattern"], case["candidate"]))) == case["matches"]
    for case in contract["ordering"]:
        actual = sorted(
            case["input"],
            key=lambda value: [ord(character) for character in value],
        )
        assert actual == case["ascending"]
        for left, right in zip(actual, actual[1:]):
            assert int(run(driver, "compare", left, right)) < 0


def decode_hex(value: bytes) -> str | None:
    if value == b"-":
        return None
    return bytes.fromhex(value.decode("ascii")).decode("utf-8")


def test_generated_source(driver: Path, root: Path) -> None:
    source = json.loads((root / "liff.json").read_text(encoding="utf-8"))
    output = subprocess.run(
        [str(driver), "dump"], check=True, capture_output=True
    ).stdout.splitlines()
    metadata = output.pop(0).split(b"\t")
    assert metadata[0] == b"M"
    assert decode_hex(metadata[1]) == source["title"]
    assert decode_hex(metadata[2]) == source["author"]

    cursor = 0
    for entry_index, (word, expected) in enumerate(source["entries"].items()):
        fields = output[cursor].split(b"\t")
        cursor += 1
        assert fields[0] == b"E"
        assert int(fields[1]) == entry_index
        assert decode_hex(fields[2]) == word
        assert decode_hex(fields[3]) == expected["part_of_speech"]
        assert decode_hex(fields[4]) == expected["definition"]
        assert int(fields[5]) == len(expected["references"])
        for reference_index, reference in enumerate(expected["references"]):
            fields = output[cursor].split(b"\t")
            cursor += 1
            assert fields[:3] == [b"R", str(entry_index).encode(), str(reference_index).encode()]
            assert decode_hex(fields[3]) == reference["target"]
            assert decode_hex(fields[4]) == reference["relation"]
            assert decode_hex(fields[5]) == reference["label"]
            result = run(driver, "search", reference["target"]).split("\t")
            assert result[:3] == ["found", "exact", reference["target"]]
    assert cursor == len(output)
    assert run(driver, "self-test") == "ok\n"


def test_cli(cli: Path, root: Path) -> None:
    source = json.loads((root / "liff.json").read_text(encoding="utf-8"))
    random_output = run(cli)
    word, definition = random_output.rstrip("\n").split("\n", 1)
    assert source["entries"][word]["definition"] == definition

    for arguments, prefix in [
        (("banteer",), "BANTEER\nA lusty and raucous old ballad"),
        (("banteeer",), "BANTEER\nA lusty and raucous old ballad"),
        (("glutt",), "GLUTT LODGE\n"),
        (("bilb",), "BILBSTER\n"),
        (("bil*",), "BILBSTER\n"),
        (("b?lbster",), "BILBSTER\n"),
        (("symonds", "yat"), "SYMOND'S YAT\n"),
    ]:
        assert run(cli, *arguments).startswith(prefix)

    assert run(cli, "high", expected_status=1) == (
        "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n"
    )
    assert run(cli, "b*", expected_status=1) == (
        "Did you mean?\n"
        "BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n"
        "BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n"
        "and 44 others\n"
    )
    eleven = run(cli, "bo*", expected_status=1)
    assert "and " not in eleven and len(eleven.rstrip("\n").split("\n")) == 12
    all_entries = run(cli, "*", expected_status=1)
    assert all_entries.endswith("and 540 others\n")
    assert len(all_entries.rstrip("\n").split("\n")) == 12
    assert run(cli, "xyzzy", expected_status=1) == 'No definition found for "xyzzy".\n'
    assert run(cli, "--help").startswith("Usage: liff")

    invalid = subprocess.run([str(cli), "--unknown"], check=False, capture_output=True, text=True)
    assert invalid.returncode == 2 and invalid.stdout == ""
    assert invalid.stderr.startswith("Usage: liff")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    arguments = parser.parse_args()
    test_search_cases(arguments.driver, arguments.root)
    test_algorithm_cases(arguments.driver, arguments.root)
    test_generated_source(arguments.driver, arguments.root)
    test_cli(arguments.cli, arguments.root)
    print("C conformance: OK")


if __name__ == "__main__":
    main()

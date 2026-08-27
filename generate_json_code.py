#!/usr/bin/env python3
"""Generate one or more source files from arbitrary JSON and templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from render_json_template import GenerationError, load_json, render_template


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_DIR / "codegen-targets.json"


def require_string(value: Any, description: str) -> str:
    if not isinstance(value, str):
        raise GenerationError(f"{description} must be a string")
    return value


def load_config(path: Path) -> tuple[str, dict[str, dict[str, str]]]:
    document = load_json(path)
    if not isinstance(document, dict):
        raise GenerationError("generator configuration must be a JSON object")

    input_name = require_string(document.get("input"), "input")
    configured_targets = document.get("targets")
    if not isinstance(configured_targets, dict):
        raise GenerationError("generator configuration must contain a 'targets' object")

    targets: dict[str, dict[str, str]] = {}
    for name, target in configured_targets.items():
        if not isinstance(name, str) or not isinstance(target, dict):
            raise GenerationError("each configured target must be a named object")
        targets[name] = {
            "template": require_string(target.get("template"), f"{name}.template"),
            "output": require_string(target.get("output"), f"{name}.output"),
        }
    return input_name, targets


def generate_target(
    name: str,
    target: dict[str, str],
    document: Any,
    config_dir: Path,
) -> tuple[Path, str]:
    template_path = config_dir / target["template"]
    output_path = config_dir / target["output"]
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GenerationError(f"Cannot load template for {name}: {exc}") from exc
    return output_path, render_template(template, document)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        "--targets",
        dest="config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="generator manifest (default: codegen-targets.json)",
    )
    parser.add_argument(
        "--input",
        "--dictionary",
        dest="input",
        type=Path,
        help="override the input JSON path declared by the configuration",
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="selected_targets",
        help="target to generate; may be repeated (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated files without writing them",
    )
    parser.add_argument(
        "--list-targets", action="store_true", help="list configured target names"
    )
    args = parser.parse_args()

    try:
        input_name, targets = load_config(args.config)
        if args.list_targets:
            print("\n".join(targets))
            return 0

        selected = args.selected_targets or list(targets)
        unknown = [name for name in selected if name not in targets]
        if unknown:
            raise GenerationError(f"Unknown target(s): {', '.join(unknown)}")

        config_dir = args.config.resolve().parent
        input_path = args.input if args.input is not None else config_dir / input_name
        document = load_json(input_path)
        generated = [
            generate_target(name, targets[name], document, config_dir)
            for name in selected
        ]
    except GenerationError as exc:
        parser.error(str(exc))

    stale = False
    for output_path, rendered in generated:
        if args.check:
            try:
                existing = output_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                print(f"Missing generated file: {output_path}", file=sys.stderr)
                stale = True
                continue
            if existing != rendered:
                print(f"Generated file is out of date: {output_path}", file=sys.stderr)
                stale = True
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")

    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render arbitrary JSON data through a small, dependency-free template engine."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GenerationError(ValueError):
    """Raised when JSON, a template, or a requested conversion is invalid."""


@dataclass(frozen=True)
class TextNode:
    value: str


@dataclass(frozen=True)
class VariableNode:
    expression: str


@dataclass(frozen=True)
class SectionNode:
    expression: str
    closing_name: str
    inverted: bool
    children: tuple["Node", ...]


Node = TextNode | VariableNode | SectionNode
MISSING = object()


def split_expression(expression: str) -> tuple[str, tuple[str, ...]]:
    parts = tuple(part.strip() for part in expression.split("|"))
    if not parts[0] or any(not part for part in parts):
        raise GenerationError(f"Invalid template expression: {expression!r}")
    if any(any(character.isspace() for character in part) for part in parts):
        raise GenerationError(f"Whitespace is not allowed inside expressions: {expression!r}")
    return parts[0], parts[1:]


def parse_template(template: str) -> tuple[Node, ...]:
    """Parse variables, iterable sections, and inverted sections."""
    root: list[Node] = []
    node_stack: list[list[Node]] = [root]
    section_stack: list[tuple[str, str, bool]] = []
    cursor = 0

    while True:
        opening = template.find("{{", cursor)
        if opening < 0:
            node_stack[-1].append(TextNode(template[cursor:]))
            break

        node_stack[-1].append(TextNode(template[cursor:opening]))
        closing = template.find("}}", opening + 2)
        if closing < 0:
            raise GenerationError("Unclosed '{{' in template")

        tag = template[opening + 2 : closing].strip()
        if not tag:
            raise GenerationError("Empty template tag")
        marker = tag[0] if tag[0] in "#^/" else ""
        expression = tag[1:].strip() if marker else tag
        path, _ = split_expression(expression)

        if marker in ("#", "^"):
            section_stack.append((expression, path, marker == "^"))
            node_stack.append([])
        elif marker == "/":
            if not section_stack:
                raise GenerationError(f"Unexpected closing section: {expression}")
            opened_expression, closing_name, inverted = section_stack.pop()
            children = tuple(node_stack.pop())
            if expression not in (closing_name, opened_expression):
                raise GenerationError(
                    f"Closing section {expression!r} does not match {closing_name!r}"
                )
            node_stack[-1].append(
                SectionNode(opened_expression, closing_name, inverted, children)
            )
        else:
            node_stack[-1].append(VariableNode(expression))
        cursor = closing + 2

    if section_stack:
        raise GenerationError(f"Unclosed template section: {section_stack[-1][1]}")
    return tuple(root)


def descend(value: Any, components: list[str]) -> Any:
    for component in components:
        if isinstance(value, Mapping) and component in value:
            value = value[component]
        elif isinstance(value, list) and component.isdigit():
            index = int(component)
            if index >= len(value):
                return MISSING
            value = value[index]
        else:
            return MISSING
    return value


def resolve_path(path: str, contexts: tuple[Any, ...]) -> Any:
    if path == "$":
        return contexts[0]
    if path == ".":
        return contexts[-1]

    if path.startswith("$."):
        candidates = (contexts[0],)
        components = path[2:].split(".")
    elif path.startswith("."):
        candidates = (contexts[-1],)
        components = path[1:].split(".")
    else:
        candidates = tuple(reversed(contexts))
        components = path.split(".")

    for candidate in candidates:
        value = descend(candidate, components)
        if value is not MISSING:
            return value
    raise GenerationError(f"Unknown template path: {path}")


def rust_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\0": "\\0",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\u{{{ord(character):x}}}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def rust_literal(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return rust_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("Rust literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(rust_literal(item) for item in value) + "]"
    raise GenerationError(
        "Rust has no generic object literal; iterate the object with |items in the template"
    )


def go_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\0": "\\x00",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def go_literal(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return go_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("Go literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return "[]any{" + ", ".join(go_literal(item) for item in value) + "}"
    raise GenerationError(
        "Go has no generic object literal; iterate the object with |items in the template"
    )


def zig_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\0": "\\x00",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def zig_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return zig_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("Zig literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return ".{" + ", ".join(zig_literal(item) for item in value) + "}"
    raise GenerationError(
        "Zig has no generic object literal; iterate the object with |items in the template"
    )


def java_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\{ord(character):03o}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def java_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return java_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("Java literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return "java.util.Arrays.asList(" + ", ".join(
            java_literal(item) for item in value
        ) + ")"
    raise GenerationError(
        "Java has no generic object literal; iterate the object with |items in the template"
    )


def typescript_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
        "\0": "\\x00",
        "\u2028": "\\u2028",
        "\u2029": "\\u2029",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def typescript_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return typescript_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError(
                "TypeScript literals cannot represent a non-finite JSON number"
            )
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(typescript_literal(item) for item in value) + "]"
    raise GenerationError(
        "TypeScript has no generic object literal; iterate the object with |items in the template"
    )


def lua_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\a": "\\a",
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\v": "\\v",
        "\f": "\\f",
        "\r": "\\r",
        "\0": "\\x00",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def lua_literal(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return lua_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("Lua literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return "{" + ", ".join(lua_literal(item) for item in value) + "}"
    raise GenerationError(
        "Lua has no generic object literal; iterate the object with |items in the template"
    )


def c_string(value: str) -> str:
    escaped: list[str] = ['"']
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "?": "\\?",
        "\a": "\\a",
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\v": "\\v",
        "\f": "\\f",
        "\r": "\\r",
    }
    for character in value:
        if character in replacements:
            escaped.append(replacements[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\{ord(character):03o}")
        else:
            escaped.append(character)
    escaped.append('"')
    return "".join(escaped)


def c_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return c_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GenerationError("C literals cannot represent a non-finite JSON number")
        return repr(value)
    if isinstance(value, list):
        return "{" + ", ".join(c_literal(item) for item in value) + "}"
    raise GenerationError(
        "C has no generic object literal; iterate the object with |items in the template"
    )


def apply_filter(name: str, value: Any) -> Any:
    if name == "json":
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if name == "python":
        return repr(value)
    if name == "rust":
        return rust_literal(value)
    if name == "go":
        return go_literal(value)
    if name == "zig":
        return zig_literal(value)
    if name == "java":
        return java_literal(value)
    if name in ("typescript", "ts"):
        return typescript_literal(value)
    if name == "lua":
        return lua_literal(value)
    if name == "c":
        return c_literal(value)
    if name == "text":
        if isinstance(value, (Mapping, list)):
            raise GenerationError("|text only accepts scalar JSON values")
        return "" if value is None else str(value)
    if name == "items":
        if not isinstance(value, Mapping):
            raise GenerationError("|items requires a JSON object")
        return [{"key": key, "value": item} for key, item in value.items()]
    if name == "keys":
        if not isinstance(value, Mapping):
            raise GenerationError("|keys requires a JSON object")
        return list(value)
    if name == "values":
        if not isinstance(value, Mapping):
            raise GenerationError("|values requires a JSON object")
        return list(value.values())
    if name == "length":
        if not isinstance(value, (Mapping, list, str)):
            raise GenerationError("|length requires an object, array, or string")
        return len(value)
    raise GenerationError(f"Unknown template filter: {name}")


def resolve_expression(expression: str, contexts: tuple[Any, ...]) -> Any:
    path, filters = split_expression(expression)
    value = resolve_path(path, contexts)
    for filter_name in filters:
        value = apply_filter(filter_name, value)
    return value


def render_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise GenerationError(
        "Cannot insert an object or array directly; use a literal filter or a section"
    )


def render_nodes(nodes: Iterable[Node], contexts: tuple[Any, ...]) -> str:
    rendered: list[str] = []
    for node in nodes:
        if isinstance(node, TextNode):
            rendered.append(node.value)
        elif isinstance(node, VariableNode):
            rendered.append(render_scalar(resolve_expression(node.expression, contexts)))
        else:
            value = resolve_expression(node.expression, contexts)
            if node.inverted:
                if not value:
                    rendered.append(render_nodes(node.children, contexts))
            elif isinstance(value, list):
                for item in value:
                    rendered.append(render_nodes(node.children, contexts + (item,)))
            elif isinstance(value, Mapping):
                rendered.append(render_nodes(node.children, contexts + (value,)))
            elif value:
                rendered.append(render_nodes(node.children, contexts + (value,)))
    return "".join(rendered)


def render_template(template: str, document: Any) -> str:
    """Render a template against any JSON-compatible root value."""
    return render_nodes(parse_template(template), (document,))


def reject_nonstandard_number(value: str) -> None:
    raise ValueError(f"non-standard JSON number {value}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), parse_constant=reject_nonstandard_number
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise GenerationError(f"Cannot load {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="input JSON file")
    parser.add_argument("--template", type=Path, required=True, help="template file")
    parser.add_argument("--output", type=Path, help="output file (default: stdout)")
    parser.add_argument(
        "--check", action="store_true", help="verify --output without writing it"
    )
    args = parser.parse_args()

    if args.check and args.output is None:
        parser.error("--check requires --output")

    try:
        document = load_json(args.input)
        template = args.template.read_text(encoding="utf-8")
        rendered = render_template(template, document)
    except (OSError, GenerationError) as exc:
        parser.error(str(exc))

    if args.output is None:
        sys.stdout.write(rendered)
        return 0
    if args.check:
        try:
            existing = args.output.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"Missing generated file: {args.output}", file=sys.stderr)
            return 1
        if existing != rendered:
            print(f"Generated file is out of date: {args.output}", file=sys.stderr)
            return 1
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

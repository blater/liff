import base64
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from render_json_template import (
    GenerationError,
    c_string,
    go_string,
    java_string,
    lua_string,
    render_template,
    rust_string,
    typescript_string,
    zig_string,
)


class GenericTemplateRendererTests(unittest.TestCase):
    def test_unrelated_nested_json_and_filters(self) -> None:
        document = {
            "project": {"name": "Comet", "enabled": True, "owner": None},
            "ports": [8080, 8443],
            "services": [
                {"name": "api", "replicas": 3},
                {"name": "worker", "replicas": 2},
            ],
        }
        template = (
            "{{project.name}} enabled={{project.enabled|python}} "
            "owner={{project.owner|json}}\n"
            "ports={{#ports}}{{.|rust}},{{/ports}}\n"
            "{{#services}}{{name}}={{replicas}}@{{$.project.name}};{{/services}}"
            "{{^project.owner}}unowned{{/project.owner}}"
        )
        self.assertEqual(
            render_template(template, document),
            "Comet enabled=True owner=null\n"
            "ports=8080,8443,\n"
            "api=3@Comet;worker=2@Comet;unowned",
        )

    def test_root_array_and_scalar_items(self) -> None:
        document = ["alpha", 7, False, None]
        self.assertEqual(
            render_template("{{#$}}{{.|json}};{{/$}}", document),
            '"alpha";7;false;null;',
        )

    def test_object_items_keys_values_and_length(self) -> None:
        document = {"colours": {"red": "#f00", "green": "#0f0"}}
        template = (
            "{{colours|length}}:"
            "{{#colours|items}}{{key}}={{value}};{{/colours}}"
            "{{#colours|keys}}[{{.}}]{{/colours}}"
            "{{#colours|values}}[{{.}}]{{/colours}}"
        )
        self.assertEqual(
            render_template(template, document),
            "2:red=#f00;green=#0f0;[red][green][#f00][#0f0]",
        )

    def test_base64_decode_filter_is_generic_and_chainable(self) -> None:
        text = "£ café 😀"
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self.assertEqual(
            render_template("{{value|base64_decode|json}}", {"value": encoded}),
            json.dumps(text, ensure_ascii=False),
        )

        for value in (
            7,
            "not base64!",
            "Zh==",
            base64.b64encode(b"\xff").decode("ascii"),
        ):
            with self.subTest(value=value), self.assertRaises(GenerationError):
                render_template("{{value|base64_decode}}", {"value": value})

    def test_python_and_rust_literals_are_language_appropriate(self) -> None:
        document = {"active": True, "missing": None, "labels": ["a", "b"]}
        template = (
            "{{active|python}}/{{active|rust}};"
            "{{missing|python}}/{{missing|rust}};{{labels|rust}}"
        )
        self.assertEqual(
            render_template(template, document),
            'True/true;None/None;["a", "b"]',
        )
        self.assertEqual(rust_string("line\n\x01"), '"line\\n\\u{1}"')

    def test_go_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ["quote\"", "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template(
                "{{active|go}}/{{missing|go}}/{{values|go}}",
                document,
            ),
            'true/nil/[]any{"quote\\\"", "slash\\\\", "line\\n", "£", "\\x00\\x01"}',
        )
        self.assertEqual(go_string("tab\treturn\r\x7f"), '"tab\\treturn\\r\\x7f"')

    def test_zig_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ["quote\"", "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template("{{active|zig}}/{{missing|zig}}/{{values|zig}}", document),
            'true/null/.{"quote\\\"", "slash\\\\", "line\\n", "£", "\\x00\\x01"}',
        )
        self.assertEqual(zig_string("tab\treturn\r\x7f"), '"tab\\treturn\\r\\x7f"')

    def test_java_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ['quote"', "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template(
                "{{active|java}}/{{missing|java}}/{{values|java}}",
                document,
            ),
            'true/null/java.util.Arrays.asList("quote\\\"", "slash\\\\", '
            '"line\\n", "£", "\\000\\001")',
        )
        self.assertEqual(java_string("tab\treturn\r\x7f"), '"tab\\treturn\\r\\177"')

    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK unavailable")
    def test_java_strings_compile_and_round_trip(self) -> None:
        values = [
            'quote"',
            "slash\\",
            "line\nreturn\rtab\t",
            "\x00\x01\b\f\x7f",
            "£ café 😀",
            "literal \\u0041",
        ]
        literals = ",\n        ".join(java_string(value) for value in values)
        source = f"""
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public final class JavaLiteralProbe {{
    public static void main(String[] arguments) {{
        String[] values = {{
        {literals}
        }};
        for (String value : values) {{
            System.out.println(Base64.getEncoder().encodeToString(
                    value.getBytes(StandardCharsets.UTF_8)));
        }}
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "JavaLiteralProbe.java"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["javac", "--release", "17", "-encoding", "UTF-8", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                ["java", "-cp", directory, "JavaLiteralProbe"],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(
            result.stdout.splitlines(),
            [base64.b64encode(value.encode()).decode() for value in values],
        )

    def test_typescript_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ['quote"', "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template(
                "{{active|typescript}}/{{missing|typescript}}/{{values|typescript}}",
                document,
            ),
            'true/null/["quote\\\"", "slash\\\\", "line\\n", "£", "\\x00\\x01"]',
        )
        self.assertEqual(
            typescript_string("tab\treturn\r\x7f\u2028"),
            '"tab\\treturn\\r\\x7f\\u2028"',
        )

    @unittest.skipUnless(
        shutil.which("tsc") and shutil.which("node"), "TypeScript unavailable"
    )
    def test_typescript_strings_compile_and_round_trip(self) -> None:
        values = [
            'quote"',
            "slash\\",
            "line\nreturn\rtab\t",
            "\x00\x01\b\f\x7f",
            "£ café 😀",
            "\u2028\u2029",
        ]
        literals = ",\n    ".join(typescript_string(value) for value in values)
        source = f"""
const values: readonly string[] = [
    {literals}
];
console.log(JSON.stringify(values));
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "literal-probe.ts"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                [
                    "tsc",
                    "--strict",
                    "--target",
                    "ES2022",
                    "--module",
                    "commonjs",
                    "--outDir",
                    directory,
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                ["node", str(Path(directory) / "literal-probe.js")],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(json.loads(result.stdout), values)

    def test_lua_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ['quote"', "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template(
                "{{active|lua}}/{{missing|lua}}/{{values|lua}}",
                document,
            ),
            'true/nil/{"quote\\\"", "slash\\\\", "line\\n", "£", "\\x00\\x01"}',
        )
        self.assertEqual(
            lua_string("tab\treturn\r\x7f"),
            '"tab\\treturn\\r\\x7f"',
        )

    @unittest.skipUnless(shutil.which("lua"), "Lua unavailable")
    def test_lua_strings_compile_and_round_trip(self) -> None:
        values = [
            'quote"',
            "slash\\",
            "line\nreturn\rtab\t",
            "\x00\x01\a\b\v\f\x7f",
            "£ café 😀",
        ]
        literals = ",\n    ".join(lua_string(value) for value in values)
        source = f"""
local values = {{
    {literals}
}}
for _, value in ipairs(values) do
    for index = 1, #value do
        io.write(string.format("%02x", string.byte(value, index)))
    end
    io.write("\\n")
end
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "literal_probe.lua"
            path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["lua", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.stdout.splitlines(), [value.encode().hex() for value in values])

    def test_c_literals_are_language_appropriate(self) -> None:
        document = {
            "active": True,
            "missing": None,
            "values": ['quote"', "slash\\", "line\n", "£", "\x00\x01"],
        }
        self.assertEqual(
            render_template(
                "{{active|c}}/{{missing|c}}/{{values|c}}",
                document,
            ),
            'true/NULL/{"quote\\\"", "slash\\\\", "line\\n", "£", "\\000\\001"}',
        )
        self.assertEqual(c_string("why??/\t\x7f"), '"why\\?\\?/\\t\\177"')

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_c_strings_compile_and_round_trip(self) -> None:
        values = [
            'quote"',
            "slash\\",
            "line\nreturn\rtab\t",
            "\x00\x01\a\b\v\f\x7f",
            "£ café 😀",
            "trigraph ??/",
        ]
        declarations = "\n".join(
            f"static const char value_{index}[] = {c_string(value)};"
            for index, value in enumerate(values)
        )
        rows = ",\n    ".join(
            f"{{ value_{index}, sizeof(value_{index}) - 1 }}"
            for index in range(len(values))
        )
        source = f"""
#include <stddef.h>
#include <stdio.h>
{declarations}
struct value {{ const char *data; size_t length; }};
int main(void) {{
    const struct value values[] = {{
    {rows}
    }};
    for (size_t row = 0; row < sizeof(values) / sizeof(values[0]); ++row) {{
        for (size_t index = 0; index < values[row].length; ++index) {{
            printf("%02x", (unsigned char) values[row].data[index]);
        }}
        putchar('\\n');
    }}
    return 0;
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "literal_probe.c"
            binary_path = Path(directory) / "literal_probe"
            source_path.write_text(source, encoding="utf-8")
            subprocess.run(
                [
                    "cc",
                    "-std=c17",
                    "-Wall",
                    "-Wextra",
                    "-Wpedantic",
                    "-Werror",
                    str(source_path),
                    "-o",
                    str(binary_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                [str(binary_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.stdout.splitlines(), [value.encode().hex() for value in values])

    def test_unknown_path_filter_and_direct_collection_are_errors(self) -> None:
        with self.assertRaises(GenerationError):
            render_template("{{missing}}", {})
        with self.assertRaises(GenerationError):
            render_template("{{value|unknown}}", {"value": 1})
        with self.assertRaises(GenerationError):
            render_template("{{value}}", {"value": [1, 2]})


if __name__ == "__main__":
    unittest.main()

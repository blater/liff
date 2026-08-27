A Dictionary of Things There Aren’t Any Words for Yet - but There Ought to Be.

# Liff

Liff is a self-contained command-line dictionary with equivalent
implementations in Rust, Go, Python, Zig, Java, TypeScript, Lua, and C.

## Usage

Every completed port implements the same `liff` command-line behavior.

```console
$ liff                 # retrieve a random entry
THRUPP
To hold a ruler on one end on a desk and make the other end go bbddbbddbbrrbrrrrddrr.

$ liff banteer         # exact lookup
BANTEER
A lusty and raucous old ballad sung after a particularly spectacular araglin (q.v.) has been pulled off.

$ liff scons           # confidence-qualified fuzzy lookup
SCONSER
A person who looks around them when talking to you, to see if there's anyone more interesting about.

$ liff ainderby steeple   # multiple-word match
AINDERBY STEEPLE
One who asks you a question with the apparent motive of wanting to hear your answer, but who cuts short your opening sentence by leaning forward and saying 'and I'll tell you why I ask...' and then talking solidly for the next hour.
```

Searches are case-insensitive and ignore insignificant punctuation. A fuzzy
candidate scoring at least 700 is returned when it is the only candidate at or
above that threshold. Multiple qualifying candidates produce a `Did you mean?`
list; weaker searches produce a not-found message.

Quoted glob patterns are also supported. Quote them so the shell passes the
wildcards to `liff` instead of expanding them as filenames:

```console
$ liff 'bil*'  # unique match: BILBSTER
$ liff 'b*'    # every headword beginning with B
$ liff 'b?d*'  # ? matches exactly one character
$ liff '*'     # every entry
```

`*` matches zero or more characters and `?` matches exactly one. One glob match
prints its definition. Multiple matches are alphabetically ordered under
`Did you mean?`: up to 11 are printed in full; with 12 or more, the first 10 are
printed followed by `and N others`.

Successful exact, fuzzy, glob, and random results exit with status 0.
Suggestions and not-found results exit with status 1; invalid CLI usage exits
with status 2.

## More sample output

A glob with several matches offers suggestions:

```console
$ liff 'b?d*'
Did you mean?
BEDFONT
BODMIN
BUDBY
BUDE
```

An unsuccessful search reports the original query:

```console
$ liff completely-made-up
No definition found for "completely-made-up".
```

## Build and maintenance

Every completed language port provides an executable `build.sh` wrapper that
can be run from any working directory:

```sh
impl/rust/build.sh
impl/go/build.sh
impl/python/build.sh
impl/zig/build.sh
impl/java/build.sh
impl/typescript/build.sh
impl/lua/build.sh
impl/c/build.sh
```

Remove compiler working directories, generated scratch output, and caches while
preserving source files and every deployable `impl/*/bin` artifact:

```sh
make tidy
```

## Dictionary data

`liff.json` is a lookup-ready version of `liff-corrected.txt`. It uses plain
JSON so lookup programs can load it with a standard-library parser and use the
`entries` object directly as a word-to-entry map.

Each entry has this shape:

```json
{
  "part_of_speech": "n.",
  "definition": "The original definition text.",
  "references": [
    {
      "target": "ANOTHER HEADWORD",
      "relation": "q.v.",
      "label": "source spelling"
    }
  ]
}
```

`part_of_speech` is `null` where the source supplies no label. `target` is
always the canonical key of another object in `entries`; `label` preserves the
spelling used in the definition. The supported link relations are `q.v.` and
`see_also`.

Regenerate the file with:

```sh
python3 build_liff_json.py
```

Verify that the committed JSON matches its source without changing files:

```sh
python3 build_liff_json.py --check
```

## Generic JSON template engine

`render_json_template.py` has no knowledge of the Liff schema. It accepts any
valid JSON root value and any compatible template:

```sh
python3 render_json_template.py \
  --input any-data.json \
  --template any-template.tmpl \
  --output generated-file
```

`generate_json_code.py` applies several templates to the same arbitrary JSON
document. Its manifest supplies the input and target paths:

```json
{
  "input": "data.json",
  "targets": {
    "python": {
      "template": "templates/data.py.tmpl",
      "output": "generated/data.py"
    }
  }
}
```

```sh
python3 generate_json_code.py --config targets.json
python3 generate_json_code.py --config targets.json --check
```

Paths such as `{{user.name}}` address nested values. Within an array section,
`{{.}}` is the current value and `$` is the JSON root. Sections iterate arrays
or test truthiness:

```text
{{#users}}{{name}}: {{active|python}}
{{/users}}{{^owner}}no owner{{/owner}}
```

Filters are generic operations:

- `json`, `python`, `rust`, `go`, `zig`, `java`, `typescript`, `lua`, and `c`
  produce escaped literals
- `items`, `keys`, and `values` expose JSON objects for iteration
- `length` returns the size of an object, array, or string
- `text` explicitly converts a scalar to text

For example, `{{#scores|items}}{{key}}={{value}};{{/scores}}` iterates an
object without knowing its keys in advance. Root arrays and scalars can be
addressed with `$`, such as `{{#$}}{{.|json}}{{/$}}`.

## Liff source modules

`codegen-targets.json` is the Liff instance of the generic multi-target
generator. Its generated Python module and Rust core data need neither
`liff.json` nor a JSON parser at runtime.

Generate every configured language:

```sh
python3 generate_json_code.py
```

Generate just one language, or check that all outputs are current:

```sh
python3 generate_json_code.py --target rust
python3 generate_json_code.py --check
```

`generate_liff_code.py` remains as a backward-compatible alias using this same
default configuration. The initial targets produce:

- `generated/liff_dictionary.py`, exposing `ENTRIES` and `lookup()`
- `impl/python/src/liff/dictionary_generated.py`, providing immutable native
  data to the complete Python core package and zipapp CLI
- `impl/rust/crates/liff-core/src/generated/dictionary.rs`, providing static
  data to the separate Rust core API and CLI crates
- `impl/go/dictionary_generated.go`, providing native immutable data to the
  separate Go core package and CLI command
- `impl/zig/src/dictionary_generated.zig`, providing native immutable data to
  the separate Zig core library and CLI command
- `impl/java/src/main/java/liff/core/GeneratedDictionary.java`, providing
  immutable native data to the separate Java core package and CLI command
- `impl/typescript/src/main/ts/dictionary-generated.ts`, providing immutable
  native data to the separate TypeScript core and CLI adapter
- `impl/lua/src/main/lua/liff/dictionary_generated.lua`, providing immutable
  native data to the separate Lua core modules and CLI adapter
- `impl/c/src/dictionary_generated.c`, providing static native data to the
  separate C17 core library and CLI adapter

Run the generator and language smoke tests with:

```sh
python3 generate_json_code.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
cargo test --manifest-path impl/rust/Cargo.toml
go -C impl/go test ./...
make -C impl/python test
make -C impl/zig test
make -C impl/java test
make -C impl/typescript test
make -C impl/lua test
make -C impl/c test
```

The language-neutral contract for implementing additional ports is
[`impl/SPECIFICATION.md`](impl/SPECIFICATION.md).

The completed language ports have implementation-specific build instructions:

- [Rust](impl/rust/README.md)
- [Go](impl/go/README.md)
- [Python](impl/python/README.md)
- [Zig](impl/zig/README.md)
- [Java](impl/java/README.md)
- [TypeScript](impl/typescript/README.md)
- [Lua](impl/lua/README.md)
- [C](impl/c/README.md)

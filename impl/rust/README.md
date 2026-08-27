# Rust implementation

This workspace separates the reusable `liff-core` API from the `liff` command
line program. Dictionary data is generated into the core crate and compiled
into the binary; neither crate reads JSON at runtime.

Build a release executable into `impl/rust/bin/liff`:

```sh
make -C impl/rust
```

The Makefile regenerates the embedded dictionary before compiling. Its main
targets are:

```sh
make -C impl/rust build            # generate and build bin/liff
make -C impl/rust test             # verify generated data and run tests
make -C impl/rust lint             # rustfmt and clippy
make -C impl/rust check            # tests plus lint
make -C impl/rust clean            # remove Cargo output and bin/
```

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target rust
python3 generate_json_code.py --target rust --check
```

Build, test, and lint:

```sh
cargo build --manifest-path impl/rust/Cargo.toml
cargo test --manifest-path impl/rust/Cargo.toml
cargo clippy --manifest-path impl/rust/Cargo.toml --all-targets -- -D warnings
```

## CLI usage

Run the built binary directly:

```sh
impl/rust/bin/liff                 # random entry
impl/rust/bin/liff banteer         # exact lookup
impl/rust/bin/liff glutt           # unique confidence-qualified lookup
impl/rust/bin/liff ainderby steeple
```

With no arguments, `liff` prints a random headword and definition. Positional
arguments are joined into one search query. Searches are case-insensitive and
ignore insignificant punctuation. A fuzzy candidate scoring at least 700 is
returned when it is the only candidate at or above that threshold; multiple
qualifying candidates produce a `Did you mean?` list.

The CLI also accepts glob patterns. Patterns should be quoted to prevent the
shell from expanding them as filenames:

```sh
impl/rust/bin/liff 'bil*'  # unique match: BILBSTER
impl/rust/bin/liff 'b*'    # every headword beginning with B
impl/rust/bin/liff 'b?d*'  # ? matches exactly one character
impl/rust/bin/liff '*'     # every entry
```

`*` matches zero or more characters and `?` matches exactly one. A unique glob
match prints its definition. Multiple matches are alphabetically ordered under
`Did you mean?`. Up to 11 are printed in full; for 12 or more, the first 10 are
followed by `and N others`.

Exit statuses are:

- `0` for random, exact, confidence-qualified, or unique glob results
- `1` for suggestions or not found
- `2` for invalid command-line usage

The same CLI can be run through Cargo during development:

```sh
cargo run --manifest-path impl/rust/Cargo.toml -p liff-cli --
cargo run --manifest-path impl/rust/Cargo.toml -p liff-cli -- banteer
cargo run --manifest-path impl/rust/Cargo.toml -p liff-cli -- ainderby steeple
```

The language-neutral product and implementation contract is defined in
`../SPECIFICATION.md`, with shared conformance cases in `../search-cases.json`
and `../algorithm-cases.json`.

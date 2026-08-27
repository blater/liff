# C implementation

This C17 port separates the reusable `liff` core library from the CLI adapter.
The generated dictionary is compiled into a statically linked native executable
that performs no runtime file or network access.

A C17 compiler, `make`, and `ar` are required. Python is used only by generation
and tests, not by the deployed executable.

Build the executable at `impl/c/bin/liff`:

```sh
impl/c/build.sh
# or: make -C impl/c
```

Available Makefile targets are:

```sh
make -C impl/c core     # build build/libliff.a
make -C impl/c build    # generate and build bin/liff
make -C impl/c test     # run shared and C-specific conformance tests
make -C impl/c lint     # strict compiler and source-format checks
make -C impl/c check    # tests plus lint
make -C impl/c clean    # remove build/ and bin/
```

Run the CLI:

```sh
impl/c/bin/liff                  # random entry
impl/c/bin/liff banteer          # exact lookup
impl/c/bin/liff glutt            # confidence-qualified lookup
impl/c/bin/liff 'bil*'           # unique glob lookup
impl/c/bin/liff 'b*'             # multiple glob matches
impl/c/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more Unicode code points and `?` exactly one. The complete product,
algorithm, API, and CLI contract is in `../SPECIFICATION.md`.

The public library API is declared in `include/liff.h`. Search and resolve
functions initialize caller-owned `LiffOutcome` values; call
`liff_outcome_destroy` after every successful operation. Dictionaries created
with `liff_dictionary_create` borrow their entry storage and must be released
with `liff_dictionary_destroy`. The process-wide generated dictionary returned
by `liff_dictionary` must not be destroyed.

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target c
python3 generate_json_code.py --target c --check
```

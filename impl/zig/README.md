# Zig implementation

This port separates the reusable `liff.zig` core from the `main.zig` command.
The generated dictionary is compiled into a native executable, which performs
no runtime file or network access.

Zig 0.16.0 is required.

The core uses an explicit allocator-backed lifetime. `initGenerated` builds and
validates the sorted normalized index; `deinit` releases it:

```zig
const liff = @import("liff.zig");

var dictionary = try liff.Dictionary.initGenerated(allocator);
defer dictionary.deinit();

var outcome = try dictionary.search(allocator, "bilb");
defer outcome.deinit(allocator);
```

Build the self-contained executable at `impl/zig/bin/liff`:

```sh
make -C impl/zig
```

The Makefile targets are:

```sh
make -C impl/zig build             # generate and build bin/liff
make -C impl/zig test              # verify generated data and run tests
make -C impl/zig lint              # check Zig formatting
make -C impl/zig check             # tests plus formatting
make -C impl/zig clean             # remove Zig output and caches
```

Run the CLI:

```sh
impl/zig/bin/liff                  # random entry
impl/zig/bin/liff banteer          # exact lookup
impl/zig/bin/liff glutt            # confidence-qualified lookup
impl/zig/bin/liff 'bil*'           # unique glob lookup
impl/zig/bin/liff 'b*'             # multiple glob matches
impl/zig/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more characters and `?` exactly one. The complete product, algorithm,
API, and CLI contract is in `../SPECIFICATION.md`.

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target zig
python3 generate_json_code.py --target zig --check
```

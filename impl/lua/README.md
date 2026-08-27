# Lua implementation

This port separates the reusable `liff` modules from the CLI adapter. The
generated dictionary is packaged as a native Lua module, and the deployed
program performs no runtime file or network access outside its own bundle.

Lua 5.4 or later is required. No Lua rocks or third-party packages are needed.

Build the self-contained source bundle in `impl/lua/bin/`:

```sh
make -C impl/lua
```

Available Makefile targets are:

```sh
make -C impl/lua build    # generate, syntax-check, and package bin/liff
make -C impl/lua test     # verify generated data and run tests
make -C impl/lua lint     # syntax and source-format checks
make -C impl/lua check    # tests plus lint
make -C impl/lua clean    # remove bin/
```

Run the CLI:

```sh
impl/lua/bin/liff                  # random entry
impl/lua/bin/liff banteer          # exact lookup
impl/lua/bin/liff glutt            # confidence-qualified lookup
impl/lua/bin/liff 'bil*'           # unique glob lookup
impl/lua/bin/liff 'b*'             # multiple glob matches
impl/lua/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more characters and `?` exactly one. The complete product, algorithm,
API, and CLI contract is in `../SPECIFICATION.md`.

The reusable API is loaded with `require("liff")` after adding
`src/main/lua/?.lua` and `src/main/lua/?/init.lua` to `package.path`.

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target lua
python3 generate_json_code.py --target lua --check
```

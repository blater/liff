# TypeScript implementation

This port separates the reusable typed core from the CLI adapter. The generated
dictionary is compiled into the deployed JavaScript modules, which perform no
runtime file or network access.

Node.js 18 or later and TypeScript 5 or later are required to build. The
deployed program requires only Node.js and has no npm dependencies.

Build the self-contained launcher bundle in `impl/typescript/bin/`:

```sh
make -C impl/typescript
```

Available Makefile targets are:

```sh
make -C impl/typescript build    # generate, compile, and package bin/liff
make -C impl/typescript test     # verify generated data and run tests
make -C impl/typescript lint     # strict type and source-format checks
make -C impl/typescript check    # tests plus lint
make -C impl/typescript clean    # remove compiler output and bin/
```

Run the CLI:

```sh
impl/typescript/bin/liff                  # random entry
impl/typescript/bin/liff banteer          # exact lookup
impl/typescript/bin/liff glutt            # confidence-qualified lookup
impl/typescript/bin/liff 'bil*'           # unique glob lookup
impl/typescript/bin/liff 'b*'             # multiple glob matches
impl/typescript/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more characters and `?` exactly one. The complete product, algorithm,
API, and CLI contract is in `../SPECIFICATION.md`.

The source API is exported by `src/main/ts/liff.ts`; the compiled CommonJS API
is `build/app/liff.js` after compilation.

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target typescript
python3 generate_json_code.py --target typescript --check
```

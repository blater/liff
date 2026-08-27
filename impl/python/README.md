# Python implementation

This port separates the importable `liff` core package from its CLI adapter.
The release artifact is a single executable Python zipapp containing all source
code and generated dictionary data. It relies only on an installed Python 3.10+
runtime and reads no repository or runtime data files.

Build `impl/python/bin/liff`:

```sh
make -C impl/python
```

The Makefile targets are:

```sh
make -C impl/python build         # generate and build the zipapp
make -C impl/python test          # generator check and unittest suite
make -C impl/python lint          # parse every source and test module
make -C impl/python check         # tests plus lint
make -C impl/python clean         # remove bin/ and bytecode caches
```

Run the CLI:

```sh
impl/python/bin/liff              # random entry
impl/python/bin/liff banteer      # exact lookup
impl/python/bin/liff glutt        # confidence-qualified lookup
impl/python/bin/liff 'bil*'       # unique glob lookup
impl/python/bin/liff 'b*'         # multiple glob matches
impl/python/bin/liff '*'          # every entry
```

Quote glob patterns so the shell does not expand them. `*` matches zero or more
characters and `?` exactly one. The complete product, algorithm, API, and CLI
contract is in `../SPECIFICATION.md`.

Use the core package from the source tree during development:

```sh
PYTHONPATH=impl/python/src python3 -c \
  'import liff; print(liff.DEFAULT_DICTIONARY.search("bilb"))'
```

Generate or verify the embedded dictionary directly:

```sh
python3 generate_json_code.py --target python_impl
python3 generate_json_code.py --target python_impl --check
```

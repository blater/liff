# Go implementation

This port separates the reusable `liff` package from the `cmd/liff` command.
The generated dictionary is compiled into the executable, which performs no
runtime file or network access.

Go 1.22 or later is required.

Build the self-contained executable at `impl/go/bin/liff`:

```sh
make -C impl/go
```

The Makefile targets are:

```sh
make -C impl/go build             # generate and build bin/liff
make -C impl/go test              # verify generated data and run tests
make -C impl/go lint              # gofmt and go vet
make -C impl/go check             # tests plus lint
make -C impl/go clean             # remove Go output and bin/
```

Run the CLI:

```sh
impl/go/bin/liff                  # random entry
impl/go/bin/liff banteer          # exact lookup
impl/go/bin/liff glutt            # confidence-qualified lookup
impl/go/bin/liff 'bil*'           # unique glob lookup
impl/go/bin/liff 'b*'             # multiple glob matches
impl/go/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more characters and `?` exactly one. The complete product, algorithm,
API, and CLI contract is in `../SPECIFICATION.md`.

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target go
python3 generate_json_code.py --target go --check
```

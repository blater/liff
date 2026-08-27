# Java implementation

This port separates the reusable `liff.core` package from the `liff.cli`
command. The generated dictionary is compiled into the application JAR, which
performs no runtime file or network access.

Java 17 or later is required. No third-party libraries or build tools are
needed beyond the JDK.

Build the self-contained launcher bundle in `impl/java/bin/`:

```sh
make -C impl/java
```

The bundle contains the executable `liff` launcher and `liff.jar`; keep those
two files together. Available Makefile targets are:

```sh
make -C impl/java build             # generate and build bin/liff plus liff.jar
make -C impl/java test              # verify generated data and run tests
make -C impl/java lint              # check generated data and source formatting
make -C impl/java check             # tests plus lint
make -C impl/java clean             # remove compiler output and bin/
```

Run the CLI:

```sh
impl/java/bin/liff                  # random entry
impl/java/bin/liff banteer          # exact lookup
impl/java/bin/liff glutt            # confidence-qualified lookup
impl/java/bin/liff 'bil*'           # unique glob lookup
impl/java/bin/liff 'b*'             # multiple glob matches
impl/java/bin/liff '*'              # every entry
```

Quote glob patterns so the shell does not expand them as filenames. `*` matches
zero or more characters and `?` exactly one. The complete product, algorithm,
API, and CLI contract is in `../SPECIFICATION.md`.

The reusable API is exposed by `liff.core.Liff` and `liff.core.Dictionary`:

```java
Outcome outcome = Liff.dictionary().search("bilb");
List<Entry> entries = Liff.entries();
```

Generate or verify the embedded dictionary directly from the repository root:

```sh
python3 generate_json_code.py --target java
python3 generate_json_code.py --target java --check
```

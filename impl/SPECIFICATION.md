# Liff product and implementation specification

Status: normative. Version: 1.

This document defines the common product and implementation contract for every
Liff port. A port may use idiomatic names and types, but its observable results,
ordering, scores, generated data, and CLI output must conform to this document
and `search-cases.json`.

## 1. Product

Liff is a small, self-contained dictionary library and command-line program.
It provides:

- a uniformly random entry when invoked without a query;
- exact, prefix-assisted, and typo-tolerant headword lookup;
- `*` and `?` glob lookup;
- deterministic suggestions for ambiguous searches;
- structured access to parts of speech and cross-references.

The deployment bundle is `impl/LANGUAGE/bin/`, with `bin/liff` as its entry
point. It must contain the dictionary and all application code/dependencies. It
may depend on the language runtime documented by that port (for example, a JVM
or Python/Lua interpreter), and may include adjacent packaged files such as a
JAR, but it must not read outside `bin/`, use network resources, or require a
separate data file. A native single-file executable is not required.

All source, generated, API, and console text is UTF-8. CLI line endings are LF
(`U+000A`) on every platform. Definition text is returned verbatim apart from
the CLI's final LF. Search applies to headwords only; full-text search and
reference traversal are outside version 1.

## 2. Architecture

Each language implementation has three layers:

```text
liff.json -> generated language data -> pure core library -> CLI adapter
```

1. **Generated data** contains immutable entries and references in native
   language syntax.
2. **Core library** owns indexing, normalization, matching, scoring, ordering,
   and random selection. It performs no console I/O.
3. **CLI adapter** parses arguments, calls the core API, formats the outcome,
   and selects an exit status. It contains no search logic.

Keep the core library independently importable/testable and the CLI in a
separate package, module, or build target.

## 3. Source and generated data

`liff.json` is authoritative. Its relevant schema is:

```text
Document
  schema_version: 1
  title: string
  author: string
  source: string
  entries: object<canonical headword, EntryData>

EntryData
  part_of_speech: string | null
  definition: string
  references: Reference[]

Reference
  target: canonical headword
  relation: "q.v." | "see_also"
  label: spelling used in the definition
```

Required invariants:

- `schema_version` is exactly 1;
- canonical headwords are unique;
- version 1 canonical headwords contain only ASCII characters;
- normalized headwords are unique;
- every reference target is a canonical headword in `entries`;
- entry order is the textual member order of `entries` in the UTF-8
  `liff.json` file, not an implementation-defined JSON object order;
- entry and reference order is preserved in generated data;
- generated files are deterministic and carry a do-not-edit notice.

Add each port to `codegen-targets.json` with a language template and generated
output path. These commands are the generation interface:

```sh
python3 generate_json_code.py --target LANGUAGE
python3 generate_json_code.py --target LANGUAGE --check
```

The first command writes native source. The second must fail if committed
generated source is stale and must not modify files.

Each target must use a correct target-language literal encoder; JSON string
syntax must not be assumed to be valid source syntax. Add a renderer filter when
the existing filters cannot encode the target language. Generator tests must
prove that quotes, backslashes, controls, LF/CR/tab, null values, and non-ASCII
UTF-8 text compile or load to their original values.

Generated runtime data must expose title, author, entries, entry fields, and
references. `schema_version` and `source` are build-time validation metadata and
need not be exposed by the runtime library.

## 4. Core model and API

Expose language-idiomatic equivalents of these immutable values:

```text
Entry       { word, part_of_speech?, definition, references[] }
Reference   { target, relation, label }
Score       integer in [0, 1000]
Suggestion  { entry, confidence: medium | low, score }
Found       { entry, kind, score? }

Request = Random | Search(query)
MatchKind = random | exact | glob | high_confidence
Outcome = Found | DidYouMean(suggestions[]) | NotFound
```

The public core operations are:

```text
entries()                 -> all entries in source order
random()                  -> entry?; uniform over all entries
search(query)             -> Outcome
resolve(Random|Search)    -> Outcome
```

Random results have no score. Exact and glob results score 1000. The core
returns every suggestion; CLI display truncation must not affect the core API.
An empty dictionary returns `NotFound`/no entry for random selection.

Ports must provide an internal or public deterministic
`random_with(choose_index)` seam. The chooser receives the exclusive upper
bound; an out-of-range result returns no entry. Tests may also use an internal,
test-only constructor to create a dictionary from supplied entries. Neither seam
is required to be a stable public product API.

## 5. Search dispatch

For `Search(query)`, apply the first matching branch:

1. If the original query contains `*` or `?`, perform glob search (section 7).
2. Normalize the query. If empty, return `NotFound`.
3. If a normalized headword equals the query, return `Found(exact, 1000)`.
4. Perform fuzzy search (sections 8–9).

An empty search query is not a random request.

## 6. Normalization

Version 1 normalization is deliberately ASCII-only so it is identical in every
UTF-8 runtime. Normalize queries and headwords as follows:

1. Convert ASCII `A`–`Z` to `a`–`z`.
2. Remove straight apostrophe (`U+0027`) and curly apostrophe (`U+2019`)
   without inserting a separator.
3. Retain ASCII `a`–`z` and `0`–`9`.
4. Replace every other run of Unicode code points with one ASCII space
   (`U+0020`). Non-ASCII letters are therefore separators.
5. Remove leading and trailing separators.

Public string values and CLI arguments are assumed to be valid UTF-8; invalid
byte sequences are outside the version 1 contract. All lengths and edits are
measured in Unicode code points, not bytes, UTF-16 code units, or grapheme
clusters. Normalized headwords contain only ASCII in version 1.

Examples:

```text
"  SYMOND'S---YAT  " -> "symonds yat"
"Sutton\tand   Cheam" -> "sutton and cheam"
"café"                  -> "caf"
"Straße"                -> "stra e"
```

Build an index sorted by normalized headword. Reject duplicate normalized
headwords.

## 7. Glob search

Normalize a glob pattern using section 6 while preserving `*` and `?`.
Collapse consecutive `*` characters.

- `*` matches zero or more Unicode code points.
- `?` matches exactly one Unicode code point.
- Matching covers the entire normalized headword.
- Character classes and escaping are not supported.

Return:

- zero matches: `NotFound`;
- one match: `Found(glob, 1000)`;
- multiple matches: `DidYouMean`, sorted by normalized headword ascending;
  every suggestion has medium confidence and score 1000.

Every ascending string comparison in this specification is lexicographic by
decoded Unicode scalar value, with no locale collation. This applies to glob
ordering and canonical-headword tie-breaking. UTF-8 byte ordering is equivalent
for valid UTF-8 strings; UTF-16 code-unit ordering is not.

A dynamic-programming matcher is sufficient: for pattern character `*`, cell
`(i,j)` is true when `(i-1,j)` or `(i,j-1)` is true; for `?` or an equal literal,
it is true when `(i-1,j-1)` is true. Initialize only `(0,0)` as true.

## 8. Fuzzy score

Use optimal-string-alignment Damerau-Levenshtein distance. Insert, delete, and
substitute cost one; one adjacent transposition costs one. This is OSA distance,
not unrestricted Damerau-Levenshtein.

For normalized query `q` and candidate `c`:

```text
maximum = max(code_point_length(q), code_point_length(c))
edit_score = floor((maximum - OSA_distance(q, c)) * 1000 / maximum)
```

Then apply prefix floors when `q` has at least four code points:

```text
if c starts with q + " ": score = max(edit_score, 900)
else if c starts with q:  score = max(edit_score, 750)
else:                     score = edit_score
```

Examples:

```text
score("banteeer", "banteer")    = 875
score("lif", "liff")            = 750
score("bilb", "bilbster")       = 750  # partial-prefix floor
score("glutt", "glutt lodge")   = 900  # complete-token floor
```

Rank candidates by score descending, then canonical headword ascending using
the comparator defined in section 7.

## 9. Fuzzy outcome policy

Constants:

```text
QUALIFYING_SCORE = 700       # inclusive
LOW_SUGGESTION_COUNT = 2
PARTIAL_PREFIX_SCORE = 750
TOKEN_PREFIX_SCORE = 900
PREFIX_MIN_CODE_POINTS = 4
```

After ranking:

1. Let `qualified` be every candidate scoring at least 700.
2. If `qualified` contains exactly one candidate, return
   `Found(high_confidence, score)`.
3. If it contains two or more, return `DidYouMean` containing all qualified
   candidates as medium confidence, followed by the top two candidates below
   700 as low confidence.
4. If it is empty, return `NotFound`.

Uniqueness—not a lead margin—permits automatic fuzzy selection.

## 10. CLI contract

### Arguments

- No positional arguments issue `Random`.
- Positional arguments are joined with one ASCII space and issued as one
  `Search` query.
- `-h` and `--help` print usage.
- Any other argument beginning with `-` is invalid usage.
- Shell wildcards must be quoted, for example `liff 'bil*'`.

### Output

All normal output goes to stdout as UTF-8 and ends with LF.

```text
Found:
<canonical headword>
<definition>

DidYouMean:
Did you mean?
<canonical headword 1>
<canonical headword 2>

NotFound:
No definition found for "<original joined query>".
```

For up to 11 suggestions, print all suggestions. For 12 or more, print the first
10 followed by:

```text
and N others
```

Here `N` is the total suggestion count minus 10. The exactly-11 exception is
intentional.

### Exit status

```text
0  Found, including random, exact, glob, and high-confidence
1  DidYouMean or NotFound
2  invalid CLI usage
```

Usage errors go to stderr as UTF-8 with LF endings. Do not print part-of-speech
labels, scores, confidence labels, or references in normal CLI results.

## 11. Build contract

Each port lives in `impl/LANGUAGE/` and should provide:

- an idiomatic core library and separate CLI target;
- a generated dictionary module compiled into the deliverable;
- a `Makefile` with `build`, `test`, `lint`, `check`, and `clean` targets;
- a release launcher or executable at `impl/LANGUAGE/bin/liff`;
- a concise README with language-specific prerequisites and commands.

`build` regenerates dictionary source before compiling. `check` verifies that
generated source is current, then runs tests, formatting checks, and available
static analysis. `clean` removes compiler output and `bin/`, but not source
inputs.

`impl/LANGUAGE/bin/liff` may be a native executable or a launcher using the
documented language runtime. The `bin/` bundle must package the generated
dictionary and all non-runtime application dependencies. Prefer the language
standard library.

## 12. Conformance

Every port must consume both `impl/search-cases.json` and
`impl/algorithm-cases.json` in tests rather than copying those cases into
language-specific fixtures. They are build-time test artifacts only: neither
file may be embedded in or read by the deployed `bin/liff` artifact.

`search-cases.json` specifies dictionary outcomes. `algorithm-cases.json`
specifies normalization, glob normalization/matching, OSA distance and score,
prefix floors, and scalar-value ordering. A port must additionally test:

- all generated entries and metadata are present;
- every structured reference resolves to exactly one entry;
- random selection is bounded and can be tested with an injected chooser/RNG;
- CLI output and exit status for random, found, ambiguous, and not-found cases;
- glob display boundaries: one, 11, 12 or more, and `*`.

A port is complete when its generator check, core tests, CLI tests, formatter,
static analysis, release build, and direct smoke tests all pass.

## 13. Porting sequence

1. Add the language template, any required literal-encoder filter and tests, and
   the `codegen-targets.json` target.
2. Generate immutable native data types and constants.
3. Implement the core model, normalization, index, glob matcher, and fuzzy
   matcher without I/O.
4. Load `search-cases.json` and `algorithm-cases.json` as build-time-only shared
   conformance suites.
5. Implement the thin CLI and golden-output tests.
6. Add the Makefile, build the self-contained artifact, and smoke-test it from
   `impl/LANGUAGE/bin/liff`.

The Rust implementation is the reference implementation. This specification
and the shared conformance cases take precedence if code and documentation ever
disagree.

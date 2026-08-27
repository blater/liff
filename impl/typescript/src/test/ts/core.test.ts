import {
    DEFAULT_DICTIONARY,
    Dictionary,
    MatchKind,
    NOT_FOUND,
    TITLE,
    AUTHOR,
    candidateScore,
    compareCodePoints,
    damerauLevenshtein,
    entries,
    globMatches,
    makeEntry,
    normalize,
    normalizeGlob,
    similarityScore,
    type DidYouMean,
    type Found,
    type Outcome,
} from "../../main/ts/liff";

declare function require(identifier: string): unknown;
declare const process: { readonly argv: readonly string[] };
declare const console: { log(text: string): void };

const fs = require("node:fs") as {
    readFileSync(path: string, encoding: "utf8"): string;
};
const nodeBuffer = require("node:buffer") as {
    readonly Buffer: {
        from(value: string, encoding: "base64"): {
            toString(encoding: "utf8"): string;
        };
    };
};

interface SearchCase {
    readonly query: string;
    readonly outcome: "found" | "did_you_mean" | "not_found";
    readonly kind?: string;
    readonly word?: string;
    readonly score?: number;
    readonly suggestions?: readonly {
        readonly word: string;
        readonly confidence: string;
        readonly score: number;
    }[];
}

interface SearchContract {
    readonly schema_version: number;
    readonly cases: readonly SearchCase[];
}

interface PairCase {
    readonly input: string;
    readonly output: string;
}

interface AlgorithmContract {
    readonly schema_version: number;
    readonly normalization: readonly PairCase[];
    readonly glob_normalization: readonly PairCase[];
    readonly edit_scores: readonly {
        readonly left: string;
        readonly right: string;
        readonly distance: number;
        readonly score: number;
    }[];
    readonly candidate_scores: readonly {
        readonly query: string;
        readonly candidate: string;
        readonly score: number;
    }[];
    readonly glob_matches: readonly {
        readonly pattern: string;
        readonly candidate: string;
        readonly matches: boolean;
    }[];
    readonly ordering: readonly {
        readonly input: readonly string[];
        readonly ascending: readonly string[];
    }[];
}

interface SourceReference {
    readonly target: string;
    readonly relation: string;
    readonly label: string;
}

interface SourceEntry {
    readonly part_of_speech: string | null;
    readonly definition: string;
    readonly references: readonly SourceReference[];
}

interface SourceDocument {
    readonly schema_version: number;
    readonly definition_encoding: "base64-utf8";
    readonly title: string;
    readonly author: string;
    readonly entries: Readonly<Record<string, SourceEntry>>;
}

const root = process.argv[2];
if (root === undefined) {
    throw new Error("repository root argument is required");
}

function readJson<T>(path: string): T {
    return JSON.parse(fs.readFileSync(path, "utf8")) as T;
}

function check(condition: boolean, message: string): asserts condition {
    if (!condition) {
        throw new Error(message);
    }
}

function equal<T>(actual: T, expected: T, message: string): void {
    if (!Object.is(actual, expected)) {
        throw new Error(`${message}: got ${String(actual)}, want ${String(expected)}`);
    }
}

function deepEqual(actual: unknown, expected: unknown, message: string): void {
    const actualJson = JSON.stringify(actual);
    const expectedJson = JSON.stringify(expected);
    if (actualJson !== expectedJson) {
        throw new Error(`${message}: got ${actualJson}, want ${expectedJson}`);
    }
}

function sharedSearchCases(): void {
    const contract = readJson<SearchContract>(`${root}/impl/search-cases.json`);
    equal(contract.schema_version, 1, "search schema version");
    for (const testCase of contract.cases) {
        const outcome: Outcome = DEFAULT_DICTIONARY.search(testCase.query);
        if (testCase.outcome === "found") {
            check(outcome.type === "found", `expected found for ${testCase.query}`);
            equal(outcome.entry.word, testCase.word, "found word");
            equal(outcome.kind, testCase.kind as MatchKind, "found kind");
            if (testCase.score !== undefined) {
                equal(outcome.score, testCase.score, "found score");
            }
        } else if (testCase.outcome === "did_you_mean") {
            check(outcome.type === "did_you_mean",
                `expected did-you-mean for ${testCase.query}`);
            const actual = outcome.suggestions.map((item) => ({
                word: item.entry.word,
                confidence: item.confidence,
                score: item.score,
            }));
            deepEqual(actual, testCase.suggestions, "suggestions");
        } else {
            check(outcome === NOT_FOUND, `expected not-found for ${testCase.query}`);
        }
    }
}

function sharedAlgorithmCases(): void {
    const contract = readJson<AlgorithmContract>(`${root}/impl/algorithm-cases.json`);
    equal(contract.schema_version, 1, "algorithm schema version");
    for (const testCase of contract.normalization) {
        equal(normalize(testCase.input), testCase.output, "normalization");
    }
    for (const testCase of contract.glob_normalization) {
        equal(normalizeGlob(testCase.input), testCase.output, "glob normalization");
    }
    for (const testCase of contract.edit_scores) {
        equal(damerauLevenshtein(testCase.left, testCase.right), testCase.distance,
            "OSA distance");
        equal(similarityScore(testCase.left, testCase.right), testCase.score,
            "similarity score");
    }
    for (const testCase of contract.candidate_scores) {
        equal(candidateScore(testCase.query, testCase.candidate), testCase.score,
            "candidate score");
    }
    for (const testCase of contract.glob_matches) {
        equal(globMatches(testCase.pattern, testCase.candidate), testCase.matches,
            "glob match");
    }
    for (const testCase of contract.ordering) {
        const actual = [...testCase.input].sort(compareCodePoints);
        deepEqual(actual, testCase.ascending, "scalar ordering");
    }
}

function generatedSourceAndReferences(): void {
    const source = readJson<SourceDocument>(`${root}/liff.json`);
    equal(source.schema_version, 2, "source schema version");
    equal(source.definition_encoding, "base64-utf8", "definition encoding");
    equal(TITLE, source.title, "title");
    equal(AUTHOR, source.author, "author");
    const generatedEntries = entries();
    const sourceEntries = Object.entries(source.entries);
    equal(generatedEntries.length, sourceEntries.length, "entry count");

    sourceEntries.forEach(([word, wanted], index) => {
        const actual = generatedEntries[index]!;
        equal(actual.word, word, "canonical word");
        equal(actual.partOfSpeech, wanted.part_of_speech, "part of speech");
        equal(
            actual.definition,
            nodeBuffer.Buffer.from(wanted.definition, "base64").toString("utf8"),
            "definition",
        );
        deepEqual(actual.references, wanted.references, "references");
        for (const reference of actual.references) {
            const resolved = DEFAULT_DICTIONARY.search(reference.target);
            check(resolved.type === "found", `unresolved reference ${reference.target}`);
            equal(resolved.kind, "exact", "reference match kind");
            equal(resolved.entry.word, reference.target, "reference target");
        }
    });
}

function randomSeamAndValidation(): void {
    const allEntries = DEFAULT_DICTIONARY.entries();
    equal(DEFAULT_DICTIONARY.randomWith(() => 0), allEntries[0], "first random entry");
    equal(DEFAULT_DICTIONARY.randomWith((bound) => bound - 1), allEntries.at(-1),
        "last random entry");
    equal(DEFAULT_DICTIONARY.randomWith((bound) => bound), undefined,
        "out-of-range random entry");
    equal(new Dictionary([]).randomWith(() => 0), undefined, "empty dictionary");

    const first = makeEntry("A-B", null, "first", []);
    const second = makeEntry("A B", null, "second", []);
    let rejected = false;
    try {
        new Dictionary([first, second]);
    } catch (error: unknown) {
        rejected = error instanceof Error && error.message.includes("duplicate");
    }
    check(rejected, "duplicate normalized headwords were accepted");

    check(Object.isFrozen(allEntries), "entry collection is not frozen");
    check(Object.isFrozen(allEntries[0]!), "entry is not frozen");
    check(Object.isFrozen(allEntries[0]!.references), "references are not frozen");
}

sharedSearchCases();
sharedAlgorithmCases();
generatedSourceAndReferences();
randomSeamAndValidation();
console.log("core.test: OK");

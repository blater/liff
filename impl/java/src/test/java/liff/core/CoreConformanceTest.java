package liff.core;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import liff.testutil.Json;

/** Dependency-free conformance runner for the Java core. */
public final class CoreConformanceTest {
    private CoreConformanceTest() {}

    public static void main(String[] arguments) throws Exception {
        sharedSearchCases();
        sharedAlgorithmCases();
        generatedSourceAndReferences();
        randomSeamAndDictionaryValidation();
        System.out.println("CoreConformanceTest: OK");
    }

    private static Path fixture(String name) {
        return Path.of(System.getProperty("liff.repoRoot"), "impl", name);
    }

    private static void sharedSearchCases() throws Exception {
        Map<String, Object> contract = object(Json.read(fixture("search-cases.json")));
        equal(1L, contract.get("schema_version"), "search schema version");
        for (Object rawCase : array(contract.get("cases"))) {
            Map<String, Object> testCase = object(rawCase);
            Outcome outcome = Liff.dictionary().search(string(testCase.get("query")));
            String wantedOutcome = string(testCase.get("outcome"));
            switch (wantedOutcome) {
                case "found" -> {
                    check(outcome instanceof Found, "expected Found for " + testCase);
                    Found found = (Found) outcome;
                    equal(testCase.get("word"), found.entry().word(), "found word");
                    equal(testCase.get("kind"), found.kind().wireName(), "match kind");
                    if (testCase.get("score") != null) {
                        equal(number(testCase.get("score")), found.score().orElseThrow(), "score");
                    }
                }
                case "did_you_mean" -> {
                    check(outcome instanceof DidYouMean, "expected DidYouMean for " + testCase);
                    List<Object> wanted = array(testCase.get("suggestions"));
                    List<Suggestion> actual = ((DidYouMean) outcome).suggestions();
                    equal(wanted.size(), actual.size(), "suggestion count");
                    for (int index = 0; index < wanted.size(); index++) {
                        Map<String, Object> expected = object(wanted.get(index));
                        Suggestion suggestion = actual.get(index);
                        equal(expected.get("word"), suggestion.entry().word(), "suggestion word");
                        equal(expected.get("confidence"), suggestion.confidence().wireName(),
                                "suggestion confidence");
                        equal(number(expected.get("score")), suggestion.score(), "suggestion score");
                    }
                }
                case "not_found" -> check(outcome == NotFound.INSTANCE,
                        "expected NotFound for " + testCase);
                default -> throw new AssertionError("unknown outcome " + wantedOutcome);
            }
        }
    }

    private static void sharedAlgorithmCases() throws Exception {
        Map<String, Object> contract = object(Json.read(fixture("algorithm-cases.json")));
        equal(1L, contract.get("schema_version"), "algorithm schema version");
        for (Object raw : array(contract.get("normalization"))) {
            Map<String, Object> testCase = object(raw);
            equal(testCase.get("output"), Normalizer.normalize(string(testCase.get("input"))),
                    "normalization");
        }
        for (Object raw : array(contract.get("glob_normalization"))) {
            Map<String, Object> testCase = object(raw);
            equal(testCase.get("output"), Normalizer.normalizeGlob(string(testCase.get("input"))),
                    "glob normalization");
        }
        for (Object raw : array(contract.get("edit_scores"))) {
            Map<String, Object> testCase = object(raw);
            String left = string(testCase.get("left"));
            String right = string(testCase.get("right"));
            equal(number(testCase.get("distance")), Dictionary.damerauLevenshtein(left, right),
                    "OSA distance");
            equal(number(testCase.get("score")), Dictionary.similarityScore(left, right),
                    "similarity score");
        }
        for (Object raw : array(contract.get("candidate_scores"))) {
            Map<String, Object> testCase = object(raw);
            equal(number(testCase.get("score")), Dictionary.candidateScore(
                    string(testCase.get("query")), string(testCase.get("candidate"))),
                    "candidate score");
        }
        for (Object raw : array(contract.get("glob_matches"))) {
            Map<String, Object> testCase = object(raw);
            equal(testCase.get("matches"), Dictionary.globMatches(
                    string(testCase.get("pattern")), string(testCase.get("candidate"))),
                    "glob match");
        }
        for (Object raw : array(contract.get("ordering"))) {
            Map<String, Object> testCase = object(raw);
            ArrayList<String> actual = strings(array(testCase.get("input")));
            actual.sort(Dictionary::compareCodePoints);
            equal(strings(array(testCase.get("ascending"))), actual, "scalar ordering");
        }
    }

    private static void generatedSourceAndReferences() throws Exception {
        Map<String, Object> root = object(Json.read(Path.of(
                System.getProperty("liff.repoRoot"), "liff.json")));
        equal(2L, root.get("schema_version"), "source schema version");
        equal("base64-utf8", root.get("definition_encoding"), "definition encoding");
        equal(root.get("title"), Liff.TITLE, "title");
        equal(root.get("author"), Liff.AUTHOR, "author");
        Map<String, Object> sourceEntries = object(root.get("entries"));
        equal(sourceEntries.size(), Liff.entries().size(), "entry count");

        int index = 0;
        for (Map.Entry<String, Object> source : sourceEntries.entrySet()) {
            Entry actual = Liff.entries().get(index++);
            Map<String, Object> expected = object(source.getValue());
            equal(source.getKey(), actual.word(), "canonical word");
            String expectedDefinition = new String(
                    Base64.getDecoder().decode(string(expected.get("definition"))),
                    StandardCharsets.UTF_8);
            equal(expectedDefinition, actual.definition(), "definition");
            Optional<String> part = expected.get("part_of_speech") == null
                    ? Optional.empty()
                    : Optional.of(string(expected.get("part_of_speech")));
            equal(part, actual.partOfSpeech(), "part of speech");
            List<Object> sourceReferences = array(expected.get("references"));
            equal(sourceReferences.size(), actual.references().size(), "reference count");
            for (int referenceIndex = 0; referenceIndex < sourceReferences.size(); referenceIndex++) {
                Map<String, Object> wanted = object(sourceReferences.get(referenceIndex));
                Reference reference = actual.references().get(referenceIndex);
                equal(wanted.get("target"), reference.target(), "reference target");
                equal(wanted.get("relation"), reference.relation(), "reference relation");
                equal(wanted.get("label"), reference.label(), "reference label");
                Outcome resolved = Liff.dictionary().search(reference.target());
                check(resolved instanceof Found, "unresolved reference " + reference.target());
                equal(reference.target(), ((Found) resolved).entry().word(), "resolved reference");
                equal(MatchKind.EXACT, ((Found) resolved).kind(), "reference match kind");
            }
        }
    }

    private static void randomSeamAndDictionaryValidation() {
        Dictionary dictionary = Liff.dictionary();
        equal(dictionary.entries().get(0), dictionary.randomWith(bound -> 0).orElseThrow(),
                "first random entry");
        equal(dictionary.entries().get(dictionary.entries().size() - 1),
                dictionary.randomWith(bound -> bound - 1).orElseThrow(), "last random entry");
        check(dictionary.randomWith(bound -> bound).isEmpty(), "out-of-range chooser");
        check(new Dictionary(List.of()).randomWith(bound -> 0).isEmpty(), "empty dictionary");

        Entry first = new Entry("A-B", Optional.empty(), "first", List.of());
        Entry second = new Entry("A B", Optional.empty(), "second", List.of());
        try {
            new Dictionary(List.of(first, second));
            throw new AssertionError("duplicate normalized headwords were accepted");
        } catch (IllegalArgumentException expected) {
            check(expected.getMessage().contains("duplicate"), "duplicate error message");
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> array(Object value) {
        return (List<Object>) value;
    }

    private static String string(Object value) {
        return (String) value;
    }

    private static int number(Object value) {
        return Math.toIntExact((Long) value);
    }

    private static ArrayList<String> strings(List<Object> values) {
        ArrayList<String> result = new ArrayList<>(values.size());
        for (Object value : values) {
            result.add(string(value));
        }
        return result;
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static void equal(Object expected, Object actual, String message) {
        if (!expected.equals(actual)) {
            throw new AssertionError(message + ": got " + actual + ", want " + expected);
        }
    }
}

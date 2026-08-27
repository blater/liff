package liff.core;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.IntUnaryOperator;

/** An indexed immutable dictionary and its lookup operations. */
public final class Dictionary {
    public static final int PERFECT_SCORE = 1000;
    public static final int QUALIFYING_SCORE = 700;
    public static final int LOW_SUGGESTION_COUNT = 2;
    public static final int TOKEN_PREFIX_SCORE = 900;
    public static final int PARTIAL_PREFIX_SCORE = 750;
    public static final int PREFIX_MIN_CODE_POINTS = 4;

    private record IndexedEntry(Entry entry, String normalized) {}
    private record ScoredCandidate(Entry entry, int score) {}

    private static final Comparator<ScoredCandidate> CANDIDATE_ORDER = (left, right) -> {
        int scoreOrder = Integer.compare(right.score(), left.score());
        return scoreOrder != 0 ? scoreOrder : compareCodePoints(left.entry().word(), right.entry().word());
    };

    private final List<Entry> entries;
    private final List<IndexedEntry> index;

    public Dictionary(List<Entry> entries) {
        this.entries = List.copyOf(entries);
        ArrayList<IndexedEntry> mutableIndex = new ArrayList<>(this.entries.size());
        for (Entry entry : this.entries) {
            mutableIndex.add(new IndexedEntry(entry, Normalizer.normalize(entry.word())));
        }
        mutableIndex.sort((left, right) -> compareCodePoints(left.normalized(), right.normalized()));
        for (int position = 1; position < mutableIndex.size(); position++) {
            if (mutableIndex.get(position - 1).normalized()
                    .equals(mutableIndex.get(position).normalized())) {
                throw new IllegalArgumentException("dictionary contains duplicate normalized headwords");
            }
        }
        this.index = List.copyOf(mutableIndex);
    }

    /** Returns every entry in canonical source order. */
    public List<Entry> entries() {
        return entries;
    }

    /** Selects one entry uniformly, or returns empty for an empty dictionary. */
    public Optional<Entry> random() {
        return randomWith(bound -> ThreadLocalRandom.current().nextInt(bound));
    }

    /** Deterministic random-selection seam; the chooser receives an exclusive bound. */
    public Optional<Entry> randomWith(IntUnaryOperator chooseIndex) {
        if (entries.isEmpty()) {
            return Optional.empty();
        }
        int chosen = chooseIndex.applyAsInt(entries.size());
        if (chosen < 0 || chosen >= entries.size()) {
            return Optional.empty();
        }
        return Optional.of(entries.get(chosen));
    }

    /** Resolves a random-selection or search request. */
    public Outcome resolve(Request request) {
        Objects.requireNonNull(request, "request");
        if (request instanceof SearchRequest search) {
            return search(search.query());
        }
        return random()
                .<Outcome>map(entry -> new Found(entry, MatchKind.RANDOM, OptionalInt.empty()))
                .orElse(NotFound.INSTANCE);
    }

    /** Resolves a request with an injected random chooser for deterministic callers. */
    public Outcome resolveWith(Request request, IntUnaryOperator chooseIndex) {
        Objects.requireNonNull(request, "request");
        Objects.requireNonNull(chooseIndex, "chooseIndex");
        if (request instanceof SearchRequest search) {
            return search(search.query());
        }
        return randomWith(chooseIndex)
                .<Outcome>map(entry -> new Found(entry, MatchKind.RANDOM, OptionalInt.empty()))
                .orElse(NotFound.INSTANCE);
    }

    /** Searches for an exact, glob, confidence-qualified, or ambiguous headword. */
    public Outcome search(String query) {
        if (query.indexOf('*') >= 0 || query.indexOf('?') >= 0) {
            return searchGlob(query);
        }

        String normalizedQuery = Normalizer.normalize(query);
        if (normalizedQuery.isEmpty()) {
            return NotFound.INSTANCE;
        }

        int exactPosition = lowerBound(normalizedQuery);
        if (exactPosition < index.size()
                && index.get(exactPosition).normalized().equals(normalizedQuery)) {
            return new Found(index.get(exactPosition).entry(), MatchKind.EXACT,
                    OptionalInt.of(PERFECT_SCORE));
        }

        ArrayList<ScoredCandidate> ranked = new ArrayList<>(index.size());
        for (IndexedEntry indexed : index) {
            ranked.add(new ScoredCandidate(indexed.entry(),
                    candidateScore(normalizedQuery, indexed.normalized())));
        }
        ranked.sort(CANDIDATE_ORDER);

        int qualified = 0;
        while (qualified < ranked.size() && ranked.get(qualified).score() >= QUALIFYING_SCORE) {
            qualified++;
        }
        if (qualified == 1) {
            ScoredCandidate candidate = ranked.get(0);
            return new Found(candidate.entry(), MatchKind.HIGH_CONFIDENCE,
                    OptionalInt.of(candidate.score()));
        }
        if (qualified == 0) {
            return NotFound.INSTANCE;
        }

        int suggestionCount = Math.min(ranked.size(), qualified + LOW_SUGGESTION_COUNT);
        ArrayList<Suggestion> suggestions = new ArrayList<>(suggestionCount);
        for (int position = 0; position < qualified; position++) {
            ScoredCandidate candidate = ranked.get(position);
            suggestions.add(new Suggestion(candidate.entry(), Confidence.MEDIUM, candidate.score()));
        }
        for (int position = qualified; position < suggestionCount; position++) {
            ScoredCandidate candidate = ranked.get(position);
            suggestions.add(new Suggestion(candidate.entry(), Confidence.LOW, candidate.score()));
        }
        return new DidYouMean(suggestions);
    }

    private Outcome searchGlob(String query) {
        String pattern = Normalizer.normalizeGlob(query);
        if (pattern.isEmpty()) {
            return NotFound.INSTANCE;
        }
        ArrayList<Entry> matches = new ArrayList<>();
        for (IndexedEntry indexed : index) {
            if (globMatches(pattern, indexed.normalized())) {
                matches.add(indexed.entry());
            }
        }
        if (matches.isEmpty()) {
            return NotFound.INSTANCE;
        }
        if (matches.size() == 1) {
            return new Found(matches.get(0), MatchKind.GLOB, OptionalInt.of(PERFECT_SCORE));
        }
        return new DidYouMean(matches.stream()
                .map(entry -> new Suggestion(entry, Confidence.MEDIUM, PERFECT_SCORE))
                .toList());
    }

    private int lowerBound(String query) {
        int lower = 0;
        int upper = index.size();
        while (lower < upper) {
            int middle = lower + (upper - lower) / 2;
            if (compareCodePoints(index.get(middle).normalized(), query) < 0) {
                lower = middle + 1;
            } else {
                upper = middle;
            }
        }
        return lower;
    }

    static int similarityScore(String left, String right) {
        int maximum = Math.max(left.codePointCount(0, left.length()),
                right.codePointCount(0, right.length()));
        if (maximum == 0) {
            return PERFECT_SCORE;
        }
        int retained = Math.max(0, maximum - damerauLevenshtein(left, right));
        return retained * PERFECT_SCORE / maximum;
    }

    static int candidateScore(String query, String candidate) {
        int editScore = similarityScore(query, candidate);
        if (query.codePointCount(0, query.length()) < PREFIX_MIN_CODE_POINTS) {
            return editScore;
        }
        if (candidate.startsWith(query + " ")) {
            return Math.max(editScore, TOKEN_PREFIX_SCORE);
        }
        if (candidate.startsWith(query)) {
            return Math.max(editScore, PARTIAL_PREFIX_SCORE);
        }
        return editScore;
    }

    static boolean globMatches(String pattern, String candidate) {
        int[] patternPoints = pattern.codePoints().toArray();
        int[] candidatePoints = candidate.codePoints().toArray();
        boolean[] previous = new boolean[candidatePoints.length + 1];
        previous[0] = true;
        for (int patternPoint : patternPoints) {
            boolean[] current = new boolean[candidatePoints.length + 1];
            if (patternPoint == '*') {
                current[0] = previous[0];
            }
            for (int position = 1; position <= candidatePoints.length; position++) {
                current[position] = switch (patternPoint) {
                    case '*' -> previous[position] || current[position - 1];
                    case '?' -> previous[position - 1];
                    default -> previous[position - 1]
                            && patternPoint == candidatePoints[position - 1];
                };
            }
            previous = current;
        }
        return previous[candidatePoints.length];
    }

    static int damerauLevenshtein(String left, String right) {
        int[] leftPoints = left.codePoints().toArray();
        int[] rightPoints = right.codePoints().toArray();
        int[] previousPrevious = new int[rightPoints.length + 1];
        int[] previous = new int[rightPoints.length + 1];
        for (int position = 0; position < previous.length; position++) {
            previous[position] = position;
        }
        for (int leftIndex = 0; leftIndex < leftPoints.length; leftIndex++) {
            int[] current = new int[rightPoints.length + 1];
            current[0] = leftIndex + 1;
            for (int rightIndex = 0; rightIndex < rightPoints.length; rightIndex++) {
                int column = rightIndex + 1;
                int substitution = leftPoints[leftIndex] == rightPoints[rightIndex] ? 0 : 1;
                current[column] = Math.min(
                        Math.min(current[column - 1] + 1, previous[column] + 1),
                        previous[column - 1] + substitution);
                if (leftIndex > 0 && rightIndex > 0
                        && leftPoints[leftIndex] == rightPoints[rightIndex - 1]
                        && leftPoints[leftIndex - 1] == rightPoints[rightIndex]) {
                    current[column] = Math.min(current[column],
                            previousPrevious[column - 2] + 1);
                }
            }
            previousPrevious = previous;
            previous = current;
        }
        return previous[rightPoints.length];
    }

    static int compareCodePoints(String left, String right) {
        int leftOffset = 0;
        int rightOffset = 0;
        while (leftOffset < left.length() && rightOffset < right.length()) {
            int leftPoint = left.codePointAt(leftOffset);
            int rightPoint = right.codePointAt(rightOffset);
            if (leftPoint != rightPoint) {
                return Integer.compare(leftPoint, rightPoint);
            }
            leftOffset += Character.charCount(leftPoint);
            rightOffset += Character.charCount(rightPoint);
        }
        return Integer.compare(left.length() - leftOffset, right.length() - rightOffset);
    }
}

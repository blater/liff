package liff.core;

import java.util.Objects;
import java.util.OptionalInt;

/** A definitive random, exact, glob, or high-confidence result. */
public record Found(Entry entry, MatchKind kind, OptionalInt score) implements Outcome {
    public Found {
        Objects.requireNonNull(entry, "entry");
        Objects.requireNonNull(kind, "kind");
        Objects.requireNonNull(score, "score");
        if (score.isPresent() && (score.getAsInt() < 0 || score.getAsInt() > 1000)) {
            throw new IllegalArgumentException("score must be between 0 and 1000");
        }
    }
}

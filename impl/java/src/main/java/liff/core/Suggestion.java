package liff.core;

import java.util.Objects;

/** One ordered candidate in an ambiguous lookup result. */
public record Suggestion(Entry entry, Confidence confidence, int score) {
    public Suggestion {
        Objects.requireNonNull(entry, "entry");
        Objects.requireNonNull(confidence, "confidence");
        if (score < 0 || score > 1000) {
            throw new IllegalArgumentException("score must be between 0 and 1000");
        }
    }
}

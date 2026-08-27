package liff.core;

/** The reason a definitive entry was returned. */
public enum MatchKind {
    RANDOM("random"),
    EXACT("exact"),
    GLOB("glob"),
    HIGH_CONFIDENCE("high_confidence");

    private final String wireName;

    MatchKind(String wireName) {
        this.wireName = wireName;
    }

    public String wireName() {
        return wireName;
    }
}

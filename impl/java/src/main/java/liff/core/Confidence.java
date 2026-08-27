package liff.core;

/** Effective confidence assigned to a suggested candidate. */
public enum Confidence {
    MEDIUM("medium"),
    LOW("low");

    private final String wireName;

    Confidence(String wireName) {
        this.wireName = wireName;
    }

    public String wireName() {
        return wireName;
    }
}

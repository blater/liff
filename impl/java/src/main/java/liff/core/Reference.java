package liff.core;

import java.util.Objects;

/** A structured cross-reference embedded in a dictionary definition. */
public record Reference(String target, String relation, String label) {
    public Reference {
        Objects.requireNonNull(target, "target");
        Objects.requireNonNull(relation, "relation");
        Objects.requireNonNull(label, "label");
    }
}

package liff.core;

import java.util.Objects;

/** A request to search dictionary headwords. */
public record SearchRequest(String query) implements Request {
    public SearchRequest {
        Objects.requireNonNull(query, "query");
    }
}

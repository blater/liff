package liff.core;

import java.util.List;

/** An ordered set of medium-confidence and trailing low-confidence candidates. */
public record DidYouMean(List<Suggestion> suggestions) implements Outcome {
    public DidYouMean {
        suggestions = List.copyOf(suggestions);
    }
}

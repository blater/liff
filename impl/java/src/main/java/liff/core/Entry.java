package liff.core;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** One immutable dictionary entry in canonical source order. */
public record Entry(
        String word,
        Optional<String> partOfSpeech,
        String definition,
        List<Reference> references) {
    public Entry {
        Objects.requireNonNull(word, "word");
        partOfSpeech = Objects.requireNonNull(partOfSpeech, "partOfSpeech");
        Objects.requireNonNull(definition, "definition");
        references = List.copyOf(references);
    }
}

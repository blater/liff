package liff.core;

import java.util.List;

/** Process-wide access to the generated Meaning of Liff dictionary. */
public final class Liff {
    public static final String TITLE = GeneratedDictionary.TITLE;
    public static final String AUTHOR = GeneratedDictionary.AUTHOR;

    private static final Dictionary DICTIONARY = new Dictionary(GeneratedDictionary.ENTRIES);

    private Liff() {}

    public static Dictionary dictionary() {
        return DICTIONARY;
    }

    public static List<Entry> entries() {
        return DICTIONARY.entries();
    }

    public static Outcome resolve(Request request) {
        return DICTIONARY.resolve(request);
    }
}

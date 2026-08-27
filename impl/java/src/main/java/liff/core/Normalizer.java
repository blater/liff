package liff.core;

final class Normalizer {
    private Normalizer() {}

    static String normalize(String input) {
        return normalize(input, false);
    }

    static String normalizeGlob(String input) {
        return normalize(input, true);
    }

    private static String normalize(String input, boolean preserveGlobs) {
        StringBuilder output = new StringBuilder(input.length());
        boolean separatorPending = false;
        for (int offset = 0; offset < input.length(); ) {
            int codePoint = input.codePointAt(offset);
            offset += Character.charCount(codePoint);
            if (codePoint == '\'' || codePoint == 0x2019) {
                continue;
            }
            boolean alphanumeric = codePoint >= 'a' && codePoint <= 'z'
                    || codePoint >= 'A' && codePoint <= 'Z'
                    || codePoint >= '0' && codePoint <= '9';
            boolean glob = preserveGlobs && (codePoint == '*' || codePoint == '?');
            if (alphanumeric || glob) {
                if (separatorPending && !output.isEmpty()) {
                    output.append(' ');
                }
                char character = (char) codePoint;
                if (character >= 'A' && character <= 'Z') {
                    character = (char) (character + ('a' - 'A'));
                }
                if (character != '*' || output.isEmpty()
                        || output.charAt(output.length() - 1) != '*') {
                    output.append(character);
                }
                separatorPending = false;
            } else {
                separatorPending = true;
            }
        }
        return output.toString();
    }
}

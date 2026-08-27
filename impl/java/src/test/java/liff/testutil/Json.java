package liff.testutil;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Minimal test-only JSON reader used for the shared conformance artifacts. */
public final class Json {
    private final String source;
    private int position;

    private Json(String source) {
        this.source = source;
    }

    public static Object read(Path path) throws IOException {
        String source = Files.readString(path, StandardCharsets.UTF_8);
        Json parser = new Json(source);
        Object value = parser.value();
        parser.whitespace();
        if (parser.position != source.length()) {
            throw parser.error("trailing content");
        }
        return value;
    }

    private Object value() {
        whitespace();
        if (position >= source.length()) {
            throw error("expected value");
        }
        return switch (source.charAt(position)) {
            case '{' -> object();
            case '[' -> array();
            case '"' -> string();
            case 't' -> literal("true", Boolean.TRUE);
            case 'f' -> literal("false", Boolean.FALSE);
            case 'n' -> literal("null", null);
            default -> number();
        };
    }

    private Map<String, Object> object() {
        expect('{');
        LinkedHashMap<String, Object> result = new LinkedHashMap<>();
        whitespace();
        if (take('}')) {
            return result;
        }
        while (true) {
            whitespace();
            String key = string();
            whitespace();
            expect(':');
            result.put(key, value());
            whitespace();
            if (take('}')) {
                return result;
            }
            expect(',');
        }
    }

    private List<Object> array() {
        expect('[');
        ArrayList<Object> result = new ArrayList<>();
        whitespace();
        if (take(']')) {
            return result;
        }
        while (true) {
            result.add(value());
            whitespace();
            if (take(']')) {
                return result;
            }
            expect(',');
        }
    }

    private String string() {
        expect('"');
        StringBuilder result = new StringBuilder();
        while (position < source.length()) {
            char character = source.charAt(position++);
            if (character == '"') {
                return result.toString();
            }
            if (character != '\\') {
                result.append(character);
                continue;
            }
            if (position >= source.length()) {
                throw error("unfinished escape");
            }
            char escape = source.charAt(position++);
            switch (escape) {
                case '"', '\\', '/' -> result.append(escape);
                case 'b' -> result.append('\b');
                case 'f' -> result.append('\f');
                case 'n' -> result.append('\n');
                case 'r' -> result.append('\r');
                case 't' -> result.append('\t');
                case 'u' -> result.append((char) hexadecimal(4));
                default -> throw error("invalid escape");
            }
        }
        throw error("unterminated string");
    }

    private int hexadecimal(int digits) {
        if (position + digits > source.length()) {
            throw error("unfinished Unicode escape");
        }
        int result = 0;
        for (int count = 0; count < digits; count++) {
            int digit = Character.digit(source.charAt(position++), 16);
            if (digit < 0) {
                throw error("invalid Unicode escape");
            }
            result = result * 16 + digit;
        }
        return result;
    }

    private Object number() {
        int start = position;
        take('-');
        digits();
        boolean floating = false;
        if (take('.')) {
            floating = true;
            digits();
        }
        if (take('e') || take('E')) {
            floating = true;
            if (!take('+')) {
                take('-');
            }
            digits();
        }
        String text = source.substring(start, position);
        try {
            if (floating) {
                return Double.valueOf(text);
            }
            return Long.valueOf(text);
        } catch (NumberFormatException exception) {
            throw error("invalid number");
        }
    }

    private void digits() {
        int start = position;
        while (position < source.length() && Character.isDigit(source.charAt(position))) {
            position++;
        }
        if (position == start) {
            throw error("expected digit");
        }
    }

    private Object literal(String text, Object value) {
        if (!source.startsWith(text, position)) {
            throw error("invalid literal");
        }
        position += text.length();
        return value;
    }

    private void whitespace() {
        while (position < source.length()) {
            char character = source.charAt(position);
            if (character != ' ' && character != '\n' && character != '\r' && character != '\t') {
                break;
            }
            position++;
        }
    }

    private void expect(char wanted) {
        if (!take(wanted)) {
            throw error("expected '" + wanted + "'");
        }
    }

    private boolean take(char wanted) {
        if (position < source.length() && source.charAt(position) == wanted) {
            position++;
            return true;
        }
        return false;
    }

    private IllegalArgumentException error(String message) {
        return new IllegalArgumentException(message + " at character " + position);
    }
}

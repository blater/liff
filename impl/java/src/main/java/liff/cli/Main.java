package liff.cli;

import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.IntUnaryOperator;
import liff.core.Dictionary;
import liff.core.DidYouMean;
import liff.core.Found;
import liff.core.Liff;
import liff.core.NotFound;
import liff.core.Outcome;
import liff.core.RandomRequest;
import liff.core.Request;
import liff.core.SearchRequest;
import liff.core.Suggestion;

/** Command-line adapter for the Liff core library. */
public final class Main {
    private static final String HELP = """
            Usage: liff [WORD ...]

            With no word, print a random definition. With a word, search the dictionary.
            Quoted patterns may use * to match any sequence and ? to match one character.""";
    private static final int FULL_SUGGESTION_LIMIT = 11;
    private static final int TRUNCATED_SUGGESTION_LIMIT = 10;

    private Main() {}

    public static void main(String[] arguments) {
        PrintWriter stdout = utf8Writer(System.out);
        PrintWriter stderr = utf8Writer(System.err);
        int status = run(arguments, stdout, stderr, Liff.dictionary(),
                bound -> ThreadLocalRandom.current().nextInt(bound));
        stdout.flush();
        stderr.flush();
        System.exit(status);
    }

    private static PrintWriter utf8Writer(java.io.OutputStream stream) {
        return new PrintWriter(new OutputStreamWriter(stream, StandardCharsets.UTF_8));
    }

    static int run(
            String[] arguments,
            PrintWriter stdout,
            PrintWriter stderr,
            Dictionary dictionary,
            IntUnaryOperator chooseIndex) {
        if (arguments.length == 1
                && (arguments[0].equals("-h") || arguments[0].equals("--help"))) {
            stdout.print(HELP);
            stdout.print('\n');
            return 0;
        }
        for (String argument : arguments) {
            if (argument.startsWith("-")) {
                stderr.print(HELP);
                stderr.print('\n');
                return 2;
            }
        }

        String query = String.join(" ", arguments);
        Request request = arguments.length == 0
                ? RandomRequest.INSTANCE
                : new SearchRequest(query);
        Outcome outcome = dictionary.resolveWith(request, chooseIndex);
        if (outcome instanceof Found found) {
            stdout.printf("%s\n%s\n", found.entry().word(), found.entry().definition());
            return 0;
        }
        if (outcome instanceof DidYouMean didYouMean) {
            List<Suggestion> suggestions = didYouMean.suggestions();
            stdout.print("Did you mean?\n");
            int displayed = suggestions.size() <= FULL_SUGGESTION_LIMIT
                    ? suggestions.size()
                    : TRUNCATED_SUGGESTION_LIMIT;
            for (Suggestion suggestion : suggestions.subList(0, displayed)) {
                stdout.print(suggestion.entry().word());
                stdout.print('\n');
            }
            if (displayed < suggestions.size()) {
                stdout.printf("and %d others\n", suggestions.size() - displayed);
            }
            return 1;
        }
        if (outcome != NotFound.INSTANCE) {
            throw new IllegalStateException("unknown outcome: " + outcome);
        }
        stdout.printf("No definition found for \"%s\".\n", query);
        return 1;
    }
}

package liff.cli;

import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import liff.core.Liff;

/** Golden-output tests for the CLI adapter. */
public final class MainTest {
    private record Result(int status, String stdout, String stderr) {}

    private MainTest() {}

    public static void main(String[] arguments) {
        randomFoundAndNotFound();
        suggestionsAndGlobBoundaries();
        helpAndInvalidUsage();
        System.out.println("MainTest: OK");
    }

    private static Result invoke(String... arguments) {
        ByteArrayOutputStream stdoutBytes = new ByteArrayOutputStream();
        ByteArrayOutputStream stderrBytes = new ByteArrayOutputStream();
        PrintWriter stdout = new PrintWriter(stdoutBytes, false, StandardCharsets.UTF_8);
        PrintWriter stderr = new PrintWriter(stderrBytes, false, StandardCharsets.UTF_8);
        int status = Main.run(arguments, stdout, stderr, Liff.dictionary(), bound -> 0);
        stdout.flush();
        stderr.flush();
        return new Result(status, stdoutBytes.toString(StandardCharsets.UTF_8),
                stderrBytes.toString(StandardCharsets.UTF_8));
    }

    private static void randomFoundAndNotFound() {
        Result random = invoke();
        equal(0, random.status(), "random status");
        check(random.stdout().startsWith("AASLEAGH\n"), "random output");
        equal("", random.stderr(), "random stderr");

        for (String query : new String[] {"banteer", "banteeer", "glutt", "bilb", "bil*"}) {
            Result found = invoke(query);
            equal(0, found.status(), "found status for " + query);
            equal("", found.stderr(), "found stderr for " + query);
        }
        check(invoke("glutt").stdout().startsWith("GLUTT LODGE\n"), "glutt match");
        check(invoke("bilb").stdout().startsWith("BILBSTER\n"), "bilb match");
        check(invoke("bil*").stdout().startsWith("BILBSTER\n"), "unique glob match");
        check(invoke("symonds", "yat").stdout().startsWith("SYMOND'S YAT\n"),
                "joined query");

        Result missing = invoke("xyzzy");
        equal(1, missing.status(), "not-found status");
        equal("No definition found for \"xyzzy\".\n", missing.stdout(), "not-found output");
        equal("", missing.stderr(), "not-found stderr");
    }

    private static void suggestionsAndGlobBoundaries() {
        Result ambiguous = invoke("high");
        equal(1, ambiguous.status(), "ambiguous status");
        equal("Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n",
                ambiguous.stdout(), "ambiguous output");

        Result many = invoke("b*");
        equal(1, many.status(), "large glob status");
        equal("Did you mean?\n"
                        + "BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n"
                        + "BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n"
                        + "and 44 others\n",
                many.stdout(), "large glob output");

        Result eleven = invoke("bo*");
        equal(1, eleven.status(), "eleven glob status");
        check(!eleven.stdout().contains("and "), "eleven results must not truncate");
        equal(12L, eleven.stdout().lines().count(), "eleven-result line count");

        Result all = invoke("*");
        equal(1, all.status(), "all glob status");
        check(all.stdout().endsWith("and 540 others\n"), "all glob truncation");
        equal(12L, all.stdout().lines().count(), "all-result line count");
    }

    private static void helpAndInvalidUsage() {
        Result help = invoke("--help");
        equal(0, help.status(), "help status");
        check(help.stdout().startsWith("Usage: liff"), "help stdout");
        equal("", help.stderr(), "help stderr");

        Result invalid = invoke("--unknown");
        equal(2, invalid.status(), "invalid status");
        equal("", invalid.stdout(), "invalid stdout");
        check(invalid.stderr().startsWith("Usage: liff"), "invalid stderr");
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static void equal(Object expected, Object actual, String message) {
        if (!expected.equals(actual)) {
            throw new AssertionError(message + ": got " + actual + ", want " + expected);
        }
    }
}

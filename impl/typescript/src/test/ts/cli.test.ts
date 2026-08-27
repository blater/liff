import { run, type TextSink } from "../../main/ts/cli";
import { DEFAULT_DICTIONARY } from "../../main/ts/liff";

declare const console: { log(text: string): void };

class BufferSink implements TextSink {
    value = "";

    write(text: string): void {
        this.value += text;
    }
}

interface Result {
    readonly status: number;
    readonly stdout: string;
    readonly stderr: string;
}

function invoke(...arguments_: string[]): Result {
    const stdout = new BufferSink();
    const stderr = new BufferSink();
    const status = run(arguments_, stdout, stderr, DEFAULT_DICTIONARY, () => 0);
    return { status, stdout: stdout.value, stderr: stderr.value };
}

function check(condition: boolean, message: string): asserts condition {
    if (!condition) {
        throw new Error(message);
    }
}

function equal<T>(actual: T, expected: T, message: string): void {
    if (!Object.is(actual, expected)) {
        throw new Error(`${message}: got ${String(actual)}, want ${String(expected)}`);
    }
}

function randomFoundAndNotFound(): void {
    const random = invoke();
    equal(random.status, 0, "random status");
    check(random.stdout.startsWith("AASLEAGH\n"), "random output");
    equal(random.stderr, "", "random stderr");

    for (const query of ["banteer", "banteeer", "glutt", "bilb", "bil*"]) {
        const result = invoke(query);
        equal(result.status, 0, `found status for ${query}`);
        equal(result.stderr, "", `found stderr for ${query}`);
    }
    check(invoke("glutt").stdout.startsWith("GLUTT LODGE\n"), "glutt match");
    check(invoke("bilb").stdout.startsWith("BILBSTER\n"), "bilb match");
    check(invoke("bil*").stdout.startsWith("BILBSTER\n"), "unique glob match");
    check(invoke("symonds", "yat").stdout.startsWith("SYMOND'S YAT\n"),
        "joined query");

    const missing = invoke("xyzzy");
    equal(missing.status, 1, "not-found status");
    equal(missing.stdout, 'No definition found for "xyzzy".\n', "not-found output");
    equal(missing.stderr, "", "not-found stderr");
}

function suggestionsAndGlobBoundaries(): void {
    const ambiguous = invoke("high");
    equal(ambiguous.status, 1, "ambiguous status");
    equal(ambiguous.stdout,
        "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n",
        "ambiguous output");

    const many = invoke("b*");
    equal(many.status, 1, "large glob status");
    equal(many.stdout,
        "Did you mean?\n"
        + "BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n"
        + "BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n"
        + "and 44 others\n",
        "large glob output");

    const eleven = invoke("bo*");
    equal(eleven.status, 1, "eleven-result status");
    check(!eleven.stdout.includes("and "), "eleven results were truncated");
    equal(eleven.stdout.trimEnd().split("\n").length, 12, "eleven-result line count");

    const all = invoke("*");
    equal(all.status, 1, "all-result status");
    check(all.stdout.endsWith("and 540 others\n"), "all-result truncation");
    equal(all.stdout.trimEnd().split("\n").length, 12, "all-result line count");
}

function helpAndInvalidUsage(): void {
    const help = invoke("--help");
    equal(help.status, 0, "help status");
    check(help.stdout.startsWith("Usage: liff"), "help output");
    equal(help.stderr, "", "help stderr");

    const invalid = invoke("--unknown");
    equal(invalid.status, 2, "invalid status");
    equal(invalid.stdout, "", "invalid stdout");
    check(invalid.stderr.startsWith("Usage: liff"), "invalid stderr");
}

randomFoundAndNotFound();
suggestionsAndGlobBoundaries();
helpAndInvalidUsage();
console.log("cli.test: OK");

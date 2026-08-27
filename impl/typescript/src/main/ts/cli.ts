import { DEFAULT_DICTIONARY } from "./liff";
import { RANDOM_REQUEST, searchRequest } from "./model";
import type { Dictionary } from "./dictionary";

export interface TextSink {
    write(text: string): unknown;
}

export const HELP = `Usage: liff [WORD ...]

With no word, print a random definition. With a word, search the dictionary.
Quoted patterns may use * to match any sequence and ? to match one character.`;

const FULL_SUGGESTION_LIMIT = 11;
const TRUNCATED_SUGGESTION_LIMIT = 10;

export function run(
    arguments_: readonly string[],
    stdout: TextSink,
    stderr: TextSink,
    dictionary: Dictionary = DEFAULT_DICTIONARY,
    chooseIndex: (exclusiveUpperBound: number) => number =
        (bound) => Math.floor(Math.random() * bound),
): number {
    if (arguments_.length === 1
            && (arguments_[0] === "-h" || arguments_[0] === "--help")) {
        stdout.write(`${HELP}\n`);
        return 0;
    }
    if (arguments_.some((argument) => argument.startsWith("-"))) {
        stderr.write(`${HELP}\n`);
        return 2;
    }

    const query = arguments_.join(" ");
    const request = arguments_.length === 0 ? RANDOM_REQUEST : searchRequest(query);
    const outcome = dictionary.resolveWith(request, chooseIndex);
    if (outcome.type === "found") {
        stdout.write(`${outcome.entry.word}\n${outcome.entry.definition}\n`);
        return 0;
    }
    if (outcome.type === "did_you_mean") {
        stdout.write("Did you mean?\n");
        const displayed = outcome.suggestions.length <= FULL_SUGGESTION_LIMIT
            ? outcome.suggestions.length
            : TRUNCATED_SUGGESTION_LIMIT;
        for (const candidate of outcome.suggestions.slice(0, displayed)) {
            stdout.write(`${candidate.entry.word}\n`);
        }
        if (displayed < outcome.suggestions.length) {
            stdout.write(`and ${outcome.suggestions.length - displayed} others\n`);
        }
        return 1;
    }
    stdout.write(`No definition found for "${query}".\n`);
    return 1;
}

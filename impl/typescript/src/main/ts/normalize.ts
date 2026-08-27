export function normalize(input: string): string {
    return normalizeInternal(input, false);
}

export function normalizeGlob(input: string): string {
    return normalizeInternal(input, true);
}

function normalizeInternal(input: string, preserveGlobs: boolean): string {
    const output: string[] = [];
    let separatorPending = false;
    for (const character of input) {
        if (character === "'" || character === "’") {
            continue;
        }
        const codePoint = character.codePointAt(0)!;
        const alphanumeric = codePoint >= 0x61 && codePoint <= 0x7a
            || codePoint >= 0x41 && codePoint <= 0x5a
            || codePoint >= 0x30 && codePoint <= 0x39;
        const glob = preserveGlobs && (character === "*" || character === "?");
        if (alphanumeric || glob) {
            if (separatorPending && output.length > 0) {
                output.push(" ");
            }
            const lowered = codePoint >= 0x41 && codePoint <= 0x5a
                ? String.fromCodePoint(codePoint + 0x20)
                : character;
            if (lowered !== "*" || output.at(-1) !== "*") {
                output.push(lowered);
            }
            separatorPending = false;
        } else {
            separatorPending = true;
        }
    }
    return output.join("");
}

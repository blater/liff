import { AUTHOR, ENTRIES, TITLE } from "./dictionary-generated";
import { Dictionary } from "./dictionary";
import type { Entry, Outcome, Request } from "./model";

export { AUTHOR, TITLE };
export * from "./dictionary";
export * from "./model";
export { normalize, normalizeGlob } from "./normalize";

export const DEFAULT_DICTIONARY = new Dictionary(ENTRIES);

export function entries(): readonly Entry[] {
    return DEFAULT_DICTIONARY.entries();
}

export function resolve(request: Request): Outcome {
    return DEFAULT_DICTIONARY.resolve(request);
}

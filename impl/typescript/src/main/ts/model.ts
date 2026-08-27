export interface Reference {
    readonly target: string;
    readonly relation: string;
    readonly label: string;
}

export interface Entry {
    readonly word: string;
    readonly partOfSpeech: string | null;
    readonly definition: string;
    readonly references: readonly Reference[];
}

export type MatchKind = "random" | "exact" | "glob" | "high_confidence";
export type Confidence = "medium" | "low";

export interface Found {
    readonly type: "found";
    readonly entry: Entry;
    readonly kind: MatchKind;
    readonly score: number | null;
}

export interface Suggestion {
    readonly entry: Entry;
    readonly confidence: Confidence;
    readonly score: number;
}

export interface DidYouMean {
    readonly type: "did_you_mean";
    readonly suggestions: readonly Suggestion[];
}

export interface NotFound {
    readonly type: "not_found";
}

export type Outcome = Found | DidYouMean | NotFound;

export interface RandomRequest {
    readonly type: "random";
}

export interface SearchRequest {
    readonly type: "search";
    readonly query: string;
}

export type Request = RandomRequest | SearchRequest;

export const RANDOM_REQUEST: RandomRequest = Object.freeze({ type: "random" });
export const NOT_FOUND: NotFound = Object.freeze({ type: "not_found" });

export function makeReference(target: string, relation: string, label: string): Reference {
    return Object.freeze({ target, relation, label });
}

export function makeEntry(
    word: string,
    partOfSpeech: string | null,
    definition: string,
    references: readonly Reference[],
): Entry {
    return Object.freeze({
        word,
        partOfSpeech,
        definition,
        references: Object.freeze([...references]),
    });
}

export function searchRequest(query: string): SearchRequest {
    return Object.freeze({ type: "search", query });
}

export function found(
    entry: Entry,
    kind: MatchKind,
    score: number | null,
): Found {
    return Object.freeze({ type: "found", entry, kind, score });
}

export function suggestion(
    entry: Entry,
    confidence: Confidence,
    score: number,
): Suggestion {
    return Object.freeze({ entry, confidence, score });
}

export function didYouMean(suggestions: readonly Suggestion[]): DidYouMean {
    return Object.freeze({
        type: "did_you_mean",
        suggestions: Object.freeze([...suggestions]),
    });
}

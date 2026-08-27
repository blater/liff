import {
    NOT_FOUND,
    didYouMean,
    found,
    makeEntry,
    suggestion,
    type Entry,
    type Outcome,
    type Request,
} from "./model";
import { normalize, normalizeGlob } from "./normalize";

export const PERFECT_SCORE = 1000;
export const QUALIFYING_SCORE = 700;
export const LOW_SUGGESTION_COUNT = 2;
export const TOKEN_PREFIX_SCORE = 900;
export const PARTIAL_PREFIX_SCORE = 750;
export const PREFIX_MIN_CODE_POINTS = 4;

interface IndexedEntry {
    readonly entry: Entry;
    readonly normalized: string;
}

interface ScoredCandidate {
    readonly entry: Entry;
    readonly score: number;
}

export class Dictionary {
    readonly #entries: readonly Entry[];
    readonly #index: readonly IndexedEntry[];

    constructor(entries: readonly Entry[]) {
        this.#entries = Object.freeze(entries.map((entry) => makeEntry(
            entry.word,
            entry.partOfSpeech,
            entry.definition,
            entry.references,
        )));
        const index = this.#entries.map((entry) => Object.freeze({
            entry,
            normalized: normalize(entry.word),
        }));
        index.sort((left, right) => compareCodePoints(left.normalized, right.normalized));
        for (let position = 1; position < index.length; position++) {
            if (index[position - 1]!.normalized === index[position]!.normalized) {
                throw new Error("dictionary contains duplicate normalized headwords");
            }
        }
        this.#index = Object.freeze(index);
    }

    entries(): readonly Entry[] {
        return this.#entries;
    }

    random(): Entry | undefined {
        return this.randomWith((bound) => Math.floor(Math.random() * bound));
    }

    randomWith(chooseIndex: (exclusiveUpperBound: number) => number): Entry | undefined {
        if (this.#entries.length === 0) {
            return undefined;
        }
        const index = chooseIndex(this.#entries.length);
        if (!Number.isInteger(index) || index < 0 || index >= this.#entries.length) {
            return undefined;
        }
        return this.#entries[index];
    }

    resolve(request: Request): Outcome {
        return this.resolveWith(request, (bound) => Math.floor(Math.random() * bound));
    }

    resolveWith(
        request: Request,
        chooseIndex: (exclusiveUpperBound: number) => number,
    ): Outcome {
        if (request.type === "search") {
            return this.search(request.query);
        }
        const entry = this.randomWith(chooseIndex);
        return entry === undefined ? NOT_FOUND : found(entry, "random", null);
    }

    search(query: string): Outcome {
        if (query.includes("*") || query.includes("?")) {
            return this.searchGlob(query);
        }

        const normalizedQuery = normalize(query);
        if (normalizedQuery.length === 0) {
            return NOT_FOUND;
        }
        const exactPosition = this.lowerBound(normalizedQuery);
        if (exactPosition < this.#index.length
                && this.#index[exactPosition]!.normalized === normalizedQuery) {
            return found(this.#index[exactPosition]!.entry, "exact", PERFECT_SCORE);
        }

        const ranked: ScoredCandidate[] = this.#index.map((indexed) => ({
            entry: indexed.entry,
            score: candidateScore(normalizedQuery, indexed.normalized),
        }));
        ranked.sort((left, right) => right.score - left.score
            || compareCodePoints(left.entry.word, right.entry.word));

        let qualified = 0;
        while (qualified < ranked.length && ranked[qualified]!.score >= QUALIFYING_SCORE) {
            qualified++;
        }
        if (qualified === 1) {
            const candidate = ranked[0]!;
            return found(candidate.entry, "high_confidence", candidate.score);
        }
        if (qualified === 0) {
            return NOT_FOUND;
        }

        const suggestions = ranked.slice(0, qualified).map((candidate) =>
            suggestion(candidate.entry, "medium", candidate.score));
        for (const candidate of ranked.slice(qualified, qualified + LOW_SUGGESTION_COUNT)) {
            suggestions.push(suggestion(candidate.entry, "low", candidate.score));
        }
        return didYouMean(suggestions);
    }

    private searchGlob(query: string): Outcome {
        const pattern = normalizeGlob(query);
        if (pattern.length === 0) {
            return NOT_FOUND;
        }
        const matches = this.#index.filter((indexed) =>
            globMatches(pattern, indexed.normalized));
        if (matches.length === 0) {
            return NOT_FOUND;
        }
        if (matches.length === 1) {
            return found(matches[0]!.entry, "glob", PERFECT_SCORE);
        }
        return didYouMean(matches.map((indexed) =>
            suggestion(indexed.entry, "medium", PERFECT_SCORE)));
    }

    private lowerBound(query: string): number {
        let lower = 0;
        let upper = this.#index.length;
        while (lower < upper) {
            const middle = lower + Math.floor((upper - lower) / 2);
            if (compareCodePoints(this.#index[middle]!.normalized, query) < 0) {
                lower = middle + 1;
            } else {
                upper = middle;
            }
        }
        return lower;
    }
}

export function similarityScore(left: string, right: string): number {
    const maximum = Math.max(Array.from(left).length, Array.from(right).length);
    if (maximum === 0) {
        return PERFECT_SCORE;
    }
    const retained = Math.max(0, maximum - damerauLevenshtein(left, right));
    return Math.floor(retained * PERFECT_SCORE / maximum);
}

export function candidateScore(query: string, candidate: string): number {
    const editScore = similarityScore(query, candidate);
    if (Array.from(query).length < PREFIX_MIN_CODE_POINTS) {
        return editScore;
    }
    if (candidate.startsWith(`${query} `)) {
        return Math.max(editScore, TOKEN_PREFIX_SCORE);
    }
    if (candidate.startsWith(query)) {
        return Math.max(editScore, PARTIAL_PREFIX_SCORE);
    }
    return editScore;
}

export function globMatches(pattern: string, candidate: string): boolean {
    const patternPoints = Array.from(pattern);
    const candidatePoints = Array.from(candidate);
    let previous = new Array<boolean>(candidatePoints.length + 1).fill(false);
    previous[0] = true;
    for (const patternPoint of patternPoints) {
        const current = new Array<boolean>(candidatePoints.length + 1).fill(false);
        if (patternPoint === "*") {
            current[0] = previous[0]!;
        }
        for (let column = 1; column <= candidatePoints.length; column++) {
            if (patternPoint === "*") {
                current[column] = previous[column]! || current[column - 1]!;
            } else if (patternPoint === "?") {
                current[column] = previous[column - 1]!;
            } else {
                current[column] = previous[column - 1]!
                    && patternPoint === candidatePoints[column - 1];
            }
        }
        previous = current;
    }
    return previous[candidatePoints.length]!;
}

export function damerauLevenshtein(left: string, right: string): number {
    const leftPoints = Array.from(left);
    const rightPoints = Array.from(right);
    let previousPrevious = new Array<number>(rightPoints.length + 1).fill(0);
    let previous = Array.from({ length: rightPoints.length + 1 }, (_, index) => index);
    for (let leftIndex = 0; leftIndex < leftPoints.length; leftIndex++) {
        const current = new Array<number>(rightPoints.length + 1).fill(0);
        current[0] = leftIndex + 1;
        for (let rightIndex = 0; rightIndex < rightPoints.length; rightIndex++) {
            const column = rightIndex + 1;
            const substitution = leftPoints[leftIndex] === rightPoints[rightIndex] ? 0 : 1;
            current[column] = Math.min(
                current[column - 1]! + 1,
                previous[column]! + 1,
                previous[column - 1]! + substitution,
            );
            if (leftIndex > 0 && rightIndex > 0
                    && leftPoints[leftIndex] === rightPoints[rightIndex - 1]
                    && leftPoints[leftIndex - 1] === rightPoints[rightIndex]) {
                current[column] = Math.min(
                    current[column]!,
                    previousPrevious[column - 2]! + 1,
                );
            }
        }
        previousPrevious = previous;
        previous = current;
    }
    return previous[rightPoints.length]!;
}

export function compareCodePoints(left: string, right: string): number {
    const leftIterator = left[Symbol.iterator]();
    const rightIterator = right[Symbol.iterator]();
    while (true) {
        const leftNext = leftIterator.next();
        const rightNext = rightIterator.next();
        if (leftNext.done || rightNext.done) {
            if (leftNext.done && rightNext.done) {
                return 0;
            }
            return leftNext.done ? -1 : 1;
        }
        const difference = leftNext.value.codePointAt(0)! - rightNext.value.codePointAt(0)!;
        if (difference !== 0) {
            return difference;
        }
    }
}

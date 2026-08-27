#include "liff.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "dictionary_generated.h"
#include "liff_internal.h"

const unsigned LIFF_PERFECT_SCORE = 1000U;
const unsigned LIFF_QUALIFYING_SCORE = 700U;
const size_t LIFF_LOW_SUGGESTION_COUNT = 2U;
const unsigned LIFF_TOKEN_PREFIX_SCORE = 900U;
const unsigned LIFF_PARTIAL_PREFIX_SCORE = 750U;
const size_t LIFF_PREFIX_MIN_CODE_POINTS = 4U;

typedef struct {
    const LiffEntry *entry;
    char *normalized;
} IndexedEntry;

typedef struct {
    const LiffEntry *entry;
    unsigned score;
} ScoredCandidate;

struct LiffDictionary {
    const LiffEntry *entries;
    size_t entry_count;
    IndexedEntry *index;
};

static int compare_indexed(const void *left_value, const void *right_value) {
    const IndexedEntry *left = left_value;
    const IndexedEntry *right = right_value;
    return liff_compare_code_points(left->normalized, right->normalized);
}

static int compare_scored(const void *left_value, const void *right_value) {
    const ScoredCandidate *left = left_value;
    const ScoredCandidate *right = right_value;
    if (left->score != right->score) {
        return left->score > right->score ? -1 : 1;
    }
    return liff_compare_code_points(left->entry->word, right->entry->word);
}

const char *liff_title(void) {
    return LIFF_GENERATED_TITLE;
}

const char *liff_author(void) {
    return LIFF_GENERATED_AUTHOR;
}

LiffDictionary *liff_dictionary_create(const LiffEntry *entries, size_t entry_count) {
    LiffDictionary *dictionary = calloc(1U, sizeof(*dictionary));
    if (dictionary == NULL) {
        return NULL;
    }
    dictionary->entries = entries;
    dictionary->entry_count = entry_count;
    if (entry_count == 0U) {
        return dictionary;
    }
    dictionary->index = calloc(entry_count, sizeof(*dictionary->index));
    if (dictionary->index == NULL) {
        free(dictionary);
        return NULL;
    }
    for (size_t position = 0U; position < entry_count; ++position) {
        dictionary->index[position].entry = &entries[position];
        dictionary->index[position].normalized = liff_normalize(entries[position].word);
        if (dictionary->index[position].normalized == NULL) {
            liff_dictionary_destroy(dictionary);
            return NULL;
        }
    }
    qsort(dictionary->index, entry_count, sizeof(*dictionary->index), compare_indexed);
    for (size_t position = 1U; position < entry_count; ++position) {
        if (strcmp(
                dictionary->index[position - 1U].normalized,
                dictionary->index[position].normalized
            ) == 0)
        {
            errno = EINVAL;
            liff_dictionary_destroy(dictionary);
            return NULL;
        }
    }
    return dictionary;
}

void liff_dictionary_destroy(LiffDictionary *dictionary) {
    if (dictionary == NULL) {
        return;
    }
    if (dictionary->index != NULL) {
        for (size_t position = 0U; position < dictionary->entry_count; ++position) {
            free(dictionary->index[position].normalized);
        }
        free(dictionary->index);
    }
    free(dictionary);
}

static bool default_initialized;
static LiffDictionary *default_dictionary;

static void initialize_default_dictionary(void) {
    default_dictionary = liff_dictionary_create(
        LIFF_GENERATED_ENTRIES,
        LIFF_GENERATED_ENTRY_COUNT
    );
}

const LiffDictionary *liff_dictionary(void) {
    if (!default_initialized) {
        initialize_default_dictionary();
        default_initialized = true;
    }
    return default_dictionary;
}

const LiffEntry *liff_entries(const LiffDictionary *dictionary, size_t *entry_count) {
    if (entry_count != NULL) {
        *entry_count = dictionary == NULL ? 0U : dictionary->entry_count;
    }
    return dictionary == NULL ? NULL : dictionary->entries;
}

const LiffEntry *liff_random_with(
    const LiffDictionary *dictionary,
    LiffChooseIndex choose_index,
    void *context
) {
    if (dictionary == NULL || choose_index == NULL || dictionary->entry_count == 0U) {
        return NULL;
    }
    const size_t chosen = choose_index(dictionary->entry_count, context);
    return chosen < dictionary->entry_count ? &dictionary->entries[chosen] : NULL;
}

static bool random_initialized;

static void initialize_random(void) {
    const unsigned seed = (unsigned)time(NULL)
        ^ (unsigned)clock()
        ^ (unsigned)(uintptr_t)&random_initialized;
    srand(seed);
}

static size_t choose_random_index(size_t bound, void *context) {
    (void)context;
    if (!random_initialized) {
        initialize_random();
        random_initialized = true;
    }
    const uint64_t base = (uint64_t)RAND_MAX + 1U;
    const uint64_t range = base * base;
    if (bound == 0U || (uint64_t)bound > range) {
        return bound;
    }
    const uint64_t limit = range - range % (uint64_t)bound;
    uint64_t value;
    do {
        value = (uint64_t)rand() * base + (uint64_t)rand();
    } while (value >= limit);
    return (size_t)(value % (uint64_t)bound);
}

const LiffEntry *liff_random(const LiffDictionary *dictionary) {
    return liff_random_with(dictionary, choose_random_index, NULL);
}

static void set_not_found(LiffOutcome *outcome) {
    *outcome = (LiffOutcome) {
        .kind = LIFF_OUTCOME_NOT_FOUND,
        .found = { 0 },
        .suggestion_count = 0U,
        .suggestions = NULL,
    };
}

static void set_found(
    LiffOutcome *outcome,
    const LiffEntry *entry,
    LiffMatchKind kind,
    bool has_score,
    unsigned score
) {
    *outcome = (LiffOutcome) {
        .kind = LIFF_OUTCOME_FOUND,
        .found = {
            .entry = entry,
            .kind = kind,
            .has_score = has_score,
            .score = score,
        },
        .suggestion_count = 0U,
        .suggestions = NULL,
    };
}

void liff_outcome_destroy(LiffOutcome *outcome) {
    if (outcome == NULL) {
        return;
    }
    free(outcome->suggestions);
    set_not_found(outcome);
}

static size_t lower_bound(const LiffDictionary *dictionary, const char *query) {
    size_t lower = 0U;
    size_t upper = dictionary->entry_count;
    while (lower < upper) {
        const size_t middle = lower + (upper - lower) / 2U;
        if (liff_compare_code_points(dictionary->index[middle].normalized, query) < 0) {
            lower = middle + 1U;
        } else {
            upper = middle;
        }
    }
    return lower;
}

static bool search_glob(
    const LiffDictionary *dictionary,
    const char *query,
    LiffOutcome *outcome
) {
    char *pattern = liff_normalize_glob(query);
    if (pattern == NULL) {
        return false;
    }
    if (pattern[0] == '\0') {
        free(pattern);
        return true;
    }
    size_t match_count = 0U;
    const LiffEntry *only_match = NULL;
    for (size_t position = 0U; position < dictionary->entry_count; ++position) {
        bool matches;
        if (!liff_glob_matches(pattern, dictionary->index[position].normalized, &matches)) {
            free(pattern);
            return false;
        }
        if (matches) {
            ++match_count;
            only_match = dictionary->index[position].entry;
        }
    }
    if (match_count == 1U) {
        set_found(outcome, only_match, LIFF_MATCH_GLOB, true, LIFF_PERFECT_SCORE);
    } else if (match_count > 1U) {
        outcome->suggestions = calloc(match_count, sizeof(*outcome->suggestions));
        if (outcome->suggestions == NULL) {
            free(pattern);
            return false;
        }
        outcome->kind = LIFF_OUTCOME_DID_YOU_MEAN;
        outcome->suggestion_count = match_count;
        size_t suggestion_position = 0U;
        for (size_t position = 0U; position < dictionary->entry_count; ++position) {
            bool matches;
            if (!liff_glob_matches(pattern, dictionary->index[position].normalized, &matches)) {
                free(pattern);
                liff_outcome_destroy(outcome);
                return false;
            }
            if (matches) {
                outcome->suggestions[suggestion_position++] = (LiffSuggestion) {
                    .entry = dictionary->index[position].entry,
                    .confidence = LIFF_CONFIDENCE_MEDIUM,
                    .score = LIFF_PERFECT_SCORE,
                };
            }
        }
    }
    free(pattern);
    return true;
}

bool liff_search(const LiffDictionary *dictionary, const char *query, LiffOutcome *outcome) {
    if (dictionary == NULL || query == NULL || outcome == NULL) {
        errno = EINVAL;
        return false;
    }
    set_not_found(outcome);
    if (strchr(query, '*') != NULL || strchr(query, '?') != NULL) {
        return search_glob(dictionary, query, outcome);
    }

    char *normalized_query = liff_normalize(query);
    if (normalized_query == NULL) {
        return false;
    }
    if (normalized_query[0] == '\0') {
        free(normalized_query);
        return true;
    }
    const size_t exact_position = lower_bound(dictionary, normalized_query);
    if (exact_position < dictionary->entry_count
        && strcmp(dictionary->index[exact_position].normalized, normalized_query) == 0)
    {
        set_found(
            outcome,
            dictionary->index[exact_position].entry,
            LIFF_MATCH_EXACT,
            true,
            LIFF_PERFECT_SCORE
        );
        free(normalized_query);
        return true;
    }

    ScoredCandidate *ranked = calloc(dictionary->entry_count, sizeof(*ranked));
    if (ranked == NULL && dictionary->entry_count > 0U) {
        free(normalized_query);
        return false;
    }
    for (size_t position = 0U; position < dictionary->entry_count; ++position) {
        ranked[position].entry = dictionary->index[position].entry;
        if (!liff_candidate_score(
                normalized_query,
                dictionary->index[position].normalized,
                &ranked[position].score
            ))
        {
            free(normalized_query);
            free(ranked);
            return false;
        }
    }
    free(normalized_query);
    qsort(ranked, dictionary->entry_count, sizeof(*ranked), compare_scored);

    size_t qualified = 0U;
    while (qualified < dictionary->entry_count
        && ranked[qualified].score >= LIFF_QUALIFYING_SCORE)
    {
        ++qualified;
    }
    if (qualified == 1U) {
        set_found(
            outcome,
            ranked[0].entry,
            LIFF_MATCH_HIGH_CONFIDENCE,
            true,
            ranked[0].score
        );
    } else if (qualified > 1U) {
        size_t suggestion_count = qualified + LIFF_LOW_SUGGESTION_COUNT;
        if (suggestion_count > dictionary->entry_count) {
            suggestion_count = dictionary->entry_count;
        }
        outcome->suggestions = calloc(suggestion_count, sizeof(*outcome->suggestions));
        if (outcome->suggestions == NULL) {
            free(ranked);
            return false;
        }
        outcome->kind = LIFF_OUTCOME_DID_YOU_MEAN;
        outcome->suggestion_count = suggestion_count;
        for (size_t position = 0U; position < suggestion_count; ++position) {
            outcome->suggestions[position] = (LiffSuggestion) {
                .entry = ranked[position].entry,
                .confidence = position < qualified
                    ? LIFF_CONFIDENCE_MEDIUM : LIFF_CONFIDENCE_LOW,
                .score = ranked[position].score,
            };
        }
    }
    free(ranked);
    return true;
}

bool liff_resolve_with(
    const LiffDictionary *dictionary,
    LiffRequest request,
    LiffChooseIndex choose_index,
    void *context,
    LiffOutcome *outcome
) {
    if (outcome == NULL) {
        errno = EINVAL;
        return false;
    }
    if (request.kind == LIFF_REQUEST_SEARCH) {
        return liff_search(dictionary, request.query, outcome);
    }
    set_not_found(outcome);
    const LiffEntry *entry = liff_random_with(dictionary, choose_index, context);
    if (entry != NULL) {
        set_found(outcome, entry, LIFF_MATCH_RANDOM, false, 0U);
    }
    return true;
}

bool liff_resolve(
    const LiffDictionary *dictionary,
    LiffRequest request,
    LiffOutcome *outcome
) {
    return liff_resolve_with(dictionary, request, choose_random_index, NULL, outcome);
}

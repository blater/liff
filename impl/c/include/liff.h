#ifndef LIFF_H
#define LIFF_H

#include <stdbool.h>
#include <stddef.h>

typedef struct {
    const char *target;
    const char *relation;
    const char *label;
} LiffReference;

typedef struct {
    const char *word;
    const char *part_of_speech;
    const char *definition;
    size_t reference_count;
    const LiffReference *references;
} LiffEntry;

typedef enum {
    LIFF_MATCH_RANDOM,
    LIFF_MATCH_EXACT,
    LIFF_MATCH_GLOB,
    LIFF_MATCH_HIGH_CONFIDENCE,
} LiffMatchKind;

typedef enum {
    LIFF_CONFIDENCE_MEDIUM,
    LIFF_CONFIDENCE_LOW,
} LiffConfidence;

typedef struct {
    const LiffEntry *entry;
    LiffConfidence confidence;
    unsigned score;
} LiffSuggestion;

typedef struct {
    const LiffEntry *entry;
    LiffMatchKind kind;
    bool has_score;
    unsigned score;
} LiffFound;

typedef enum {
    LIFF_OUTCOME_NOT_FOUND,
    LIFF_OUTCOME_FOUND,
    LIFF_OUTCOME_DID_YOU_MEAN,
} LiffOutcomeKind;

typedef struct {
    LiffOutcomeKind kind;
    LiffFound found;
    size_t suggestion_count;
    LiffSuggestion *suggestions;
} LiffOutcome;

typedef enum {
    LIFF_REQUEST_RANDOM,
    LIFF_REQUEST_SEARCH,
} LiffRequestKind;

typedef struct {
    LiffRequestKind kind;
    const char *query;
} LiffRequest;

typedef struct LiffDictionary LiffDictionary;
typedef size_t (*LiffChooseIndex)(size_t exclusive_upper_bound, void *context);

extern const unsigned LIFF_PERFECT_SCORE;
extern const unsigned LIFF_QUALIFYING_SCORE;
extern const size_t LIFF_LOW_SUGGESTION_COUNT;
extern const unsigned LIFF_TOKEN_PREFIX_SCORE;
extern const unsigned LIFF_PARTIAL_PREFIX_SCORE;
extern const size_t LIFF_PREFIX_MIN_CODE_POINTS;

const char *liff_title(void);
const char *liff_author(void);

LiffDictionary *liff_dictionary_create(const LiffEntry *entries, size_t entry_count);
void liff_dictionary_destroy(LiffDictionary *dictionary);
const LiffDictionary *liff_dictionary(void);

const LiffEntry *liff_entries(const LiffDictionary *dictionary, size_t *entry_count);
const LiffEntry *liff_random(const LiffDictionary *dictionary);
const LiffEntry *liff_random_with(
    const LiffDictionary *dictionary,
    LiffChooseIndex choose_index,
    void *context
);

bool liff_search(const LiffDictionary *dictionary, const char *query, LiffOutcome *outcome);
bool liff_resolve(
    const LiffDictionary *dictionary,
    LiffRequest request,
    LiffOutcome *outcome
);
bool liff_resolve_with(
    const LiffDictionary *dictionary,
    LiffRequest request,
    LiffChooseIndex choose_index,
    void *context,
    LiffOutcome *outcome
);
void liff_outcome_destroy(LiffOutcome *outcome);

#endif

#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "liff.h"
#include "liff_internal.h"

static const char *match_kind_name(LiffMatchKind kind) {
    switch (kind) {
        case LIFF_MATCH_RANDOM:
            return "random";
        case LIFF_MATCH_EXACT:
            return "exact";
        case LIFF_MATCH_GLOB:
            return "glob";
        case LIFF_MATCH_HIGH_CONFIDENCE:
            return "high_confidence";
    }
    return "unknown";
}

static const char *confidence_name(LiffConfidence confidence) {
    return confidence == LIFF_CONFIDENCE_MEDIUM ? "medium" : "low";
}

static int search(const char *query) {
    LiffOutcome outcome;
    if (!liff_search(liff_dictionary(), query, &outcome)) {
        return 2;
    }
    if (outcome.kind == LIFF_OUTCOME_FOUND) {
        printf("found\t%s\t%s\t", match_kind_name(outcome.found.kind), outcome.found.entry->word);
        if (outcome.found.has_score) {
            printf("%u", outcome.found.score);
        } else {
            putchar('-');
        }
        putchar('\n');
    } else if (outcome.kind == LIFF_OUTCOME_DID_YOU_MEAN) {
        printf("did_you_mean\t%zu\n", outcome.suggestion_count);
        for (size_t position = 0U; position < outcome.suggestion_count; ++position) {
            const LiffSuggestion *suggestion = &outcome.suggestions[position];
            printf(
                "%s\t%s\t%u\n",
                suggestion->entry->word,
                confidence_name(suggestion->confidence),
                suggestion->score
            );
        }
    } else {
        puts("not_found");
    }
    liff_outcome_destroy(&outcome);
    return 0;
}

static void write_hex(const char *value) {
    if (value == NULL) {
        putchar('-');
        return;
    }
    const unsigned char *bytes = (const unsigned char *)value;
    while (*bytes != '\0') {
        printf("%02x", *bytes++);
    }
}

static int dump(void) {
    size_t entry_count;
    const LiffEntry *entries = liff_entries(liff_dictionary(), &entry_count);
    fputs("M\t", stdout);
    write_hex(liff_title());
    putchar('\t');
    write_hex(liff_author());
    putchar('\n');
    for (size_t entry_index = 0U; entry_index < entry_count; ++entry_index) {
        const LiffEntry *entry = &entries[entry_index];
        printf("E\t%zu\t", entry_index);
        write_hex(entry->word);
        putchar('\t');
        write_hex(entry->part_of_speech);
        putchar('\t');
        write_hex(entry->definition);
        printf("\t%zu\n", entry->reference_count);
        for (size_t reference_index = 0U;
             reference_index < entry->reference_count;
             ++reference_index)
        {
            const LiffReference *reference = &entry->references[reference_index];
            printf("R\t%zu\t%zu\t", entry_index, reference_index);
            write_hex(reference->target);
            putchar('\t');
            write_hex(reference->relation);
            putchar('\t');
            write_hex(reference->label);
            putchar('\n');
        }
    }
    return 0;
}

static size_t choose_value(size_t bound, void *context) {
    (void)bound;
    return *(const size_t *)context;
}

static int self_test(void) {
    const LiffDictionary *dictionary = liff_dictionary();
    size_t count;
    const LiffEntry *entries = liff_entries(dictionary, &count);
    size_t choice = 0U;
    if (liff_random_with(dictionary, choose_value, &choice) != &entries[0]) {
        return 1;
    }
    choice = count - 1U;
    if (liff_random_with(dictionary, choose_value, &choice) != &entries[count - 1U]) {
        return 1;
    }
    choice = count;
    if (liff_random_with(dictionary, choose_value, &choice) != NULL) {
        return 1;
    }
    LiffDictionary *empty = liff_dictionary_create(NULL, 0U);
    if (empty == NULL || liff_random_with(empty, choose_value, &choice) != NULL) {
        liff_dictionary_destroy(empty);
        return 1;
    }
    liff_dictionary_destroy(empty);

    const LiffEntry duplicates[] = {
        { .word = "A-B", .part_of_speech = NULL, .definition = "first",
          .reference_count = 0U, .references = NULL },
        { .word = "A B", .part_of_speech = NULL, .definition = "second",
          .reference_count = 0U, .references = NULL },
    };
    errno = 0;
    LiffDictionary *invalid = liff_dictionary_create(duplicates, 2U);
    if (invalid != NULL || errno != EINVAL) {
        liff_dictionary_destroy(invalid);
        return 1;
    }

    choice = 0U;
    LiffOutcome outcome;
    if (!liff_resolve_with(
            dictionary,
            (LiffRequest) { .kind = LIFF_REQUEST_RANDOM, .query = NULL },
            choose_value,
            &choice,
            &outcome
        )
        || outcome.kind != LIFF_OUTCOME_FOUND
        || outcome.found.kind != LIFF_MATCH_RANDOM
        || outcome.found.has_score)
    {
        return 1;
    }
    liff_outcome_destroy(&outcome);
    puts("ok");
    return 0;
}

int main(int argument_count, char *arguments[]) {
    if (argument_count < 2) {
        return 2;
    }
    const char *operation = arguments[1];
    if (strcmp(operation, "search") == 0 && argument_count == 3) {
        return search(arguments[2]);
    }
    if (strcmp(operation, "normalize") == 0 && argument_count == 3) {
        char *value = liff_normalize(arguments[2]);
        if (value == NULL) {
            return 2;
        }
        fputs(value, stdout);
        free(value);
        return 0;
    }
    if (strcmp(operation, "normalize-glob") == 0 && argument_count == 3) {
        char *value = liff_normalize_glob(arguments[2]);
        if (value == NULL) {
            return 2;
        }
        fputs(value, stdout);
        free(value);
        return 0;
    }
    if (strcmp(operation, "distance") == 0 && argument_count == 4) {
        const size_t value = liff_damerau_levenshtein(arguments[2], arguments[3]);
        if (value == SIZE_MAX) {
            return 2;
        }
        printf("%zu\n", value);
        return 0;
    }
    if (strcmp(operation, "similarity") == 0 && argument_count == 4) {
        unsigned value;
        if (!liff_similarity_score(arguments[2], arguments[3], &value)) {
            return 2;
        }
        printf("%u\n", value);
        return 0;
    }
    if (strcmp(operation, "candidate") == 0 && argument_count == 4) {
        unsigned value;
        if (!liff_candidate_score(arguments[2], arguments[3], &value)) {
            return 2;
        }
        printf("%u\n", value);
        return 0;
    }
    if (strcmp(operation, "glob") == 0 && argument_count == 4) {
        bool value;
        if (!liff_glob_matches(arguments[2], arguments[3], &value)) {
            return 2;
        }
        printf("%d\n", value ? 1 : 0);
        return 0;
    }
    if (strcmp(operation, "compare") == 0 && argument_count == 4) {
        printf("%d\n", liff_compare_code_points(arguments[2], arguments[3]));
        return 0;
    }
    if (strcmp(operation, "dump") == 0 && argument_count == 2) {
        return dump();
    }
    if (strcmp(operation, "self-test") == 0 && argument_count == 2) {
        return self_test();
    }
    return 2;
}

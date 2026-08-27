#include "liff_cli.h"

#include <stdlib.h>
#include <string.h>

#include "liff.h"

static const char HELP[] =
    "Usage: liff [WORD ...]\n"
    "\n"
    "With no word, print a random definition. With a word, search the dictionary.\n"
    "Quoted patterns may use * to match any sequence and ? to match one character.";

static const size_t FULL_SUGGESTION_LIMIT = 11U;
static const size_t TRUNCATED_SUGGESTION_LIMIT = 10U;

static char *join_arguments(int argument_count, char *const arguments[]) {
    size_t length = 0U;
    for (int index = 0; index < argument_count; ++index) {
        length += strlen(arguments[index]);
        if (index > 0) {
            ++length;
        }
    }
    char *query = malloc(length + 1U);
    if (query == NULL) {
        return NULL;
    }
    size_t offset = 0U;
    for (int index = 0; index < argument_count; ++index) {
        if (index > 0) {
            query[offset++] = ' ';
        }
        const size_t argument_length = strlen(arguments[index]);
        memcpy(query + offset, arguments[index], argument_length);
        offset += argument_length;
    }
    query[offset] = '\0';
    return query;
}

int liff_cli_run(int argument_count, char *const arguments[], FILE *output, FILE *errors) {
    if (argument_count == 1
        && (strcmp(arguments[0], "-h") == 0 || strcmp(arguments[0], "--help") == 0))
    {
        fprintf(output, "%s\n", HELP);
        return 0;
    }
    for (int index = 0; index < argument_count; ++index) {
        if (arguments[index][0] == '-') {
            fprintf(errors, "%s\n", HELP);
            return 2;
        }
    }

    char *query = join_arguments(argument_count, arguments);
    if (query == NULL) {
        fputs("liff: out of memory\n", errors);
        return 2;
    }
    const LiffDictionary *dictionary = liff_dictionary();
    if (dictionary == NULL) {
        free(query);
        fputs("liff: could not initialize dictionary\n", errors);
        return 2;
    }
    const LiffRequest request = argument_count == 0
        ? (LiffRequest) { .kind = LIFF_REQUEST_RANDOM, .query = NULL }
        : (LiffRequest) { .kind = LIFF_REQUEST_SEARCH, .query = query };
    LiffOutcome outcome;
    if (!liff_resolve(dictionary, request, &outcome)) {
        free(query);
        fputs("liff: lookup failed\n", errors);
        return 2;
    }

    int status;
    if (outcome.kind == LIFF_OUTCOME_FOUND) {
        fprintf(output, "%s\n%s\n", outcome.found.entry->word, outcome.found.entry->definition);
        status = 0;
    } else if (outcome.kind == LIFF_OUTCOME_DID_YOU_MEAN) {
        fputs("Did you mean?\n", output);
        const size_t displayed = outcome.suggestion_count <= FULL_SUGGESTION_LIMIT
            ? outcome.suggestion_count : TRUNCATED_SUGGESTION_LIMIT;
        for (size_t position = 0U; position < displayed; ++position) {
            fprintf(output, "%s\n", outcome.suggestions[position].entry->word);
        }
        if (displayed < outcome.suggestion_count) {
            fprintf(output, "and %zu others\n", outcome.suggestion_count - displayed);
        }
        status = 1;
    } else {
        fprintf(output, "No definition found for \"%s\".\n", query);
        status = 1;
    }
    liff_outcome_destroy(&outcome);
    free(query);
    return status;
}

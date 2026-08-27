#include "liff_internal.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "liff.h"

static uint32_t utf8_next(const unsigned char *input, size_t length, size_t *offset) {
    const unsigned char first = input[(*offset)++];
    if (first < 0x80U) {
        return first;
    }
    unsigned count;
    uint32_t code_point;
    if ((first & 0xe0U) == 0xc0U) {
        count = 1U;
        code_point = first & 0x1fU;
    } else if ((first & 0xf0U) == 0xe0U) {
        count = 2U;
        code_point = first & 0x0fU;
    } else {
        count = 3U;
        code_point = first & 0x07U;
    }
    while (count-- > 0U && *offset < length) {
        code_point = (code_point << 6U) | (input[(*offset)++] & 0x3fU);
    }
    return code_point;
}

static char *normalize_internal(const char *input, bool preserve_globs) {
    const size_t input_length = strlen(input);
    char *output = malloc(input_length + 1U);
    if (output == NULL) {
        return NULL;
    }
    size_t input_offset = 0U;
    size_t output_length = 0U;
    bool separator_pending = false;
    while (input_offset < input_length) {
        uint32_t code_point = utf8_next(
            (const unsigned char *)input,
            input_length,
            &input_offset
        );
        if (code_point == 0x27U || code_point == 0x2019U) {
            continue;
        }
        const bool lower = code_point >= 'a' && code_point <= 'z';
        const bool upper = code_point >= 'A' && code_point <= 'Z';
        const bool digit = code_point >= '0' && code_point <= '9';
        const bool glob = preserve_globs && (code_point == '*' || code_point == '?');
        if (lower || upper || digit || glob) {
            if (separator_pending && output_length > 0U) {
                output[output_length++] = ' ';
            }
            char character = (char)code_point;
            if (upper) {
                character = (char)(character + ('a' - 'A'));
            }
            if (character != '*' || output_length == 0U || output[output_length - 1U] != '*') {
                output[output_length++] = character;
            }
            separator_pending = false;
        } else {
            separator_pending = true;
        }
    }
    output[output_length] = '\0';
    return output;
}

char *liff_normalize(const char *input) {
    return normalize_internal(input, false);
}

char *liff_normalize_glob(const char *input) {
    return normalize_internal(input, true);
}

int liff_compare_code_points(const char *left, const char *right) {
    const size_t left_length = strlen(left);
    const size_t right_length = strlen(right);
    size_t left_offset = 0U;
    size_t right_offset = 0U;
    while (left_offset < left_length && right_offset < right_length) {
        const uint32_t left_point = utf8_next(
            (const unsigned char *)left,
            left_length,
            &left_offset
        );
        const uint32_t right_point = utf8_next(
            (const unsigned char *)right,
            right_length,
            &right_offset
        );
        if (left_point != right_point) {
            return left_point < right_point ? -1 : 1;
        }
    }
    if (left_offset == left_length && right_offset == right_length) {
        return 0;
    }
    return left_offset == left_length ? -1 : 1;
}

static uint32_t *to_code_points(const char *input, size_t *count) {
    const size_t byte_length = strlen(input);
    uint32_t *points = malloc((byte_length == 0U ? 1U : byte_length) * sizeof(*points));
    if (points == NULL) {
        return NULL;
    }
    size_t offset = 0U;
    *count = 0U;
    while (offset < byte_length) {
        points[(*count)++] = utf8_next(
            (const unsigned char *)input,
            byte_length,
            &offset
        );
    }
    return points;
}

size_t liff_damerau_levenshtein(const char *left, const char *right) {
    size_t left_count;
    size_t right_count;
    uint32_t *left_points = to_code_points(left, &left_count);
    uint32_t *right_points = to_code_points(right, &right_count);
    if (left_points == NULL || right_points == NULL) {
        free(left_points);
        free(right_points);
        return SIZE_MAX;
    }

    const size_t row_size = right_count + 1U;
    size_t *previous_previous = calloc(row_size, sizeof(*previous_previous));
    size_t *previous = malloc(row_size * sizeof(*previous));
    size_t *current = malloc(row_size * sizeof(*current));
    if (previous_previous == NULL || previous == NULL || current == NULL) {
        free(left_points);
        free(right_points);
        free(previous_previous);
        free(previous);
        free(current);
        return SIZE_MAX;
    }
    for (size_t column = 0U; column < row_size; ++column) {
        previous[column] = column;
    }
    for (size_t row = 1U; row <= left_count; ++row) {
        current[0] = row;
        for (size_t column = 1U; column <= right_count; ++column) {
            const size_t substitution = left_points[row - 1U] == right_points[column - 1U]
                ? 0U : 1U;
            size_t value = current[column - 1U] + 1U;
            if (previous[column] + 1U < value) {
                value = previous[column] + 1U;
            }
            if (previous[column - 1U] + substitution < value) {
                value = previous[column - 1U] + substitution;
            }
            if (row > 1U && column > 1U
                && left_points[row - 1U] == right_points[column - 2U]
                && left_points[row - 2U] == right_points[column - 1U]
                && previous_previous[column - 2U] + 1U < value)
            {
                value = previous_previous[column - 2U] + 1U;
            }
            current[column] = value;
        }
        size_t *swap = previous_previous;
        previous_previous = previous;
        previous = current;
        current = swap;
    }
    const size_t result = previous[right_count];
    free(left_points);
    free(right_points);
    free(previous_previous);
    free(previous);
    free(current);
    return result;
}

bool liff_similarity_score(const char *left, const char *right, unsigned *score) {
    size_t left_count;
    size_t right_count;
    uint32_t *left_points = to_code_points(left, &left_count);
    uint32_t *right_points = to_code_points(right, &right_count);
    const bool allocated = left_points != NULL && right_points != NULL;
    free(left_points);
    free(right_points);
    if (!allocated) {
        return false;
    }
    const size_t maximum = left_count > right_count ? left_count : right_count;
    if (maximum == 0U) {
        *score = LIFF_PERFECT_SCORE;
        return true;
    }
    const size_t distance = liff_damerau_levenshtein(left, right);
    if (distance == SIZE_MAX) {
        return false;
    }
    const size_t retained = distance > maximum ? 0U : maximum - distance;
    *score = (unsigned)(retained * 1000U / maximum);
    return true;
}

bool liff_candidate_score(const char *query, const char *candidate, unsigned *score) {
    if (!liff_similarity_score(query, candidate, score)) {
        return false;
    }
    size_t query_count;
    uint32_t *query_points = to_code_points(query, &query_count);
    if (query_points == NULL) {
        return false;
    }
    free(query_points);
    if (query_count < LIFF_PREFIX_MIN_CODE_POINTS) {
        return true;
    }
    const size_t query_bytes = strlen(query);
    if (strncmp(candidate, query, query_bytes) == 0) {
        const unsigned floor = candidate[query_bytes] == ' '
            ? LIFF_TOKEN_PREFIX_SCORE : LIFF_PARTIAL_PREFIX_SCORE;
        if (*score < floor) {
            *score = floor;
        }
    }
    return true;
}

bool liff_glob_matches(const char *pattern, const char *candidate, bool *matches) {
    size_t pattern_count;
    size_t candidate_count;
    uint32_t *pattern_points = to_code_points(pattern, &pattern_count);
    uint32_t *candidate_points = to_code_points(candidate, &candidate_count);
    if (pattern_points == NULL || candidate_points == NULL) {
        free(pattern_points);
        free(candidate_points);
        return false;
    }
    bool *previous = calloc(candidate_count + 1U, sizeof(*previous));
    bool *current = malloc((candidate_count + 1U) * sizeof(*current));
    if (previous == NULL || current == NULL) {
        free(pattern_points);
        free(candidate_points);
        free(previous);
        free(current);
        return false;
    }
    previous[0] = true;
    for (size_t row = 0U; row < pattern_count; ++row) {
        memset(current, 0, (candidate_count + 1U) * sizeof(*current));
        if (pattern_points[row] == '*') {
            current[0] = previous[0];
        }
        for (size_t column = 1U; column <= candidate_count; ++column) {
            if (pattern_points[row] == '*') {
                current[column] = previous[column] || current[column - 1U];
            } else if (pattern_points[row] == '?') {
                current[column] = previous[column - 1U];
            } else {
                current[column] = previous[column - 1U]
                    && pattern_points[row] == candidate_points[column - 1U];
            }
        }
        bool *swap = previous;
        previous = current;
        current = swap;
    }
    *matches = previous[candidate_count];
    free(pattern_points);
    free(candidate_points);
    free(previous);
    free(current);
    return true;
}

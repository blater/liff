#ifndef LIFF_INTERNAL_H
#define LIFF_INTERNAL_H

#include <stdbool.h>
#include <stddef.h>

char *liff_normalize(const char *input);
char *liff_normalize_glob(const char *input);
int liff_compare_code_points(const char *left, const char *right);
size_t liff_damerau_levenshtein(const char *left, const char *right);
bool liff_similarity_score(const char *left, const char *right, unsigned *score);
bool liff_candidate_score(const char *query, const char *candidate, unsigned *score);
bool liff_glob_matches(const char *pattern, const char *candidate, bool *matches);

#endif

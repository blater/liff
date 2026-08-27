use std::cmp::Ordering;

use crate::generated;
use crate::model::Entry;
use crate::normalize::{normalize, normalize_glob};

/// Minimum score required for a unique automatic fuzzy match.
pub const HIGH_CONFIDENCE_MIN: u16 = 700;
/// Minimum score required to offer a candidate as a medium suggestion.
pub const MEDIUM_CONFIDENCE_MIN: u16 = 700;
/// Number of low-confidence candidates appended to a suggestion response.
pub const LOW_SUGGESTION_LIMIT: usize = 2;
/// Score floor for a query matching one or more complete leading tokens.
pub const TOKEN_PREFIX_SCORE: u16 = 900;
/// Score floor for a query matching the start of a headword.
pub const PARTIAL_PREFIX_SCORE: u16 = 750;
/// Minimum query length eligible for either prefix score.
pub const PREFIX_MIN_CHARS: usize = 4;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
/// Integer similarity score from zero through 1000.
pub struct Score(u16);

impl Score {
    /// Score assigned to a normalized exact match.
    pub const PERFECT: Self = Self(1000);

    const fn new(basis_points: u16) -> Self {
        Self(basis_points)
    }

    #[must_use]
    /// Return the score as integer basis points from zero through 1000.
    pub const fn basis_points(self) -> u16 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// Reason an entry was returned as a definitive result.
pub enum MatchKind {
    /// Selected uniformly without a search query.
    Random,
    /// Matched exactly after normalization.
    Exact,
    /// Was the sole entry matched by a glob pattern.
    Glob,
    /// Was the only fuzzy candidate meeting the automatic-match threshold.
    HighConfidence,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// Effective confidence assigned to a suggested candidate.
pub enum Confidence {
    /// Candidate met the medium threshold or was an ambiguous high candidate.
    Medium,
    /// Candidate was one of the best two below the medium threshold.
    Low,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// Definitive entry match and the reason it was selected.
pub struct Found {
    entry: &'static Entry,
    kind: MatchKind,
    score: Option<Score>,
}

impl Found {
    const fn new(entry: &'static Entry, kind: MatchKind, score: Option<Score>) -> Self {
        Self { entry, kind, score }
    }

    #[must_use]
    /// Return the matching entry.
    pub const fn entry(&self) -> &'static Entry {
        self.entry
    }

    #[must_use]
    /// Return how the entry was selected.
    pub const fn kind(&self) -> MatchKind {
        self.kind
    }

    #[must_use]
    /// Return its similarity score, absent only for random selection.
    pub const fn score(&self) -> Option<Score> {
        self.score
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// One ordered candidate in a “did you mean?” response.
pub struct Suggestion {
    entry: &'static Entry,
    confidence: Confidence,
    score: Score,
}

impl Suggestion {
    const fn new(entry: &'static Entry, confidence: Confidence, score: Score) -> Self {
        Self {
            entry,
            confidence,
            score,
        }
    }

    #[must_use]
    /// Return the suggested entry.
    pub const fn entry(&self) -> &'static Entry {
        self.entry
    }

    #[must_use]
    /// Return the candidate's effective confidence tier.
    pub const fn confidence(&self) -> Confidence {
        self.confidence
    }

    #[must_use]
    /// Return the candidate's similarity score.
    pub const fn score(&self) -> Score {
        self.score
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
/// Complete result of resolving a dictionary request.
pub enum Outcome {
    /// A definitive random, exact, or high-confidence result.
    Found(Found),
    /// Ordered medium suggestions followed by up to two low suggestions.
    DidYouMean(Vec<Suggestion>),
    /// No candidate met the minimum threshold.
    NotFound,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// Operation requested from the dictionary.
pub enum Request<'a> {
    /// Select a uniformly random entry.
    Random,
    /// Search for the supplied headword.
    Search(&'a str),
}

#[derive(Debug)]
struct IndexedEntry {
    entry: &'static Entry,
    normalized: String,
}

#[derive(Clone, Copy, Debug)]
struct ScoredCandidate {
    entry: &'static Entry,
    score: Score,
}

#[derive(Debug)]
/// Indexed immutable dictionary and its lookup operations.
pub struct Dictionary {
    entries: &'static [Entry],
    index: Vec<IndexedEntry>,
}

impl Dictionary {
    pub(crate) fn liff() -> Self {
        Self::from_entries(generated::ENTRIES)
    }

    fn from_entries(entries: &'static [Entry]) -> Self {
        let mut index: Vec<_> = entries
            .iter()
            .map(|entry| IndexedEntry {
                entry,
                normalized: normalize(entry.word()),
            })
            .collect();
        index.sort_by(|left, right| left.normalized.cmp(&right.normalized));

        for pair in index.windows(2) {
            assert_ne!(
                pair[0].normalized, pair[1].normalized,
                "dictionary contains duplicate normalized headwords"
            );
        }

        Self { entries, index }
    }

    #[must_use]
    /// Return every entry in canonical source order.
    pub const fn entries(&self) -> &'static [Entry] {
        self.entries
    }

    #[must_use]
    /// Resolve either a random-selection or search request.
    pub fn resolve(&self, request: Request<'_>) -> Outcome {
        match request {
            Request::Random => self.random().map_or(Outcome::NotFound, |entry| {
                Outcome::Found(Found::new(entry, MatchKind::Random, None))
            }),
            Request::Search(query) => self.search(query),
        }
    }

    #[must_use]
    /// Return a uniformly selected entry, or `None` for an empty dictionary.
    pub fn random(&self) -> Option<&'static Entry> {
        self.random_with(|length| rand::random_range(0..length))
    }

    #[must_use]
    /// Select using an injected index chooser, primarily for deterministic tests.
    ///
    /// The closure receives the exclusive upper bound. Returning an out-of-range
    /// index produces `None`.
    pub fn random_with(&self, choose_index: impl FnOnce(usize) -> usize) -> Option<&'static Entry> {
        if self.entries.is_empty() {
            return None;
        }
        self.entries.get(choose_index(self.entries.len()))
    }

    #[must_use]
    /// Search for a normalized exact or confidence-qualified fuzzy match.
    pub fn search(&self, query: &str) -> Outcome {
        if query.contains(['*', '?']) {
            return self.search_glob(query);
        }

        let normalized_query = normalize(query);
        if normalized_query.is_empty() {
            return Outcome::NotFound;
        }

        if let Some(indexed) = self
            .index
            .iter()
            .find(|indexed| indexed.normalized == normalized_query)
        {
            return Outcome::Found(Found::new(
                indexed.entry,
                MatchKind::Exact,
                Some(Score::PERFECT),
            ));
        }

        let mut ranked: Vec<_> = self
            .index
            .iter()
            .map(|indexed| ScoredCandidate {
                entry: indexed.entry,
                score: candidate_score(&normalized_query, &indexed.normalized),
            })
            .collect();
        ranked.sort_by(compare_candidates);

        let qualifying_count = ranked
            .iter()
            .take_while(|candidate| candidate.score.0 >= HIGH_CONFIDENCE_MIN)
            .count();
        if qualifying_count == 1 {
            let best = ranked[0];
            return Outcome::Found(Found::new(
                best.entry,
                MatchKind::HighConfidence,
                Some(best.score),
            ));
        }

        if qualifying_count == 0 {
            return Outcome::NotFound;
        }

        let mut suggestions = Vec::with_capacity(qualifying_count + LOW_SUGGESTION_LIMIT);
        suggestions.extend(ranked[..qualifying_count].iter().map(|candidate| {
            Suggestion::new(candidate.entry, Confidence::Medium, candidate.score)
        }));
        suggestions.extend(
            ranked[qualifying_count..]
                .iter()
                .take(LOW_SUGGESTION_LIMIT)
                .map(|candidate| {
                    Suggestion::new(candidate.entry, Confidence::Low, candidate.score)
                }),
        );
        Outcome::DidYouMean(suggestions)
    }

    fn search_glob(&self, query: &str) -> Outcome {
        let pattern = normalize_glob(query);
        if pattern.is_empty() {
            return Outcome::NotFound;
        }

        let matches: Vec<_> = self
            .index
            .iter()
            .filter(|indexed| glob_matches(&pattern, &indexed.normalized))
            .collect();

        match matches.as_slice() {
            [] => Outcome::NotFound,
            [indexed] => Outcome::Found(Found::new(
                indexed.entry,
                MatchKind::Glob,
                Some(Score::PERFECT),
            )),
            _ => Outcome::DidYouMean(
                matches
                    .into_iter()
                    .map(|indexed| {
                        Suggestion::new(indexed.entry, Confidence::Medium, Score::PERFECT)
                    })
                    .collect(),
            ),
        }
    }
}

fn compare_candidates(left: &ScoredCandidate, right: &ScoredCandidate) -> Ordering {
    right
        .score
        .cmp(&left.score)
        .then_with(|| left.entry.word().cmp(right.entry.word()))
}

fn similarity_score(left: &str, right: &str) -> Score {
    let left_length = left.chars().count();
    let right_length = right.chars().count();
    let maximum_length = left_length.max(right_length);
    if maximum_length == 0 {
        return Score::PERFECT;
    }

    let distance = damerau_levenshtein(left, right);
    let retained = maximum_length.saturating_sub(distance);
    let basis_points = (retained * 1000 / maximum_length) as u16;
    Score::new(basis_points)
}

fn candidate_score(query: &str, candidate: &str) -> Score {
    let edit_score = similarity_score(query, candidate);
    if query.chars().count() < PREFIX_MIN_CHARS {
        return edit_score;
    }

    match candidate.strip_prefix(query) {
        Some(remainder) if remainder.starts_with(' ') => {
            Score::new(edit_score.0.max(TOKEN_PREFIX_SCORE))
        }
        Some(_) => Score::new(edit_score.0.max(PARTIAL_PREFIX_SCORE)),
        None => edit_score,
    }
}

fn glob_matches(pattern: &str, candidate: &str) -> bool {
    let candidate: Vec<char> = candidate.chars().collect();
    let mut previous = vec![false; candidate.len() + 1];
    previous[0] = true;

    for pattern_character in pattern.chars() {
        let mut current = vec![false; candidate.len() + 1];
        if pattern_character == '*' {
            current[0] = previous[0];
        }

        for (index, candidate_character) in candidate.iter().enumerate() {
            let column = index + 1;
            current[column] = match pattern_character {
                '*' => previous[column] || current[column - 1],
                '?' => previous[column - 1],
                literal => previous[column - 1] && literal == *candidate_character,
            };
        }
        previous = current;
    }

    previous[candidate.len()]
}

fn damerau_levenshtein(left: &str, right: &str) -> usize {
    let left: Vec<char> = left.chars().collect();
    let right: Vec<char> = right.chars().collect();
    let mut previous_previous = vec![0; right.len() + 1];
    let mut previous: Vec<usize> = (0..=right.len()).collect();

    for (left_index, left_character) in left.iter().enumerate() {
        let row = left_index + 1;
        let mut current = vec![0; right.len() + 1];
        current[0] = row;

        for (right_index, right_character) in right.iter().enumerate() {
            let column = right_index + 1;
            let substitution_cost = usize::from(left_character != right_character);
            current[column] = (current[column - 1] + 1)
                .min(previous[column] + 1)
                .min(previous[column - 1] + substitution_cost);

            if row > 1
                && column > 1
                && left_character == &right[right_index - 1]
                && left[left_index - 1] == *right_character
            {
                current[column] = current[column].min(previous_previous[column - 2] + 1);
            }
        }

        previous_previous = previous;
        previous = current;
    }

    previous[right.len()]
}

#[cfg(test)]
mod tests {
    use serde::Deserialize;

    use super::{candidate_score, damerau_levenshtein, glob_matches, similarity_score};
    use crate::normalize::{normalize, normalize_glob};

    #[derive(Deserialize)]
    struct AlgorithmCases {
        schema_version: u32,
        normalization: Vec<NormalizationCase>,
        glob_normalization: Vec<NormalizationCase>,
        edit_scores: Vec<EditScoreCase>,
        candidate_scores: Vec<CandidateScoreCase>,
        glob_matches: Vec<GlobCase>,
        ordering: Vec<OrderingCase>,
    }

    #[derive(Deserialize)]
    struct NormalizationCase {
        input: String,
        output: String,
    }

    #[derive(Deserialize)]
    struct EditScoreCase {
        left: String,
        right: String,
        distance: usize,
        score: u16,
    }

    #[derive(Deserialize)]
    struct CandidateScoreCase {
        query: String,
        candidate: String,
        score: u16,
    }

    #[derive(Deserialize)]
    struct GlobCase {
        pattern: String,
        candidate: String,
        matches: bool,
    }

    #[derive(Deserialize)]
    struct OrderingCase {
        input: Vec<String>,
        ascending: Vec<String>,
    }

    fn algorithm_cases() -> AlgorithmCases {
        serde_json::from_str(include_str!("../../../../algorithm-cases.json"))
            .expect("shared algorithm cases must be valid JSON")
    }

    #[test]
    fn adjacent_transposition_is_one_edit() {
        assert_eq!(damerau_levenshtein("liff", "ilff"), 1);
    }

    #[test]
    fn score_uses_integer_basis_points() {
        assert_eq!(similarity_score("banteeer", "banteer").basis_points(), 875);
        assert_eq!(similarity_score("lif", "liff").basis_points(), 750);
    }

    #[test]
    fn complete_leading_token_gets_prefix_score() {
        assert_eq!(candidate_score("glutt", "glutt lodge").basis_points(), 900);
    }

    #[test]
    fn partial_leading_token_gets_medium_prefix_score() {
        assert_eq!(candidate_score("bilb", "bilbster").basis_points(), 750);
        assert_eq!(candidate_score("glen", "glentaggart").basis_points(), 750);
    }

    #[test]
    fn prefix_scoring_requires_a_minimum_length() {
        assert_ne!(candidate_score("mo", "mo i rana").basis_points(), 900);
        assert_ne!(candidate_score("bil", "bilbster").basis_points(), 750);
    }

    #[test]
    fn glob_supports_zero_or_more_and_single_character_wildcards() {
        assert!(glob_matches("bil*", "bilbster"));
        assert!(glob_matches("b?lbster", "bilbster"));
        assert!(glob_matches("*", "bilbster"));
        assert!(!glob_matches("bil?", "bilbster"));
    }

    #[test]
    fn shared_algorithm_cases_match_the_contract() {
        let cases = algorithm_cases();
        assert_eq!(cases.schema_version, 1);

        for case in cases.normalization {
            assert_eq!(normalize(&case.input), case.output, "{:?}", case.input);
        }
        for case in cases.glob_normalization {
            assert_eq!(normalize_glob(&case.input), case.output, "{:?}", case.input);
        }
        for case in cases.edit_scores {
            assert_eq!(
                damerau_levenshtein(&case.left, &case.right),
                case.distance,
                "{:?} -> {:?}",
                case.left,
                case.right
            );
            assert_eq!(
                similarity_score(&case.left, &case.right).basis_points(),
                case.score,
                "{:?} -> {:?}",
                case.left,
                case.right
            );
        }
        for case in cases.candidate_scores {
            assert_eq!(
                candidate_score(&case.query, &case.candidate).basis_points(),
                case.score,
                "{:?} -> {:?}",
                case.query,
                case.candidate
            );
        }
        for case in cases.glob_matches {
            assert_eq!(
                glob_matches(&case.pattern, &case.candidate),
                case.matches,
                "{:?} -> {:?}",
                case.pattern,
                case.candidate
            );
        }
        for case in cases.ordering {
            let mut actual = case.input;
            actual.sort();
            assert_eq!(actual, case.ascending);
        }
    }
}

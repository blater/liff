package liff

import (
	"math/rand/v2"
	"sort"
	"strings"
)

const (
	// QualifyingScore is the inclusive automatic/medium threshold.
	QualifyingScore Score = 700
	// LowSuggestionCount is the number of sub-threshold ambiguous suggestions.
	LowSuggestionCount = 2
	// TokenPrefixScore is the floor for a complete leading-token match.
	TokenPrefixScore Score = 900
	// PartialPrefixScore is the floor for a partial leading-token match.
	PartialPrefixScore Score = 750
	// PrefixMinCodePoints is the shortest query eligible for a prefix floor.
	PrefixMinCodePoints = 4
)

type indexedEntry struct {
	entry      *Entry
	normalized string
}

type scoredCandidate struct {
	entry *Entry
	score Score
}

// Dictionary is an indexed immutable dictionary and its lookup operations.
type Dictionary struct {
	entries []Entry
	index   []indexedEntry
}

func newDictionary(entries []Entry) *Dictionary {
	owned := append([]Entry(nil), entries...)
	index := make([]indexedEntry, len(owned))
	for i := range owned {
		index[i] = indexedEntry{entry: &owned[i], normalized: normalize(owned[i].word)}
	}
	sort.Slice(index, func(i, j int) bool { return index[i].normalized < index[j].normalized })
	for i := 1; i < len(index); i++ {
		if index[i-1].normalized == index[i].normalized {
			panic("dictionary contains duplicate normalized headwords")
		}
	}
	return &Dictionary{entries: owned, index: index}
}

var defaultDictionary = newDictionary(generatedEntries)

// DefaultDictionary returns the process-wide generated dictionary.
func DefaultDictionary() *Dictionary { return defaultDictionary }

// Entries returns all entries in canonical source order.
func (d *Dictionary) Entries() []Entry { return append([]Entry(nil), d.entries...) }

// Resolve handles either a random or search request.
func (d *Dictionary) Resolve(request Request) Outcome {
	if request.kind == requestSearch {
		return d.Search(request.query)
	}
	entry, ok := d.Random()
	if !ok {
		return Outcome{}
	}
	return foundOutcome(newFound(entry, MatchRandom, 0, false))
}

// Resolve handles a request against the process-wide generated dictionary.
func Resolve(request Request) Outcome { return defaultDictionary.Resolve(request) }

// Random returns a uniformly selected entry, or false for an empty dictionary.
func (d *Dictionary) Random() (*Entry, bool) {
	return d.RandomWith(func(length int) int { return rand.IntN(length) })
}

// RandomWith selects using an injected index chooser.
//
// The chooser receives the exclusive upper bound. An out-of-range result
// returns false.
func (d *Dictionary) RandomWith(chooseIndex func(int) int) (*Entry, bool) {
	if len(d.entries) == 0 {
		return nil, false
	}
	index := chooseIndex(len(d.entries))
	if index < 0 || index >= len(d.entries) {
		return nil, false
	}
	return &d.entries[index], true
}

// Search returns an exact, glob, confidence-qualified, ambiguous, or not-found outcome.
func (d *Dictionary) Search(query string) Outcome {
	if strings.ContainsAny(query, "*?") {
		return d.searchGlob(query)
	}

	normalizedQuery := normalize(query)
	if normalizedQuery == "" {
		return Outcome{}
	}

	exactIndex := sort.Search(len(d.index), func(i int) bool {
		return d.index[i].normalized >= normalizedQuery
	})
	if exactIndex < len(d.index) && d.index[exactIndex].normalized == normalizedQuery {
		return foundOutcome(newFound(d.index[exactIndex].entry, MatchExact, PerfectScore, true))
	}

	ranked := make([]scoredCandidate, len(d.index))
	for i, indexed := range d.index {
		ranked[i] = scoredCandidate{
			entry: indexed.entry,
			score: candidateScore(normalizedQuery, indexed.normalized),
		}
	}
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		return ranked[i].entry.word < ranked[j].entry.word
	})

	qualified := 0
	for qualified < len(ranked) && ranked[qualified].score >= QualifyingScore {
		qualified++
	}
	if qualified == 1 {
		best := ranked[0]
		return foundOutcome(newFound(best.entry, MatchHighConfidence, best.score, true))
	}
	if qualified == 0 {
		return Outcome{}
	}

	capacity := qualified + LowSuggestionCount
	if capacity > len(ranked) {
		capacity = len(ranked)
	}
	suggestions := make([]Suggestion, 0, capacity)
	for _, candidate := range ranked[:qualified] {
		suggestions = append(suggestions, newSuggestion(
			candidate.entry, ConfidenceMedium, candidate.score,
		))
	}
	lowEnd := qualified + LowSuggestionCount
	if lowEnd > len(ranked) {
		lowEnd = len(ranked)
	}
	for _, candidate := range ranked[qualified:lowEnd] {
		suggestions = append(suggestions, newSuggestion(
			candidate.entry, ConfidenceLow, candidate.score,
		))
	}
	return suggestionsOutcome(suggestions)
}

func (d *Dictionary) searchGlob(query string) Outcome {
	pattern := normalizeGlob(query)
	if pattern == "" {
		return Outcome{}
	}

	matches := make([]*Entry, 0)
	for _, indexed := range d.index {
		if globMatches(pattern, indexed.normalized) {
			matches = append(matches, indexed.entry)
		}
	}
	if len(matches) == 0 {
		return Outcome{}
	}
	if len(matches) == 1 {
		return foundOutcome(newFound(matches[0], MatchGlob, PerfectScore, true))
	}

	suggestions := make([]Suggestion, len(matches))
	for i, entry := range matches {
		suggestions[i] = newSuggestion(entry, ConfidenceMedium, PerfectScore)
	}
	return suggestionsOutcome(suggestions)
}

func similarityScore(left, right string) Score {
	leftLength := len([]rune(left))
	rightLength := len([]rune(right))
	maximum := max(leftLength, rightLength)
	if maximum == 0 {
		return PerfectScore
	}
	distance := damerauLevenshtein(left, right)
	retained := maximum - distance
	if retained < 0 {
		retained = 0
	}
	return Score(retained * 1000 / maximum)
}

func candidateScore(query, candidate string) Score {
	editScore := similarityScore(query, candidate)
	if len([]rune(query)) < PrefixMinCodePoints {
		return editScore
	}
	if strings.HasPrefix(candidate, query+" ") {
		return max(editScore, TokenPrefixScore)
	}
	if strings.HasPrefix(candidate, query) {
		return max(editScore, PartialPrefixScore)
	}
	return editScore
}

func globMatches(pattern, candidate string) bool {
	candidateRunes := []rune(candidate)
	previous := make([]bool, len(candidateRunes)+1)
	previous[0] = true

	for _, patternRune := range []rune(pattern) {
		current := make([]bool, len(candidateRunes)+1)
		if patternRune == '*' {
			current[0] = previous[0]
		}
		for i, candidateRune := range candidateRunes {
			column := i + 1
			switch patternRune {
			case '*':
				current[column] = previous[column] || current[column-1]
			case '?':
				current[column] = previous[column-1]
			default:
				current[column] = previous[column-1] && patternRune == candidateRune
			}
		}
		previous = current
	}
	return previous[len(candidateRunes)]
}

func damerauLevenshtein(left, right string) int {
	leftRunes := []rune(left)
	rightRunes := []rune(right)
	previousPrevious := make([]int, len(rightRunes)+1)
	previous := make([]int, len(rightRunes)+1)
	for i := range previous {
		previous[i] = i
	}

	for leftIndex, leftRune := range leftRunes {
		row := leftIndex + 1
		current := make([]int, len(rightRunes)+1)
		current[0] = row
		for rightIndex, rightRune := range rightRunes {
			column := rightIndex + 1
			substitutionCost := 0
			if leftRune != rightRune {
				substitutionCost = 1
			}
			current[column] = min(
				current[column-1]+1,
				previous[column]+1,
				previous[column-1]+substitutionCost,
			)
			if row > 1 && column > 1 &&
				leftRune == rightRunes[rightIndex-1] && leftRunes[leftIndex-1] == rightRune {
				current[column] = min(current[column], previousPrevious[column-2]+1)
			}
		}
		previousPrevious = previous
		previous = current
	}

	return previous[len(rightRunes)]
}

// Package liff provides typed, reusable access to the generated Meaning of
// Liff dictionary.
package liff

// Reference is a structured cross-reference embedded in an entry definition.
// Its fields are immutable outside this package.
type Reference struct {
	target   string
	relation string
	label    string
}

func newReference(target, relation, label string) Reference {
	return Reference{target: target, relation: relation, label: label}
}

// Target returns the canonical target headword.
func (r Reference) Target() string { return r.target }

// Relation returns the source relation, such as "q.v." or "see_also".
func (r Reference) Relation() string { return r.relation }

// Label returns the spelling displayed in the source definition.
func (r Reference) Label() string { return r.label }

// Entry is one immutable dictionary entry compiled into the program.
type Entry struct {
	word         string
	partOfSpeech *string
	definition   string
	references   []Reference
}

func newEntry(word string, partOfSpeech *string, definition string, references []Reference) Entry {
	return Entry{
		word:         word,
		partOfSpeech: partOfSpeech,
		definition:   definition,
		references:   references,
	}
}

func optionalString(value string) *string { return &value }

// Word returns the canonical headword.
func (e Entry) Word() string { return e.word }

// PartOfSpeech returns the source label and whether one is present.
func (e Entry) PartOfSpeech() (string, bool) {
	if e.partOfSpeech == nil {
		return "", false
	}
	return *e.partOfSpeech, true
}

// Definition returns the original definition text.
func (e Entry) Definition() string { return e.definition }

// References returns a copy of the structured references in source order.
func (e Entry) References() []Reference { return append([]Reference(nil), e.references...) }

// Score is an integer similarity score from zero through 1000.
type Score uint16

// PerfectScore is assigned to normalized exact and unique glob matches.
const PerfectScore Score = 1000

// BasisPoints returns the score as an integer from zero through 1000.
func (s Score) BasisPoints() uint16 { return uint16(s) }

// MatchKind explains why an entry was returned as a definitive result.
type MatchKind string

const (
	// MatchRandom indicates uniform random selection.
	MatchRandom MatchKind = "random"
	// MatchExact indicates equality after normalization.
	MatchExact MatchKind = "exact"
	// MatchGlob indicates the sole entry matched by a glob pattern.
	MatchGlob MatchKind = "glob"
	// MatchHighConfidence indicates the only fuzzy candidate reaching 700.
	MatchHighConfidence MatchKind = "high_confidence"
)

// Confidence is the effective tier of a suggested candidate.
type Confidence string

const (
	// ConfidenceMedium indicates a candidate reaching the qualifying threshold.
	ConfidenceMedium Confidence = "medium"
	// ConfidenceLow indicates one of the two best sub-threshold candidates.
	ConfidenceLow Confidence = "low"
)

// Found is a definitive dictionary result.
type Found struct {
	entry    *Entry
	kind     MatchKind
	score    Score
	hasScore bool
}

func newFound(entry *Entry, kind MatchKind, score Score, hasScore bool) Found {
	return Found{entry: entry, kind: kind, score: score, hasScore: hasScore}
}

// Entry returns the matching entry.
func (f Found) Entry() *Entry { return f.entry }

// Kind returns how the entry was selected.
func (f Found) Kind() MatchKind { return f.kind }

// Score returns the similarity score and whether one is present.
func (f Found) Score() (Score, bool) { return f.score, f.hasScore }

// Suggestion is one ordered candidate in a DidYouMean outcome.
type Suggestion struct {
	entry      *Entry
	confidence Confidence
	score      Score
}

func newSuggestion(entry *Entry, confidence Confidence, score Score) Suggestion {
	return Suggestion{entry: entry, confidence: confidence, score: score}
}

// Entry returns the suggested entry.
func (s Suggestion) Entry() *Entry { return s.entry }

// Confidence returns the candidate's confidence tier.
func (s Suggestion) Confidence() Confidence { return s.confidence }

// Score returns the candidate's score.
func (s Suggestion) Score() Score { return s.score }

// OutcomeKind identifies the variant stored in an Outcome.
type OutcomeKind uint8

const (
	// OutcomeNotFound indicates no qualifying candidate.
	OutcomeNotFound OutcomeKind = iota
	// OutcomeFound indicates a definitive result.
	OutcomeFound
	// OutcomeDidYouMean indicates an ordered ambiguous result.
	OutcomeDidYouMean
)

// Outcome is the complete result of resolving a dictionary request.
type Outcome struct {
	kind        OutcomeKind
	found       Found
	suggestions []Suggestion
}

func foundOutcome(found Found) Outcome {
	return Outcome{kind: OutcomeFound, found: found}
}

func suggestionsOutcome(suggestions []Suggestion) Outcome {
	return Outcome{kind: OutcomeDidYouMean, suggestions: suggestions}
}

// Kind returns the outcome variant.
func (o Outcome) Kind() OutcomeKind { return o.kind }

// Found returns the definitive result and whether this is a Found outcome.
func (o Outcome) Found() (Found, bool) { return o.found, o.kind == OutcomeFound }

// Suggestions returns a copy of the ordered suggestions. It is empty for other outcomes.
func (o Outcome) Suggestions() []Suggestion {
	return append([]Suggestion(nil), o.suggestions...)
}

// RequestKind identifies a random or search request.
type RequestKind uint8

const (
	requestRandom RequestKind = iota
	requestSearch
)

// Request describes a dictionary operation.
type Request struct {
	kind  RequestKind
	query string
}

// RandomRequest creates a uniformly random-selection request.
func RandomRequest() Request { return Request{kind: requestRandom} }

// SearchRequest creates a search request for query.
func SearchRequest(query string) Request { return Request{kind: requestSearch, query: query} }

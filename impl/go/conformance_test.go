package liff

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"slices"
	"sort"
	"testing"
)

func fixturePath(name string) string {
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		panic("cannot locate Go test source")
	}
	return filepath.Join(filepath.Dir(filename), "..", name)
}

func readFixture(t *testing.T, name string, target any) {
	t.Helper()
	data, err := os.ReadFile(fixturePath(name))
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	if err := json.Unmarshal(data, target); err != nil {
		t.Fatalf("decode %s: %v", name, err)
	}
}

type searchContract struct {
	SchemaVersion int          `json:"schema_version"`
	Cases         []searchCase `json:"cases"`
}

type searchCase struct {
	Query       string               `json:"query"`
	Outcome     string               `json:"outcome"`
	Kind        string               `json:"kind"`
	Word        string               `json:"word"`
	Score       *uint16              `json:"score"`
	Suggestions []expectedSuggestion `json:"suggestions"`
}

type expectedSuggestion struct {
	Word       string `json:"word"`
	Confidence string `json:"confidence"`
	Score      uint16 `json:"score"`
}

func TestSharedSearchCases(t *testing.T) {
	var contract searchContract
	readFixture(t, "search-cases.json", &contract)
	if contract.SchemaVersion != 1 {
		t.Fatalf("search schema version = %d, want 1", contract.SchemaVersion)
	}

	for _, testCase := range contract.Cases {
		t.Run(testCase.Query, func(t *testing.T) {
			outcome := DefaultDictionary().Search(testCase.Query)
			switch testCase.Outcome {
			case "found":
				found, ok := outcome.Found()
				if !ok {
					t.Fatalf("outcome = %#v, want found", outcome)
				}
				if found.Entry().Word() != testCase.Word {
					t.Errorf("word = %q, want %q", found.Entry().Word(), testCase.Word)
				}
				if string(found.Kind()) != testCase.Kind {
					t.Errorf("kind = %q, want %q", found.Kind(), testCase.Kind)
				}
				if testCase.Score != nil {
					score, present := found.Score()
					if !present || score.BasisPoints() != *testCase.Score {
						t.Errorf("score = (%d, %v), want %d", score, present, *testCase.Score)
					}
				}
			case "did_you_mean":
				if outcome.Kind() != OutcomeDidYouMean {
					t.Fatalf("outcome kind = %v, want DidYouMean", outcome.Kind())
				}
				actual := outcome.Suggestions()
				if len(actual) != len(testCase.Suggestions) {
					t.Fatalf("suggestion count = %d, want %d", len(actual), len(testCase.Suggestions))
				}
				for i, expected := range testCase.Suggestions {
					if actual[i].Entry().Word() != expected.Word ||
						string(actual[i].Confidence()) != expected.Confidence ||
						actual[i].Score().BasisPoints() != expected.Score {
						t.Errorf("suggestion %d = (%q, %q, %d), want (%q, %q, %d)",
							i,
							actual[i].Entry().Word(), actual[i].Confidence(), actual[i].Score(),
							expected.Word, expected.Confidence, expected.Score)
					}
				}
			case "not_found":
				if outcome.Kind() != OutcomeNotFound {
					t.Errorf("outcome kind = %v, want NotFound", outcome.Kind())
				}
			default:
				t.Fatalf("unknown expected outcome %q", testCase.Outcome)
			}
		})
	}
}

type algorithmContract struct {
	SchemaVersion     int                     `json:"schema_version"`
	Normalization     []normalizationCase     `json:"normalization"`
	GlobNormalization []normalizationCase     `json:"glob_normalization"`
	EditScores        []editScoreCase         `json:"edit_scores"`
	CandidateScores   []candidateScoreCase    `json:"candidate_scores"`
	GlobMatches       []globMatchCase         `json:"glob_matches"`
	Ordering          []lexicographicSortCase `json:"ordering"`
}

type normalizationCase struct {
	Input  string `json:"input"`
	Output string `json:"output"`
}

type editScoreCase struct {
	Left     string `json:"left"`
	Right    string `json:"right"`
	Distance int    `json:"distance"`
	Score    uint16 `json:"score"`
}

type candidateScoreCase struct {
	Query     string `json:"query"`
	Candidate string `json:"candidate"`
	Score     uint16 `json:"score"`
}

type globMatchCase struct {
	Pattern   string `json:"pattern"`
	Candidate string `json:"candidate"`
	Matches   bool   `json:"matches"`
}

type lexicographicSortCase struct {
	Input     []string `json:"input"`
	Ascending []string `json:"ascending"`
}

func TestSharedAlgorithmCases(t *testing.T) {
	var contract algorithmContract
	readFixture(t, "algorithm-cases.json", &contract)
	if contract.SchemaVersion != 1 {
		t.Fatalf("algorithm schema version = %d, want 1", contract.SchemaVersion)
	}

	for _, testCase := range contract.Normalization {
		if actual := normalize(testCase.Input); actual != testCase.Output {
			t.Errorf("normalize(%q) = %q, want %q", testCase.Input, actual, testCase.Output)
		}
	}
	for _, testCase := range contract.GlobNormalization {
		if actual := normalizeGlob(testCase.Input); actual != testCase.Output {
			t.Errorf("normalizeGlob(%q) = %q, want %q", testCase.Input, actual, testCase.Output)
		}
	}
	for _, testCase := range contract.EditScores {
		if actual := damerauLevenshtein(testCase.Left, testCase.Right); actual != testCase.Distance {
			t.Errorf("distance(%q, %q) = %d, want %d", testCase.Left, testCase.Right, actual, testCase.Distance)
		}
		if actual := similarityScore(testCase.Left, testCase.Right).BasisPoints(); actual != testCase.Score {
			t.Errorf("score(%q, %q) = %d, want %d", testCase.Left, testCase.Right, actual, testCase.Score)
		}
	}
	for _, testCase := range contract.CandidateScores {
		if actual := candidateScore(testCase.Query, testCase.Candidate).BasisPoints(); actual != testCase.Score {
			t.Errorf("candidateScore(%q, %q) = %d, want %d", testCase.Query, testCase.Candidate, actual, testCase.Score)
		}
	}
	for _, testCase := range contract.GlobMatches {
		if actual := globMatches(testCase.Pattern, testCase.Candidate); actual != testCase.Matches {
			t.Errorf("globMatches(%q, %q) = %v, want %v", testCase.Pattern, testCase.Candidate, actual, testCase.Matches)
		}
	}
	for _, testCase := range contract.Ordering {
		actual := append([]string(nil), testCase.Input...)
		sort.Strings(actual)
		if !slices.Equal(actual, testCase.Ascending) {
			t.Errorf("ordering = %q, want %q", actual, testCase.Ascending)
		}
	}
}

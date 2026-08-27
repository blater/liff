package liff

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"testing"
)

type sourceDocument struct {
	SchemaVersion      int                  `json:"schema_version"`
	Title              string               `json:"title"`
	Author             string               `json:"author"`
	Source             string               `json:"source"`
	DefinitionEncoding string               `json:"definition_encoding"`
	Entries            orderedSourceEntries `json:"entries"`
}

type orderedSourceEntries []sourceEntry

type sourceEntry struct {
	Word         string
	PartOfSpeech *string           `json:"part_of_speech"`
	Definition   string            `json:"definition"`
	References   []sourceReference `json:"references"`
}

type sourceReference struct {
	Target   string `json:"target"`
	Relation string `json:"relation"`
	Label    string `json:"label"`
}

func (entries *orderedSourceEntries) UnmarshalJSON(data []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	if _, err := decoder.Token(); err != nil {
		return err
	}
	for decoder.More() {
		wordToken, err := decoder.Token()
		if err != nil {
			return err
		}
		var entry sourceEntry
		if err := decoder.Decode(&entry); err != nil {
			return err
		}
		entry.Word = wordToken.(string)
		*entries = append(*entries, entry)
	}
	_, err := decoder.Token()
	return err
}

func TestGeneratedDataExactlyMatchesSource(t *testing.T) {
	var source sourceDocument
	readFixture(t, "../liff.json", &source)
	if source.SchemaVersion != 2 {
		t.Fatalf("source schema version = %d, want 2", source.SchemaVersion)
	}
	if source.DefinitionEncoding != "base64-utf8" {
		t.Fatalf("definition encoding = %q, want base64-utf8", source.DefinitionEncoding)
	}
	if source.Title != Title || source.Author != Author || source.Source != "liff-corrected.txt" {
		t.Errorf("generated metadata does not match source: %#v", source)
	}

	actual := DefaultDictionary().Entries()
	if len(actual) != len(source.Entries) {
		t.Fatalf("entry count = %d, want %d", len(actual), len(source.Entries))
	}
	for i, expected := range source.Entries {
		entry := actual[i]
		if entry.Word() != expected.Word {
			t.Fatalf("entry %d word = %q, want source-order word %q", i, entry.Word(), expected.Word)
		}
		partOfSpeech, present := entry.PartOfSpeech()
		if expected.PartOfSpeech == nil {
			if present {
				t.Errorf("%s part of speech = %q, want absent", expected.Word, partOfSpeech)
			}
		} else if !present || partOfSpeech != *expected.PartOfSpeech {
			t.Errorf("%s part of speech = (%q, %v), want %q", expected.Word, partOfSpeech, present, *expected.PartOfSpeech)
		}
		expectedDefinition, err := base64.StdEncoding.DecodeString(expected.Definition)
		if err != nil {
			t.Fatalf("%s definition is not valid Base64: %v", expected.Word, err)
		}
		if entry.Definition() != string(expectedDefinition) {
			t.Errorf("%s definition differs from source", expected.Word)
		}

		references := entry.References()
		if len(references) != len(expected.References) {
			t.Fatalf("%s reference count = %d, want %d", expected.Word, len(references), len(expected.References))
		}
		for referenceIndex, expectedReference := range expected.References {
			reference := references[referenceIndex]
			if reference.Target() != expectedReference.Target ||
				reference.Relation() != expectedReference.Relation ||
				reference.Label() != expectedReference.Label {
				t.Errorf("%s reference %d differs from source", expected.Word, referenceIndex)
			}
		}
	}
}

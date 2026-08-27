package liff

import "testing"

func TestGeneratedDictionaryMetadataAndEntries(t *testing.T) {
	if Title != "The Meaning of Liff" {
		t.Errorf("Title = %q", Title)
	}
	if Author != "Douglas Adams" {
		t.Errorf("Author = %q", Author)
	}
	entries := DefaultDictionary().Entries()
	if len(entries) != 550 {
		t.Fatalf("entry count = %d, want 550", len(entries))
	}
	if entries[0].Word() != "AASLEAGH" || entries[len(entries)-1].Word() != "ZEAL MONACHORUM" {
		t.Errorf("source-order endpoints = %q, %q", entries[0].Word(), entries[len(entries)-1].Word())
	}
}

func TestEveryReferenceResolvesExactly(t *testing.T) {
	for _, entry := range DefaultDictionary().Entries() {
		for _, reference := range entry.References() {
			outcome := DefaultDictionary().Search(reference.Target())
			found, ok := outcome.Found()
			if !ok || found.Kind() != MatchExact || found.Entry().Word() != reference.Target() {
				t.Errorf("%s has unresolved reference %s", entry.Word(), reference.Target())
			}
		}
	}
}

func TestRandomWithIsDeterministicAndBoundsChecked(t *testing.T) {
	dictionary := DefaultDictionary()
	entries := dictionary.Entries()
	first, ok := dictionary.RandomWith(func(int) int { return 0 })
	if !ok || first.Word() != entries[0].Word() {
		t.Errorf("first injected random result = (%v, %v)", first, ok)
	}
	last, ok := dictionary.RandomWith(func(length int) int { return length - 1 })
	if !ok || last.Word() != entries[len(entries)-1].Word() {
		t.Errorf("last injected random result = (%v, %v)", last, ok)
	}
	if _, ok := dictionary.RandomWith(func(length int) int { return length }); ok {
		t.Error("out-of-range chooser unexpectedly succeeded")
	}
	if _, ok := newDictionary(nil).RandomWith(func(int) int { return 0 }); ok {
		t.Error("empty dictionary unexpectedly returned an entry")
	}
}

func TestRandomRequestReturnsADictionaryEntryWithoutScore(t *testing.T) {
	outcome := Resolve(RandomRequest())
	found, ok := outcome.Found()
	if !ok || found.Kind() != MatchRandom {
		t.Fatalf("random outcome = %#v", outcome)
	}
	if _, present := found.Score(); present {
		t.Error("random result unexpectedly has a score")
	}
}

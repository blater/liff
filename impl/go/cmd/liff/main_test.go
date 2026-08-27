package main

import (
	"bytes"
	"strings"
	"testing"

	"liff"
)

func invoke(arguments ...string) (int, string, string) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	status := run(arguments, &stdout, &stderr)
	return status, stdout.String(), stderr.String()
}

func TestNoArgumentsPrintsRandomEntry(t *testing.T) {
	status, output, stderr := invoke()
	if status != 0 || stderr != "" {
		t.Fatalf("status = %d, stderr = %q", status, stderr)
	}
	word, definition, ok := strings.Cut(strings.TrimSuffix(output, "\n"), "\n")
	if !ok {
		t.Fatalf("random output has no definition: %q", output)
	}
	for _, entry := range liff.DefaultDictionary().Entries() {
		if entry.Word() == word {
			if entry.Definition() != definition {
				t.Errorf("definition differs for %s", word)
			}
			return
		}
	}
	t.Errorf("random word %q is not in the dictionary", word)
}

func TestFoundSearchesPrintEntry(t *testing.T) {
	tests := []struct {
		arguments []string
		prefix    string
	}{
		{[]string{"banteer"}, "BANTEER\nA lusty and raucous old ballad"},
		{[]string{"banteeer"}, "BANTEER\nA lusty and raucous old ballad"},
		{[]string{"glutt"}, "GLUTT LODGE\n"},
		{[]string{"bilb"}, "BILBSTER\n"},
		{[]string{"bil*"}, "BILBSTER\n"},
		{[]string{"b?lbster"}, "BILBSTER\n"},
		{[]string{"symonds", "yat"}, "SYMOND'S YAT\n"},
	}
	for _, testCase := range tests {
		status, output, stderr := invoke(testCase.arguments...)
		if status != 0 || stderr != "" || !strings.HasPrefix(output, testCase.prefix) {
			t.Errorf("run(%q) = status %d, stdout %q, stderr %q", testCase.arguments, status, output, stderr)
		}
	}
}

func TestAmbiguousAndLargeGlobOutput(t *testing.T) {
	status, output, _ := invoke("high")
	if status != 1 || output != "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n" {
		t.Errorf("ambiguous output = status %d, %q", status, output)
	}

	status, output, _ = invoke("b*")
	want := "Did you mean?\n" +
		"BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n" +
		"BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n" +
		"and 44 others\n"
	if status != 1 || output != want {
		t.Errorf("large glob output = status %d, %q", status, output)
	}

	status, output, _ = invoke("*")
	if status != 1 || !strings.HasSuffix(output, "and 540 others\n") || len(strings.Split(strings.TrimSuffix(output, "\n"), "\n")) != 12 {
		t.Errorf("all-entry glob output = status %d, %q", status, output)
	}
}

func TestExactlyElevenSuggestionsAreAllPrinted(t *testing.T) {
	status, output, _ := invoke("bo*")
	if status != 1 || strings.Contains(output, "and ") {
		t.Fatalf("eleven-result output = status %d, %q", status, output)
	}
	if lines := strings.Split(strings.TrimSuffix(output, "\n"), "\n"); len(lines) != 12 {
		t.Errorf("line count = %d, want 12", len(lines))
	}
}

func TestNotFoundHelpAndInvalidUsage(t *testing.T) {
	status, output, stderr := invoke("xyzzy")
	if status != 1 || output != "No definition found for \"xyzzy\".\n" || stderr != "" {
		t.Errorf("not found = status %d, stdout %q, stderr %q", status, output, stderr)
	}

	status, output, stderr = invoke("--help")
	if status != 0 || !strings.HasPrefix(output, "Usage: liff") || stderr != "" {
		t.Errorf("help = status %d, stdout %q, stderr %q", status, output, stderr)
	}

	status, output, stderr = invoke("--unknown")
	if status != 2 || output != "" || !strings.HasPrefix(stderr, "Usage: liff") {
		t.Errorf("invalid = status %d, stdout %q, stderr %q", status, output, stderr)
	}
}

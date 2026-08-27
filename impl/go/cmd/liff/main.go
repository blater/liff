package main

import (
	"fmt"
	"io"
	"os"
	"strings"

	"liff"
)

const help = "Usage: liff [WORD ...]\n\n" +
	"With no word, print a random definition. With a word, search the dictionary.\n" +
	"Quoted patterns may use * to match any sequence and ? to match one character."

const (
	fullSuggestionLimit      = 11
	truncatedSuggestionLimit = 10
)

func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }

func run(arguments []string, stdout, stderr io.Writer) int {
	if len(arguments) == 1 && (arguments[0] == "-h" || arguments[0] == "--help") {
		fmt.Fprintln(stdout, help)
		return 0
	}
	for _, argument := range arguments {
		if strings.HasPrefix(argument, "-") {
			fmt.Fprintln(stderr, help)
			return 2
		}
	}

	var query string
	var request liff.Request
	if len(arguments) == 0 {
		request = liff.RandomRequest()
	} else {
		query = strings.Join(arguments, " ")
		request = liff.SearchRequest(query)
	}

	outcome := liff.Resolve(request)
	switch outcome.Kind() {
	case liff.OutcomeFound:
		found, _ := outcome.Found()
		fmt.Fprintf(stdout, "%s\n%s\n", found.Entry().Word(), found.Entry().Definition())
		return 0
	case liff.OutcomeDidYouMean:
		suggestions := outcome.Suggestions()
		fmt.Fprintln(stdout, "Did you mean?")
		displayed := len(suggestions)
		if displayed > fullSuggestionLimit {
			displayed = truncatedSuggestionLimit
		}
		for _, suggestion := range suggestions[:displayed] {
			fmt.Fprintln(stdout, suggestion.Entry().Word())
		}
		if displayed < len(suggestions) {
			fmt.Fprintf(stdout, "and %d others\n", len(suggestions)-displayed)
		}
		return 1
	default:
		fmt.Fprintf(stdout, "No definition found for \"%s\".\n", query)
		return 1
	}
}

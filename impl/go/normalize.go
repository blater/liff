package liff

import "strings"

func normalize(input string) string { return normalizeWith(input, false) }

func normalizeGlob(input string) string { return normalizeWith(input, true) }

func normalizeWith(input string, preserveGlobs bool) string {
	var normalized strings.Builder
	normalized.Grow(len(input))
	separatorPending := false

	for _, character := range input {
		if character == '\'' || character == '\u2019' {
			continue
		}
		isASCIIAlphaNumeric := character >= 'a' && character <= 'z' ||
			character >= 'A' && character <= 'Z' ||
			character >= '0' && character <= '9'
		isGlob := preserveGlobs && (character == '*' || character == '?')
		if isASCIIAlphaNumeric || isGlob {
			if separatorPending && normalized.Len() > 0 {
				normalized.WriteByte(' ')
			}
			if character != '*' || !strings.HasSuffix(normalized.String(), "*") {
				if character >= 'A' && character <= 'Z' {
					character += 'a' - 'A'
				}
				normalized.WriteRune(character)
			}
			separatorPending = false
		} else {
			separatorPending = true
		}
	}

	return normalized.String()
}

pub(crate) fn normalize(input: &str) -> String {
    normalize_with(input, false)
}

pub(crate) fn normalize_glob(input: &str) -> String {
    normalize_with(input, true)
}

fn normalize_with(input: &str, preserve_globs: bool) -> String {
    let mut normalized = String::with_capacity(input.len());
    let mut separator_pending = false;

    for character in input.chars() {
        if matches!(character, '\'' | '\u{2019}') {
            continue;
        }
        if character.is_ascii_alphanumeric() || preserve_globs && matches!(character, '*' | '?') {
            if separator_pending && !normalized.is_empty() {
                normalized.push(' ');
            }
            if character != '*' || !normalized.ends_with('*') {
                normalized.push(character.to_ascii_lowercase());
            }
            separator_pending = false;
        } else {
            separator_pending = true;
        }
    }

    normalized
}

#[cfg(test)]
mod tests {
    use super::{normalize, normalize_glob};

    #[test]
    fn normalizes_case_whitespace_and_punctuation() {
        assert_eq!(normalize("  SYMOND'S---YAT  "), "symonds yat");
        assert_eq!(normalize("Sutton\tand   Cheam"), "sutton and cheam");
    }

    #[test]
    fn punctuation_only_normalizes_to_empty() {
        assert_eq!(normalize(" -- ' -- "), "");
    }

    #[test]
    fn glob_normalization_preserves_wildcards() {
        assert_eq!(normalize_glob("  BIL***  "), "bil*");
        assert_eq!(normalize_glob("SYMOND'S ?AT"), "symonds ?at");
    }
}

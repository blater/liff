use liff_core::{dictionary, MatchKind, Outcome, Request, AUTHOR, TITLE};

#[test]
fn generated_dictionary_is_complete() {
    assert_eq!(TITLE, "The Meaning of Liff");
    assert_eq!(AUTHOR, "Douglas Adams");
    assert_eq!(dictionary().entries().len(), 550);
}

#[test]
fn every_reference_resolves_exactly() {
    for entry in dictionary().entries() {
        for reference in entry.references() {
            match dictionary().search(reference.target()) {
                Outcome::Found(found) => {
                    assert_eq!(found.kind(), MatchKind::Exact);
                    assert_eq!(found.entry().word(), reference.target());
                }
                other => panic!(
                    "{} has unresolved reference {}: {other:?}",
                    entry.word(),
                    reference.target()
                ),
            }
        }
    }
}

#[test]
fn injected_random_index_is_deterministic_and_bounds_checked() {
    let entries = dictionary().entries();
    assert_eq!(dictionary().random_with(|_| 0), entries.first());
    assert_eq!(
        dictionary().random_with(|length| length - 1),
        entries.last()
    );
    assert_eq!(dictionary().random_with(|length| length), None);
}

#[test]
fn random_request_returns_a_dictionary_entry() {
    let Outcome::Found(found) = dictionary().resolve(Request::Random) else {
        panic!("non-empty dictionary must return a random entry");
    };
    assert_eq!(found.kind(), MatchKind::Random);
    assert!(dictionary()
        .entries()
        .iter()
        .any(|entry| entry == found.entry()));
}

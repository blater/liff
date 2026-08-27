use liff_core::{dictionary, Confidence, MatchKind, Outcome};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Contract {
    schema_version: u32,
    cases: Vec<ContractCase>,
}

#[derive(Debug, Deserialize)]
struct ContractCase {
    query: String,
    outcome: String,
    kind: Option<String>,
    word: Option<String>,
    score: Option<u16>,
    suggestions: Option<Vec<ExpectedSuggestion>>,
}

#[derive(Debug, Deserialize)]
struct ExpectedSuggestion {
    word: String,
    confidence: String,
    score: u16,
}

#[test]
fn shared_search_cases_match_the_contract() {
    let contract: Contract = serde_json::from_str(include_str!("../../../../search-cases.json"))
        .expect("shared search cases must be valid JSON");
    assert_eq!(contract.schema_version, 1);

    for case in contract.cases {
        let outcome = dictionary().search(&case.query);
        match (case.outcome.as_str(), outcome) {
            ("found", Outcome::Found(found)) => {
                assert_eq!(
                    Some(found.entry().word()),
                    case.word.as_deref(),
                    "{}",
                    case.query
                );
                assert_eq!(
                    Some(match found.kind() {
                        MatchKind::Random => "random",
                        MatchKind::Exact => "exact",
                        MatchKind::Glob => "glob",
                        MatchKind::HighConfidence => "high_confidence",
                    }),
                    case.kind.as_deref(),
                    "{}",
                    case.query
                );
                if let Some(expected_score) = case.score {
                    assert_eq!(
                        found.score().map(liff_core::Score::basis_points),
                        Some(expected_score),
                        "{}",
                        case.query
                    );
                }
            }
            ("did_you_mean", Outcome::DidYouMean(actual)) => {
                let expected = case
                    .suggestions
                    .as_ref()
                    .expect("suggestion cases must specify suggestions");
                assert_eq!(actual.len(), expected.len(), "{}", case.query);
                for (actual, expected) in actual.iter().zip(expected) {
                    assert_eq!(actual.entry().word(), expected.word, "{}", case.query);
                    assert_eq!(
                        actual.confidence(),
                        match expected.confidence.as_str() {
                            "medium" => Confidence::Medium,
                            "low" => Confidence::Low,
                            other => panic!("unknown confidence {other}"),
                        },
                        "{}",
                        case.query
                    );
                    assert_eq!(
                        actual.score().basis_points(),
                        expected.score,
                        "{}",
                        case.query
                    );
                }
            }
            ("not_found", Outcome::NotFound) => {}
            (expected, actual) => panic!(
                "query {:?}: expected outcome {expected}, got {actual:?}",
                case.query
            ),
        }
    }
}

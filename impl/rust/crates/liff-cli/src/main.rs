use std::env;
use std::process::ExitCode;

use liff_core::{dictionary, Outcome, Request};

const HELP: &str = "Usage: liff [WORD ...]\n\
                    \n\
                    With no word, print a random definition. With a word, search the dictionary.\n\
                    Quoted patterns may use * to match any sequence and ? to match one character.";
const FULL_SUGGESTION_LIMIT: usize = 11;
const TRUNCATED_SUGGESTION_LIMIT: usize = 10;

fn main() -> ExitCode {
    let arguments: Vec<String> = env::args().skip(1).collect();
    if arguments.len() == 1 && matches!(arguments[0].as_str(), "-h" | "--help") {
        println!("{HELP}");
        return ExitCode::SUCCESS;
    }
    if arguments.iter().any(|argument| argument.starts_with('-')) {
        eprintln!("{HELP}");
        return ExitCode::from(2);
    }

    let query = (!arguments.is_empty()).then(|| arguments.join(" "));
    let request = query.as_deref().map_or(Request::Random, Request::Search);

    match dictionary().resolve(request) {
        Outcome::Found(found) => {
            println!("{}\n{}", found.entry().word(), found.entry().definition());
            ExitCode::SUCCESS
        }
        Outcome::DidYouMean(suggestions) => {
            println!("Did you mean?");
            let displayed = if suggestions.len() <= FULL_SUGGESTION_LIMIT {
                suggestions.len()
            } else {
                TRUNCATED_SUGGESTION_LIMIT
            };
            for suggestion in &suggestions[..displayed] {
                println!("{}", suggestion.entry().word());
            }
            if displayed < suggestions.len() {
                println!("and {} others", suggestions.len() - displayed);
            }
            ExitCode::from(1)
        }
        Outcome::NotFound => {
            println!(
                "No definition found for \"{}\".",
                query.as_deref().unwrap_or_default()
            );
            ExitCode::from(1)
        }
    }
}

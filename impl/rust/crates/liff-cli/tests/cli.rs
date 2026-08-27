use std::process::{Command, Output};

use liff_core::dictionary;

fn run(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_liff"))
        .args(arguments)
        .output()
        .expect("liff CLI must run")
}

fn stdout(output: &Output) -> String {
    String::from_utf8(output.stdout.clone()).expect("CLI stdout must be UTF-8")
}

#[test]
fn no_arguments_prints_a_random_entry() {
    let output = run(&[]);
    assert!(output.status.success());
    let output = stdout(&output);
    let (word, definition) = output
        .trim_end()
        .split_once('\n')
        .expect("random output must contain a word and definition");
    let entry = dictionary()
        .entries()
        .iter()
        .find(|entry| entry.word() == word)
        .expect("random word must exist");
    assert_eq!(definition, entry.definition());
}

#[test]
fn exact_and_high_confidence_matches_print_the_entry() {
    for arguments in [&["banteer"][..], &["banteeer"][..]] {
        let output = run(arguments);
        assert!(output.status.success());
        assert!(stdout(&output).starts_with("BANTEER\nA lusty and raucous old ballad"));
    }
}

#[test]
fn complete_token_prefix_is_a_high_confidence_match() {
    let output = run(&["glutt"]);
    assert!(output.status.success());
    assert!(stdout(&output).starts_with("GLUTT LODGE\n"));
}

#[test]
fn unique_partial_prefix_is_an_automatic_match() {
    let output = run(&["bilb"]);
    assert!(output.status.success());
    assert!(stdout(&output).starts_with("BILBSTER\n"));
}

#[test]
fn unique_glob_match_prints_the_entry() {
    let output = run(&["bil*"]);
    assert!(output.status.success());
    assert!(stdout(&output).starts_with("BILBSTER\n"));
}

#[test]
fn eleven_glob_matches_are_all_printed() {
    let output = run(&["bo*"]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stdout(&output),
        "Did you mean?\n\
         BODMIN\n\
         BOLSOVER\n\
         BONKLE\n\
         BOOLTEENS\n\
         BOOTHBY GRAFFOE\n\
         BOSCASTLE\n\
         BOTCHERBY\n\
         BOTLEY\n\
         BOTOLPHS\n\
         BOTUSFLEMING\n\
         BOZEMAN\n"
    );
}

#[test]
fn large_glob_result_prints_ten_and_the_remaining_count() {
    let output = run(&["b*"]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stdout(&output),
        "Did you mean?\n\
         BABWORTH\n\
         BALDOCK\n\
         BALLYCUMBER\n\
         BANFF\n\
         BANTEER\n\
         BARSTIBLEY\n\
         BAUGHURST\n\
         BAUMBER\n\
         BEALINGS\n\
         BEAULIEU HILL\n\
         and 44 others\n"
    );
}

#[test]
fn all_entries_glob_is_truncated_with_the_remaining_count() {
    let output = run(&["*"]);
    assert_eq!(output.status.code(), Some(1));
    let output = stdout(&output);
    assert!(output.starts_with("Did you mean?\nAASLEAGH\nABERBEEG\n"));
    assert_eq!(output.lines().count(), 12);
    assert!(output.ends_with("and 540 others\n"));
}

#[test]
fn ambiguous_complete_token_prefix_prints_suggestions() {
    let output = run(&["high"]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stdout(&output),
        "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n"
    );
}

#[test]
fn positional_arguments_form_one_multiword_query() {
    let output = run(&["symonds", "yat"]);
    assert!(output.status.success());
    assert!(stdout(&output).starts_with("SYMOND'S YAT\n"));
}

#[test]
fn unique_candidate_at_or_above_700_is_an_automatic_match() {
    let output = run(&["kentt"]);
    assert!(output.status.success());
    assert!(stdout(&output).starts_with("KENT\n"));
}

#[test]
fn low_match_prints_not_found_and_exits_one() {
    let output = run(&["xyzzy"]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(stdout(&output), "No definition found for \"xyzzy\".\n");
}

#[test]
fn help_and_invalid_options_have_stable_exit_codes() {
    let help = run(&["--help"]);
    assert!(help.status.success());
    assert!(stdout(&help).starts_with("Usage: liff"));

    let invalid = run(&["--unknown"]);
    assert_eq!(invalid.status.code(), Some(2));
    assert!(invalid.stdout.is_empty());
    assert!(String::from_utf8(invalid.stderr)
        .expect("CLI stderr must be UTF-8")
        .starts_with("Usage: liff"));
}

//! Typed, reusable access to the generated Meaning of Liff dictionary.
//!
//! Use [`dictionary`] for direct operations or [`resolve`] for the unified
//! random/search request interface shared by the command-line implementation.

#![warn(missing_docs)]

mod generated;
mod model;
mod normalize;
mod search;

use std::sync::OnceLock;

pub use model::{Entry, Reference};
pub use search::{
    Confidence, Dictionary, Found, MatchKind, Outcome, Request, Score, Suggestion,
    HIGH_CONFIDENCE_MIN, LOW_SUGGESTION_LIMIT, MEDIUM_CONFIDENCE_MIN, PARTIAL_PREFIX_SCORE,
    PREFIX_MIN_CHARS, TOKEN_PREFIX_SCORE,
};

/// Title recorded in the source dictionary.
pub const TITLE: &str = generated::TITLE;
/// Author recorded in the source dictionary.
pub const AUTHOR: &str = generated::AUTHOR;

static DICTIONARY: OnceLock<Dictionary> = OnceLock::new();

#[must_use]
/// Return the lazily initialized global dictionary.
pub fn dictionary() -> &'static Dictionary {
    DICTIONARY.get_or_init(Dictionary::liff)
}

#[must_use]
/// Resolve a random or search request against the global dictionary.
pub fn resolve(request: Request<'_>) -> Outcome {
    dictionary().resolve(request)
}

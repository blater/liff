#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// A cross-reference embedded in an entry definition.
pub struct Reference {
    target: &'static str,
    relation: &'static str,
    label: &'static str,
}

impl Reference {
    pub(crate) const fn new(
        target: &'static str,
        relation: &'static str,
        label: &'static str,
    ) -> Self {
        Self {
            target,
            relation,
            label,
        }
    }

    #[must_use]
    /// Return the canonical target headword.
    pub const fn target(&self) -> &'static str {
        self.target
    }

    #[must_use]
    /// Return the source relation, such as `q.v.` or `see_also`.
    pub const fn relation(&self) -> &'static str {
        self.relation
    }

    #[must_use]
    /// Return the spelling displayed in the source definition.
    pub const fn label(&self) -> &'static str {
        self.label
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
/// One immutable dictionary entry compiled into the program.
pub struct Entry {
    word: &'static str,
    part_of_speech: Option<&'static str>,
    definition: &'static str,
    references: &'static [Reference],
}

impl Entry {
    pub(crate) const fn new(
        word: &'static str,
        part_of_speech: Option<&'static str>,
        definition: &'static str,
        references: &'static [Reference],
    ) -> Self {
        Self {
            word,
            part_of_speech,
            definition,
            references,
        }
    }

    #[must_use]
    /// Return the canonical headword.
    pub const fn word(&self) -> &'static str {
        self.word
    }

    #[must_use]
    /// Return the source part-of-speech label, when present.
    pub const fn part_of_speech(&self) -> Option<&'static str> {
        self.part_of_speech
    }

    #[must_use]
    /// Return the definition.
    pub const fn definition(&self) -> &'static str {
        self.definition
    }

    #[must_use]
    /// Return all structured cross-references in source order.
    pub const fn references(&self) -> &'static [Reference] {
        self.references
    }
}

const std = @import("std");
const liff = @import("liff.zig");
const normalizer = @import("normalize.zig");

const SearchContract = struct {
    schema_version: u32,
    cases: []SearchCase,
};

const SearchCase = struct {
    query: []const u8,
    outcome: []const u8,
    kind: ?[]const u8 = null,
    word: ?[]const u8 = null,
    score: ?u16 = null,
    suggestions: ?[]ExpectedSuggestion = null,
};

const ExpectedSuggestion = struct {
    word: []const u8,
    confidence: []const u8,
    score: u16,
};

test "shared search cases" {
    const allocator = std.testing.allocator;
    var dictionary = try liff.Dictionary.initGenerated(allocator);
    defer dictionary.deinit();
    const fixture = try readFixture(allocator, "impl/search-cases.json");
    defer allocator.free(fixture);
    var parsed = try std.json.parseFromSlice(
        SearchContract,
        allocator,
        fixture,
        .{},
    );
    defer parsed.deinit();
    try std.testing.expectEqual(@as(u32, 1), parsed.value.schema_version);

    for (parsed.value.cases) |case| {
        var outcome = try dictionary.search(allocator, case.query);
        defer outcome.deinit(allocator);
        if (std.mem.eql(u8, case.outcome, "found")) {
            switch (outcome) {
                .found => |found| {
                    try std.testing.expectEqualStrings(case.word.?, found.entry.word);
                    try std.testing.expectEqualStrings(case.kind.?, @tagName(found.kind));
                    if (case.score) |score| try std.testing.expectEqual(score, found.score.?);
                },
                else => return error.ExpectedFound,
            }
        } else if (std.mem.eql(u8, case.outcome, "did_you_mean")) {
            switch (outcome) {
                .did_you_mean => |suggestions| {
                    const expected = case.suggestions.?;
                    try std.testing.expectEqual(expected.len, suggestions.len);
                    for (suggestions, expected) |actual, wanted| {
                        try std.testing.expectEqualStrings(wanted.word, actual.entry.word);
                        try std.testing.expectEqualStrings(
                            wanted.confidence,
                            @tagName(actual.confidence),
                        );
                        try std.testing.expectEqual(wanted.score, actual.score);
                    }
                },
                else => return error.ExpectedDidYouMean,
            }
        } else if (std.mem.eql(u8, case.outcome, "not_found")) {
            switch (outcome) {
                .not_found => {},
                else => return error.ExpectedNotFound,
            }
        } else {
            return error.UnknownExpectedOutcome;
        }
    }
}

const AlgorithmContract = struct {
    schema_version: u32,
    normalization: []NormalizationCase,
    glob_normalization: []NormalizationCase,
    edit_scores: []EditScoreCase,
    candidate_scores: []CandidateScoreCase,
    glob_matches: []GlobCase,
    ordering: []OrderingCase,
};

const NormalizationCase = struct {
    input: []const u8,
    output: []const u8,
};

const EditScoreCase = struct {
    left: []const u8,
    right: []const u8,
    distance: usize,
    score: u16,
};

const CandidateScoreCase = struct {
    query: []const u8,
    candidate: []const u8,
    score: u16,
};

const GlobCase = struct {
    pattern: []const u8,
    candidate: []const u8,
    matches: bool,
};

const OrderingCase = struct {
    input: [][]const u8,
    ascending: [][]const u8,
};

test "shared algorithm cases" {
    const allocator = std.testing.allocator;
    const fixture = try readFixture(allocator, "impl/algorithm-cases.json");
    defer allocator.free(fixture);
    var parsed = try std.json.parseFromSlice(
        AlgorithmContract,
        allocator,
        fixture,
        .{},
    );
    defer parsed.deinit();
    try std.testing.expectEqual(@as(u32, 1), parsed.value.schema_version);

    for (parsed.value.normalization) |case| {
        const actual = try normalizer.normalize(allocator, case.input);
        defer allocator.free(actual);
        try std.testing.expectEqualStrings(case.output, actual);
    }
    for (parsed.value.glob_normalization) |case| {
        const actual = try normalizer.normalizeGlob(allocator, case.input);
        defer allocator.free(actual);
        try std.testing.expectEqualStrings(case.output, actual);
    }
    for (parsed.value.edit_scores) |case| {
        try std.testing.expectEqual(
            case.distance,
            try liff.damerauLevenshtein(allocator, case.left, case.right),
        );
        try std.testing.expectEqual(
            case.score,
            try liff.similarityScore(allocator, case.left, case.right),
        );
    }
    for (parsed.value.candidate_scores) |case| {
        try std.testing.expectEqual(
            case.score,
            try liff.candidateScore(allocator, case.query, case.candidate),
        );
    }
    for (parsed.value.glob_matches) |case| {
        try std.testing.expectEqual(
            case.matches,
            try liff.globMatches(allocator, case.pattern, case.candidate),
        );
    }
    for (parsed.value.ordering) |case| {
        const actual = try allocator.dupe([]const u8, case.input);
        defer allocator.free(actual);
        std.mem.sort([]const u8, actual, {}, lessThanString);
        try std.testing.expectEqual(case.ascending.len, actual.len);
        for (actual, case.ascending) |value, expected| {
            try std.testing.expectEqualStrings(expected, value);
        }
    }
}

fn lessThanString(_: void, left: []const u8, right: []const u8) bool {
    return std.mem.order(u8, left, right) == .lt;
}

test "generated dictionary exactly matches source and references resolve" {
    const allocator = std.testing.allocator;
    var dictionary = try liff.Dictionary.initGenerated(allocator);
    defer dictionary.deinit();
    const fixture = try readFixture(allocator, "liff.json");
    defer allocator.free(fixture);
    var parsed = try std.json.parseFromSlice(
        std.json.Value,
        allocator,
        fixture,
        .{},
    );
    defer parsed.deinit();

    const root = parsed.value.object;
    try std.testing.expectEqual(@as(i64, 1), root.get("schema_version").?.integer);
    try std.testing.expectEqualStrings(liff.title, root.get("title").?.string);
    try std.testing.expectEqualStrings(liff.author, root.get("author").?.string);
    const source_entries = root.get("entries").?.object;
    try std.testing.expectEqual(source_entries.count(), dictionary.entries().len);

    var iterator = source_entries.iterator();
    var index: usize = 0;
    while (iterator.next()) |source| : (index += 1) {
        const entry = dictionary.entries()[index];
        try std.testing.expectEqualStrings(source.key_ptr.*, entry.word);
        const value = source.value_ptr.object;
        try std.testing.expectEqualStrings(value.get("definition").?.string, entry.definition);
        const source_part = value.get("part_of_speech").?;
        switch (source_part) {
            .null => try std.testing.expect(entry.part_of_speech == null),
            .string => |part| try std.testing.expectEqualStrings(part, entry.part_of_speech.?),
            else => return error.InvalidPartOfSpeech,
        }
        const references = value.get("references").?.array.items;
        try std.testing.expectEqual(references.len, entry.references.len);
        for (references, entry.references) |source_reference, reference| {
            const object = source_reference.object;
            try std.testing.expectEqualStrings(object.get("target").?.string, reference.target);
            try std.testing.expectEqualStrings(object.get("relation").?.string, reference.relation);
            try std.testing.expectEqualStrings(object.get("label").?.string, reference.label);

            var outcome = try dictionary.search(allocator, reference.target);
            defer outcome.deinit(allocator);
            switch (outcome) {
                .found => |found| {
                    try std.testing.expectEqual(liff.MatchKind.exact, found.kind);
                    try std.testing.expectEqualStrings(reference.target, found.entry.word);
                },
                else => return error.UnresolvedReference,
            }
        }
    }
}

fn readFixture(allocator: std.mem.Allocator, path: []const u8) ![]u8 {
    return std.Io.Dir.cwd().readFileAlloc(
        std.testing.io,
        path,
        allocator,
        .limited(10 * 1024 * 1024),
    );
}

test "random selection seam and empty dictionary" {
    var dictionary = try liff.Dictionary.initGenerated(std.testing.allocator);
    defer dictionary.deinit();
    try std.testing.expectEqualStrings(
        dictionary.entries()[0].word,
        dictionary.randomWith(0).?.word,
    );
    try std.testing.expectEqualStrings(
        dictionary.entries()[dictionary.entries().len - 1].word,
        dictionary.randomWith(dictionary.entries().len - 1).?.word,
    );
    try std.testing.expect(dictionary.randomWith(dictionary.entries().len) == null);
    var empty = try liff.Dictionary.init(std.testing.allocator, &.{});
    defer empty.deinit();
    try std.testing.expect(empty.randomWith(0) == null);

    var prng = std.Random.DefaultPrng.init(42);
    var outcome = try dictionary.resolve(
        std.testing.allocator,
        .random,
        prng.random(),
    );
    defer outcome.deinit(std.testing.allocator);
    switch (outcome) {
        .found => |found| {
            try std.testing.expectEqual(liff.MatchKind.random, found.kind);
            try std.testing.expect(found.score == null);
        },
        else => return error.ExpectedRandomEntry,
    }
}

test "dictionary construction rejects duplicate normalized headwords" {
    const duplicate_entries = [_]liff.Entry{
        .{
            .word = "A-B",
            .part_of_speech = null,
            .definition = "first",
            .references = &.{},
        },
        .{
            .word = "A B",
            .part_of_speech = null,
            .definition = "second",
            .references = &.{},
        },
    };
    try std.testing.expectError(
        error.DuplicateNormalizedHeadword,
        liff.Dictionary.init(std.testing.allocator, &duplicate_entries),
    );
}

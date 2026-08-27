const std = @import("std");
const generated = @import("dictionary_generated.zig");
const normalizer = @import("normalize.zig");

pub const model = @import("model.zig");
pub const Reference = model.Reference;
pub const Entry = model.Entry;
pub const MatchKind = model.MatchKind;
pub const Confidence = model.Confidence;
pub const Found = model.Found;
pub const Suggestion = model.Suggestion;
pub const Outcome = model.Outcome;
pub const Request = model.Request;

pub const title = generated.title;
pub const author = generated.author;

pub const perfect_score: u16 = 1000;
pub const qualifying_score: u16 = 700;
pub const low_suggestion_count: usize = 2;
pub const token_prefix_score: u16 = 900;
pub const partial_prefix_score: u16 = 750;
pub const prefix_min_code_points: usize = 4;

const ScoredCandidate = struct {
    entry: *const Entry,
    score: u16,
};

const IndexedEntry = struct {
    entry: *const Entry,
    normalized: []u8,
};

pub const Dictionary = struct {
    source_entries: []const Entry,
    index: []IndexedEntry,
    allocator: std.mem.Allocator,

    pub fn init(
        allocator: std.mem.Allocator,
        source_entries: []const Entry,
    ) !Dictionary {
        const index = try allocator.alloc(IndexedEntry, source_entries.len);
        var initialized: usize = 0;
        errdefer {
            for (index[0..initialized]) |indexed| allocator.free(indexed.normalized);
            allocator.free(index);
        }
        for (source_entries, index) |*entry, *indexed| {
            indexed.* = .{
                .entry = entry,
                .normalized = try normalizer.normalize(allocator, entry.word),
            };
            initialized += 1;
        }
        std.mem.sort(IndexedEntry, index, {}, compareIndexedEntries);
        var position: usize = 1;
        while (position < index.len) : (position += 1) {
            if (std.mem.eql(u8, index[position - 1].normalized, index[position].normalized)) {
                return error.DuplicateNormalizedHeadword;
            }
        }
        return .{
            .source_entries = source_entries,
            .index = index,
            .allocator = allocator,
        };
    }

    pub fn initGenerated(allocator: std.mem.Allocator) !Dictionary {
        return init(allocator, &generated.entries);
    }

    pub fn deinit(self: *Dictionary) void {
        for (self.index) |indexed| self.allocator.free(indexed.normalized);
        self.allocator.free(self.index);
        self.* = undefined;
    }

    pub fn entries(self: *const Dictionary) []const Entry {
        return self.source_entries;
    }

    pub fn resolve(
        self: *const Dictionary,
        allocator: std.mem.Allocator,
        request: Request,
        random_source: std.Random,
    ) !Outcome {
        return switch (request) {
            .random => if (self.random(random_source)) |entry|
                .{ .found = .{ .entry = entry, .kind = .random, .score = null } }
            else
                .not_found,
            .search => |query| self.search(allocator, query),
        };
    }

    pub fn random(self: *const Dictionary, random_source: std.Random) ?*const Entry {
        if (self.source_entries.len == 0) return null;
        return &self.source_entries[random_source.uintLessThan(usize, self.source_entries.len)];
    }

    pub fn randomWith(self: *const Dictionary, index: usize) ?*const Entry {
        if (index >= self.source_entries.len) return null;
        return &self.source_entries[index];
    }

    pub fn search(
        self: *const Dictionary,
        allocator: std.mem.Allocator,
        query: []const u8,
    ) !Outcome {
        if (std.mem.indexOfAny(u8, query, "*?") != null) {
            return self.searchGlob(allocator, query);
        }

        const normalized_query = try normalizer.normalize(allocator, query);
        defer allocator.free(normalized_query);
        if (normalized_query.len == 0) return .not_found;

        const exact_position = lowerBound(self.index, normalized_query);
        if (exact_position < self.index.len) {
            const indexed = self.index[exact_position];
            if (std.mem.eql(u8, normalized_query, indexed.normalized)) {
                return .{ .found = .{
                    .entry = indexed.entry,
                    .kind = .exact,
                    .score = perfect_score,
                } };
            }
        }

        const ranked = try allocator.alloc(ScoredCandidate, self.index.len);
        defer allocator.free(ranked);
        for (self.index, ranked) |indexed, *candidate| {
            candidate.* = .{
                .entry = indexed.entry,
                .score = try candidateScore(allocator, normalized_query, indexed.normalized),
            };
        }
        std.mem.sort(ScoredCandidate, ranked, {}, compareScoredCandidates);

        var qualified_count: usize = 0;
        while (qualified_count < ranked.len and
            ranked[qualified_count].score >= qualifying_score)
        {
            qualified_count += 1;
        }
        if (qualified_count == 1) {
            return .{ .found = .{
                .entry = ranked[0].entry,
                .kind = .high_confidence,
                .score = ranked[0].score,
            } };
        }
        if (qualified_count == 0) return .not_found;

        const suggestion_count = @min(
            ranked.len,
            qualified_count + low_suggestion_count,
        );
        const suggestions = try allocator.alloc(Suggestion, suggestion_count);
        for (ranked[0..qualified_count], suggestions[0..qualified_count]) |candidate, *suggestion| {
            suggestion.* = .{
                .entry = candidate.entry,
                .confidence = .medium,
                .score = candidate.score,
            };
        }
        for (ranked[qualified_count..suggestion_count], suggestions[qualified_count..]) |candidate, *suggestion| {
            suggestion.* = .{
                .entry = candidate.entry,
                .confidence = .low,
                .score = candidate.score,
            };
        }
        return .{ .did_you_mean = suggestions };
    }

    fn searchGlob(
        self: *const Dictionary,
        allocator: std.mem.Allocator,
        query: []const u8,
    ) !Outcome {
        const pattern = try normalizer.normalizeGlob(allocator, query);
        defer allocator.free(pattern);
        if (pattern.len == 0) return .not_found;

        var matches: std.ArrayList(*const Entry) = .empty;
        defer matches.deinit(allocator);
        for (self.index) |indexed| {
            if (try globMatches(allocator, pattern, indexed.normalized)) {
                try matches.append(allocator, indexed.entry);
            }
        }

        if (matches.items.len == 0) return .not_found;
        if (matches.items.len == 1) {
            return .{ .found = .{
                .entry = matches.items[0],
                .kind = .glob,
                .score = perfect_score,
            } };
        }

        const suggestions = try allocator.alloc(Suggestion, matches.items.len);
        for (matches.items, suggestions) |entry, *suggestion| {
            suggestion.* = .{
                .entry = entry,
                .confidence = .medium,
                .score = perfect_score,
            };
        }
        return .{ .did_you_mean = suggestions };
    }
};

pub const generated_entries = generated.entries;

fn compareIndexedEntries(_: void, left: IndexedEntry, right: IndexedEntry) bool {
    return std.mem.order(u8, left.normalized, right.normalized) == .lt;
}

fn lowerBound(index: []const IndexedEntry, query: []const u8) usize {
    var lower: usize = 0;
    var upper = index.len;
    while (lower < upper) {
        const middle = lower + (upper - lower) / 2;
        if (std.mem.order(u8, index[middle].normalized, query) == .lt) {
            lower = middle + 1;
        } else {
            upper = middle;
        }
    }
    return lower;
}

fn compareScoredCandidates(_: void, left: ScoredCandidate, right: ScoredCandidate) bool {
    if (left.score != right.score) return left.score > right.score;
    return std.mem.order(u8, left.entry.word, right.entry.word) == .lt;
}

pub fn similarityScore(
    allocator: std.mem.Allocator,
    left: []const u8,
    right: []const u8,
) !u16 {
    const maximum = @max(left.len, right.len);
    if (maximum == 0) return perfect_score;
    const distance = try damerauLevenshtein(allocator, left, right);
    const retained = maximum -| distance;
    return @intCast(retained * 1000 / maximum);
}

pub fn candidateScore(
    allocator: std.mem.Allocator,
    query: []const u8,
    candidate: []const u8,
) !u16 {
    const edit_score = try similarityScore(allocator, query, candidate);
    if (query.len < prefix_min_code_points) return edit_score;
    if (std.mem.startsWith(u8, candidate, query) and
        candidate.len > query.len and candidate[query.len] == ' ')
    {
        return @max(edit_score, token_prefix_score);
    }
    if (std.mem.startsWith(u8, candidate, query)) {
        return @max(edit_score, partial_prefix_score);
    }
    return edit_score;
}

pub fn globMatches(
    allocator: std.mem.Allocator,
    pattern: []const u8,
    candidate: []const u8,
) !bool {
    const previous_buffer = try allocator.alloc(bool, candidate.len + 1);
    defer allocator.free(previous_buffer);
    const current_buffer = try allocator.alloc(bool, candidate.len + 1);
    defer allocator.free(current_buffer);
    @memset(previous_buffer, false);
    previous_buffer[0] = true;
    var previous = previous_buffer;
    var current = current_buffer;

    for (pattern) |pattern_character| {
        @memset(current, false);
        if (pattern_character == '*') current[0] = previous[0];
        for (candidate, 1..) |candidate_character, column| {
            current[column] = switch (pattern_character) {
                '*' => previous[column] or current[column - 1],
                '?' => previous[column - 1],
                else => previous[column - 1] and pattern_character == candidate_character,
            };
        }
        const swap = previous;
        previous = current;
        current = swap;
    }
    return previous[candidate.len];
}

pub fn damerauLevenshtein(
    allocator: std.mem.Allocator,
    left: []const u8,
    right: []const u8,
) !usize {
    const previous_previous_buffer = try allocator.alloc(usize, right.len + 1);
    defer allocator.free(previous_previous_buffer);
    const previous_buffer = try allocator.alloc(usize, right.len + 1);
    defer allocator.free(previous_buffer);
    const current_buffer = try allocator.alloc(usize, right.len + 1);
    defer allocator.free(current_buffer);
    var previous_previous = previous_previous_buffer;
    @memset(previous_previous, 0);
    var previous = previous_buffer;
    for (previous, 0..) |*value, index| value.* = index;
    var current = current_buffer;

    for (left, 1..) |left_character, row| {
        current[0] = row;
        for (right, 1..) |right_character, column| {
            const substitution_cost: usize = @intFromBool(left_character != right_character);
            current[column] = @min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + substitution_cost,
            );
            if (row > 1 and column > 1 and
                left_character == right[column - 2] and left[row - 2] == right_character)
            {
                current[column] = @min(
                    current[column],
                    previous_previous[column - 2] + 1,
                );
            }
        }
        const old_previous_previous = previous_previous;
        previous_previous = previous;
        previous = current;
        current = old_previous_previous;
    }
    return previous[right.len];
}

test {
    _ = normalizer;
}

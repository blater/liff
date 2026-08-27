const std = @import("std");

pub const Reference = struct {
    target: []const u8,
    relation: []const u8,
    label: []const u8,
};

pub const Entry = struct {
    word: []const u8,
    part_of_speech: ?[]const u8,
    definition: []const u8,
    references: []const Reference,
};

pub const MatchKind = enum {
    random,
    exact,
    glob,
    high_confidence,
};

pub const Confidence = enum {
    medium,
    low,
};

pub const Found = struct {
    entry: *const Entry,
    kind: MatchKind,
    score: ?u16,
};

pub const Suggestion = struct {
    entry: *const Entry,
    confidence: Confidence,
    score: u16,
};

pub const Outcome = union(enum) {
    found: Found,
    did_you_mean: []Suggestion,
    not_found,

    pub fn deinit(self: *Outcome, allocator: std.mem.Allocator) void {
        switch (self.*) {
            .did_you_mean => |suggestions| allocator.free(suggestions),
            else => {},
        }
        self.* = undefined;
    }
};

pub const Request = union(enum) {
    random,
    search: []const u8,
};

const std = @import("std");
const liff = @import("liff.zig");

const help =
    \\Usage: liff [WORD ...]
    \\
    \\With no word, print a random definition. With a word, search the dictionary.
    \\Quoted patterns may use * to match any sequence and ? to match one character.
;

const full_suggestion_limit: usize = 11;
const truncated_suggestion_limit: usize = 10;

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    const args = try init.minimal.args.toSlice(init.arena.allocator());

    var stdout_buffer: [4096]u8 = undefined;
    var stdout_file_writer = std.Io.File.stdout().writer(init.io, &stdout_buffer);
    const stdout = &stdout_file_writer.interface;
    var stderr_buffer: [4096]u8 = undefined;
    var stderr_file_writer = std.Io.File.stderr().writer(init.io, &stderr_buffer);
    const stderr = &stderr_file_writer.interface;

    var seed: u64 = undefined;
    init.io.random(std.mem.asBytes(&seed));
    var prng = std.Random.DefaultPrng.init(seed);
    var dictionary = try liff.Dictionary.initGenerated(allocator);
    defer dictionary.deinit();
    const random_index = if (dictionary.entries().len == 0)
        0
    else
        prng.random().uintLessThan(usize, dictionary.entries().len);

    const status = try run(&dictionary, allocator, args[1..], stdout, stderr, random_index);
    try stdout.flush();
    try stderr.flush();
    if (status != 0) std.process.exit(status);
}

pub fn run(
    dictionary: *const liff.Dictionary,
    allocator: std.mem.Allocator,
    arguments: []const []const u8,
    stdout: *std.Io.Writer,
    stderr: *std.Io.Writer,
    random_index: usize,
) !u8 {
    if (arguments.len == 1 and
        (std.mem.eql(u8, arguments[0], "-h") or
            std.mem.eql(u8, arguments[0], "--help")))
    {
        try stdout.print("{s}\n", .{help});
        return 0;
    }
    for (arguments) |argument| {
        if (argument.len > 0 and argument[0] == '-') {
            try stderr.print("{s}\n", .{help});
            return 2;
        }
    }

    var outcome: liff.Outcome = undefined;
    var query: []u8 = undefined;
    if (arguments.len == 0) {
        outcome = if (dictionary.randomWith(random_index)) |entry|
            .{ .found = .{ .entry = entry, .kind = .random, .score = null } }
        else
            .not_found;
        query = try allocator.alloc(u8, 0);
    } else {
        query = try std.mem.join(allocator, " ", arguments);
        outcome = try dictionary.search(allocator, query);
    }
    defer allocator.free(query);
    defer outcome.deinit(allocator);

    switch (outcome) {
        .found => |found| {
            try stdout.print("{s}\n{s}\n", .{ found.entry.word, found.entry.definition });
            return 0;
        },
        .did_you_mean => |suggestions| {
            try stdout.writeAll("Did you mean?\n");
            const displayed = if (suggestions.len <= full_suggestion_limit)
                suggestions.len
            else
                truncated_suggestion_limit;
            for (suggestions[0..displayed]) |suggestion| {
                try stdout.print("{s}\n", .{suggestion.entry.word});
            }
            if (displayed < suggestions.len) {
                try stdout.print("and {d} others\n", .{suggestions.len - displayed});
            }
            return 1;
        },
        .not_found => {
            try stdout.print("No definition found for \"{s}\".\n", .{query});
            return 1;
        },
    }
}

fn invoke(arguments: []const []const u8) !struct { status: u8, stdout: []u8, stderr: []u8 } {
    const allocator = std.testing.allocator;
    var dictionary = try liff.Dictionary.initGenerated(allocator);
    defer dictionary.deinit();
    var stdout: std.Io.Writer.Allocating = .init(allocator);
    errdefer stdout.deinit();
    var stderr: std.Io.Writer.Allocating = .init(allocator);
    errdefer stderr.deinit();
    const status = try run(&dictionary, allocator, arguments, &stdout.writer, &stderr.writer, 0);
    return .{
        .status = status,
        .stdout = try stdout.toOwnedSlice(),
        .stderr = try stderr.toOwnedSlice(),
    };
}

test "CLI random, found, and not-found outcomes" {
    const allocator = std.testing.allocator;
    const random_result = try invoke(&.{});
    defer allocator.free(random_result.stdout);
    defer allocator.free(random_result.stderr);
    try std.testing.expectEqual(@as(u8, 0), random_result.status);
    try std.testing.expect(std.mem.startsWith(u8, random_result.stdout, "AASLEAGH\n"));
    try std.testing.expectEqualStrings("", random_result.stderr);

    const found = try invoke(&.{"bil*"});
    defer allocator.free(found.stdout);
    defer allocator.free(found.stderr);
    try std.testing.expectEqual(@as(u8, 0), found.status);
    try std.testing.expect(std.mem.startsWith(u8, found.stdout, "BILBSTER\n"));

    const missing = try invoke(&.{"xyzzy"});
    defer allocator.free(missing.stdout);
    defer allocator.free(missing.stderr);
    try std.testing.expectEqual(@as(u8, 1), missing.status);
    try std.testing.expectEqualStrings(
        "No definition found for \"xyzzy\".\n",
        missing.stdout,
    );
}

test "CLI suggestions and glob display boundaries" {
    const allocator = std.testing.allocator;
    const ambiguous = try invoke(&.{"high"});
    defer allocator.free(ambiguous.stdout);
    defer allocator.free(ambiguous.stderr);
    try std.testing.expectEqual(@as(u8, 1), ambiguous.status);
    try std.testing.expectEqualStrings(
        "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n",
        ambiguous.stdout,
    );

    const large = try invoke(&.{"b*"});
    defer allocator.free(large.stdout);
    defer allocator.free(large.stderr);
    try std.testing.expectEqual(@as(u8, 1), large.status);
    try std.testing.expect(std.mem.endsWith(u8, large.stdout, "and 44 others\n"));

    const eleven = try invoke(&.{"bo*"});
    defer allocator.free(eleven.stdout);
    defer allocator.free(eleven.stderr);
    try std.testing.expectEqual(@as(u8, 1), eleven.status);
    try std.testing.expect(std.mem.indexOf(u8, eleven.stdout, "and ") == null);
    try std.testing.expectEqual(@as(usize, 12), std.mem.count(u8, eleven.stdout, "\n"));

    const all = try invoke(&.{"*"});
    defer allocator.free(all.stdout);
    defer allocator.free(all.stderr);
    try std.testing.expectEqual(@as(u8, 1), all.status);
    try std.testing.expect(std.mem.endsWith(u8, all.stdout, "and 540 others\n"));
}

test "CLI help and invalid usage" {
    const allocator = std.testing.allocator;
    const help_result = try invoke(&.{"--help"});
    defer allocator.free(help_result.stdout);
    defer allocator.free(help_result.stderr);
    try std.testing.expectEqual(@as(u8, 0), help_result.status);
    try std.testing.expect(std.mem.startsWith(u8, help_result.stdout, "Usage: liff"));

    const invalid = try invoke(&.{"--unknown"});
    defer allocator.free(invalid.stdout);
    defer allocator.free(invalid.stderr);
    try std.testing.expectEqual(@as(u8, 2), invalid.status);
    try std.testing.expectEqualStrings("", invalid.stdout);
    try std.testing.expect(std.mem.startsWith(u8, invalid.stderr, "Usage: liff"));
}

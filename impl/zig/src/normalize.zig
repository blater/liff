const std = @import("std");

pub fn normalize(allocator: std.mem.Allocator, input: []const u8) ![]u8 {
    return normalizeWith(allocator, input, false);
}

pub fn normalizeGlob(allocator: std.mem.Allocator, input: []const u8) ![]u8 {
    return normalizeWith(allocator, input, true);
}

fn normalizeWith(
    allocator: std.mem.Allocator,
    input: []const u8,
    preserve_globs: bool,
) ![]u8 {
    var output: std.ArrayList(u8) = .empty;
    errdefer output.deinit(allocator);
    try output.ensureTotalCapacity(allocator, input.len);
    var separator_pending = false;
    var index: usize = 0;

    while (index < input.len) {
        if (input[index] == '\'') {
            index += 1;
            continue;
        }
        if (std.mem.startsWith(u8, input[index..], "\xE2\x80\x99")) {
            index += 3;
            continue;
        }

        const character = input[index];
        const is_ascii_alphanumeric = std.ascii.isAlphanumeric(character);
        const is_glob = preserve_globs and (character == '*' or character == '?');
        if (is_ascii_alphanumeric or is_glob) {
            if (separator_pending and output.items.len > 0) {
                try output.append(allocator, ' ');
            }
            const lowered = std.ascii.toLower(character);
            if (lowered != '*' or output.items.len == 0 or output.items[output.items.len - 1] != '*') {
                try output.append(allocator, lowered);
            }
            separator_pending = false;
            index += 1;
        } else {
            separator_pending = true;
            const sequence_length = std.unicode.utf8ByteSequenceLength(character) catch 1;
            index += @min(sequence_length, input.len - index);
        }
    }

    return output.toOwnedSlice(allocator);
}

test "normalization smoke cases" {
    const allocator = std.testing.allocator;
    const plain = try normalize(allocator, "  SYMOND'S---YAT  ");
    defer allocator.free(plain);
    try std.testing.expectEqualStrings("symonds yat", plain);

    const glob = try normalizeGlob(allocator, " BIL*** ");
    defer allocator.free(glob);
    try std.testing.expectEqualStrings("bil*", glob);
}

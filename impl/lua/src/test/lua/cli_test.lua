local root = assert(arg[1], "repository root argument is required")
package.path = root .. "/impl/lua/src/main/lua/?.lua;"
    .. root .. "/impl/lua/src/main/lua/?/init.lua;"
    .. package.path

local cli = require("liff.cli")
local liff = require("liff")

local function sink()
    return {
        value = "",
        write = function(self, ...)
            for index = 1, select("#", ...) do
                self.value = self.value .. tostring(select(index, ...))
            end
        end,
    }
end

local function invoke(...)
    local arguments = { ... }
    local stdout = sink()
    local stderr = sink()
    local status = cli.run(arguments, stdout, stderr, liff.DEFAULT_DICTIONARY,
        function() return 0 end)
    return status, stdout.value, stderr.value
end

local function equal(actual, expected, message)
    if actual ~= expected then
        error(string.format("%s: got %q, want %q", message, tostring(actual), tostring(expected)))
    end
end

local function check(condition, message)
    if not condition then
        error(message)
    end
end

local status, output, errors = invoke()
equal(status, 0, "random status")
check(output:sub(1, #"AASLEAGH\n") == "AASLEAGH\n", "random output")
equal(errors, "", "random stderr")

for _, query in ipairs({ "banteer", "banteeer", "glutt", "bilb", "bil*" }) do
    status, output, errors = invoke(query)
    equal(status, 0, "found status")
    equal(errors, "", "found stderr")
end
_, output = invoke("glutt")
check(output:sub(1, #"GLUTT LODGE\n") == "GLUTT LODGE\n", "glutt match")
_, output = invoke("bilb")
check(output:sub(1, #"BILBSTER\n") == "BILBSTER\n", "bilb match")
_, output = invoke("symonds", "yat")
check(output:sub(1, #"SYMOND'S YAT\n") == "SYMOND'S YAT\n", "joined query")

status, output, errors = invoke("high")
equal(status, 1, "ambiguous status")
equal(output, "Did you mean?\nHIGH LIMERIGG\nHIGH OFFLEY\nAITH\nCHICAGO\n",
    "ambiguous output")

status, output = invoke("b*")
equal(status, 1, "large glob status")
equal(output,
    "Did you mean?\n"
        .. "BABWORTH\nBALDOCK\nBALLYCUMBER\nBANFF\nBANTEER\n"
        .. "BARSTIBLEY\nBAUGHURST\nBAUMBER\nBEALINGS\nBEAULIEU HILL\n"
        .. "and 44 others\n",
    "large glob output")

status, output = invoke("bo*")
equal(status, 1, "eleven-result status")
check(not output:find("and ", 1, true), "eleven results were truncated")
local _, eleven_lines = output:gsub("\n", "\n")
equal(eleven_lines, 12, "eleven-result line count")

status, output = invoke("*")
equal(status, 1, "all-result status")
check(output:sub(-#"and 540 others\n") == "and 540 others\n", "all-result truncation")

status, output, errors = invoke("xyzzy")
equal(status, 1, "not-found status")
equal(output, "No definition found for \"xyzzy\".\n", "not-found output")
equal(errors, "", "not-found stderr")

status, output, errors = invoke("--help")
equal(status, 0, "help status")
check(output:sub(1, #"Usage: liff") == "Usage: liff", "help output")
equal(errors, "", "help stderr")

status, output, errors = invoke("--unknown")
equal(status, 2, "invalid status")
equal(output, "", "invalid stdout")
check(errors:sub(1, #"Usage: liff") == "Usage: liff", "invalid stderr")

io.write("cli_test: OK\n")

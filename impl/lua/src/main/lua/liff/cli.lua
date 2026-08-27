local liff = require("liff")

local M = {}

M.HELP = [[Usage: liff [WORD ...]

With no word, print a random definition. With a word, search the dictionary.
Quoted patterns may use * to match any sequence and ? to match one character.]]

local FULL_SUGGESTION_LIMIT = 11
local TRUNCATED_SUGGESTION_LIMIT = 10

function M.run(arguments, stdout, stderr, dictionary, choose_index)
    dictionary = dictionary or liff.DEFAULT_DICTIONARY
    choose_index = choose_index or function(bound)
        return math.random(0, bound - 1)
    end

    if #arguments == 1 and (arguments[1] == "-h" or arguments[1] == "--help") then
        stdout:write(M.HELP, "\n")
        return 0
    end
    for _, argument in ipairs(arguments) do
        if argument:sub(1, 1) == "-" then
            stderr:write(M.HELP, "\n")
            return 2
        end
    end

    local query = table.concat(arguments, " ")
    local request = #arguments == 0 and liff.random_request or liff.search_request(query)
    local outcome = dictionary:resolve_with(request, choose_index)
    if outcome.type == "found" then
        stdout:write(outcome.entry.word, "\n", outcome.entry.definition, "\n")
        return 0
    end
    if outcome.type == "did_you_mean" then
        stdout:write("Did you mean?\n")
        local displayed = #outcome.suggestions <= FULL_SUGGESTION_LIMIT
            and #outcome.suggestions or TRUNCATED_SUGGESTION_LIMIT
        for position = 1, displayed do
            stdout:write(outcome.suggestions[position].entry.word, "\n")
        end
        if displayed < #outcome.suggestions then
            stdout:write("and ", #outcome.suggestions - displayed, " others\n")
        end
        return 1
    end
    stdout:write("No definition found for \"", query, "\".\n")
    return 1
end

return M

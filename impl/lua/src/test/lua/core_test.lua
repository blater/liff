local root = assert(arg[1], "repository root argument is required")
package.path = root .. "/impl/lua/src/main/lua/?.lua;"
    .. root .. "/impl/lua/src/main/lua/?/init.lua;"
    .. root .. "/impl/lua/src/test/lua/?.lua;"
    .. package.path

local json = require("json")
local liff = require("liff")
local model = require("liff.model")

local function equal(actual, expected, message)
    if actual ~= expected then
        error(string.format("%s: got %s, want %s", message, tostring(actual), tostring(expected)))
    end
end

local function check(condition, message)
    if not condition then
        error(message)
    end
end

local function shared_search_cases()
    local contract = json.read(root .. "/impl/search-cases.json")
    equal(contract.schema_version, 1, "search schema version")
    for _, case in ipairs(contract.cases) do
        local outcome = liff.DEFAULT_DICTIONARY:search(case.query)
        if case.outcome == "found" then
            equal(outcome.type, "found", "found outcome")
            equal(outcome.entry.word, case.word, "found word")
            equal(outcome.kind, case.kind, "found kind")
            if case.score ~= nil then
                equal(outcome.score, case.score, "found score")
            end
        elseif case.outcome == "did_you_mean" then
            equal(outcome.type, "did_you_mean", "suggestion outcome")
            equal(#outcome.suggestions, #case.suggestions, "suggestion count")
            for index, expected in ipairs(case.suggestions) do
                local actual = outcome.suggestions[index]
                equal(actual.entry.word, expected.word, "suggestion word")
                equal(actual.confidence, expected.confidence, "suggestion confidence")
                equal(actual.score, expected.score, "suggestion score")
            end
        elseif case.outcome == "not_found" then
            equal(outcome.type, "not_found", "not-found outcome")
        else
            error("unknown expected outcome: " .. case.outcome)
        end
    end
end

local function shared_algorithm_cases()
    local contract = json.read(root .. "/impl/algorithm-cases.json")
    equal(contract.schema_version, 1, "algorithm schema version")
    for _, case in ipairs(contract.normalization) do
        equal(liff.normalize(case.input), case.output, "normalization")
    end
    for _, case in ipairs(contract.glob_normalization) do
        equal(liff.normalize_glob(case.input), case.output, "glob normalization")
    end
    for _, case in ipairs(contract.edit_scores) do
        equal(liff.damerau_levenshtein(case.left, case.right), case.distance, "OSA distance")
        equal(liff.similarity_score(case.left, case.right), case.score, "similarity score")
    end
    for _, case in ipairs(contract.candidate_scores) do
        equal(liff.candidate_score(case.query, case.candidate), case.score, "candidate score")
    end
    for _, case in ipairs(contract.glob_matches) do
        equal(liff.glob_matches(case.pattern, case.candidate), case.matches, "glob match")
    end
    for _, case in ipairs(contract.ordering) do
        local actual = {}
        for index, value in ipairs(case.input) do
            actual[index] = value
        end
        table.sort(actual, function(left, right)
            return liff.compare_code_points(left, right) < 0
        end)
        equal(#actual, #case.ascending, "ordering count")
        for index, expected in ipairs(case.ascending) do
            equal(actual[index], expected, "scalar ordering")
        end
    end
end

local function generated_source_and_references()
    local source = json.read(root .. "/liff.json")
    equal(source.schema_version, 1, "source schema version")
    equal(liff.TITLE, source.title, "title")
    equal(liff.AUTHOR, source.author, "author")
    local source_order = source.entries.__order
    local entries = liff.entries()
    equal(#entries, #source_order, "entry count")
    for index, word in ipairs(source_order) do
        local actual = entries[index]
        local expected = source.entries[word]
        equal(actual.word, word, "canonical word")
        local expected_part = expected.part_of_speech
        if expected_part == json.null then
            expected_part = nil
        end
        equal(actual.part_of_speech, expected_part, "part of speech")
        equal(actual.definition, expected.definition, "definition")
        equal(#actual.references, #expected.references, "reference count")
        for reference_index, wanted in ipairs(expected.references) do
            local reference = actual.references[reference_index]
            equal(reference.target, wanted.target, "reference target")
            equal(reference.relation, wanted.relation, "reference relation")
            equal(reference.label, wanted.label, "reference label")
            local resolved = liff.DEFAULT_DICTIONARY:search(reference.target)
            equal(resolved.type, "found", "resolved reference outcome")
            equal(resolved.kind, "exact", "resolved reference kind")
            equal(resolved.entry.word, reference.target, "resolved reference word")
        end
    end
end

local function random_seam_and_validation()
    local dictionary = liff.DEFAULT_DICTIONARY
    local entries = dictionary:entries()
    equal(dictionary:random_with(function() return 0 end), entries[1], "first random entry")
    equal(dictionary:random_with(function(bound) return bound - 1 end), entries[#entries],
        "last random entry")
    equal(dictionary:random_with(function(bound) return bound end), nil,
        "out-of-range random entry")
    equal(liff.Dictionary.new({}):random_with(function() return 0 end), nil,
        "empty dictionary")

    local first = model.entry("A-B", nil, "first", {})
    local second = model.entry("A B", nil, "second", {})
    local accepted, message = pcall(function()
        liff.Dictionary.new({ first, second })
    end)
    check(not accepted and tostring(message):find("duplicate", 1, true),
        "duplicate normalized headwords were accepted")

    local mutable = pcall(function()
        entries[1].word = "CHANGED"
    end)
    check(not mutable, "entry mutation was accepted")

    local outcome = dictionary:resolve_with(liff.random_request, function() return 0 end)
    equal(outcome.type, "found", "random outcome")
    equal(outcome.kind, "random", "random kind")
    equal(outcome.score, nil, "random score")
end

shared_search_cases()
shared_algorithm_cases()
generated_source_and_references()
random_seam_and_validation()
io.write("core_test: OK\n")

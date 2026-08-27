local model = require("liff.model")
local normalizer = require("liff.normalize")

local M = {}

M.PERFECT_SCORE = 1000
M.QUALIFYING_SCORE = 700
M.LOW_SUGGESTION_COUNT = 2
M.TOKEN_PREFIX_SCORE = 900
M.PARTIAL_PREFIX_SCORE = 750
M.PREFIX_MIN_CODE_POINTS = 4

local function code_points(value)
    local result = {}
    for _, code_point in utf8.codes(value) do
        result[#result + 1] = code_point
    end
    return result
end

function M.compare_code_points(left, right)
    local left_points = code_points(left)
    local right_points = code_points(right)
    local common = math.min(#left_points, #right_points)
    for index = 1, common do
        if left_points[index] ~= right_points[index] then
            return left_points[index] < right_points[index] and -1 or 1
        end
    end
    if #left_points == #right_points then
        return 0
    end
    return #left_points < #right_points and -1 or 1
end

function M.damerau_levenshtein(left, right)
    local left_points = code_points(left)
    local right_points = code_points(right)
    local previous_previous = {}
    local previous = {}
    for index = 1, #right_points + 1 do
        previous_previous[index] = 0
        previous[index] = index - 1
    end

    for left_index = 1, #left_points do
        local current = { left_index }
        for right_index = 1, #right_points do
            local column = right_index + 1
            local substitution = left_points[left_index] == right_points[right_index] and 0 or 1
            current[column] = math.min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + substitution
            )
            if left_index > 1 and right_index > 1
                and left_points[left_index] == right_points[right_index - 1]
                and left_points[left_index - 1] == right_points[right_index]
            then
                current[column] = math.min(
                    current[column],
                    previous_previous[right_index - 1] + 1
                )
            end
        end
        previous_previous = previous
        previous = current
    end
    return previous[#right_points + 1]
end

function M.similarity_score(left, right)
    local maximum = math.max(utf8.len(left), utf8.len(right))
    if maximum == 0 then
        return M.PERFECT_SCORE
    end
    local retained = math.max(0, maximum - M.damerau_levenshtein(left, right))
    return math.floor(retained * M.PERFECT_SCORE / maximum)
end

function M.candidate_score(query, candidate)
    local edit_score = M.similarity_score(query, candidate)
    if utf8.len(query) < M.PREFIX_MIN_CODE_POINTS then
        return edit_score
    end
    if candidate:sub(1, #query + 1) == query .. " " then
        return math.max(edit_score, M.TOKEN_PREFIX_SCORE)
    end
    if candidate:sub(1, #query) == query then
        return math.max(edit_score, M.PARTIAL_PREFIX_SCORE)
    end
    return edit_score
end

function M.glob_matches(pattern, candidate)
    local pattern_points = code_points(pattern)
    local candidate_points = code_points(candidate)
    local previous = { true }
    for index = 2, #candidate_points + 1 do
        previous[index] = false
    end

    for _, pattern_point in ipairs(pattern_points) do
        local current = {}
        current[1] = pattern_point == 0x2a and previous[1] or false
        for candidate_index = 1, #candidate_points do
            local column = candidate_index + 1
            if pattern_point == 0x2a then
                current[column] = previous[column] or current[column - 1]
            elseif pattern_point == 0x3f then
                current[column] = previous[column - 1]
            else
                current[column] = previous[column - 1]
                    and pattern_point == candidate_points[candidate_index]
            end
        end
        previous = current
    end
    return previous[#candidate_points + 1]
end

local states = setmetatable({}, { __mode = "k" })
local Dictionary = {}
Dictionary.__index = Dictionary
Dictionary.__newindex = function()
    error("attempt to modify an immutable dictionary", 2)
end
Dictionary.__metatable = "immutable"

function Dictionary.new(source_entries)
    local entries = {}
    local index = {}
    for position = 1, #source_entries do
        local source = source_entries[position]
        local entry = model.entry(
            source.word,
            source.part_of_speech,
            source.definition,
            source.references
        )
        entries[position] = entry
        index[position] = {
            entry = entry,
            normalized = normalizer.normalize(entry.word),
        }
    end
    table.sort(index, function(left, right)
        return M.compare_code_points(left.normalized, right.normalized) < 0
    end)
    for position = 2, #index do
        if index[position - 1].normalized == index[position].normalized then
            error("dictionary contains duplicate normalized headwords", 2)
        end
    end

    local self = setmetatable({}, Dictionary)
    states[self] = {
        entries = model.array(entries),
        index = index,
    }
    return self
end

function Dictionary:entries()
    return states[self].entries
end

function Dictionary:random_with(choose_index)
    local entries = states[self].entries
    if #entries == 0 then
        return nil
    end
    local index = choose_index(#entries)
    if type(index) ~= "number" or index % 1 ~= 0 or index < 0 or index >= #entries then
        return nil
    end
    return entries[index + 1]
end

function Dictionary:random()
    return self:random_with(function(bound)
        return math.random(0, bound - 1)
    end)
end

function Dictionary:resolve_with(request, choose_index)
    if request.type == "search" then
        return self:search(request.query)
    end
    local entry = self:random_with(choose_index)
    if entry == nil then
        return model.not_found
    end
    return model.found(entry, "random", nil)
end

function Dictionary:resolve(request)
    return self:resolve_with(request, function(bound)
        return math.random(0, bound - 1)
    end)
end

local function lower_bound(index, query)
    local lower = 1
    local upper = #index + 1
    while lower < upper do
        local middle = lower + math.floor((upper - lower) / 2)
        if M.compare_code_points(index[middle].normalized, query) < 0 then
            lower = middle + 1
        else
            upper = middle
        end
    end
    return lower
end

function Dictionary:search(query)
    if query:find("*", 1, true) or query:find("?", 1, true) then
        return self:search_glob(query)
    end

    local normalized_query = normalizer.normalize(query)
    if normalized_query == "" then
        return model.not_found
    end
    local state = states[self]
    local exact_position = lower_bound(state.index, normalized_query)
    if exact_position <= #state.index
        and state.index[exact_position].normalized == normalized_query
    then
        return model.found(state.index[exact_position].entry, "exact", M.PERFECT_SCORE)
    end

    local ranked = {}
    for position, indexed in ipairs(state.index) do
        ranked[position] = {
            entry = indexed.entry,
            score = M.candidate_score(normalized_query, indexed.normalized),
        }
    end
    table.sort(ranked, function(left, right)
        if left.score ~= right.score then
            return left.score > right.score
        end
        return M.compare_code_points(left.entry.word, right.entry.word) < 0
    end)

    local qualified = 0
    while qualified < #ranked and ranked[qualified + 1].score >= M.QUALIFYING_SCORE do
        qualified = qualified + 1
    end
    if qualified == 1 then
        local candidate = ranked[1]
        return model.found(candidate.entry, "high_confidence", candidate.score)
    end
    if qualified == 0 then
        return model.not_found
    end

    local suggestions = {}
    for position = 1, qualified do
        local candidate = ranked[position]
        suggestions[#suggestions + 1] = model.suggestion(
            candidate.entry,
            "medium",
            candidate.score
        )
    end
    local last = math.min(#ranked, qualified + M.LOW_SUGGESTION_COUNT)
    for position = qualified + 1, last do
        local candidate = ranked[position]
        suggestions[#suggestions + 1] = model.suggestion(
            candidate.entry,
            "low",
            candidate.score
        )
    end
    return model.did_you_mean(suggestions)
end

function Dictionary:search_glob(query)
    local pattern = normalizer.normalize_glob(query)
    if pattern == "" then
        return model.not_found
    end
    local matches = {}
    for _, indexed in ipairs(states[self].index) do
        if M.glob_matches(pattern, indexed.normalized) then
            matches[#matches + 1] = indexed.entry
        end
    end
    if #matches == 0 then
        return model.not_found
    end
    if #matches == 1 then
        return model.found(matches[1], "glob", M.PERFECT_SCORE)
    end
    local suggestions = {}
    for position, entry in ipairs(matches) do
        suggestions[position] = model.suggestion(entry, "medium", M.PERFECT_SCORE)
    end
    return model.did_you_mean(suggestions)
end

M.Dictionary = Dictionary

return M

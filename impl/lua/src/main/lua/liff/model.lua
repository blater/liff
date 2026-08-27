local M = {}

local function immutable_error()
    error("attempt to modify an immutable value", 2)
end

function M.immutable(data)
    return setmetatable({}, {
        __index = data,
        __newindex = immutable_error,
        __len = function()
            return #data
        end,
        __pairs = function()
            return next, data, nil
        end,
        __metatable = "immutable",
    })
end

function M.array(values)
    local copy = {}
    for index = 1, #values do
        copy[index] = values[index]
    end
    return M.immutable(copy)
end

function M.reference(target, relation, label)
    return M.immutable({
        target = target,
        relation = relation,
        label = label,
    })
end

function M.entry(word, part_of_speech, definition, references)
    return M.immutable({
        word = word,
        part_of_speech = part_of_speech,
        definition = definition,
        references = M.array(references),
    })
end

function M.found(entry, kind, score)
    return M.immutable({
        type = "found",
        entry = entry,
        kind = kind,
        score = score,
    })
end

function M.suggestion(entry, confidence, score)
    return M.immutable({
        entry = entry,
        confidence = confidence,
        score = score,
    })
end

function M.did_you_mean(suggestions)
    return M.immutable({
        type = "did_you_mean",
        suggestions = M.array(suggestions),
    })
end

M.not_found = M.immutable({ type = "not_found" })
M.random_request = M.immutable({ type = "random" })

function M.search_request(query)
    return M.immutable({ type = "search", query = query })
end

return M

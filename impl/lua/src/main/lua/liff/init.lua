local data = require("liff.dictionary_generated")
local dictionary_module = require("liff.dictionary")
local model = require("liff.model")

local M = {
    TITLE = data.title,
    AUTHOR = data.author,
    Dictionary = dictionary_module.Dictionary,
    DEFAULT_DICTIONARY = dictionary_module.Dictionary.new(data.entries),
    random_request = model.random_request,
    search_request = model.search_request,
    normalize = require("liff.normalize").normalize,
    normalize_glob = require("liff.normalize").normalize_glob,
    candidate_score = dictionary_module.candidate_score,
    similarity_score = dictionary_module.similarity_score,
    damerau_levenshtein = dictionary_module.damerau_levenshtein,
    glob_matches = dictionary_module.glob_matches,
    compare_code_points = dictionary_module.compare_code_points,
}

function M.entries()
    return M.DEFAULT_DICTIONARY:entries()
end

function M.resolve(request)
    return M.DEFAULT_DICTIONARY:resolve(request)
end

return M

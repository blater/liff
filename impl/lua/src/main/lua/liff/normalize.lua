local M = {}

local function normalize_internal(input, preserve_globs)
    local output = {}
    local separator_pending = false
    for _, code_point in utf8.codes(input) do
        if code_point ~= 0x27 and code_point ~= 0x2019 then
            local alphanumeric = code_point >= 0x61 and code_point <= 0x7a
                or code_point >= 0x41 and code_point <= 0x5a
                or code_point >= 0x30 and code_point <= 0x39
            local glob = preserve_globs and (code_point == 0x2a or code_point == 0x3f)
            if alphanumeric or glob then
                if separator_pending and #output > 0 then
                    output[#output + 1] = " "
                end
                if code_point >= 0x41 and code_point <= 0x5a then
                    code_point = code_point + 0x20
                end
                local character = string.char(code_point)
                if character ~= "*" or output[#output] ~= "*" then
                    output[#output + 1] = character
                end
                separator_pending = false
            else
                separator_pending = true
            end
        end
    end
    return table.concat(output)
end

function M.normalize(input)
    return normalize_internal(input, false)
end

function M.normalize_glob(input)
    return normalize_internal(input, true)
end

return M

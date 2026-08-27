local M = {}

M.null = setmetatable({}, { __tostring = function() return "null" end })

local Parser = {}
Parser.__index = Parser

local function fail(self, message)
    error(message .. " at byte " .. self.position, 0)
end

function Parser:peek()
    return self.source:sub(self.position, self.position)
end

function Parser:take(character)
    if self:peek() == character then
        self.position = self.position + 1
        return true
    end
    return false
end

function Parser:expect(character)
    if not self:take(character) then
        fail(self, "expected '" .. character .. "'")
    end
end

function Parser:whitespace()
    while self.position <= #self.source do
        local character = self:peek()
        if character ~= " " and character ~= "\n"
            and character ~= "\r" and character ~= "\t"
        then
            return
        end
        self.position = self.position + 1
    end
end

function Parser:hexadecimal()
    local text = self.source:sub(self.position, self.position + 3)
    if #text ~= 4 or not text:match("^[0-9a-fA-F]+$") then
        fail(self, "invalid Unicode escape")
    end
    self.position = self.position + 4
    return tonumber(text, 16)
end

function Parser:string()
    self:expect('"')
    local output = {}
    while self.position <= #self.source do
        local character = self:peek()
        self.position = self.position + 1
        if character == '"' then
            return table.concat(output)
        end
        if character ~= "\\" then
            output[#output + 1] = character
        else
            local escape = self:peek()
            self.position = self.position + 1
            local replacements = {
                ['"'] = '"',
                ["\\"] = "\\",
                ["/"] = "/",
                b = "\b",
                f = "\f",
                n = "\n",
                r = "\r",
                t = "\t",
            }
            if replacements[escape] ~= nil then
                output[#output + 1] = replacements[escape]
            elseif escape == "u" then
                local code_point = self:hexadecimal()
                if code_point >= 0xd800 and code_point <= 0xdbff
                    and self.source:sub(self.position, self.position + 1) == "\\u"
                then
                    self.position = self.position + 2
                    local low = self:hexadecimal()
                    if low < 0xdc00 or low > 0xdfff then
                        fail(self, "invalid low surrogate")
                    end
                    code_point = 0x10000 + (code_point - 0xd800) * 0x400 + (low - 0xdc00)
                end
                output[#output + 1] = utf8.char(code_point)
            else
                fail(self, "invalid string escape")
            end
        end
    end
    fail(self, "unterminated string")
end

function Parser:number()
    local start = self.position
    self:take("-")
    if self:take("0") then
        -- A leading zero is the complete integer part.
    else
        if not self:peek():match("%d") then
            fail(self, "expected digit")
        end
        while self:peek():match("%d") do
            self.position = self.position + 1
        end
    end
    if self:take(".") then
        if not self:peek():match("%d") then
            fail(self, "expected fractional digit")
        end
        while self:peek():match("%d") do
            self.position = self.position + 1
        end
    end
    local exponent = self:peek()
    if exponent == "e" or exponent == "E" then
        self.position = self.position + 1
        if not self:take("+") then
            self:take("-")
        end
        if not self:peek():match("%d") then
            fail(self, "expected exponent digit")
        end
        while self:peek():match("%d") do
            self.position = self.position + 1
        end
    end
    local value = tonumber(self.source:sub(start, self.position - 1))
    if value == nil then
        fail(self, "invalid number")
    end
    return value
end

function Parser:literal(text, value)
    if self.source:sub(self.position, self.position + #text - 1) ~= text then
        fail(self, "invalid literal")
    end
    self.position = self.position + #text
    return value
end

function Parser:array()
    self:expect("[")
    local result = {}
    self:whitespace()
    if self:take("]") then
        return result
    end
    while true do
        result[#result + 1] = self:value()
        self:whitespace()
        if self:take("]") then
            return result
        end
        self:expect(",")
    end
end

function Parser:object()
    self:expect("{")
    local result = { __order = {} }
    self:whitespace()
    if self:take("}") then
        return result
    end
    while true do
        self:whitespace()
        local key = self:string()
        self:whitespace()
        self:expect(":")
        result[key] = self:value()
        result.__order[#result.__order + 1] = key
        self:whitespace()
        if self:take("}") then
            return result
        end
        self:expect(",")
    end
end

function Parser:value()
    self:whitespace()
    local character = self:peek()
    if character == "{" then
        return self:object()
    elseif character == "[" then
        return self:array()
    elseif character == '"' then
        return self:string()
    elseif character == "t" then
        return self:literal("true", true)
    elseif character == "f" then
        return self:literal("false", false)
    elseif character == "n" then
        return self:literal("null", M.null)
    end
    return self:number()
end

function M.decode(source)
    local parser = setmetatable({ source = source, position = 1 }, Parser)
    local result = parser:value()
    parser:whitespace()
    if parser.position <= #source then
        fail(parser, "trailing content")
    end
    return result
end

function M.read(path)
    local file = assert(io.open(path, "rb"))
    local source = assert(file:read("a"))
    file:close()
    return M.decode(source)
end

return M

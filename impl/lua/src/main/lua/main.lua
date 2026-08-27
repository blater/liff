local script_directory = arg[0]:match("^(.*)/[^/]+$") or "."
package.path = script_directory .. "/?.lua;"
    .. script_directory .. "/?/init.lua;"
    .. package.path

local cli = require("liff.cli")
local arguments = {}
for index = 1, #arg do
    arguments[index] = arg[index]
end

os.exit(cli.run(arguments, io.stdout, io.stderr), true)

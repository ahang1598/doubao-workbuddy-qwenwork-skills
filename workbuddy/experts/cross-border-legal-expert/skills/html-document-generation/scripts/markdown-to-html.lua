-- Author：基于 word-document-processing skill
-- 聚合 Lua 过滤器，按顺序加载
local script_path = debug.getinfo(1, "S").source:sub(2)
local script_dir = script_path:match("(.*[/\\])") or "./"
package.path = script_dir .. "?.lua;" .. script_dir .. "?/init.lua;" .. package.path

local modules = {
    'disable-ordered-list-numbering',
    'image-title-to-caption',
}

local filters = {}

local function is_array(t)
	if type(t) ~= 'table' then return false end
	local n = #t
	local count = 0
	for k, _ in pairs(t) do
		if type(k) ~= 'number' then return false end
		count = count + 1
	end
	return count == n
end

local function append_filter(ret, name)
	local kind = type(ret)
	if kind == 'table' then
		if is_array(ret) then
			for i = 1, #ret do
				filters[#filters+1] = ret[i]
			end
		else
			filters[#filters+1] = ret
		end
	elseif kind == 'function' then
		filters[#filters+1] = ret
	elseif ret ~= nil then
		io.stderr:write(string.format('[markdown-to-html] 警告: 模块 %s 返回不支持的类型: %s\n', name, kind))
	end
end

for _, m in ipairs(modules) do
	local ok, ret = pcall(require, m)
	if ok then
		append_filter(ret, m)
	else
		io.stderr:write(string.format('[markdown-to-html] 警告: 加载模块 %s 失败: %s\n', m, ret))
	end
end

return filters

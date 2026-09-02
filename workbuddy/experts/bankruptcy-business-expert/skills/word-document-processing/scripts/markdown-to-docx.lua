-- Author：Achuan-2
-- 调用：pandoc input.md -o output.docx --lua-filter=markdown-to-docx.lua

-- =================================================================
-- 路径处理：动态获取当前脚本所在目录，确保 require 能找到子模块
-- =================================================================
local script_path = debug.getinfo(1, "S").source:sub(2) -- 获取脚本文件路径
-- 兼容 Windows (\) 和 Unix (/) 路径，获取所在目录
local script_dir = script_path:match("(.*[/\\])") or "./"
-- 将脚本所在目录添加到 Lua 的搜索路径中
-- 这样 require('lua/xxx') 就会相对于本脚本所在位置查找
package.path = script_dir .. "?.lua;" .. script_dir .. "?/init.lua;" .. package.path


-- 通过一个按顺序维护的模块列表来组织需要加载的 Pandoc 过滤器。
-- 在此列表中添加/调整顺序即可，无需再手写多段 require 与循环。
local modules = {
    -- 禁用 Pandoc 有序列表自动编号，使用 Markdown 原文的文字序号
    'lua/disable-ordered-list-numbering',
    -- 为行内代码添加自定义样式
    'lua/add-inline-code',
    -- 支持在 Markdown 中插入分页符（\newpage / <div page-break>）
    'lua/pagebreak',
    -- 将 Markdown 中的水平线（---）转为空段落（去除 Word 默认的可见横线）
    'lua/horizontal-rule-to-spacer',
    -- 将 RawBlock 中的 HTML 表格转换为 Pandoc Table AST（支持 colspan/rowspan）
    -- 必须在 html-inline-to-ast 之前：表格 cell 内容用 pandoc.read 重新解析，
    -- 会生成新的 RawInline(<u>) / Span(color)，这些需要后续 html-inline-to-ast 处理
    'lua/html-table-to-ast',
    -- 将 RawInline 中的 HTML 行内标签（<u>、<span style="color">）转换为 Pandoc AST
    -- 必须在 html-table-to-ast 之后：处理表格 cell 内重新解析出的 <u>/<span>，
    -- 并把 <u> 内嵌的 <span color> 合并属性生成 RawInline openxml
    'lua/html-inline-to-ast',
	-- 为文本添加字体颜色支持：Span(style=color) → RawInline openxml
	-- 必须在 html-inline-to-ast 之后：此时 <u> 已合并颜色 span 为 RawInline openxml
	'lua/preserve_font_color',
    -- 段落对齐支持：通过 Fenced Div class（.text-center / .text-right / .text-left）控制
    'lua/text-align',
    -- 首行缩进控制：通过 Fenced Div class（.no-indent / .indent）控制
    'lua/text-indent',
    -- 目录标记清理：自动目录已停用（体验不佳），此模块仅删除 [TOC] / [TOC:N] 标记
    'lua/toc',
    -- pandoc默认把图片alt作为图片标题，改为title作为图片标题
	'lua/image-title-to-caption',
	-- 在下方继续追加模块名称，例如：
	-- 'your-extra-filter-module',
}

-- 收集最终要返回给 Pandoc 的过滤器（数组形式）。
local filters = {}

-- 判断一个 table 是否是“数组” (连续的整数索引)。
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

-- 将一个模块返回的内容追加到 filters：
-- 支持：
-- 1) 单个过滤器 table (如 { Para = function(...) ... end })
-- 2) 过滤器数组 { {Para=...}, {Image=...} }
-- 3) 单个函数（极少见，但也容忍）
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
		io.stderr:write(string.format('[markdown-to-docx] 警告: 模块 %s 返回不支持的类型: %s\n', name, kind))
	end
end

for _, m in ipairs(modules) do
	local ok, ret = pcall(require, m)
	if ok then
		append_filter(ret, m)
	else
		io.stderr:write(string.format('[markdown-to-docx] 警告: 加载模块 %s 失败: %s\n', m, ret))
	end
end

return filters
--- 将 RawInline 中的 HTML 行内标签转换为 Pandoc AST / 直接 OpenXML。
---
--- Pandoc 默认 markdown 格式会把 <u>、<span> 等 HTML 行内标签解析为 RawInline，
--- DOCX writer 不处理 RawInline HTML，导致下划线等格式丢失。
---
--- 实现策略：
--- 1. <u>...</u> → pandoc.Underline
--- 2. <span style="color:...">...</span> → pandoc.Span(color attr)
--- 3. 嵌套场景（<u><span>...</span></u>）：
---    问题：Underline 包裹 Span(color) 时，DOCX writer 将 Span(color) 渲染为
---    RawInline openxml <w:r><w:rPr><w:color/></w:rPr><w:t>...</w:t></w:r>，
---    这个 <w:r> 是独立 run，把外层 Underline 的 <w:u> 属性丢掉了。
---    解决：检测到 <u> 内部含颜色 span 时，直接生成 RawInline openxml，
---    合并 <w:u> 和 <w:color> 到同一个 <w:rPr>，绕过 Pandoc writer 限制。

local function is_html_rawinline(el)
    return el and el.t == "RawInline" and el.format == "html"
end

-- XML 文本转义（pandoc.utils.escape 在 pandoc 3.x 已移除，需手动实现）
local function xml_escape(s)
    s = s:gsub("&", "&amp;")
    s = s:gsub("<", "&lt;")
    s = s:gsub(">", "&gt;")
    s = s:gsub('"', "&quot;")
    s = s:gsub("'", "&apos;")
    return s
end

-- 将颜色字符串规范化为 6 位大写十六进制（不带 #）
-- 支持：颜色名(red)、#hex(#ff0000 / #f00)、rgb()/rgba()
-- 解析失败返回 nil
local COLOR_NAMES = {
    red = "FF0000", blue = "0000FF", green = "008000",
    black = "000000", white = "FFFFFF", yellow = "FFFF00",
    orange = "FFA500", purple = "800080", gray = "808080", grey = "808080",
}
local function parse_color(s)
    if not s then return nil end
    s = s:gsub("%s+", "")
    local lower = s:lower()
    if COLOR_NAMES[lower] then return COLOR_NAMES[lower] end

    -- #rrggbb
    local hex6 = s:match("#?(%x%x%x%x%x%x)")
    if hex6 then return hex6:upper() end

    -- #rgb -> rrggbb
    local hex3 = s:match("#?(%x%x%x)$")
    if hex3 then
        local r, g, b = hex3:sub(1,1), hex3:sub(2,2), hex3:sub(3,3)
        return (r..r..g..g..b..b):upper()
    end

    -- rgb(r,g,b)
    local r, g, b = s:match("rgb%((%d+),(%d+),(%d+)%)")
    if r and g and b then
        local function h(n)
            local nv = tonumber(n) or 0
            if nv < 0 then nv = 0 end
            if nv > 255 then nv = 255 end
            return string.format("%02X", nv)
        end
        return h(r)..h(g)..h(b)
    end

    return nil
end

-- 提取 span 标签的 color 样式（从 style="color:..." 形式的 HTML 文本）
local function parse_span_color(text)
    local color = text:match('color%s*:%s*([%w#]+)')
    if not color then
        -- 尝试 rgb()/rgba() 形式
        color = text:match('color%s*:%s*(rgb[^;%s]*)')
    end
    return parse_color(color)
end

-- 将 inline 列表的文本内容提取并 XML 转义为 <w:t> 用的纯字符串
-- 支持 Str、Space、其他 inline 通过 stringify 兜底
local function extract_escaped_text(inlines)
    local parts = {}
    for _, inl in ipairs(inlines) do
        if inl.t == "Str" then
            table.insert(parts, xml_escape(inl.text))
        elseif inl.t == "Space" then
            table.insert(parts, " ")
        else
            -- 兜底：stringify 递归取文本，再转义
            local text = pandoc.utils.stringify(inl)
            table.insert(parts, xml_escape(text))
        end
    end
    return table.concat(parts)
end

-- 提取 <u>、<span> 等开始标签的属性
-- 返回 (tag_name, color_or_nil)；不匹配返回 nil
local function parse_open_tag(text)
    local lower = text:lower()
    -- <u> 或 <u attr>
    local u_tag = lower:match("^<u([%s>])")
    if u_tag then
        return "u", nil
    end
    -- <span ... style="..." ...>
    if lower:match("^<span[^>]*>") then
        local color = parse_span_color(text)
        return "span", color
    end
    return nil
end

-- 构造合并了 underline + color 的 OpenXML run
local function build_underline_color_run(text_escaped, color)
    local rpr = "<w:rPr><w:u w:val=\"single\"/>"
    if color then
        rpr = rpr .. "<w:color w:val=\"" .. color .. "\"/>"
    end
    rpr = rpr .. "</w:rPr>"
    return pandoc.RawInline("openxml",
        "<w:r>" .. rpr .. "<w:t xml:space=\"preserve\">" .. text_escaped .. "</w:t></w:r>")
end

-- 主处理函数：递归扫描 inlines，处理 <u>/<span> 嵌套
-- outer_underline: 当处于 <u> 内部递归时为 true（用于合并属性）
function process_inlines(inlines, outer_underline)
    local new_inlines = {}
    local i = 1

    while i <= #inlines do
        local el = inlines[i]

        if is_html_rawinline(el) then
            local lower = el.text:lower()

            -- <u> 标签
            if lower:match("^<u[%s>]") then
                -- 查找对应的 </u>（支持嵌套）
                local collected = {}
                local u_depth = 1
                local found_close = false
                local j = i + 1
                while j <= #inlines do
                    local next_el = inlines[j]
                    if is_html_rawinline(next_el) then
                        local nl = next_el.text:lower()
                        if nl:match("^<u[%s>]") then
                            u_depth = u_depth + 1
                        elseif nl:match("^</u>") then
                            u_depth = u_depth - 1
                            if u_depth == 0 then
                                found_close = true
                                break
                            end
                        end
                    end
                    table.insert(collected, next_el)
                    j = j + 1
                end

                if found_close then
                    -- 递归处理内部内容，标记进入 underline 上下文
                    local inner_collected = process_inlines(collected, true)
                    -- <u> 上下文内：将 Span(color) 替换为合并了 <w:u>+<w:color> 的 RawInline openxml，
                    -- 绕过 Pandoc writer 把 Span(color) 渲染为独立 <w:r> 丢失 <w:u> 的问题
                    local replaced = {}
                    for _, inl in ipairs(inner_collected) do
                        if inl.t == "Span" and inl.attr and inl.attr.attributes and inl.attr.attributes.style then
                            local style = inl.attr.attributes.style
                            local color_raw = style:match("color%s*:%s*([^;]+)")
                            local color = parse_color(color_raw)
                            local text_escaped = extract_escaped_text(inl.content)
                            table.insert(replaced, build_underline_color_run(text_escaped, color))
                        else
                            table.insert(replaced, inl)
                        end
                    end
                    table.insert(new_inlines, pandoc.Underline(pandoc.Inlines(replaced)))
                    i = j + 1
                else
                    table.insert(new_inlines, el)
                    i = i + 1
                end

            -- <span style="color:..."> 标签
            elseif lower:match("^<span[^>]*style[^>]*>") then
                local span_color = parse_span_color(el.text)
                -- 查找对应 </span>（支持嵌套）
                local collected = {}
                local span_depth = 1
                local found_close = false
                local j = i + 1
                while j <= #inlines do
                    local next_el = inlines[j]
                    if is_html_rawinline(next_el) then
                        local nl = next_el.text:lower()
                        if nl:match("^<span[^>]*>") then
                            span_depth = span_depth + 1
                        elseif nl:match("^</span>") then
                            span_depth = span_depth - 1
                            if span_depth == 0 then
                                found_close = true
                                break
                            end
                        end
                    end
                    table.insert(collected, next_el)
                    j = j + 1
                end

                if found_close then
                    -- 嵌套在 <u> 内：直接生成 RawInline openxml，合并 <w:u>+<w:color>
                    if outer_underline then
                        local text_escaped = extract_escaped_text(collected)
                        table.insert(new_inlines, build_underline_color_run(text_escaped, span_color))
                    else
                        -- 顶层 span：用 pandoc.Span + style attr
                        local inner_collected = process_inlines(collected, false)
                        local inner = pandoc.Inlines(inner_collected)
                        if span_color then
                            local span = pandoc.Span(inner, pandoc.Attr("", {}, {style = "color:#" .. span_color}))
                            table.insert(new_inlines, span)
                        else
                            table.insert(new_inlines, pandoc.Span(inner))
                        end
                    end
                    i = j + 1
                else
                    table.insert(new_inlines, el)
                    i = i + 1
                end

            -- 跳过孤立的闭合标签
            elseif lower:match("^</u>") or lower:match("^</span>") then
                i = i + 1
            else
                table.insert(new_inlines, el)
                i = i + 1
            end
        else
            -- 普通 inline（Str/Space 等）
            table.insert(new_inlines, el)
            i = i + 1
        end
    end

    return new_inlines
end

return {
    {
        Inlines = function(inlines)
            return process_inlines(inlines, false)
        end,
    },
}

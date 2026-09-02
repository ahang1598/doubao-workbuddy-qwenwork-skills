-- 支持在 Markdown 中插入分页符，转换到 Word 后生成分页。
--
-- 支持的 Markdown 写法（独立成行，前后空行）：
--   1. \newpage
--      —— 简洁，最易手写 / agent 生成
--   2. <div style="page-break-after: always"></div>
--      —— raw HTML 约定，pandoc 解析为 Div 元素
--   3. <div style="page-break-before: always"></div>
--      —— 同上的等价变体
--
-- 全部转为 OpenXML 分页 run：
--   <w:r><w:br w:type="page"/></w:r>
--
-- 实现策略：在 Pandoc AST 层识别，输出一个仅含 RawInline openxml 的 Para，
-- 后续 pandoc writer 直接渲染该 openxml 到 docx。

-- 构造 Word 分页 run
local PAGEBREAK_XML = '<w:r><w:br w:type="page"/></w:r>'

local function make_pagebreak_para()
    return pandoc.Para{ pandoc.RawInline("openxml", PAGEBREAK_XML) }
end

-- 判定 RawBlock 是否为分页符触发器
-- pandoc 把行内 \newpage / <div style=...></div> 解析为 RawBlock "tex" 或 RawBlock "html"
local function is_pagebreak_rawblock(el)
    if el.t ~= "RawBlock" then return false end
    local fmt = el.format:lower()
    if fmt == "tex" or fmt == "latex" then
        local lower = el.text:lower()
        if lower:match("\\newpage") or lower:match("\\pagebreak") then
            return true
        end
    elseif fmt == "html" then
        local lower = el.text:lower()
        if lower:match("page%-break%-after") or lower:match("page%-break%-before") then
            -- 关键字 "always" 或 "always;" 都视为分页
            if lower:match("always") then
                return true
            end
        end
    end
    return false
end

-- 判定 Div（pandoc 把 <div style="page-break-..."></div> 解析为 Div 元素，不是 RawBlock）
local function is_pagebreak_div(el)
    if el.t ~= "Div" then return false end
    if not el.attr or not el.attr.attributes then return false end
    local style = el.attr.attributes.style
    if not style then return false end
    local lower = style:lower()
    if lower:match("page%-break%-after") or lower:match("page%-break%-before") then
        if lower:match("always") then
            return true
        end
    end
    return false
end

-- RawBlock 钩子：\newpage 和 raw HTML div
function RawBlock(el)
    if is_pagebreak_rawblock(el) then
        return make_pagebreak_para()
    end
    return nil
end

-- Div 钩子：pandoc 解析后的 Div 元素
function Div(el)
    if is_pagebreak_div(el) then
        return make_pagebreak_para()
    end
    return nil
end

return { RawBlock = RawBlock, Div = Div }


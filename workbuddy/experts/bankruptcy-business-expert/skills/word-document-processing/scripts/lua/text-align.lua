--- 段落对齐支持：通过 Fenced Div 的 class 控制段落左/中/右/两端对齐。
---
--- 语法：
---   ::: {.text-center}
---   居中段落内容
---   :::
---
---   ::: {.text-right}
---   右对齐内容
---   :::
---
---   ::: {.text-justify}
---   两端对齐（正文默认）
---   :::
---
--- 支持的 class：
---   .text-center  → 居中对齐
---   .text-right   → 右对齐
---   .text-left    → 左对齐（默认，一般无需显式使用）
---   .text-justify → 两端对齐（法律文书正文标准格式）
---
--- 实现策略：检测 Div 的对齐 class，将内部段落转换为带 OpenXML
--- <w:pPr><w:jc w:val="..."/></w:pPr> 的 RawBlock，确保 DOCX 输出正确对齐。

-- class → OpenXML jc value 映射
local ALIGN_MAP = {
    ["text-center"]  = "center",
    ["text-right"]   = "right",
    ["text-left"]    = "left",
    ["text-justify"] = "both",
}

-- 从 Div attr 中提取对齐值，未匹配返回 nil
local function get_align_class(attr)
    if not attr or not attr.classes then return nil end
    for _, cls in ipairs(attr.classes) do
        if ALIGN_MAP[cls] then
            return ALIGN_MAP[cls], cls
        end
    end
    return nil
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

-- 将 inline 元素转成 OpenXML <w:r><w:t> 文本（简单实现，保留纯文本）
local function inlines_to_openxml(inlines)
    local parts = {}
    for _, inl in ipairs(inlines) do
        if inl.t == "Str" then
            parts[#parts + 1] = "<w:r><w:t xml:space=\"preserve\">" .. xml_escape(inl.text) .. "</w:t></w:r>"
        elseif inl.t == "Space" then
            parts[#parts + 1] = "<w:r><w:t xml:space=\"preserve\"> </w:t></w:r>"
        elseif inl.t == "SoftBreak" or inl.t == "LineBreak" then
            parts[#parts + 1] = "<w:r><w:br/></w:r>"
        elseif inl.t == "Strong" or inl.t == "Emph" or inl.t == "Underline" then
            -- 递归处理嵌套行内元素，加粗/斜体/下划线用 <w:rPr> 包装
            local rpr = ""
            if inl.t == "Strong" then rpr = "<w:rPr><w:b/></w:rPr>" end
            if inl.t == "Emph" then rpr = "<w:rPr><w:i/></w:rPr>" end
            if inl.t == "Underline" then rpr = "<w:rPr><w:u w:val=\"single\"/></w:rPr>" end
            local inner = inlines_to_openxml(inl.content)
            -- 把 rPr 注入到每个 <w:r> 中
            inner = inner:gsub("<w:r>", "<w:r>" .. rpr)
            parts[#parts + 1] = inner
        elseif inl.t == "Span" then
            -- Span：直接递归内部内容（颜色等样式暂不处理，由其他过滤器负责）
            parts[#parts + 1] = inlines_to_openxml(inl.content)
        elseif inl.t == "RawInline" then
            -- 原样保留 RawInline（如 HTML 片段）
            parts[#parts + 1] = inl.text
        end
    end
    return table.concat(parts, "")
end

-- 构造带对齐属性的 OpenXML 段落 RawBlock
local function make_aligned_block(block, jc_val)
    local inlines = block.content or {}
    local runs = inlines_to_openxml(inlines)
    local ppr = "<w:pPr><w:jc w:val=\"" .. jc_val .. "\"/></w:pPr>"
    local xml = "<w:p>" .. ppr .. runs .. "</w:p>"
    return pandoc.RawBlock("openxml", xml)
end

-- 向已生成的 OpenXML 段落 RawBlock 注入对齐属性（<w:jc>）。
-- 若本过滤器位于 text-indent 之后执行，内部段落已是带缩进属性的 RawBlock，
-- 这里识别并在 <w:pPr> 中插入对齐，保证两类 class 共存时两者都生效。
local function inject_align_to_rawblock(block, jc_val)
    local raw = block.text
    local ppr_start, ppr_end = raw:find("<w:pPr>", 1, true)
    if ppr_start then
        local injected = raw:sub(1, ppr_start - 1) .. "<w:pPr><w:jc w:val=\"" .. jc_val .. "\"/>" .. raw:sub(ppr_end + 1)
        return pandoc.RawBlock("openxml", injected)
    end
    local p_start, p_end = raw:find("<w:p>", 1, true)
    if p_start then
        local injected = raw:sub(1, p_end) .. "<w:pPr><w:jc w:val=\"" .. jc_val .. "\"/></w:pPr>" .. raw:sub(p_end + 1)
        return pandoc.RawBlock("openxml", injected)
    end
    return block
end

-- 处理 Div 内部的 blocks，将对齐属性应用到每个段落
local function process_blocks(blocks, jc_val)
    local result = {}
    for _, block in ipairs(blocks) do
        if block.t == "Para" or block.t == "Plain" then
            table.insert(result, make_aligned_block(block, jc_val))
        elseif block.t == "Div" then
            -- 嵌套 Div：递归处理内部内容
            table.insert(result, process_div(block, jc_val))
        elseif block.t == "RawBlock" and block.format == "openxml"
               and block.text:find("<w:p", 1, true) then
            -- 已由 text-indent 等过滤器转换的 OpenXML 段落：注入对齐
            table.insert(result, inject_align_to_rawblock(block, jc_val))
        else
            -- 其他类型（Table、Header 等）原样保留
            table.insert(result, block)
        end
    end
    return result
end

-- 处理单个 Div（支持递归嵌套）
local function process_div(div, outer_align)
    local jc_val, cls = get_align_class(div.attr)

    if jc_val then
        -- 本 Div 有对齐 class：提取并移除该 class（避免重复处理）
        local new_classes = {}
        for _, c in ipairs(div.attr.classes) do
            if c ~= cls then
                table.insert(new_classes, c)
            end
        end
        local new_attr = pandoc.Attr(
            div.attr.identifier or "",
            new_classes,
            div.attr.attributes or {}
        )
        -- 应用对齐到内部所有段落
        local new_blocks = process_blocks(div.content, jc_val)
        -- 如果还有其他 class 或 identifier，保留 Div 包装；否则展平
        if #new_classes > 0 or (div.attr.identifier and div.attr.identifier ~= "") then
            return pandoc.Div(new_blocks, new_attr)
        else
            -- 无其他属性，直接返回处理后的 blocks（展平）
            return new_blocks
        end
    elseif outer_align then
        -- 本 Div 无对齐 class，但父级有：透传对齐到内部
        local new_blocks = process_blocks(div.content, outer_align)
        return pandoc.Div(new_blocks, div.attr)
    else
        -- 无任何对齐信息，原样返回
        return div
    end
end

return {
    {
        Div = function(div)
            local result = process_div(div, nil)
            -- 如果结果是 table（展平后的 blocks），用 Pandoc.Blocks 包装
            if type(result) == "table" and #result > 0 and result[1].t ~= "Div" then
                -- 检查是否是 blocks 数组而非单个 Div
                local is_blocks = true
                for _, item in ipairs(result) do
                    if item.t ~= "Para" and item.t ~= "Plain" and item.t ~= "RawBlock"
                       and item.t ~= "Table" and item.t ~= "Header"
                       and item.t ~= "BulletList" and item.t ~= "OrderedList" then
                        is_blocks = false
                        break
                    end
                end
                if is_blocks then
                    return result
                end
            end
            return result
        end,
    },
}

--- 首行缩进控制：通过 Fenced Div 的 class 控制段落是否启用首行缩进。
---
--- 语法：
---   ::: {.no-indent}
---   这段不首行缩进（署名、日期、引用块等）
---   :::
---
---   ::: {.indent}
---   这段强制首行缩进（覆盖 no-indent 的嵌套场景）
---   :::
---
--- 支持的 class：
---   .no-indent → 取消首行缩进（w:firstLine="0"）
---   .indent    → 强制首行缩进 2 字符（w:firstLineChars="200"）
---
--- 实现策略：检测 Div 的缩进 class，将内部段落转换为带 <w:ind> 属性的
--- RawBlock，覆盖模板 Normal 样式的默认首行缩进。
--- 与对齐 class（.text-center/.text-right 等）共存于同一 Div 时，也会向
--- 已由 text-align 过滤器转换的 OpenXML RawBlock 中注入缩进属性。

-- XML 文本转义（pandoc.utils.escape 在 pandoc 3.x 已移除，需手动实现）
local function xml_escape(s)
    s = s:gsub("&", "&amp;")
    s = s:gsub("<", "&lt;")
    s = s:gsub(">", "&gt;")
    s = s:gsub('"', "&quot;")
    s = s:gsub("'", "&apos;")
    return s
end

-- class → 缩进 XML 片段
-- no-indent: 取消首行缩进
-- indent: 强制首行缩进 2 字符（中文标准）
local INDENT_MAP = {
    ["no-indent"] = '<w:ind w:firstLine="0"/>',
    ["indent"]    = '<w:ind w:firstLineChars="200" w:firstLine="480"/>',
}

-- 从 Div attr 中提取缩进 class，未匹配返回 nil
local function get_indent_class(attr)
    if not attr or not attr.classes then return nil end
    for _, cls in ipairs(attr.classes) do
        if INDENT_MAP[cls] then
            return INDENT_MAP[cls], cls
        end
    end
    return nil
end

-- 将 inline 元素转成 OpenXML <w:r><w:t> 文本
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
            local rpr = ""
            if inl.t == "Strong" then rpr = "<w:rPr><w:b/></w:rPr>" end
            if inl.t == "Emph" then rpr = "<w:rPr><w:i/></w:rPr>" end
            if inl.t == "Underline" then rpr = "<w:rPr><w:u w:val=\"single\"/></w:rPr>" end
            local inner = inlines_to_openxml(inl.content)
            inner = inner:gsub("<w:r>", "<w:r>" .. rpr)
            parts[#parts + 1] = inner
        elseif inl.t == "Span" then
            parts[#parts + 1] = inlines_to_openxml(inl.content)
        elseif inl.t == "RawInline" then
            parts[#parts + 1] = inl.text
        end
    end
    return table.concat(parts, "")
end

-- 构造带缩进属性的 OpenXML 段落 RawBlock
local function make_indented_block(block, ind_xml)
    local inlines = block.content or {}
    local runs = inlines_to_openxml(inlines)
    local ppr = "<w:pPr>" .. ind_xml .. "</w:pPr>"
    local xml = "<w:p>" .. ppr .. runs .. "</w:p>"
    return pandoc.RawBlock("openxml", xml)
end

-- 向已生成的 OpenXML 段落 RawBlock 注入缩进属性（<w:ind>）。
-- text-align 过滤器先执行时，会把 Div 内段落转成 RawBlock，这里识别并
-- 在 <w:pPr> 中插入缩进，保证对齐 class 与缩进 class 共存于同一 Div 时两者都生效。
local function inject_indent_to_rawblock(block, ind_xml)
    local raw = block.text
    local ppr_start, ppr_end = raw:find("<w:pPr>", 1, true)
    if ppr_start then
        local injected = raw:sub(1, ppr_start - 1) .. "<w:pPr>" .. ind_xml .. raw:sub(ppr_end + 1)
        return pandoc.RawBlock("openxml", injected)
    end
    -- 无 pPr：在 <w:p> 后补建 pPr
    local p_start, p_end = raw:find("<w:p>", 1, true)
    if p_start then
        local injected = raw:sub(1, p_end) .. "<w:pPr>" .. ind_xml .. "</w:pPr>" .. raw:sub(p_end + 1)
        return pandoc.RawBlock("openxml", injected)
    end
    -- 非段落 RawBlock（如表格），原样保留
    return block
end

-- 处理 Div 内部的 blocks，将缩进属性应用到每个段落
local function process_blocks(blocks, ind_xml)
    local result = {}
    for _, block in ipairs(blocks) do
        if block.t == "Para" or block.t == "Plain" then
            table.insert(result, make_indented_block(block, ind_xml))
        elseif block.t == "Div" then
            -- 嵌套 Div：递归处理内部内容
            table.insert(result, process_div(block, ind_xml))
        elseif block.t == "RawBlock" and block.format == "openxml"
               and block.text:find("<w:p", 1, true) then
            -- 已由 text-align 等过滤器转换的 OpenXML 段落：注入缩进
            table.insert(result, inject_indent_to_rawblock(block, ind_xml))
        else
            -- 其他类型（Table、Header 等）原样保留
            table.insert(result, block)
        end
    end
    return result
end

-- 处理单个 Div（支持递归嵌套）
local function process_div(div, outer_ind)
    local ind_xml, cls = get_indent_class(div.attr)

    if ind_xml then
        -- 本 Div 有缩进 class：提取并移除该 class（避免重复处理）
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
        -- 应用缩进到内部所有段落
        local new_blocks = process_blocks(div.content, ind_xml)
        -- 如果还有其他 class 或 identifier，保留 Div 包装；否则展平
        if #new_classes > 0 or (div.attr.identifier and div.attr.identifier ~= "") then
            return pandoc.Div(new_blocks, new_attr)
        else
            return new_blocks
        end
    elseif outer_ind then
        -- 本 Div 无缩进 class，但父级有：透传缩进到内部
        local new_blocks = process_blocks(div.content, outer_ind)
        return pandoc.Div(new_blocks, div.attr)
    else
        -- 无任何缩进信息，原样返回
        return div
    end
end

return {
    {
        Div = function(div)
            local result = process_div(div, nil)
            if type(result) == "table" and #result > 0 and result[1].t ~= "Div" then
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

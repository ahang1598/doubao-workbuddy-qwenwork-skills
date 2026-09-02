--- 将 RawBlock 中的 HTML 表格转换为 Pandoc Table AST。
---
--- 问题：Pandoc 默认 markdown 格式会把 HTML 表格的每个标签解析为独立的 RawBlock，
--- DOCX 输出时这些 RawBlock 会被丢弃。
---
--- 方案：在 Pandoc 函数中遍历 blocks，合并连续的 RawBlock 和文本块，
--- 检测到完整 <table>...</table> 后用 Pandoc Table API 构造 AST。
---
--- 注意：pandoc.Cell(blocks, align, rowspan, colspan, attr) 的 rowspan/colspan 是整数。

local function is_html_rawblock(el)
    return el and el.t == "RawBlock" and el.format == "html"
end

-- 合并连续的 HTML RawBlock 及其间的文本块，返回完整表格 HTML 字符串
local function try_merge_table(blocks, start_idx)
    local merged = ""
    local i = start_idx
    local found_table_start = false
    local found_table_end = false

    while i <= #blocks do
        local block = blocks[i]

        if is_html_rawblock(block) then
            merged = merged .. block.text
        elseif block.t == "Plain" or block.t == "Para" then
            -- 文本块：用 pandoc.write 输出为 HTML，保留 <u>/<span>/<strong> 等行内元素
            -- 不能用 pandoc.utils.stringify（会丢失所有格式信息）
            local inline_doc = pandoc.Pandoc({block})
            local html = pandoc.write(inline_doc, 'html')
            -- 清理 pandoc.write 添加的多余空白
            html = html:gsub("^%s+", ""):gsub("%s+$", "")
            if html == "" then
                -- 空段落，跳过
            else
                merged = merged .. html
            end
        else
            -- 其他类型 block（Header, Table, Div 等）
            if found_table_start and not found_table_end then
                return nil, 0
            end
            break
        end

        -- 检测 <table 开始
        if merged:find("<table") then
            found_table_start = true
        end

        -- 检测 </table> 结束
        if found_table_start and merged:find("</table>") then
            found_table_end = true
            return merged, i - start_idx + 1
        end

        i = i + 1
    end

    return nil, 0
end

-- 解析合并后的 HTML 表格字符串为 Pandoc Table AST
local function parse_html_table(html_str)
    -- 提取 <table>...</table> 内容
    local table_content = html_str:match("<table[^>]*>(.*)</table>")
    if not table_content then
        return nil
    end

    -- 解析行 <tr>...</tr>
    local rows = {}
    -- 按列位收集用户显式指定的列宽（百分比/小数）
    -- key=列位索引(1-based), value=0~1 之间的小数比例
    -- 只在第一行（通常含 <th>）扫描 width，避免被合并单元格干扰
    local user_col_widths = {}
    local first_row_done = false
    for tr in table_content:gmatch("<tr[^>]*>(.-)</tr>") do
        local cells = {}
        local is_header = false

        -- 解析单元格 <td> 或 <th>
        local pos = 1
        while pos <= #tr do
            local start_tag, tag_name, attrs, close_pos = tr:match("()<(t[hd])([^>]*)>()", pos)
            if not start_tag then break end

            if tag_name:lower() == "th" then
                is_header = true
            end

            -- 查找闭合标签 </td> 或 </th>
            local close_tag_pattern = "</" .. tag_name .. ">"
            local content_end = tr:find(close_tag_pattern, close_pos, true)

            if content_end then
                local content = tr:sub(close_pos, content_end - 1)
                -- 将单元格内容作为 Markdown 重新解析为 Pandoc AST
                -- 这样 <span style="color">、**粗体** 等会被正确解析为
                -- Span/Strong 等行内元素，保留所有格式信息
                -- （后续 preserve_font_color 等过滤器会进一步处理）
                local cell_blocks = pandoc.read(content, 'markdown').blocks
                -- 取第一个 block 的 inlines（Plain/Para 的 content）
                local inlines = {}
                if #cell_blocks > 0 then
                    local first = cell_blocks[1]
                    if first.t == "Plain" or first.t == "Para" then
                        for _, inl in ipairs(first.content) do
                            inlines[#inlines + 1] = inl
                        end
                    else
                        -- 非 Plain/Para（如列表、表格）：原样作为 block 保留
                        inlines = nil
                        cell_blocks = { first }
                    end
                end

                -- 表格单元格内剥离 Underline 元素：表格本身有边框线，
                -- 下划线会造成视觉冗余。保留 Underline 内部的文本内容。
                if inlines then
                    local stripped = {}
                    for _, inl in ipairs(inlines) do
                        if inl.t == "Underline" then
                            -- 展开 Underline 内部所有 inlines
                            for _, inner in ipairs(inl.content) do
                                stripped[#stripped + 1] = inner
                            end
                        else
                            stripped[#stripped + 1] = inl
                        end
                    end
                    inlines = stripped
                end

                -- 解析 colspan/rowspan（整数）
                local colspan = tonumber(attrs:match('colspan%s*=%s*["\']?(%d+)["\']?') or "1") or 1
                local rowspan = tonumber(attrs:match('rowspan%s*=%s*["\']?(%d+)["\']?') or "1") or 1

                -- 解析 style="width:NN%" / "width:NNpx" 等显式列宽
                -- 仅在第一行扫描，按 colspan 加权分配到对应列位
                -- （HTML 表格约定：第一行的 width 决定列宽）
                if not first_row_done then
                    local width_str = attrs:match('style%s*=%s*["\'][^"\']*width%s*:%s*([%d%.]+)')
                    if width_str then
                        local width_num = tonumber(width_str)
                        if width_num then
                            -- 判断单位：如果有 % 标记，width_num 是百分比；否则忽略（不处理 px/em）
                            local has_percent = attrs:match('style%s*=%s*["\'][^"\']*width%s*:%s*[%d%.]+%%')
                            if has_percent then
                                -- 百分比转小数（如 30 → 0.30）
                                local ratio = width_num / 100
                                -- 按 colspan 平均分配到 colspan 个列位
                                local per_col = ratio / colspan
                                for k = 1, colspan do
                                    user_col_widths[#user_col_widths + 1] = per_col
                                end
                            end
                        end
                    end
                end

                -- 解析 align 属性
                local align_str = (attrs:match('align%s*=%s*["\']?(%w+)["\']?') or ""):lower()
                local align = pandoc.AlignDefault
                if align_str == "center" then
                    align = pandoc.AlignCenter
                elseif align_str == "right" then
                    align = pandoc.AlignRight
                elseif align_str == "left" then
                    align = pandoc.AlignLeft
                end

                -- 创建 Cell（pandoc.Cell 签名：blocks, align, rowspan, colspan, attr）
                local cell
                if inlines then
                    cell = pandoc.Cell(
                        pandoc.Plain(inlines),
                        align,
                        rowspan,
                        colspan
                    )
                else
                    -- 空单元格或复杂 block
                    cell = pandoc.Cell(
                        cell_blocks or {pandoc.Plain{pandoc.Str("")}},
                        align,
                        rowspan,
                        colspan
                    )
                end
                table.insert(cells, cell)

                pos = content_end + #close_tag_pattern
            else
                pos = close_pos
            end
        end

        if #cells > 0 then
            local row = pandoc.Row(cells)
            table.insert(rows, {row = row, is_header = is_header})
        end
        first_row_done = true
    end

    if #rows == 0 then
        return nil
    end

    -- 分离表头和数据行
    local header_rows = {}
    local body_rows = {}
    for _, r in ipairs(rows) do
        if r.is_header then
            table.insert(header_rows, r.row)
        else
            table.insert(body_rows, r.row)
        end
    end

    -- 计算最大逻辑列位数（所有行的 colspan 总和取最大值）
    -- HTML 表格允许不规则单元格数，但 pandoc Table AST 严格校验每行
    -- 逻辑列位数必须等于 col_specs 数量，否则报 "unassigned table cell"
    local num_cols = 0
    -- 同时保留原始 cell 的 colspan 信息，便于后续补齐
    local row_specs = {}  -- { {is_header=, cells={ {rowspan=,colspan=,cell=}... } }... }
    for _, r in ipairs(rows) do
        local count = 0
        local spec = { is_header = r.is_header, cells = {} }
        for _, cell in ipairs(r.row.cells or {}) do
            local cs = cell.col_span
            if type(cs) == "table" then cs = cs[1] or 1 end
            local rs = cell.row_span
            if type(rs) == "table" then rs = rs[1] or 1 end
            cs = tonumber(cs) or 1
            rs = tonumber(rs) or 1
            count = count + cs
            spec.cells[#spec.cells + 1] = { cell = cell, colspan = cs, rowspan = rs }
        end
        row_specs[#row_specs + 1] = spec
        if count > num_cols then
            num_cols = count
        end
    end

    if num_cols == 0 then
        return nil
    end

    -- 补齐每行至 num_cols 列位数
    -- 由于 rowspan 横跨多行的情况复杂（需要追踪被占用的列位），
    -- 这里只补齐简单情况：当行 colspan 总和不足 num_cols 时，末尾追加空单元格
    -- （HTML 表格的主流场景，rowspan 占位由 pandoc 内部 AST 处理）
    local fixed_header_rows = {}
    local fixed_body_rows = {}
    for _, spec in ipairs(row_specs) do
        -- 重新构造 Row，确保列位对齐
        local cells = {}
        local used_cols = 0
        for _, c in ipairs(spec.cells) do
            cells[#cells + 1] = c.cell
            used_cols = used_cols + c.colspan
        end
        -- 不足则补齐空单元格
        while used_cols < num_cols do
            cells[#cells + 1] = pandoc.Cell(
                pandoc.Plain{pandoc.Str("")},
                pandoc.AlignDefault,
                1,
                1
            )
            used_cols = used_cols + 1
        end
        -- 超过则跳过（理论上不应发生，因为 num_cols 已是最大值）
        local new_row = pandoc.Row(cells)
        if spec.is_header then
            fixed_header_rows[#fixed_header_rows + 1] = new_row
        else
            fixed_body_rows[#fixed_body_rows + 1] = new_row
        end
    end
    header_rows = fixed_header_rows
    body_rows = fixed_body_rows

    -- 创建列规格
    -- 如果第一行所有列位都有用户显式 width（百分比），则用这些值作为 ColWidth，
    -- 并给 Table 加 id="user-widths" 标记（doc_styler.py 检测到此标记会跳过动态列宽计算）
    local col_specs = {}
    local all_user_widths = (#user_col_widths == num_cols)
    if all_user_widths then
        -- 验证总和接近 1（容差 0.05）
        local sum = 0
        for _, w in ipairs(user_col_widths) do sum = sum + w end
        if math.abs(sum - 1.0) > 0.05 then
            -- 总和不合理，放弃用户宽度
            all_user_widths = false
        end
    end
    if all_user_widths then
        for i = 1, num_cols do
            -- ColWidth 是浮点数（不是函数）：0.30 表示 30%
            table.insert(col_specs, {pandoc.AlignDefault, user_col_widths[i]})
        end
    else
        -- 没有用户显式宽度：用 ColWidthDefault（nil），让 Pandoc 自动算
        for i = 1, num_cols do
            table.insert(col_specs, {pandoc.AlignDefault, pandoc.ColWidthDefault})
        end
    end

    -- 构建 Table
    local table_head = pandoc.TableHead(header_rows)
    local bodies = {
        {
            attr = {},
            body = body_rows,
            head = {},
            row_head_columns = 0
        }
    }
    local table_foot = pandoc.TableFoot({})

    -- 如果所有列位都有用户宽度，给 Table 加 id 标记，
    -- doc_styler.py 检测到 <w:bookmarkStart w:name="user-widths"/> 跳过列宽计算
    local table_attr = all_user_widths
        and pandoc.Attr("user-widths", {}, {})
        or pandoc.Attr("", {}, {})

    -- 尝试构造 Table，捕获错误
    local ok, result = pcall(function()
        return pandoc.Table(
            pandoc.Caption{},
            col_specs,
            table_head,
            bodies,
            table_foot,
            table_attr
        )
    end)
    if not ok then
        return nil
    end
    return result
end

return {
    {
        Pandoc = function(doc)
            local new_blocks = {}
            local i = 1
            local blocks = doc.blocks

            while i <= #blocks do
                local block = blocks[i]

                if is_html_rawblock(block) and block.text:find("<table") then
                    local merged_html, consumed = try_merge_table(blocks, i)
                    if merged_html then
                        local table_ast = parse_html_table(merged_html)
                        if table_ast then
                            table.insert(new_blocks, table_ast)
                            i = i + consumed
                        else
                            table.insert(new_blocks, block)
                            i = i + 1
                        end
                    else
                        table.insert(new_blocks, block)
                        i = i + 1
                    end
                else
                    table.insert(new_blocks, block)
                    i = i + 1
                end
            end

            doc.blocks = new_blocks
            return doc
        end,
    },
}

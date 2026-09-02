-- 禁用 Pandoc 有序列表自动编号，保留 Markdown 原文的序号文字
-- 将 OrderedList 展开为普通段落，序号作为文本前缀拼入段落内容

function OrderedList(el)
    local result = pandoc.List()
    local start_num = el.start or 1
    local style = el.style or "DefaultStyle"
    local delimiter = el.delimiter or "DefaultDelimiter"

    for i, item in ipairs(el.content) do
        local num = start_num + i - 1
        local prefix = _build_prefix(num, style, delimiter)

        for _, block in ipairs(item) do
            if block.t == "Plain" or block.t == "Para" then
                local new_inlines = {pandoc.Str(prefix)}
                for _, inline in ipairs(block.content) do
                    table.insert(new_inlines, inline)
                end
                result:insert(pandoc.Para(new_inlines))
            else
                result:insert(block)
            end
        end
    end
    return result
end

function _build_prefix(num, style, delimiter)
    local m
    local sm = {
        Decimal      = tostring(num),
        UpperRoman   = ({[1]="I",[2]="II",[3]="III",[4]="IV",[5]="V",
                         [6]="VI",[7]="VII",[8]="VIII",[9]="IX",[10]="X"})[num],
        LowerRoman   = ({[1]="i",[2]="ii",[3]="iii",[4]="iv",[5]="v"})[num],
        UpperAlpha   = string.char(64 + ((num - 1) % 26) + 1),
        LowerAlpha   = string.char(96 + ((num - 1) % 26) + 1),
        DefaultStyle = tostring(num),
        Example      = "(" .. tostring(num) .. ")",
    }
    m = sm[style] or tostring(num)

    local dm = {
        DefaultDelimiter = ".",
        OneParen         = ")",
        TwoParens        = "",
        Period           = ".",
    }
    local d = dm[delimiter] or "."

    if delimiter == "TwoParens" then
        return "(" .. m .. ") "
    else
        return m .. d .. " "
    end
end

return { OrderedList = OrderedList }

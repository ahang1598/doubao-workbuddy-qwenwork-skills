-- 处理 Markdown 中的水平线（---）转换为 Word 时的行为。
--
-- 问题：Pandoc 把 Markdown 的 --- 转为 HorizontalRule 元素，
-- DOCX writer 把 HorizontalRule 渲染为 VML <v:rect o:hr="t"/>
-- 水平线对象，在 Word 中显示为可见横线。法律文档中用户写 ---
-- 通常只是想分隔内容，并不希望出现横线。
--
-- 策略：把 HorizontalRule 转换为带上下间距的空段落（RawBlock openxml），
-- 保留视觉分隔感但无可见横线。
--
-- 注意：若用户希望 --- 强制分页，应使用 \newpage（见 SKILL.md 分页符章节），
-- --- 与分页是不同语义，过滤器不混淆。

-- 空段落的上下间距（单位：1/20 pt，即 240 = 12pt，是 Word spacing 属性的单位）
-- Word 的 w:spacing w:before/after 单位是 1/20 pt（与 Pt 的关系：N pt = N*20）
local SPACING_BEFORE_TWENTIETHS = 120  -- 6pt
local SPACING_AFTER_TWENTIETHS = 120   -- 6pt

function HorizontalRule(el)
    -- 直接输出 RawBlock openxml，构造一个仅含间距属性的空 <w:p>
    -- 这样可以精确控制间距，且不产生任何可见元素（无 v:rect、无横线）
    local xml = string.format(
        '<w:p><w:pPr><w:spacing w:before="%d" w:after="%d" w:line="240" w:lineRule="auto"/></w:pPr></w:p>',
        SPACING_BEFORE_TWENTIETHS, SPACING_AFTER_TWENTIETHS
    )
    return pandoc.RawBlock("openxml", xml)
end

return { HorizontalRule = HorizontalRule }

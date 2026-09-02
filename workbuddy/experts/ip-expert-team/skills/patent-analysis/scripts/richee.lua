-- richee.lua — pandoc Lua 滤镜：为 word-report 实现风险等级胶囊。
--
-- 用法：pandoc 输入.md -o 输出.docx \
--        --reference-doc=assets/richee-reference.docx --lua-filter=scripts/richee.lua \
--        --from markdown+east_asian_line_breaks
--
-- 严格遵循《Richee 输出规范》word-report：
--   - 风险用浅红/浅琥珀/浅绿底配深色文字，且必须同时有文字（OUT-COM-004）。
--   - 依据标签为封闭集合，只支持本滤镜声明的四个风险等级（OUT-COM-005）。
-- 不依赖、不读取 Richee-output-standard 规范库。
--
-- 本文件不 return 任何 table，让 pandoc 自动收集顶层函数。

-- 字体与风险色调（与 build_reference.py 一致）
local FONT_HAN = "微软雅黑"

-- 封闭集合：四个风险等级 → 浅底 + 深字
local TONES = {
  ["risk-high"]    = { bg = "FEE2E2", fg = "B91C1C" },  -- 高风险：浅红
  ["risk-mid"]     = { bg = "FEF3C7", fg = "B45309" },  -- 中风险：浅琥珀
  ["risk-low"]     = { bg = "DCFCE7", fg = "15803D" },  -- 低风险：浅绿
  ["risk-pending"] = { bg = "F3F4F6", fg = "6B7280" },  -- 待补充：中性灰
}

local function xml_escape(s)
  s = s or ""
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"))
end

local function tone_of(classes)
  for _, cls in ipairs(classes) do
    if TONES[cls] then return TONES[cls], cls end
  end
  return nil, nil
end

-- 生成一个风险胶囊 run（前后留空格做内边距；同时承载文字，满足 OUT-COM-004）
local function pill_xml(classes, text)
  local tone, key = tone_of(classes)
  if not tone then
    -- 不在封闭集合内：不渲染胶囊，交回原文（避免运行时自创标签）
    return nil
  end
  return string.format(
    '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>' ..
    '<w:b/><w:color w:val="%s"/><w:shd w:val="clear" w:color="auto" w:fill="%s"/>' ..
    '<w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> %s </w:t></w:r>',
    FONT_HAN, FONT_HAN, FONT_HAN, FONT_HAN, tone.fg, tone.bg, xml_escape(text))
end

-- 触发：行内 span 必须含 .tag 且含一个风险等级 class
function Span(el)
  if not el.classes:includes("tag") then return nil end
  local xml = pill_xml(el.classes, pandoc.utils.stringify(el.content))
  if not xml then return nil end
  return { pandoc.RawInline("openxml", xml) }
end

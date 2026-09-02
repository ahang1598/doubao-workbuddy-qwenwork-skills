-- REF：https://github.com/WingDr/siyuan-plugin-citation/blob/main/scripts/citation.lua
-- 作用：统一处理 Markdown 中混入的“原始 HTML”及自定义标记，使导出 docx 时获得接近 Word 原生的显示效果：
--   1) 将 ==高亮== 语法转成 Word 原生 highlight run（<w:highlight w:val="yellow"/>）。
--   2) 将成对的 <sup>/<sub>/<u> RawInline 标签递归匹配并转换为 Pandoc Superscript/Subscript/Underline（旧版无 Underline 构造器则降级为 Span.class="underline"）。
--   3) 解析 <img ...>（无论是 RawInline 还是单行 RawBlock）抽取 alt/src/title/width/height（含 style 中的尺寸），构造 Pandoc Image 并补充属性。若段落仅包含一个由 HTML 转换的图片，则按 alt 优先、title 其次自动提升为 Figure（caption）。
-- 兼容性说明：Pandoc ≥ 2.19 时使用 pandoc.Underline；更早版本自动回退为带 underline 类的 Span，不影响后续样式自定义。与 image-title-to-caption.lua 配合可在 HTML img 有 title 时将其写入 caption。
-- 本过滤器与 image-title-to-caption.lua 配合使用时，HTML img 标签转为图片的同时，设置图片 caption 为图片 title 属性。

function Str(el)
    local text = el.text

    -- 高亮语法处理
    local parts = {}
    local last_end = 1
    for start_pos, match, end_pos in text:gmatch("()==([^=]+)==()") do
        if start_pos > last_end then
        table.insert(parts, pandoc.Str(text:sub(last_end, start_pos - 1)))
        end
        -- 真正的 Word 高亮 run
        table.insert(parts,
        pandoc.RawInline("openxml",
            '<w:r>'
            .. '<w:rPr><w:highlight w:val="yellow"/></w:rPr>'
            .. '<w:t>' .. match .. '</w:t>'
            .. '</w:r>'
        )
        )
        last_end = end_pos
    end

    if last_end <= #text then
        table.insert(parts, pandoc.Str(text:sub(last_end)))
    end

    if #parts > 0 then
        return parts
    end

    -- 默认返回原始文本
    return el
end


-- 将 Raw HTML 的 <sup>/<sub>/<u> 成对标签转成 Pandoc 内联节点
-- 使 docx 输出得到 Word 原生的上下标与下划线

local function is_raw_html(el)
  return el.t == "RawInline" and type(el.format) == "string"
         and el.format:match("^html")
end

-- 更宽容地匹配开/闭标签（允许空格与属性）
local function is_open_tag(el, tag)
  return is_raw_html(el)
     and el.text:match("^%s*<%s*" .. tag .. "%f[%s/>][^>]*>%s*$")
end

local function is_close_tag(el, tag)
  return is_raw_html(el)
     and el.text:match("^%s*</%s*" .. tag .. "%s*>%s*$")
end

-- 递归转换函数：扫描并成对收集，再包成目标内联节点
local function convert_inlines(inlines)
  local out = {}
  local i = 1
  while i <= #inlines do
    local el = inlines[i]

    local function consume_pair(tag, ctor) -- ctor: 函数(buf)->Inline
      local buf = {}
      local j = i + 1
      local found = false
      while j <= #inlines do
        local e2 = inlines[j]
        if is_close_tag(e2, tag) then
          found = true
          break
        end
        table.insert(buf, e2)
        j = j + 1
      end
      if found then
        -- 递归处理内部，支持嵌套
        buf = convert_inlines(buf)
        table.insert(out, ctor(buf))
        return j + 1
      else
        -- 没找到闭合，原样输出开标签并前进一位
        table.insert(out, el)
        return i + 1
      end
    end

    if is_open_tag(el, "sup") then
      i = consume_pair("sup", pandoc.Superscript)

    elseif is_open_tag(el, "sub") then
      i = consume_pair("sub", pandoc.Subscript)

    elseif is_open_tag(el, "u") then
      -- 优先用原生 Underline；若旧版 pandoc 无该构造器，则降级为 Span class="underline"
      local function mk_underline(buf)
        if pandoc.Underline then
          return pandoc.Underline(buf)
        else
          return pandoc.Span(buf, {class = "underline"})
        end
      end
      i = consume_pair("u", mk_underline)

    else
      table.insert(out, el)
      i = i + 1
    end
  end
  return out
end

-- 解析 style 属性中的 width 和 height
local function parse_style_dimensions(style_attr)
    local width, height = nil, nil
    if style_attr then
        -- 匹配 width: 值
        width = style_attr:match('width%s*:%s*([^;]+)')
        if width then
            width = width:match('^%s*(.-)%s*$') -- 去除前后空格
        end
        
        -- 匹配 height: 值
        height = style_attr:match('height%s*:%s*([^;]+)')
        if height then
            height = height:match('^%s*(.-)%s*$') -- 去除前后空格
        end
    end
    return width, height
end

-- 通用的 <img ...> 属性解析函数
-- 返回 table 或 nil: {
--   alt, src, title, width, height, attrTable(用于构建 pandoc.Attr 的 kv 数组)
-- }
local function extract_img_info(txt, opts)
  if not txt or not txt:match('<%s*img[%s/>]') then return nil end
  opts = opts or {}

  -- 兼容自闭合或普通写法，先截取第一对 <img ...>
  -- 不做严格 HTML 解析，仅用模式匹配
  local alt = txt:match('alt%s*=%s*"([^"]*)"') or txt:match("alt%s*=%s*'([^']*)'") or ''
  local src = txt:match('src%s*=%s*"([^"]+)"') or txt:match("src%s*=%s*'([^']+)'")
  if not src or src == '' then return nil end
  local title = txt:match('title%s*=%s*"([^"]*)"') or txt:match("title%s*=%s*'([^']*)'") or ''
  local style = txt:match('style%s*=%s*"([^"]*)"') or txt:match("style%s*=%s*'([^']*)'")
  local width, height = parse_style_dimensions(style)
  if not width then width = txt:match('width%s*=%s*"([^"]+)"') or txt:match("width%s*=%s*'([^']+)'") end
  if not height then height = txt:match('height%s*=%s*"([^"]+)"') or txt:match("height%s*=%s*'([^']+)'") end

  local kv = {}
  if width then table.insert(kv, {'width', width}) end
  if height then table.insert(kv, {'height', height}) end

  return {
    alt = alt,
    src = src,
    title = title,
    width = width,
    height = height,
    attrTable = kv,
  }
end

-- 将 HTML <img ...> (RawInline) 转为 Pandoc Image
local function html_img_inline_filter(el)
  if not (el.t == 'RawInline' and type(el.format) == 'string' and el.format:match('^html')) then
    return nil
  end
  local info = extract_img_info(el.text)
  if not info then return nil end
  local kv = info.attrTable or {}
  table.insert(kv, {'data-html-img', '1'}) -- 供后续 Para 过滤器识别来源
  local attr = (#kv > 0) and pandoc.Attr('', {}, kv) or pandoc.Attr()
  return pandoc.Image({ pandoc.Str(info.alt) }, info.src, info.title ~= '' and info.title or nil, attr)
end

-- 将只含一个来源为 HTML <img> 的段落提升为 Figure（优先 alt, 其次 title）
local function html_img_para_promote(para)
  if #para.content ~= 1 then return nil end
  local el = para.content[1]
  if el.t ~= 'Image' or not (el.attr and el.attr.attributes) then return nil end
  for _, kv in ipairs(el.attr.attributes) do
    if kv[1] == 'data-html-img' then
      local alt_text = ''
      if el.caption and #el.caption > 0 then
        local buff = {}
        for _,c in ipairs(el.caption) do if c.t == 'Str' then table.insert(buff, c.text) end end
        alt_text = table.concat(buff, ' ')
      end
      if alt_text ~= '' then
        return pandoc.Figure({ pandoc.Plain({ el }) }, { pandoc.Str(alt_text) })
      elseif el.title and el.title ~= '' then
        return pandoc.Figure({ pandoc.Plain({ el }) }, { pandoc.Str(el.title) })
      else
        return pandoc.Figure({ pandoc.Plain({ el }) }, {})
      end
    end
  end
  return nil
end

-- 单独一行 <img ...> RawBlock 转为 Figure / Para
local function html_img_rawblock_filter(el)
  if not (el.format and el.format:match('^html')) then return nil end
  local txt = el.text
  local trimmed = txt:gsub('%s+$',''):gsub('^%s+','')
  if not trimmed:match('^<%s*img[^>]->?%s*/?>$') then return nil end
  local info = extract_img_info(trimmed)
  if not info then return nil end
  local kv = info.attrTable or {}
  local attr = (#kv > 0) and pandoc.Attr('', {}, kv) or pandoc.Attr()
  local img = pandoc.Image({ pandoc.Str(info.alt) }, info.src, info.title ~= '' and info.title or nil, attr)
  local alt, title = info.alt, info.title
  if alt ~= '' or (title and title ~= '') then
    local caption_text = (alt ~= '' and alt) or title
    return pandoc.Figure({ pandoc.Plain({ img }) }, { pandoc.Str(caption_text) })
  end
  return pandoc.Para({ img })
end

-- 返回过滤器

return {
  { Str = Str },

  { Inlines = convert_inlines },

  -- 处理 HTML <img .../> 转换为 Pandoc Image 内联，便于后续过滤器统一处理标题到 caption
  { Inline = html_img_inline_filter },
  -- 单行段落里由 HTML 转换的 Image（带 title）提升为 Figure
  { Para = html_img_para_promote },
  -- 单独 RawBlock 的 img 行处理
  { RawBlock = html_img_rawblock_filter }
}

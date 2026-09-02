-- Author: Achuan-2
function Code(el)
  -- 为行内代码添加一个自定义的 Word 样式名称
  return pandoc.Span(el.text, {["custom-style"] = "Inline Code"})
end
return { Code = Code }
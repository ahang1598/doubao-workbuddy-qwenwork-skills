-- 将图片的 title 属性转为 <figcaption> 题注
-- Pandoc 默认用 alt 作为图片标题，此过滤器改为用 title

local function stringify(s)
    return s and pandoc.utils.stringify(s) or ""
end

function Image(el)
    if el.caption and #el.caption > 0 then
        local caption_text = stringify(el.caption)
        el.caption = {}
        if caption_text ~= "" then
            local figure = pandoc.Figure(
                { pandoc.Para({ el }) },
                { { caption_text } }
            )
            return figure
        end
    end
    return el
end

return { Image = Image }

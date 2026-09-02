--- 目录标记清理：删除 Markdown 中的 [TOC] / [TOC:N] 标记。
---
--- 背景：自动目录（Word TOC 域）体验不佳，已停用生成。
--- 保留此模块仅用于清理标记本身，避免 [TOC] 以纯文本形式残留在文档中。
---
--- 语法（独立成行，前后空行）：
---   [TOC]       -- 无效果，标记被删除
---   [TOC:3]     -- 无效果，标记被删除

local function is_toc_marker(text)
    if text:match("^%s*%[TOC%]%s*$") then
        return true
    end
    if text:match("^%s*%[TOC:%d+]%s*$") then
        return true
    end
    return false
end

return {
    {
        -- Pandoc 文档级过滤：删除独立成行的 [TOC] / [TOC:N] 标记
        Pandoc = function(doc)
            local new_blocks = {}
            for _, blk in ipairs(doc.blocks) do
                if (blk.t == "Para" or blk.t == "Plain")
                    and is_toc_marker(pandoc.utils.stringify(blk.content)) then
                    -- 标记被删除，不生成任何内容
                else
                    table.insert(new_blocks, blk)
                end
            end
            doc.blocks = new_blocks
            return doc
        end,
    },
}

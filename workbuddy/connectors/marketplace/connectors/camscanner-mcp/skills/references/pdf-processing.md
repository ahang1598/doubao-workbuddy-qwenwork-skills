# PDF 处理工具参考

## convert_pdf — PDF 格式转换

将 PDF 转换为其他格式。

| target_type | 输出格式 | 说明 |
|-------------|----------|------|
| word | .docx | 保留排版和格式 |
| excel | .xlsx | 提取表格结构 |
| txt | 纯文本 | 仅提取文字内容 |
| md | Markdown | 保留标题、列表、表格等结构 |

适用场景：
- PDF 中有表格需要编辑 → target_type="excel"
- PDF 需要提取文字进行编辑 → target_type="word"
- PDF 需要纯文本内容（如搜索、分析） → target_type="txt" 或 "md"
- 技术文档需要保留结构 → target_type="md"

## convert_pdf_to_images — PDF 转图片列表

将 PDF 每页转为独立图片，返回 file_id 列表。

输出：每一页生成一个 JPG 图片，按页序排列。适用于：
- 需要逐页处理 PDF（如对每页做图片增强）
- 需要图片格式的 PDF 内容

## convert_pdf_to_images_zip — PDF 转图片 ZIP

将 PDF 所有页转为图片后打包为 ZIP。适用于：
- 需要批量下载 PDF 所有页图片
- 不需要逐页处理，只需要一次性获取

## watermark_file — PDF 添加水印

在 PDF 每页添加文字水印。水印斜 45° 覆盖。

## remove_watermark_pdf — PDF 去水印

AI 智能识别并去除 PDF 中的水印。适用于：
- PDF 文档被添加了文字水印
- 需要清晰无水印版本的 PDF

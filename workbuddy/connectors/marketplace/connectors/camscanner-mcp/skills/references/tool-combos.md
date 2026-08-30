# 工具组合参考

本文档列出常见的多步骤操作场景，供 Agent 参考选择正确的 tool 调用链。

## 场景 → 工具组合映射

### 格式转换类

| 用户需求 | 工具链 |
|----------|--------|
| 单张图片 → Word | upload_file → convert_image(target_type=word) → download_file + create_cloud_doc |
| 单张图片 → Excel | upload_file → convert_image(target_type=excel) → download_file + create_cloud_doc |
| 单张图片 → PDF | upload_file → convert_image_to_pdf → download_file + create_cloud_doc |
| 多张图片 → 合并 PDF | upload_file ×N → convert_images_to_pdf(file_ids=[...]) → download_file + create_cloud_doc |
| 多张图片 → 合并 Word | upload_file ×N → convert_images_to_word(file_ids=[...]) → download_file + create_cloud_doc |
| 多张图片 → 合并 Excel | upload_file ×N → convert_images_to_excel(file_ids=[...]) → download_file + create_cloud_doc |
| PDF → Word | upload_file → convert_pdf(target_type=word) → download_file + create_cloud_doc |
| PDF → Excel | upload_file → convert_pdf(target_type=excel) → download_file + create_cloud_doc |
| PDF → Markdown | upload_file → convert_pdf(target_type=md) → download_file + create_cloud_doc |
| TXT → Word | upload_file → convert_txt → download_file + create_cloud_doc |

### 图片处理类

| 用户需求 | 工具链 |
|----------|--------|
| 去阴影 | upload_file → enhance_image(enhance_mode=5) → download_file + create_cloud_doc |
| 锐化 | upload_file → enhance_image(enhance_mode=2) → download_file + create_cloud_doc |
| 高清化 | upload_file → image_hd → download_file + create_cloud_doc |
| 老照片修复 | upload_file → restore_photo → download_file + create_cloud_doc |
| 去水印（图片） | upload_file → enhance_image(enhance_mode=10) → download_file + create_cloud_doc |
| 去水印（PDF） | upload_file → remove_watermark_pdf → download_file + create_cloud_doc |
| 加水印（图片） | upload_file → watermark_image(text=xxx) → download_file + create_cloud_doc |
| 加水印（PDF） | upload_file → watermark_file(file_id=xxx, file_type=pdf, text=xxx) → download_file + create_cloud_doc |
| 图片翻译 | upload_file → translate_image(to=xx) → download_file + create_cloud_doc |
| 提取公式 | upload_file → extract_image → 直接返回 LaTeX 文本 |

### 复合操作

| 用户需求 | 工具链 |
|----------|--------|
| 增强后转 Word | upload_file → enhance_image → convert_image(file_id=增强后结果, target_type=word) → download + cloud |
| PDF 逐页增强 | upload_file → convert_pdf_to_images → 对每页 enhance_image → convert_images_to_pdf → download + cloud |
| 图片编辑文字 | upload_file → scan_image_edit → edit_image(edit_data=...) → download + create_cloud_doc |
| 检测后增强 | upload_file → validate_image → 根据结果选择增强方式 → download + cloud |

---

## 注意事项

1. **大文件上传**：对于大文件（≥50KB），使用 HTTP API 直接上传（curl --data-binary），避免 base64 编码占用 Agent 上下文
2. **file_id 传递**：每个 tool 返回的 file_id 可以直接作为下一个 tool 的输入，无需重新 upload
3. **批量上传**：多文件场景需逐个 upload_file，收集所有 file_id 后传入批量工具
4. **结果过期**：file_id 有时效性（通常 24 小时），处理完毕后应及时 download 或 create_cloud_doc
5. **云端保存类型匹配**：create_cloud_doc 的 file_type 必须与实际文件类型匹配（word 对应 .docx，excel 对应 .xlsx 等）

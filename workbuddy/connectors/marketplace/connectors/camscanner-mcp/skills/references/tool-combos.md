# 工具组合参考

本文档列出常见的多步骤操作场景，供 Agent 参考选择正确的 tool 调用链。

## 场景 → 工具组合映射

### 格式转换类

| 用户需求 | 工具链 |
|----------|--------|
| 单张图片 → Word | 上传文件 → convert_image(target_type=word) → download_file + create_cloud_doc |
| 单张图片 → Excel | 上传文件 → convert_image(target_type=excel) → download_file + create_cloud_doc |
| 单张图片 → PDF | 上传文件 → convert_image_to_pdf → download_file + create_cloud_doc |
| 多张图片 → 合并 PDF | 上传文件 ×N → convert_images_to_pdf(file_ids=[...]) → download_file + create_cloud_doc |
| 多张图片 → 合并 Word | 上传文件 ×N → convert_images_to_word(file_ids=[...]) → download_file + create_cloud_doc |
| 多张图片 → 合并 Excel | 上传文件 ×N → convert_images_to_excel(file_ids=[...]) → download_file + create_cloud_doc |
| PDF → Word | 上传文件 → convert_pdf(target_type=word) → download_file + create_cloud_doc |
| PDF → Excel | 上传文件 → convert_pdf(target_type=excel) → download_file + create_cloud_doc |
| PDF → Markdown | 上传文件 → convert_pdf(target_type=md) → download_file + create_cloud_doc |
| TXT → Word | 上传文件 → convert_txt → download_file + create_cloud_doc |

### 图片处理类

| 用户需求 | 工具链 |
|----------|--------|
| 去阴影 | 上传文件 → enhance_image(enhance_mode=5) → download_file + create_cloud_doc |
| 锐化 | 上传文件 → enhance_image(enhance_mode=2) → download_file + create_cloud_doc |
| 高清化 | 上传文件 → image_hd → download_file + create_cloud_doc |
| 老照片修复 | 上传文件 → restore_photo → download_file + create_cloud_doc |
| 去水印（图片） | 上传文件 → enhance_image(enhance_mode=10) → download_file + create_cloud_doc |
| 去水印（PDF） | 上传文件 → remove_watermark_pdf → download_file + create_cloud_doc |
| 加水印（图片） | 上传文件 → watermark_image(text=xxx) → download_file + create_cloud_doc |
| 加水印（PDF） | 上传文件 → watermark_file(file_id=xxx, file_type=pdf, text=xxx) → download_file + create_cloud_doc |
| 图片翻译 | 上传文件 → translate_image(to=xx) → download_file + create_cloud_doc |
| 提取公式 | 上传文件 → extract_image → download_file + create_cloud_doc |

### 复合操作

| 用户需求 | 工具链 |
|----------|--------|
| 增强后转 Word | 上传文件 → enhance_image → convert_image(file_id=增强后结果, target_type=word) → download + cloud |
| PDF 逐页增强 | 上传文件 → convert_pdf_to_images → 对每页 enhance_image → convert_images_to_pdf → download + cloud |
| 图片编辑文字 | 上传文件 → scan_image_edit → edit_image(edit_data=...) → download + create_cloud_doc |
| 检测后增强 | 上传文件 → validate_image → 根据结果选择增强方式 → download + cloud |
| 发票识别 | 上传文件 → extract_receipt(output_mode=raw) → 解析 JSON 向用户展示 |
| 搜索云文档 | search_cloud_doc(keyword=..., doc_type=..., start_time=...) → 展示结果列表 |

---

## 注意事项

1. **文件上传**：上传文件指 `create_upload` → 二进制上传 → `complete_upload`，最终获得 `file_id`
2. **file_id 传递**：每个 tool 返回的 file_id 可以直接作为下一个 tool 的输入，无需重新上传
3. **批量上传**：多文件场景逐个上传，收集所有 file_id 后传入批量工具
4. **结果过期**：file_id 有时效性（通常 24 小时），处理完毕后应及时 download 或 create_cloud_doc
5. **云端保存类型匹配**：create_cloud_doc 的 file_type 必须与实际文件类型匹配（word 对应 .docx，excel 对应 .xlsx 等）
6. **无需上传的工具**：`search_cloud_doc` 是纯参数查询工具，不需要文件上传步骤
7. **发票识别输出**：`extract_receipt` 使用 `output_mode=raw` 可直接获取 JSON，无需再 download_file

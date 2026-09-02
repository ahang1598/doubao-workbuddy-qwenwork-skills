---
name: linkfox-file-upload
description: 把本地文件上传到云端（阿里云 OSS），返回可公开访问的 HTTPS URL。任何"需要一个 URL 而手头只有本地文件"的场景都走本 skill——例如把生成的图片/视频/报告/CSV/PDF 回传给前端展示、分享给用户、或喂给只接受 URL 入参的下游接口（如商品库更新图片、A+ 图入库、把素材链接写回飞书表格）。用户说"上传文件""把这个图/视频/文件传上去""传到 OSS/云端""给我个下载链接/公开链接""upload this file""get a public url"时触发；即使没说"上传"二字，只要要把本地产物变成可访问链接、或某接口要求传 imageUrls/url 而当前只有本地路径，也应触发本 skill。注意：上传即对外发布，文件会获得公开可访问 URL；上传前确认内容可公开。
---

# 文件上传（OSS）

把本地文件上传到阿里云 OSS，拿到可公开访问的 HTTPS URL。底层复用共享实现 `_shared/linkfox_paths.py` 的 `get_sts_voucher()` + `upload_file()`，上传成功后自动把 URL 登记进会话 `_meta.json`。

## 何时用

- 生成的图片/视频/报告/CSV/PDF 要回传前端、分享给用户。
- 下游接口只接受 URL（如 `linkfox-product-center-listing-update-images` 的 `imageUrls`、A+ 图入库、写回飞书多维表格的附件链接），而当前只有本地文件路径——先用本 skill 拿 URL，再调下游。

## 调用方式

```bash
python scripts/file_upload.py <local_path> [<local_path> ...]
```

- 支持一次传多个文件（共用一份 STS 凭证，省一次取证）。
- 输出 JSON 数组，每个元素：
  - 成功：`{"url": "https://...", "path": "<OSS对象键>", "name": "<原文件名>", "size": <字节>, "ext": "<扩展名>"}`
  - 失败：`{"error": true, "input": "<路径>", "message": "<原因>"}`
- 任一文件失败 → 进程非零码退出（成功项仍输出），便于上层判断。

## 使用指引

1. 只传**确实要对外发布**的文件——上传后即获得公开可访问 URL。
2. 文件大小 / 类型受 OSS 凭证约束（`maxFileSize` / `supportedTypes`），超限会返回结构化错误，不崩栈。
3. 取 URL 后若要喂给下游接口，直接用返回的 `url` 字段。
4. 依赖 `oss2`（`pip install oss2`）与环境变量 `LINKFOX_AGENT_API_KEY`；缺失时返回明确错误。

## 限制

- 仅上传，不做转码/压缩/裁剪。
- URL 公开可访问，不要上传敏感/私密内容。
- 单次失败的文件需修正后重传（成功项不会重复上传）。

## 反馈

底层返回字段与凭证约束见 [`references/api.md`](references/api.md)。

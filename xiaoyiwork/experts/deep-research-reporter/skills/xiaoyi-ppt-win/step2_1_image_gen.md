# 子流程二·一：图片生成

> **前置条件**：子流程二已完成，大纲文件保存在 `$PPT_SESSION_DIR/outline_pre.md`。

**目标**：
1. 解析大纲中的 `<image_user_provided>` 标签，将用户上传的图片预处理后上传到 OSMS，替换为实际图片引用。
2. 解析大纲中的 `<image_gen_queries>` 标签，调用 Seedream 生成图片，替换为实际图片引用，并将图片上传获取 URL。
3. `<image_search_queries>` 标签保留不动，由后续流程处理。

```bash
echo "$PPT_SESSION_ID"
echo "$PPT_SESSION_DIR"
PPT_SESSION_ID="$PPT_SESSION_ID"
$PYTHON_CMD $XIAOYI_PPT_DIR/scripts/replace_gen_images.py "$PPT_SESSION_DIR/outline_pre.md"
```

脚本内部流程：
1. 正则提取大纲中所有 `<image_user_provided>` 标签，预处理用户图片（格式转换），上传到 OSMS，替换为 `![{"caption":"...","content":"","width":"...","height":"...","filename":"xxx.jpg"}](xxx.jpg)` 格式
2. 正则提取大纲中所有 `<image_gen_queries>caption</image_gen_queries>` 标签
3. 逐条调用 Seedream API 生成图片并下载。
4. 将 `<image_gen_queries>` 替换为 `![{"caption":"...","content":"","width":"...","height":"..."}](filename)` 格式
5. 上传所有图片到 OSMS，将 URL 列表保存至`$PPT_SESSION_DIR/image_urls.json`
6. 替换后的大纲保存至`$PPT_SESSION_DIR/outline.md`

**完成后**：
- 替换后的大纲文件：`$PPT_SESSION_DIR/outline.md`
- 图片 URL 列表：`$PPT_SESSION_DIR/image_urls.json`

完成标志：输出 `✅ 图片已就绪，正在为您生成PPT，请稍候`。

---

## ⚠️ 下一步（必须执行）

> **在执行任何 PPT 生成操作之前，必须先使用 Read 工具读取 `$XIAOYI_PPT_DIR/step3_generate_monitor.md` 的完整内容，再继续。**
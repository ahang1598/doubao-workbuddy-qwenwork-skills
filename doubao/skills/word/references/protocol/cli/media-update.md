---
keyword: media-update
---

**功能**：图片插入、替换与属性更新流程

# 本地 Word 图片插入、替换与属性更新

本文负责图片插入、资源替换和属性更新的 CLI 用法；上传命令查询 `media-upload`，`<img>` 的属性、取值和结构约束查询 `xml:img`。

按目标选择处理方式：

- **插入或替换资源**：按 `media-upload` 的来源表取得图片资源 token。当前 Canvas 里的图片 token 或本次上传得到的 `file_token` 可以复用。网络图片先下载到本地，再上传。
- **仅修改属性**：inline 图片，或浮动图片的裁剪、边框、环绕、锚点相对定位等声明式属性使用 XML，保留原 `src`。已有浮动图片的移动、缩放、旋转、翻转、层叠、重锚和原样复制使用 `object`。

## 图片与插入位置

插入或替换时用用户指定的图片来源。上传的 `--parent-node` 和 Canvas 命令的 `--doc` 使用同一文档 `token`。图片资源的 `file_token` 放进 `<img src>`。只改现有图片属性时保留原 `src`。

`--block-id` 使用插入锚点或现有图片 ID。正文的行内图片从所属顶层块定位，页眉页脚里的图片用 `layout` 读取。新增图片没指定尺寸时，保持原图比例，显示宽度不超过页面可用宽度。已有页面尺寸和页边距可以直接用，缺少时再读 `layout`。

查看图片或保存原图见 `media-preview` 和 `media-download`。

## 插入新图片

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<anchor_block_id>" \
  --content '<img src="file_xxx" width="360pt" height="270pt"/>'
```

- `--block-id` 是插入锚点，不是上传使用的 `--parent-node`。
- 示例中的尺寸按实际图片和页面可用宽度填写。
- `<img>` 只写 `xml:img` 明确支持的属性。
- 后续操作需要新图片 block ID 时，从图片所在范围读取。
- 新增 `<img>` 不复用既有图片 ID；以 inline 图片为锚点时，content 必须恰好是单个 `<img>`，结果位于同一段文本流。

## 替换已有图片

先用 `--detail full` 取得原图片的完整 XML，保留用户未要求修改的属性。以下命令仅示意目标属性，实际 content 须以完整基线为底稿，不可照抄后丢弃其他属性。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<image_block_id>" \
  --content '<img src="file_xxx" width="800" height="600" border-style="solid" border-width="1pt" border-color="#000000"/>'
```

standalone 图片的 content 里带上从 fetch 读到的 `id` 属性（须与 `--block-id` 一致），block ID 就会保留；省略 `id` 会新建 record，原 ID 立即失效。inline 图片的专用替换只更新原图片 record，content 必须恰好是单个 `<img>`，不改变原 ID、inline mark 或宿主段落。

## 更新现有图片属性

不上传图片、不更换 `src`。inline 图片和浮动图片的声明式属性以最新完整 `<img>` 为底稿，只修改目标属性；已有浮动图片的物理操作改用 `object`。

### 浮动定位与环绕

先按 fetch 文档读取目标所在容器的完整 XML，保留用户未要求修改的 sidecar。提交最终几何，不提交 pointer delta，不模拟拖拽或跨 carrier 重新锚定。目标布局或宿主 inline occurrence 已变化时，旧请求会失败，必须重新 Fetch。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace --block-id "<image_block_id>" \
  --content '<img id="<image_block_id>" src="<原 token>" layout="floating" wrap="square" position-h-relative-from="page" position-h-align="right" position-v-relative-from="page" position-v-align="bottom"/>'
```

示例仅展示定位字段；实际写入须保留原尺寸和其他非目标属性，并满足 XML 规范中的每轴定位互斥、simple position 与双轴定位切换约束。

### inline 图片的水平对齐

水平对齐属于宿主 `<p align>`，不是 `<img>` 属性。先读 `xml:p`，获取并回放完整宿主 XML，只改目标对齐；该值同时影响同段文字和其他 inline object。

## 失败处理

- 更新失败或结果未知时，见[异常处理](../../workflows/canvas-doc-recovery.md)。
- `ATTR_CAPABILITY_LIMITED`（如图片 `href`、`action-type`）对应用户目标或基线保真要求时，按上层工作流能力与恢复流程处理，不得只忽略 warning 或反复换写法。图片替代文本使用已支持的 `alt-description` / `alt-title`，不要写笼统的 `alt`。
- 上传失败：不要执行 `lark-cli docs +local-update`。
- 上传成功、文档更新失败：明确告诉用户图片已经上传但尚未写入文档，并保留返回的 `file_token` 供重试；当前没有稳定的素材自动删除契约，不要自行删除。
- 文档更新结果为 `partial_success`：从 `warnings` 说明已知限制。上传 token 只表示素材已上传。
- block ID 失效或内容冲突：重新 fetch 目标范围；资源替换沿用已上传的 `file_token`，仅改属性保留最新基线的原 `src`，重新规划更新；不要重复上传同一图片。
- 客户端不可达或本地 Word 已关闭：停止当前 CLI 流程，不要把活动文档 `<token>` 当本地路径。

## 明确禁止

- 不使用 `lark-cli docs +media-insert`；
- 不把普通文件路径或网络 URL 写入 `src`；
- 图片资源必须通过 `src` 引用；不使用在线文档的附件类型、`align` 或 `file-view`；
- 不把图片上传和文档更新并行执行；
- 不根据 token 外形自行判断对象类型或构造 `office_docx_file` 私有请求。

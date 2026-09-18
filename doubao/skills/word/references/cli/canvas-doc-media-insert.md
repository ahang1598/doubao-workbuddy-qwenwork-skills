# 本地 Word 图片插入、替换与属性更新

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

本文负责图片上传、插入、资源替换和属性更新的 CLI 流程与验证；`<img>` 的属性、取值和结构约束见 [`canvas-doc-media.md`](../xml/canvas-doc-media.md)。

按目标选择处理方式：

- **插入或替换资源**：已有有效图片 token 可直接复用；本地文件或网络 URL 须先用 `docs +media-upload` 取得 `data.file_token`，再通过 `docs +local-update` 写入。
- **仅修改属性**：修改尺寸、裁剪、旋转、边框、浮动或环绕等属性时，保留原 `src`，跳过来源选择和上传。

## 前置条件

执行前必须读取：

1. [`canvas-doc-fetch.md`](canvas-doc-fetch.md) — 获取插入点或原图片 block ID；
2. [`canvas-doc-update.md`](canvas-doc-update.md) — block 指令、生命周期和验证规则；
3. [`canvas-doc-xml.md`](../xml/canvas-doc-xml.md) — 公共 XML、节点身份、颜色和转义规则；
4. [`canvas-doc-media.md`](../xml/canvas-doc-media.md) — `<img>` 属性及浮动/嵌入结构约束。

确认以下标识来自宿主上下文，不要自行猜测：

- `<token>`：Canvas 上下文提供的当前本地 Word token；既传给 `docs +local-fetch` / `docs +local-update --doc`，也在上传新图片时传给 `docs +media-upload --parent-node`。不要另找 `obj_token`，也不要用文档路径或 block ID 顶替；
- `block_id`：插入锚点或待替换图片 block，来自最新一次 fetch。

## 来源选择（Agent 必读）

本节仅适用于插入图片或替换资源；仅改现有图片属性时直接使用最新 Fetch 的原 `src`。
> **最高优先级：用户明确指定图片来源时，严格使用该来源。** 不要因为另一种来源更方便，就擅自改用已有 token、其他本地文件或在线文档链路。

按以下规则处理：

| 图片来源 | 本地 Word 处理方式 | 禁止做法 |
|---|---|---|
| 当前本地 Word fetch 返回的图片 token，或本次上传已经返回的 `file_token` | 直接写入 `<img src="...">`，跳过上传 | 不要重复上传同一图片 |
| 用户给出明确的本地图片路径 | 使用 `docs +media-upload --file <path>`，取得 `file_token` 后更新文档 | 不要把文件路径直接写入 `src` |
| 用户给出 HTTP/HTTPS 图片 URL | 先下载为可访问的本地图片文件，再执行上传和更新 | 不要把 URL 写入 `src`，也不要改用在线文档的 `<img href>` |
| 用户只说明“剪切板里的图”“刚复制的截图” | 告知当前 `docs +media-upload` 不支持剪切板，请用户提供可访问的本地图片文件 | 不要调用 `docs +media-insert --from-clipboard`，也不要猜测图片路径 |
| 上下文没有唯一、明确的图片来源 | 只问一个澄清问题，确认使用已有 token、本地文件还是网络 URL | 不要扫描目录、猜测最近图片或任意选择文档内图片 |

补充规则：

- 用户明确给出本地文件时，即使剪切板中可能存在相同图片，也使用该文件。
- 用户明确给出网络 URL 时，即使文档内可能已有相似图片，也按该 URL 下载并上传。
- 只有 token 明确来自当前本地 Word fetch 或一次已成功完成的上传时，才能省略上传；不要根据 token 外形猜测资源有效性。
- 从 URL 下载失败、文件不存在或剪切板没有可用本地文件时，停止写入并说明缺失条件；不要静默换来源。

## 标准流程

1. 按 [`canvas-doc-fetch.md`](canvas-doc-fetch.md#选择-detail) `--detail full` 读取最小完整目标范围，确认锚点或原图片 record ID；inline 图片从所属正文顶层容器读取，页眉页脚内的内容按 layout 读取，不把嵌套图片 ID 直接作为 range 锚点。
> 当插入全新图片且用户未指定 `width`、`height` 时，再执行 `docs +local-fetch --scope layout --detail full`，根据当前页面尺寸和页边距设置不超出可用区域且保持原图比例的尺寸；不要直接使用原图尺寸或照抄示例值。
2. 插入或替换资源时按“来源选择”确定图片 token：已有有效 token 时直接复用；本地文件或已下载的 URL 图片继续执行上传。仅改属性时保留原 `src`，跳过第 3 步。
3. 需要上传时，先使用同一个本地 Word `<token>` 作为 `--parent-node` 执行 `--dry-run`，确认请求的 `parent_type` 被映射为 `office_docx_file`；再执行 `docs +media-upload` 并保存返回的 `data.file_token`。未发生映射时停止，不尝试其他 token。
4. 使用 `block_insert_after` 插入图片，或使用 `block_replace` 替换资源/更新属性。以最新完整 XML 为底稿，只改目标字段，回放全部非目标属性；具体命令目标以 [`canvas-doc-update.md`](canvas-doc-update.md#可寻址标签与可用命令) 为准。
5. 重新 fetch 目标范围，确认 `<img src>`、尺寸和其他样式已经生效，并比较未修改属性。查看图片或保存原图时，完整读取[图片资源读取](canvas-doc-fetch.md#图片资源读取)，资源 token 均从 `<img src>` 提取。

不要并行上传和更新：后一步依赖前一步返回的 `file_token`。

## 1. 上传图片

```bash
# 先预览上传请求
lark-cli docs +media-upload \
  --file "./image.png" \
  --parent-type docx_image \
  --parent-node "<token>" \
  --dry-run

# 确认 parent_type=office_docx_file 后执行上传
lark-cli docs +media-upload \
  --file "./image.png" \
  --parent-type docx_image \
  --parent-node "<token>"
```

调用方仍传公开参数值 `docx_image`；CLI 识别本地 Word token 后自动把下游 `parent_type` 映射为 `office_docx_file`。若 dry-run 没有发生该映射，停止执行，不要手工改写请求或直接调用 Drive 私有接口。

成功结果中的关键字段位于 `data`：

```json
{
  "data": {
    "file_token": "file_xxx",
    "file_name": "image.png",
    "size": 12345
  }
}
```

- `data.file_token` 是后续 `<img src="...">` 使用的资源 token。
- 文件大于 20MB 时命令会自动改用分片上传。

## 2. 插入新图片

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<anchor_block_id>" \
  --content '<img src="file_xxx" width="800" height="600"/>'
```

- `--block-id` 是插入锚点，不是上传使用的 `--parent-node`。
- `<img>` 只写 [`canvas-doc-media.md`](../xml/canvas-doc-media.md) 明确支持的属性。
- 插入完成后重新 fetch，取得新图片 block ID；不要猜测新 ID。

## 3. 替换已有图片

先用 `--detail full` 取得原图片的完整 XML，保留用户未要求修改的属性。以下命令仅示意目标属性，实际 content 须以完整基线为底稿，不可照抄后丢弃其他属性。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<image_block_id>" \
  --content '<img src="file_xxx" width="800" height="600" rotation="90" flip-horizontal="false" flip-vertical="false" border-style="solid" border-width="1pt" border-color="#000000"/>'
```

standalone 图片的 content 里带上从 fetch 读到的 `id` 属性，block ID 就会保留；省略 `id` 会新建 record，原 ID 立即失效。inline 图片的专用替换只更新原图片 record，content 必须恰好是单个 `<img>`，不改变原 ID、inline mark 或宿主段落。无论哪种情况，下一步修改前都要重新 fetch 确认写入结果；不得删除其他图片 block。

## 4. 更新现有图片属性

不上传图片、不更换 `src`；以最新完整 `<img>` 为底稿，只修改目标属性。图片 record ID、content 形状和 inline/standalone 区别沿用上一节及通用 update 契约。

### 浮动定位与环绕

先按 fetch 文档读取目标所在容器的完整 XML，保留用户未要求修改的 sidecar。提交最终几何，不提交 pointer delta，不模拟拖拽或跨 carrier 重新锚定。目标布局或宿主 inline occurrence 已变化时，旧请求会失败，必须重新 Fetch。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace --block-id "<image_block_id>" \
  --content '<img id="<image_block_id>" src="<原 token>" layout="floating" wrap="square" position-h-relative-from="page" position-h-align="right" position-v-relative-from="page" position-v-align="bottom"/>'
```

示例仅展示定位字段；实际写入须保留原尺寸和其他非目标属性，并满足 XML 规范中的每轴定位互斥、simple position 与双轴定位切换约束。写后回读完整图片，确认 identity、宿主 inline occurrence 和未修改 sidecar 均保持。

### inline 图片的水平对齐

水平对齐属于宿主 `<p align>`，不是 `<img>` 属性。先读 [`canvas-doc-text.md`](../xml/canvas-doc-text.md)，获取并回放完整宿主 XML，只改目标对齐；该值同时影响同段文字和其他 inline object。写后核对整个宿主段落，而不只检查图片。

## 失败处理

- 更新失败、结果未知或回读偏离时，统一遵循 [`canvas-doc-recovery.md`](../workflows/canvas-doc-recovery.md#失败处理) 的停止条件与共享修正预算，不另起重试流程。
- `ATTR_CAPABILITY_LIMITED`（如图片 `href`、`action-type`）对应用户目标或基线保真要求时，按工作流能力预检处理，不得只忽略 warning 或反复换写法。图片替代文本使用已支持的 `alt-description` / `alt-title`，不要写笼统的 `alt`。
- 上传失败：不要执行 `docs +local-update`。
- 上传成功、文档更新失败：明确告诉用户图片已经上传但尚未写入文档，并保留返回的 `file_token` 供重试；当前没有稳定的素材自动删除契约，不要自行删除。
- 文档更新结果为 `partial_success`：检查 `warnings`，再 fetch 验证；不要仅因已经取得 token 就宣称插入成功。
- block ID 失效或内容冲突：重新 fetch 目标范围；资源替换沿用已上传的 `file_token`，仅改属性保留最新基线的原 `src`，重新规划更新；不要重复上传同一图片。
- 客户端不可达或本地 Word 已关闭：停止当前 CLI 流程，不要把活动文档 `<token>` 当本地路径。

## 明确禁止

- 不使用 `docs +media-insert`；
- 不把普通文件路径或网络 URL 写入 `src`；
- 图片资源必须通过 `src` 引用；不使用在线文档的附件类型、`align` 或 `file-view`；
- 不把图片上传和文档更新并行执行；
- 不根据 token 外形自行判断对象类型或构造 `office_docx_file` 私有请求。

===== 全文完 =====

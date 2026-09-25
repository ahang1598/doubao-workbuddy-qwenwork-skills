# slides +update-slide（整页更新已有页面）

把一整页 XML 交给某个已有页面，页面变成 `--content` 描述的样子。`slide_id` 和页序都不变。

## 命令

```bash
# 标准用法：整页 XML 从文件读（推荐：避免 shell 转义和长参数截断）
lark-cli slides +update-slide\
  --presentation "https://xxx.feishu.cn/slides/slidesXXXXXXXXXXXXXXXXXXXXXX" \
  --slide-id "piy" \
  --content @page.xml

# XML 从 stdin 读
cat page.xml | lark-cli slides +update-slide\
  --presentation "$PRES" --slide-id "$SLIDE" --content -

# wiki 链接直接传（CLI 自动解析并校验 obj_type=slides）
lark-cli slides +update-slide\
  --presentation "https://xxx.feishu.cn/wiki/wikcnXXXXXX" \
  --slide-id "piy" --content @page.xml

# 预览请求，不实际写入
lark-cli slides +update-slide\
  --presentation "$PRES" --slide-id "$SLIDE" --content @page.xml --dry-run
```

## 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--presentation` | 是 | `xml_presentation_id`、`/slides/` URL 或 `/wiki/` URL |
| `--slide-id` | 是 | 要整页替换的页面 `slide_id` |
| `--content` | 是 | 这一页的完整目标 XML，单一 `<slide>` 根；支持字面量、`@file`、stdin `-`。别名：`--xml` / `--slide-xml` / `--slide-content` / `--content-xml` |
| `--revision-id` | 否 | 默认 `-1`（最新）。它只选择服务端执行所基于的快照，不是“页面有新编辑就拒绝”的乐观锁；传旧版本号会以旧快照重建页面并丢弃其后的编辑 |
| `--tid` | 否 | 调用方提供的任务/事务标识，CLI 原样透传；用于关联同一编辑任务或重试，不等同于版本前置条件，不能单独保证并发冲突时拒绝写入。一般留空 |
| `--no-lint` | 否 | 跳过服务端版式校验（默认开启）；只能在当前页已被拦、完整报告已读完且符合[单页例外规则](../workflow/validation-xml.md)时单独使用，禁止多页共用或自动重试附加 |

`@file` 和 `+xml-get --output` 一样**只接受当前目录下的相对路径**，绝对路径会被拒。
命令别名：`slides +update`（隐藏）；服务别名：`lark-cli slide …` 等价于 `lark-cli slides …`。

如果要求“从读取之后页面一旦变化就不再写入”，不能只传 `--revision-id` 或 `--tid`。写入前必须再次用 `+xml-get` 回读最新版，比较读取期间是否发生变化；有变化时先基于最新版重新合并本次修改，再执行整页写回。当前 shortcut 不提供严格的 compare-and-swap 保证。

## 语义：`--content` 就是这一页的最终状态

**没写进 `--content` 的东西会从页面上消失。** 这不是补丁，是整页覆盖。

如果 `--content` 中包含树状图，树状图主体必须是 `make_relation_atomized(..., strict_no_embed=True)` 或 CLI `--atomized` 输出的可编辑 `<shape>` / `<line>` / `<shape type="custom">` / 文本框；不得用 `<embed>` 替代，否则整页覆盖会把树状图固化成不可编辑插图。

| 你在 `--content` 里怎么写 | 页面上的结果 |
|---|---|
| 元素带原来的 `id` | 按新 XML 更新这个元素 |
| 元素不带 `id` | 作为新元素插入到它所在的位置 |
| 原来有、`--content` 里没有的元素 | **删除** |
| `<style>` 改了 | 背景等页面样式跟着改 |
| 没写 `<note>` | 讲者备注被清空 |

一次请求就能同时做完改样式、插入、删除、换备注、换背景——这是 `+replace-slide` 逐元素 part 做不到的（它没法寻址背景，也没有 move 操作）。

## 标准读-改-写流程

```bash
# 1. 首次编辑前保存当前页原稿和 lint 基线（文件名应区分任务/页面）
lark-cli slides +xml-get\
  --presentation "$PRES" --slide-id "$SLIDE" --output page-source.xml \
  --json > page-source-response.json 2> page-source-error.json
```

确认本次读取成功后，有问题就按 `--details --document` 和 `--details --slide-number <报告内部页码>` 读完文档级及本页详情；按 `pagination.next_offset` 翻到 `has_more: false`。来源基线尚未读完时不开始修改。复制 `page-source.xml` 为 `page.xml` 并实际完成编辑，保留原有元素 ID，新元素不写 ID；核对正文、数值、单位和标签的计划内差异后，再执行写入：

```bash
# 整页写回，直接读取本次 CLI 返回
lark-cli slides +update-slide\
  --presentation "$PRES" --slide-id "$SLIDE" --content @page.xml
```

先 `--dry-run` 看请求，确认无误再执行。

已有本轮原稿基线时继续保留；写入前的最新回读另存，不能把已修改结果覆盖成原稿。报告解析与前后比较见 [validation-xml.md](../workflow/validation-xml.md)。

> ⚠️ **第 1 步不要加 `--remove-attr-id`。** 那个参数会把所有元素的 `id` 去掉，再交给 `+update-slide` 的话，每个元素都会被当成新元素插入、原来的全部被删除——页面看起来一样，但所有元素换了新 id，锚在旧 id 上的评论和 block 直达链接全部失效，而且**不会有任何报错**。`--remove-attr-id` 只用于只读查看。

## 命令校验与空页限制

| 情况 | 报错 |
|---|---|
| 根元素不是 `<slide>`（例如直接给了 `<shape>`） | `--content root must be <slide>` → 改单个元素请用 `+replace-slide` |
| 根 `id` 和 `--slide-id` 不一致 | 拒绝。这通常是 A 页的 XML 要写到 B 页 —— 会毁掉 B 页 |
| 根 `id` 缺失 | 自动补上 `--slide-id`，不报错 |
| 根标签带命名空间前缀（`<sml:slide>`） | 拒绝。页面 id 没法贴到带前缀的标签上；写成 `<slide>`，需要命名空间就用默认 `xmlns` |
| `<slide>` 之后还有第二个根元素或多余文本 | 拒绝。服务端解析会静默丢掉它们 |
| XML 不合法 | 拒绝，带上出错位置 |
| `<slide/>`（自闭合，空页） | 命令本身可以解析，但服务端版式校验会报 `blank_slide` 并拒绝写入 |

标为“拒绝”的情况由命令校验拦截，**不会发出任何请求**；空页由服务端拒绝，按本 Skill 也不得提交空页。

## 什么时候不要用它

- **只改一个元素** → 用 [`+replace-slide`](lark-slides-replace-slide.md)，一条 `block_replace` part 更省，也不用带上整页
- **要改多个页面** → 对每一页各跑一次本命令
- **要新建页面** → `slides +create` 或 `xml_presentation.slide create`

## 写入后验证

写入结果按下方返回字段确认；写入成功后，回读整份演示文稿的最新 XML 与 lint 报告，另存完整响应并完成内容与版式验证：

```bash
lark-cli slides +xml-get\
  --presentation "$PRES" --output readback.xml \
  --json > readback-response.json 2> readback-error.json
```

按当前已加载 `lark-slides/SKILL.md` 指向的 [validation-xml.md](../workflow/validation-xml.md) 完成验证：通过 `lint_inspect.py` 的 lint 检测报告摘要定位并分页读取响应中的文档级与页面级问题，目标页与原稿基线对比；核对总页数、目标页和关键元素（包括需要保留的 ID、文本、背景与备注）。读取 `ok: true` 不能代替 lint 通过，报告缺失不能当作无问题；发现新增/加重的真实问题或计划外差异时，先停止后续写入并重新基于最新版处理，修复后开启写入 lint 重提并回读复验。原稿基线只有单页时，不把其他页未出现在基线中视为问题新引入。

## 成功输出

```json
{
  "ok": true,
  "identity": "user",
  "data": {
    "xml_presentation_id": "slides_example_presentation_id",
    "slide_id": "piy",
    "revision_id": 43
  }
}
```

| `data` 下的字段 | 说明 |
|------|------|
| `xml_presentation_id` | 实际写入的演示文稿 ID |
| `slide_id` | 与传入相同——整页覆盖不换页 id |
| `revision_id` | 写入后的新版本号 |
| `issues` | 仅在**页面已写入成功**且服务端有发现时返回，不影响本次调用的成功状态。内容是未达阻断级的版式校验发现。按实际类型读取：对象/数组直接读，JSON 字符串解码后读，普通文本原样读；完整读取全部发现，立即回读并截图核验，真实问题须修复 |

服务端拒绝这次写入时（`failed_reason` 非空）**不会**返回成功输出，而是报错并带上原因——单个 part 承载整页，任何失败都意味着页面没被写入。

- 原因包含 `not found`：先检查 `--presentation` 和 `--slide-id`，再用 `slides +xml-get` 回读当前页面 ID。页面可能已删除，或 ID 来自另一份演示文稿。
- 其他 invalid-parameter 错误：检查 `--content` 中不支持的元素、缺少 `<content/>` 的 `<shape>`，以及超出 960×540 的坐标。

### 返回字段与处理

返回 JSON 的外层 `ok` 表示调用是否成功，`identity` 表示调用身份；成功时业务字段位于 `data`，失败时错误信息位于 `error`。按以下字段判断结果并处理 lint 发现。

| 当次响应 | 读取与处理 |
|---|---|
| `ok: true`，未附问题发现 | 从 `data` 记录 ID、版本等业务字段，继续流程 |
| `ok: true`，有 `data.issues` | 页面已写入；对象/数组直接读，JSON 字符串先解码，普通文本完整读。逐条处理发现，按验证流程回读与截图；不能因成功而忽略 |
| `ok: false`，`error.code: 4000153` | 被拒页面未写入；对 `error.message` 的完整 JSON 字符串解码，读完报告后修复并开启 lint 重提 |
| 其他失败或返回不完整 | 读完整 `error` 或诊断，按实际原因处理；不能只读 `data` 并把缺失字段默认成零问题 |

返回的是 lint 报告对象时，先看 `summary` 中的 `error_count`、`warning_count`、`info_count` 和 `status`，再读 `document.errors/warnings/infos` 和 `slides[].errors/warnings/infos` 的全部问题；`slides[].issues` 可能是分级列表的镜像，不能重复计数；合并列表中的额外发现也须读取，根 `issues` 不能当作全页列表。逐条读 `code`、`message`、实际存在的 `hint` 及定位/测量字段；`element_ids` 可能为空，需继续看 `elements`、`target.xml_path` 或 schema 的 `path`。单页报告内部 `slide_number: 1` 不一定是整稿第 1 页，关联本次请求/响应的 `slide_id`。

字符串长度不是问题数，`summary` 或前几百字符也不是完整问题正文。报告过大或工具输出截断时，先检查是否已有该次完整响应文件；有文件时可用 `lint_inspect.py` 分页读取，只有截断文本时无法恢复遗漏内容，不能据此认定问题已全部处理。使用 `--no-lint` 后的成功不代表校验通过；异常、长报告和单页例外规则见 [validation-xml.md](../workflow/validation-xml.md)。

## 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| 3350001，原因包含 `not found` | `--presentation` 不匹配，或 `--slide-id` 对应的页面已被删除 | 检查 `--presentation` 和 `--slide-id`，再用 `slides +xml-get` 回读当前页面 ID |
| 3350001，其他 invalid param | `--content` 的 XML 结构有问题（如 `<shape>` 缺 `<content/>`、包含服务端不支持的元素） | 按 [error-handling.md](../workflow/error-handling.md) 检查 `--content` 的 XML 结构 |
| 3350002 not found | `--revision-id` 传了不存在的版本号 | 用 `-1` 或真实存在的 `revision_id` |
| 4000153 `xml lint blocked` | 服务端版式校验拒绝了本次写回，页面维持原状 | 按 [validation-xml.md](../workflow/validation-xml.md) 解析并读完 `error.message` 的完整报告，修复后开启 lint 重提 |
| 1061004 / 403 | 当前身份对这份 PPT 没有编辑权限 | 检查是否拥有 `slides:presentation:update` 或 `slides:presentation:write_only` scope；wiki 链接另需 `wiki:node:read` |

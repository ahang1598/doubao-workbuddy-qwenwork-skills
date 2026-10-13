# report-generator — HTML 巡检报告生成子技能

> [!IMPORTANT]
> 当用户要求「**生成巡店报告 / 巡检报告 / 导出报告**」时使用本子技能。
> **禁止使用 `data-report` 等外部技能或自行拼接 HTML。**

> **跨平台路径说明**：本文档命令示例中 `<TEMP>` 为临时文件存放目录占位符，按优先级选择：
> 1. **workspace 相对路径（推荐）**：`./tmp/`（当前工作目录下创建 `tmp/` 子目录）——适用于 Agent 环境中 shell 重定向被安全策略阻止的场景，Agent 可通过 `create_file` 等工具写入
> 2. **系统临时目录**：macOS/Linux 用 `/tmp`，Windows PowerShell 用 `$env:TEMP`
>
> **如果 shell 重定向 `>` 无法写入文件**（部分 Agent 运行环境的安全策略限制），请改用以下方式：
> - 先用 shell 命令获取 JSON 输出，再通过 `create_file` / 文件写入工具保存到 `./tmp/` 目录

## 端到端操作流程（必读）

### 前置条件

- 主技能已完成 `init validate`（base_id 已绑定）
- 至少有一个已派发的任务（`dispatch init` 已执行过）
- 需要知道**动态任务表的 `tableId`**（从 `dispatch init` 输出的 `task_table_id` 获取，或从主技能的 `config.json` 中读取）

### 步骤 1：导出字段定义

> [!CAUTION]
> **每次生成报告前必须重新导出 `fields.json`，禁止复用旧文件。**
> 当用户解绑旧 AI 表格或重新派发任务后，字段 ID 会发生变化，旧的 `fields.json` 会导致字段映射断层（AI 审核→附件关联失败、报告无图片）。

```bash
dws aitable field list --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TEMP>/fields.json
```

输出格式为 `{data: {fields: [...]}}`，子技能已兼容此格式，**无需手动修改**。

### 步骤 2：导出巡检记录

> [!CAUTION]
> **每次生成报告前必须重新导出 `data.json`，禁止复用旧文件。**
>
> **⚠️ 分页问题**：`dws aitable record list` 默认只返回第一页（最多 100 条记录）。
> 如果门店数 × 检查项数 > 100（例如 16 家门店 × 9 个检查项 = 144 条），**必须处理分页**。
> 检查响应中的 `data.nextCursor` 字段，如果非空则需要继续请求：
> ```bash
> # 首次请求
> dws aitable record list --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TEMP>/data_page1.json
> # 如果响应中有 nextCursor，继续请求（将 nextCursor 值传入 --cursor 参数）
> dws aitable record list --base-id <BASE_ID> --table-id <TABLE_ID> --cursor <nextCursor值> --format json > <TEMP>/data_page2.json
> ```
> 然后将所有页的 records 合并为一个数组写入 `data.json`。
> **不处理分页将导致报告数据严重不完整！**

```bash
dws aitable record list --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TEMP>/data.json
```

输出格式为 `{data: {records: [...]}}`，子技能已兼容此格式，**无需手动修改**。

> **附件字段**：`record list` 命令会返回 attachment 类型字段的完整信息（含 `url`），
> 照片 URL 可直接用于 HTML 报告的 `<img>` 标签。

### 步骤 3：生成 HTML 报告

```bash
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <TEMP>/data.json --fields <TEMP>/fields.json --output <TEMP>/report.html --mode <MODE>
```

可选参数：
- `--stores "店A,店B,店C"` — 预期门店列表（逗号分隔），用于统计未提交门店数
- `--mode <MODE>` — 报告模式，**必须正确选择**：
- `--template <HTML文件路径>` — 用户自定义 HTML 模板（直接替换占位符，不脱敏）
- `--save-template <single|multi>` — 将 `--template` 持久化为用户默认模板

| `--mode` 值 | 适用场景 | 模板 | 特征 |
| :--- | :--- | :--- | :--- |
| `single-store` | **仅当用户明确说"为某一家门店生成单店报告"** | `single_store_template.html` | 渐变色 header · 总结分析卡片 · 网格卡片布局 · 图片点击放大 |
| `multi-store` | **其他所有情况（默认）** | 内置拼装 / 用户自定义多店模板 | 整体概览 KPI · 各门店分 section · 共性问题分析表 |
| `auto`（默认） | 等同于 `multi-store` | 默认走多店报告 | — |

> [!CAUTION]
> **单店 vs 多店分流规则（Agent 必须严格遵守，违反将导致报告格式错误）：**
>
> **用 `--mode single-store` 的条件：用户明确指定了一家且仅一家门店。**
> - 「为西溪1店生成报告」→ 单店 ✅
> - 「看看朝阳店的情况」→ 单店 ✅
>
> **以下所有情况均使用 `--mode multi-store`（或 auto）：**
> - 「为 A 门店、B 门店生成报告」—— 多家门店 = 多店报告
> - 「为所有杭州的门店生成报告」—— 筛选条件可能命中多家 = 多店报告
> - 「生成今天巡店任务的巡店报告」—— 未指定具体门店 = 多店报告
> - 不确定时 —— 一律多店
>
> **核心原则：只有明确指向一家门店时才单店，其余全部多店。**

### 步骤 4：内嵌图片 + 智能压缩（必须执行）

> [!IMPORTANT]
> 生成 HTML 后**必须执行此步骤**，将所有网络图片下载、转为 base64 内嵌、并自动压缩到 ≤1.9 MB。
> - **OSS 签名链接有过期时间**，不内嵌的话报告过一段时间后照片将全部失效。
> - **智能压缩默认启用**（v0.0.9+），无需手动加 `--compress` 参数。
> - 压缩目标 ≤ 1.9 MB，确保钉钉移动端能正常渲染。
> - 如需保留原始图片大小（仅用于打印场景），可加 `--no-compress`。

**推荐用法（DWS 附件模式）**——解决 AI 表格附件 OSS 签名 403 问题：

```bash
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py embed-images \
  --input <TEMP>/report.html \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --skill-cli <主技能CLI路径> \
  --fields <TEMP>/fields.json
```

> `--skill-cli` 是主技能 `scripts/cli.py` 的绝对路径（Agent 在运行时可从环境变量或 skill 安装目录获取）。
> 该模式通过主技能的 `attachment get-urls` 命令获取带鲜活签名的下载 URL，
> 然后以 `resourceId`（OSS URL 路径中的 UUID）作为匹配键替换 HTML 中对应的图片。

**简单用法（直接下载模式）**——适用于公网可直接访问的图片 URL：

```bash
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py embed-images --input <TEMP>/report.html
```

参数说明：
- `--input` / `-i`：HTML 文件路径（必填）
- `--output` / `-o`：输出路径（默认覆盖原文件）
- `--base-id`：AI 表格 Base ID（DWS 模式必填）
- `--table-id`：数据表 ID（DWS 模式必填）
- `--skill-cli`：主技能 CLI 路径（DWS 模式必填）
- `--fields` / `-f`：字段定义 JSON（DWS 模式推荐，用于自动识别 attachment 字段）
- `--no-compress`：关闭智能压缩（压缩**默认启用**，一般无需传此参数）
- `--target-size-mb`：目标文件大小 (MB)，默认 1.9
- `--text-buffer-kb`：预留文字+CSS 空间 (KB)，默认 400
- `--min-quality`：最低 JPEG 质量，默认 30
- `--max-quality`：最高 JPEG 质量，默认 95

> [!IMPORTANT]
> **智能压缩默认启用**，无需手动加 `--compress`。
> 压缩算法按原始大小比例动态分配配额，保证小图不被过度压缩、大图质量可控。
> 目标是让最终 HTML 文件 ≤ 1.9 MB，确保在钉钉手机端能正常打开。
> 如需保留原始图片大小（如用于打印），可传入 `--no-compress` 关闭。

> [!CAUTION]
> **AI 表格附件的 OSS URL 带签名认证**，直接用 urllib/curl 下载会 403 Forbidden。
> 生成报告后内嵌图片时**必须使用 DWS 附件模式**（传入 `--base-id` + `--table-id` + `--skill-cli`），
> 否则所有图片都会转换失败。

### Windows PowerShell 完整执行示例

> [!IMPORTANT]
> Windows 上执行时注意以下差异：
> - 临时文件路径使用 `$env:TEMP` 而非 `/tmp`
> - **无需手动设置 PYTHONPATH**——`scripts/main.py` 入口已自动处理模块路径
> - **⚠️ 编码问题（最重要）**：PowerShell 保存文件时**必须确保 UTF-8 无 BOM 编码**，否则中文字段名会变成乱码（`?`），导致 AI审核→附件字段映射失败、报告无图片。
>   - **禁止**使用 `-Encoding ascii`（中文变 `?`）
>   - **禁止**使用 `Out-File -Encoding utf8`（PS5 会加 BOM）
>   - **推荐**：用 `[IO.File]::WriteAllText()` 直接写 UTF-8 无 BOM 文件（兼容 PS5 和 PS7）

```powershell
# 1. 导出字段定义（UTF-8 无 BOM，兼容 PowerShell 5.x 和 7.x）
$fields = dws aitable field list --base-id <BASE_ID> --table-id <TABLE_ID> --format json
[IO.File]::WriteAllText("$env:TEMP\fields.json", $fields)

# 2. 导出巡检记录
$data = dws aitable record list --base-id <BASE_ID> --table-id <TABLE_ID> --format json
[IO.File]::WriteAllText("$env:TEMP\data.json", $data)

# 3. 生成 HTML 报告
cd <SKILL_DIR>\skills\report-generator
python3 scripts/main.py generate-report "$env:TEMP\data.json" --fields "$env:TEMP\fields.json" --output "$env:TEMP\report.html" --mode auto

# 4. 内嵌图片（DWS 附件模式）
python3 scripts/main.py embed-images --input "$env:TEMP\report.html" --base-id <BASE_ID> --table-id <TABLE_ID> --skill-cli <主技能CLI路径> --fields "$env:TEMP\fields.json"
```

### 步骤 5：推送报告（可选）

如果用户要求推送给特定人员或群，使用**钉钉文档上传 + 授权 + 单条消息**方案。
相比旧的「钉盘上传 + 两条消息」方案，新方案优势：
- **单条消息**：文案摘要 + 文档链接合为一条
- **保留完整样式**：HTML 的 CSS 和 base64 内嵌图片全部保留
- **在线预览**：收件人点击链接即可在钉钉内预览，无需下载

#### 5a. 上传 HTML 到钉钉文档

```bash
dws doc upload --file <HTML文件路径> --name "<报告标题>" --format json
# 示例：
dws doc upload --file <TEMP>/report.html --name "杭州西溪店巡检报告" --format json
```

> 从返回 JSON 中提取两个关键字段：
> - `nodeId`：用于后续添加协作者权限
> - `docUrl`：用于拼接消息内容中的文档链接

#### 5b. 获取收件人信息

```bash
# 获取 openDingTalkId（发送消息用）和 userId（添加权限用）
dws contact user search --query "收件人姓名" --format json
```

> **注意**：`dws chat message send` 使用 `openDingTalkId`，而 `dws doc permission add` 使用 `userId`，两者都需要获取。

#### 5c. 添加协作者权限（必须执行，不可跳过）

> [!CAUTION]
> **此步骤不可省略！** 上传文档后必须立即通过 `dws doc permission add` 为所有收件人添加查看权限，否则收件人将**无法访问**文档链接，报告推送等于无效。

```bash
dws doc permission add --node <nodeId> --user <userId> --role READER --format json
# 批量添加多个收件人（逗号分隔，单次最多 30 个）：
dws doc permission add --node <nodeId> --user 440535,123456 --role READER --format json
```

> `--role` 支持四种角色（必须大写）：
> - `READER`：仅可查看，不可下载（**推荐用于报告发送**）
> - `DOWNLOADER`：可查看并下载
> - `EDITOR`：可查看、编辑
> - `MANAGER`：管理员

#### 5d. 构造并发送单条消息

```bash
dws chat message send --open-dingtalk-id "<openDingTalkId>" \
  "**<报告标题>**\n\n📊 提交率: X% | 审核通过率: Y%\n不合格项: xxx\n\n查看完整报告（含现场照片）：<docUrl>"
```

> **消息内容要求**：
> - 支持 Markdown 格式（`**粗体**`、`\n` 换行等）
> - **必须包含** `docUrl` 完整链接（格式：`https://alidocs.dingtalk.com/i/nodes/<nodeId>`）
> - 文案应包含：报告标题、关键 KPI（提交率/通过率）、不合格项/门店摘要
> - **禁止**使用 `dt_media_upload` 返回的链接

> [!CAUTION]
> **严禁使用 `dt_media_upload` 上传 HTML 文件**——该接口返回的链接后缀为 `.unknown`，
> 收件人无法正常预览。
> **严禁使用 `dws drive upload` 旧方案**——需要发两条消息且体验差。
> **必须**通过 `dws doc upload` → `dws doc permission add` → `dws chat message send` 三步完成单条消息推送。

## HTML 报告模板（必读）

> [!CAUTION]
> 生成 HTML 报告时，`generate-report` 命令会根据 `--mode` 自动选择内置模板。
> **禁止自行设计 HTML 结构或拼接 HTML**——直接调用命令即可。

### 两套模板对照

| 维度 | 单店模板 (`single_store_template.html`) | 多店模板 (`report_template.html`) |
| :--- | :--- | :--- |
| **header** | 渐变色背景，门店名 + 报告类型 + 日期 + 督导员 | 纯文本标题，日期 + 生成时间 |
| **总结** | 总结分析卡片（文字段落：整体情况 + 不合格项） | 整体概览 KPI 网格（提交率/通过率/不合格/待确认/未提交） |
| **详情** | 网格卡片式检查项（每项：照片 + 状态标签 + AI 描述） | 列表式检查项（每项：状态徽章 + AI 审核文本 + 照片网格） |
| **附加** | 图片点击放大 lightbox | 共性问题分析表格 |
| **footer** | 生成时间 + 数据来源 | AI 自动生成声明 |

### ⚠️ 检查项数据一一对应约束

> [!CAUTION]
> **每个检查项的照片、AI 审核评语必须严格一一对应，禁止跨检查项混用数据。**
>
> - 检查项 `OC 鲜食柜陈列` 的照片**只能**来自 `OC 鲜食柜陈列` attachment 字段
> - 检查项 `OC 鲜食柜陈列` 的 AI 审核**只能**来自 `AI审核_OC 鲜食柜陈列` 字段
> - **禁止**将 A 检查项的照片展示在 B 检查项下，或将 A 的 AI 审核结果标注到 B
>
> `generate-report` 命令通过 `ai_to_attachment_map`（从 `aiConfig.prompt[].fieldRef` 自动构建）
> 确保每个 AI 审核字段精确关联到其对应的附件字段。如果报告中出现错位，
> 请检查 `fields.json` 中的 `aiConfig` 是否正确。

## 自定义 HTML 模板

> [!IMPORTANT]
> 用户可以提供自己的 HTML 报告模板，系统会持久化保存并在后续生成中优先使用。

### 模板优先级

```
用户本次通过 --template 传入 > 持久化的用户自定义模板 > 内置默认模板
```

### 持久化规则

- 持久化位置：`~/.store-inspection/custom_report_template_single.html` / `custom_report_template_multi.html`
- 单店和多店模板各最多保留**一份**
- 如已有持久化模板，`--save-template` 时会输出旧模板预览并提示覆盖
- 持久化后，后续所有报告生成都会使用该模板，除非用户提供新模板

### 降级提示

当用户没有配置过自定义模板，也没有本次传入时，CLI 会输出：
```
ℹ️ 当前没有持久化的多店巡店模板，将使用默认模板生成报告
```
Agent 应将此信息**原样告知用户**。

## 用法速查

```bash
# 生成多店报告（默认）
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <data.json> --fields <fields.json> --output <report.html>

# 生成单店报告（仅当用户明确要求"单店报告"）
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <data.json> --fields <fields.json> --output <report.html> --mode single-store

# 使用用户自定义模板并持久化为多店模板
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <data.json> --fields <fields.json> --template ~/my_template.html --save-template multi

# 使用用户自定义模板并持久化为单店模板
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <data.json> --fields <fields.json> --template ~/my_template.html --save-template single --mode single-store

# 内嵌图片（防止 OSS 链接过期，生成后必须执行）
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py embed-images --input <report.html>

# 查看完整参数
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report --help
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py embed-images --help
```

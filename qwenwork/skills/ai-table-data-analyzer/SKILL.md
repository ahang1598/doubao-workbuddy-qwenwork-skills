---
name: ai-table-data-analyzer
name_en: ai-table-data-analyzer
name_zh: AI表格数据可视化分析
description: |
  数据可视化与可视化数据分析报告：将本地 Excel/CSV/TSV、钉钉在线电子表格(axls)或已有钉钉 AI 表格统一转为 AI 表格数据源，根据数据特征设计图表组合，在其上创建原生可视化仪表盘(dashboard：指标卡/趋势/构成/排名图表)，是"上传表格出数据可视化报告"(data-report 类)诉求的钉钉原生方案。
  TRIGGER: 用户要求把 Excel/CSV/在线表格做成钉钉看板/仪表盘/数据大屏/数据可视化报告；或指定已有 AI 表格(名称或 alidocs URL)要求生成仪表盘/看板；或提出"做个看板"/"搭个仪表盘"/"数据上墙"/"出个可视化分析"等带钉钉落地诉求的表达。
  DO NOT TRIGGER: 用户明确只要本地自包含 HTML 报告、不要钉钉落地；仅导入数据不建看板(走 dws aitable 导入流程)；只修改已有图表配置(直接用 dws aitable chart/dashboard 命令)；非钉钉平台的 BI 需求。
description_en: |
  Data visualization & visual analytics reports on DingTalk: unifies local Excel/CSV/TSV files, DingTalk online spreadsheets (axls) and existing AI tables into an AI-table data source, designs chart combinations from data characteristics, and creates native dashboards (KPI cards / trends / composition / rankings) — a DingTalk-native answer to "upload a spreadsheet, get a visual data report" (data-report style) requests.
  TRIGGER: user wants Excel/CSV/online sheets turned into DingTalk dashboards / data screens / visual reports; or names an existing AI table (name or alidocs URL) to build a dashboard; or says "make a dashboard" / "visualize my data" with DingTalk as the target.
  DO NOT TRIGGER: user explicitly wants a local self-contained HTML report only, no DingTalk; import-only without a dashboard; editing existing chart configs directly; non-DingTalk BI needs.
version: 1.0.0
install_source: official
install_method: download
skill_id: official_ULsGCjKv
enabled_at: 1791893750075
---

# ai-table-data-analyzer — 多源数据 → 钉钉 AI 表格 → 仪表盘

把四类数据源收敛为钉钉 AI 表格，再在其上创建原生仪表盘：

```
本地 xlsx/csv ─┐
钉钉在线表格 ──┼→ (预处理) → 导入 AI 表格 → 数据画像 → 图表方案 → 用户确认 → 创建 dashboard + charts → 交付链接
已有 AI 表格 ──┘
```

## 🔒 硬规则

1. **先分流再动手** — 数据源类型(本地文件 / axls 在线表格 / AI 表格 / 下载型节点)未判定前，禁止开始导入或建图。
2. **AI 表格是唯一底座** — 非 AI 表格数据源必须先落地为 AI 表格，禁止绕过(如用本地文件数据直接拼图表配置)。
3. **图表方案先确认再创建** — 输出图表清单方案，用户确认后才执行 `dashboard create` / `chart create`；用户明确表示"直接做"时可跳过确认。
4. **配置不编造** — 图表 config 必须按 [chart-widgets-reference.md](references/chart-widgets-reference.md) 模板或 `dws aitable chart widgets-example` 返回填写；dashboard theme 固定 `{"key":"DEFAULT","background":null,"image":""}`。
5. **dws 通用纪律** — 所有命令加 `--format json`；baseId/tableId/fieldId/dashboardId/chartId 只从命令返回提取；写操作失败先加 `--verbose` 重试一次，仍失败报告用户。
6. **严禁删除用户仪表盘** — 本技能流程中任何情况下都不执行 `dashboard delete`，也不清空/覆盖已有仪表盘里的图表；用户要求删除时，告知其在钉钉客户端手动操作。

## Step 0 · 数据源判定

| 输入形态 | 判定动作 | 路由 |
|---|---|---|
| 本地路径 `.xlsx/.xlsm/.csv/.tsv` | 直接判定 | → Step 1A 文件链路 |
| 本地路径 `.xls` | 不支持旧二进制格式 | 请用户另存为 xlsx |
| `alidocs.dingtalk.com/i/nodes/...` URL | **必须先 probe**：`dws doc info --node "<URL>" --format json` | `extension=able` → Step 3(AI 表格直连)；`extension=axls` → Step 1B；`extension=xlsx/xls/csv` → `dws doc download --node <URL> --output ./<name>` 后转 Step 1A |
| `alidocs.dingtalk.com/spreadsheetv2/...` URL | 在线表格直链，完整 URL 原样传给 `--node` | → Step 1B |
| `/i/p/` 分享短链 | dws 无法解析 | 告知用户不支持，请提供原始文档链接 |
| 用户只给了 AI 表格名称 | `dws aitable base search --query "<名称>" --format json` 定位 baseId | → Step 3 |
| 含糊不清 | AskUserQuestion 澄清数据源 | — |

多组织提示：命令报「不支持跨组织访问」时，先试 `--profile <corpId>`（`dws profile list` 查组织）；**托管认证模式下 `--profile` 会被拒（报 "not supported in managed authentication mode"），此时必须切换连接器组织**：qw_action `qwenwork.settings.connector.builtin.dws` disconnect → connect（用户在浏览器选目标组织登录）→ 轮询确认 authenticated 后重试。

## Step 1 · 数据获取与预处理

### 1A 本地文件链路

1. **体检**（本技能自带 inspect 脚本，无外部技能依赖）：
   ```bash
   python "${SKILL_DIR}/scripts/xlsx_reader.py" "<file>" --inspect
   ```
   （`${SKILL_DIR}` 为本技能目录，即 `~/.qwenworkcn/skills/ai-table-data-analyzer`。）返回 `sheet_dims`/`column_info`/`data_traps`(每条带 `suggested_read_code`)/`previews`。需要 pandas/openpyxl；系统 python3 装不了包时先建 venv（如 `python3 -m venv /tmp/xlsxenv && /tmp/xlsxenv/bin/pip install pandas openpyxl`）再跑。脚本缺失或环境不可用时降级为 pandas 自行读取预览。
2. **清洗**（按需，用 pandas 落一份干净 xlsx 到工作区）：去掉全空行/重复行、合并表头摊平、多 sheet 时与用户确认导哪个（或分表导入）、数值列 `astype(float)`、日期列转 `yyyy-MM-dd` 字符串。
   > 导入服务的字段类型是按文件内容自动推断的：**文件里数值列必须真是数值、日期列必须真是日期**，否则 AI 表格会建出文本字段，仪表盘无法聚合。
3. **CSV 限制**：表头固定第一行、无 sheet、不支持 `--header-row`。表头不在第一行或结构复杂的 csv，先用 pandas 整理成规范 xlsx。

### 1B 钉钉在线电子表格(axls)链路

```bash
dws sheet export --node "<NODE_ID或URL>" --output ./<name>.xlsx --format json
```
内置轮询+下载，一步到位。随后走 1A 的体检与清洗。

### 1C 已有 AI 表格

跳过 Step 1/2，直接进 Step 3。

## Step 2 · 导入 AI 表格

1. **确定目标 Base**：
   - 用户指定了已有 Base → `base search` 定位 baseId。
   - 默认：**新建 Base**，`dws aitable base create --name "<数据主题>" --format json` → 提取 baseId。
2. **执行导入**（首选 dws 官方脚本，已包装凭证申请→OSS 上传→触发导入三步）：
   ```bash
   python ~/.qwenworkcn/skills/dws/scripts/aitable_import_via_task.py <baseId> <cleaned.xlsx>
   ```
   ⚠️ 托管认证模式下脚本会失败（其内部以子进程调 dws，报 "pending host-side execution"），**直接走手动三步**：`import upload --file-name <名> --file-size <字节>` → `curl -X PUT "<uploadUrl>" -H "Content-Type:" --data-binary @<file>`（Content-Type 必须置空，HTTP 200 即成功）→ `import data --import-id <ID> --timeout 30`。
3. **验证**：`base get --base-id <ID>` 取新 tableId → `table get` 核对字段名与类型 → `record query --limit 5` 抽查数据。发现数值字段被建成文本 → 回到 1A 修文件后重新导入（新建表模式可先 `table delete` 旧表，删除前须经用户确认）。

## Step 3 · 数据画像与图表方案

1. 取结构：`dws aitable table get --base-id <ID> --table-id <TID> --format json`（字段名/类型/fieldId）。
2. 采样统计：`dws aitable record query --base-id <ID> --table-id <TID> --all --field-ids <目标字段> --format json` 本地聚合，了解行数、数值量级、维度基数、日期跨度。
   > `--all` 报 `partial:true` 时改 `--limit` + `--cursor` 翻页重试；持续失败则降级 `aitable export data --scope table` 导 xlsx 本地用 pandas 分析。
3. 按 [chart-widgets-reference.md](references/chart-widgets-reference.md) 的**选型规则表**设计图表组合（典型 4~8 张：指标卡行 + 趋势 + 构成 + 排名，按需加明细表/筛选器）。
4. **输出方案并确认**：列出每张图的「名称 / chartType / 维度 / 度量与聚合 / 布局」，等用户确认或调整后再进 Step 4。

## Step 4 · 创建仪表盘与图表

1. 确定仪表盘载体（**复用优先，绝不删除**）：
   ```bash
   # 查看 Base 内已有节点（含仪表盘，nodeType=dashboard，nodeId 即 dashboardId）
   dws aitable section list-nodes --base-id <ID> --format json
   ```
   - Base 里已有**空仪表盘**（`dashboard get` 显示无图表）→ 直接复用，用 `dashboard update --name "<看板名>"` 改名，提取其 dashboardId。新建 Base 自带的空仪表盘属此情况。
   - 没有空仪表盘 → 新建：`dws aitable dashboard create --base-id <ID> --name "<看板名>" --format json`，提取 dashboardId（返回若含 dashboard URL 一并记下）。
   - 已有**非空**仪表盘 → 那是用户资产，不动它（不删、不清空），为本任务新建一个仪表盘。
2. **先确认网格列数（建图前必做）**：`dws aitable dashboard get --base-id <ID> --dashboard-id <DID> --format json`，看 `data.meta`：
   - `schemaVersion=2`（返回表现为 `schemaVersionTypeVerified: true`）→ **48 列网格**；
   - 没有 schemaVersion 或值为 1（meta 为空/无该字段）→ **12 列网格**。
   后续所有 `--layout` 的 x/w 必须按确认到的列数取值，错配会导致图表错位或被压成窄条。
3. 逐张创建图表（config 按参考模板填真实 tableId/fieldId）：
   ```bash
   dws aitable chart create --base-id <ID> --dashboard-id <DID> \
     --config '<图表配置JSON>' --layout '{"x":0,"y":0,"w":6,"h":4}' --format json
   ```
   **layout 必填；网格列数以第 2 步确认为准**：同行图表高度必须一致、宽度之和 = 网格总列数。推荐排布（12 列模式数值）：指标卡行 `w=3,h=3~4` 并排 4 张；主趋势图 `w=12,h=6`；双图并排各 `w=6,h=5~6`；明细表 `w=12,h=6`。**48 列模式把 x/w 一律 ×4**（指标卡 `w=12`、全宽 `w=48`、并排各 `w=24`，h 不变）。y 值按已占行数顺延。
4. 布局自检：`dashboard get` 检查 charts 是否齐全、有无空洞；不整齐时 `dws aitable dashboard arrange --base-id <ID> --dashboard-id <DID>` 自动重排，或 `chart update`（`--config` 必填完整配置）微调单图 layout。

## Step 5 · 验证与交付

- `dashboard get` 确认图表数量与方案一致。
- 交付消息包含：数据源与处理摘要（导入/新建了什么表、行数、字段概况）、图表清单、访问链接（命令返回有 dashboard URL 用之，否则拼 `https://alidocs.dingtalk.com/i/nodes/{baseId}`），并提示可继续增删改图表。
- 可选：用户要求分享时 `dws aitable dashboard share update --enabled true --share-type ORG`（PUBLIC 在部分组织被禁；回显 `shareType="[1]"` 是已知服务端问题，按 ORG 理解）。

## 易错点速查

- `import upload` **没有** `--file` flag，只申请凭证；文件要自己 curl PUT 且 Content-Type 置空，否则 403。
- `chart create` 缺 `--layout` 本地直接拒绝；`chart update` 缺 `--config` 服务端拒绝。
- 建图前不确认网格列数：`schemaVersion=2`（`schemaVersionTypeVerified:true`）是 48 列网格，照搬 12 列坐标会把图表挤成窄条；无 schemaVersion 或为 1 才是 12 列。
- dashboard config 的 theme 编造会渲染失败，固定 DEFAULT。
- `record query` 默认只回 100 条，统计必须 `--all`；`nextCursor` 非空说明未拿全。
- `export data` 只有 `--timeout-ms`（上限 30000），没有 `--timeout-sec`；`--output` 不会下载文件，要拿 `downloadUrl` 自己 curl。
- 删除 base/table/chart 属危险操作：先向用户展示摘要，确认后加 `--yes`。**仪表盘例外：本技能严禁 `dashboard delete`**（见硬规则 6），复用空仪表盘或新建，永不删除用户仪表盘。

## 依赖

- **dws skill（必需）**：所有钉钉侧操作；脚本 `~/.qwenworkcn/skills/dws/scripts/aitable_import_via_task.py`。
- **本地文件体检脚本（自带）**：`scripts/xlsx_reader.py`；运行环境需 pandas/openpyxl。

## references 索引

| 文件 | 内容 |
|---|---|
| `references/chart-widgets-reference.md` | 图表选型规则表 + 常用 chartType 配置模板 + measure/dimension/聚合函数规范 + 布局约定 |

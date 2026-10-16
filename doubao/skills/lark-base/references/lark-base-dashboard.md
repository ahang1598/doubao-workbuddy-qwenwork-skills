# Dashboard（仪表盘/数据看板）模块指引

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

Dashboard 是 Base 中的数据可视化看板，可以把表格数据变成**组件**（图表、指标卡等）进行展示。

## 核心概念

- **Dashboard（仪表盘）**：容器，包含多个组件
- **Block（组件）**：仪表盘中的单个可视化元素（柱状图、折线图、饼图、指标卡等）
- **data_config**：组件的数据源配置（表名、字段、分组等）

## 能力速览

| 你想做什么 | 用这些命令 | 关键文档 |
|------|-----------|---------|
| 创建/删除/改名称 | `+dashboard-create/delete/update` | 本页下方「仪表盘管理」 |
| 在仪表盘里添加组件 | `+dashboard-block-create` | 先定位 dashboard、表和字段，再读 [dashboard-block-data-config.md](dashboard-block-data-config.md) 构造 `data_config` |
| 修改组件 | `+dashboard-block-update` | 先读 block 现状，再读 [dashboard-block-data-config.md](dashboard-block-data-config.md) 决定替换哪些顶层 key |
| 创建/更新时指定组件精确位置大小 | `+dashboard-block-create/update --position` | 本页下方「精确布局 --position vs +dashboard-arrange」 |
| 查看仪表盘有哪些组件 | `+dashboard-get` 或 `+dashboard-block-list` | 本页下方「查看仪表盘」 |
| 读取图表计算结果 | `+dashboard-block-get-data` | 返回图表最终数据协议；需要 block 元数据先用 `+dashboard-block-get` |
| 在仪表盘里展示数据明细、甘特图或画册 | `+dashboard-block-create --type view`；更新/获取用组件命令 | [视图组件](lark-base-dashboard-view.md)，筛选、分组、排序、可见字段四类配置直接放在 `data_config` |
| 配置、替换或清除同源图表联动 | `+dashboard-block-update --linkage`；Get 回读 | [图表联动](lark-base-dashboard-linkage.md)，提交源组件的完整目标列表 |
| 查询或设置仪表盘跟随访问者权限统计开关 | 按目标环境已发布的接口调用 | [仪表盘跟随访问者权限统计开关](lark-base-dashboard-advperm.md) |
| 添加供使用者选值的交互筛选器 | `+dashboard-block-create --type slicer`；更新用 `+dashboard-block-update` | 单字段离散值选择；操作前读 [切片器契约](dashboard-block-data-config.md#slicer-切片器契约) |
| 读取、设置或清空整盘的预设过滤条件 | 按目标环境已发布的接口调用 | [仪表盘全局筛选](lark-base-dashboard-global-filter.md) |
| 按钮组件绑定、解绑或查询工作流 | 专用 `button_rule` GET/PUT；完整定义复用 `+workflow-get` | [仪表盘按钮绑定工作流](lark-base-dashboard-button-rule.md) |
| 读取视图组件的记录明细 | `+dashboard-block-get` 取得 `tableId / viewId`，再用 `+record-list --view-id` | [视图组件数据读取](lark-base-dashboard-view.md#读取视图组件数据)；继承视图配置并按需分页 |
| 智能重排组件布局 | `+dashboard-arrange` | 用户明确要求重排，或本次会话新建仪表盘的收尾整理；无法指定 `x/y/w/h`、精确位置或尺寸 |

## 交付健康门禁（写任务必做）

当本次请求创建、修改或复用 Dashboard 组件，或修改了这些组件依赖的表/字段时，写响应成功和组件出现在 list 中只证明资源存在，不证明配置与数据可用。自动修改范围只包括本次创建的组件，或可唯一映射到用户明确要求交付物的既有组件；其他同义/冲突组件只做只读检查和报告，未经用户确认不得更新或删除。只读发现限定在目标 Dashboard 内，不扫描其他 Dashboard。

完成前按以下顺序验收；多个组件放在一个 shell 工具调用内串行读取，避免拆成多轮：

1. 已知全部可信交付组件 ID 且无需检查重复或冲突时直接读取，不执行全 Dashboard list。需要定位交付组件或用户要求检查重复/冲突时，才用 `+dashboard-block-list --page-size 100`；用静态 `--jq` 投影保留 `has_more`、`page_token` 和候选的 `block_id/name/type/data_config` 字段引用，并按返回的 `page_token` 读到 `has_more=false`。一个既有组件可唯一映射到用户明确要求的交付物时可原位修复；其他同名或同义冲突组件只报告，未经确认不改删。
2. 对本次创建、明确要求修改或明确复用的每个交付组件用 `+dashboard-block-get` 读取服务端实际 `data_config`。视图组件的 Get 返回 `tableId / viewId / viewType` 引用，使用这组真实 ID 调用对应 `+view-get-*` 核对持久化配置，不能要求 Get 原样返回创建输入。逐项对照需求和真实表/字段，确认该组件适用的数据源、维度、指标、聚合、筛选与排序均被保留；不存在的引用、API 错误或服务端静默丢失关键配置均未通过。交互筛选器还需核对组件类型、绑定字段及用户要求的展示与选择模式；过滤条件保存成功或单次统计值正确，不能代替交互控件的验收。
3. 对这些交付组件中的图表或指标卡用 `+dashboard-block-get-data` 验证实际计算结果，确认所需维度与 measure 存在且粒度正确。`view` 按 [视图组件数据读取](lark-base-dashboard-view.md#读取视图组件数据) 使用 `+record-list --view-id` 核对记录；其他专属组件按对应配置指南验收，不能套用图表结果协议。空数据只有在一次有界源表记录查询证明本应为空时才可接受；有匹配源数据却返回空维度、空/缺失 measure 或矛盾数值时进入定向修复。`text` 组件只需 get。
4. 本轮新建且含组件的 Dashboard，用户未给可执行的精确布局约束时，组件全部创建完成后必须执行一次 `+dashboard-arrange`。随后用 `+dashboard-block-get` 回读全部交付组件的位置，按下方 12 列栅格规则检查坐标、尺寸合法且组件不重叠。用户未给可执行的精确布局约束时，还需检查中间无整行空白、无行内空档、非末行铺满、末行从左侧开始；不合格时按下方 `--position` 规则做一次定向修复并复验。用户给了可执行的精确布局约束时跳过 arrange，在上述坐标、尺寸和不重叠检查之外，核对用户指定的位置、尺寸和顺序，不用通用紧凑判据改写用户布局；若用户约束与基本布局规则冲突，应说明冲突并请用户澄清。既有 Dashboard 未经用户授权不得整盘重排。
5. 图表依赖本次新增或修改的 formula/lookup 时，用一次有界记录查询抽查有输入的样例行。整批终验后，对每类失败最多执行一次定向修复和一次复验；仍失败则报告具体未完成项。非目标既有组件未经用户确认不得更新或删除，删除操作还必须遵循高风险确认规则。

## 已有 Dashboard 的冲突检查

在已有 Dashboard 中新增、替换或纠错前，先用 `+dashboard-block-list` 读取该 Dashboard 的全部组件，并识别与目标指标同名、同义，或使用相同数据源但 range、grain、measure 不一致的组件。

- 可唯一确认是用户要求修复的旧组件时原位更新；需要改变组件 `type` 时按下文规则删除后重建。
- 用户要求新建 Dashboard 时，不要静默复用含冲突组件的旧 Dashboard；创建独立 Dashboard 承载本次交付。用户明确要求修改既有 Dashboard 时，未经授权不得删除其他组件；若冲突组件无法安全修改或删除，应报告阻塞，不得用并存的新组件宣称整个看板正确。
- 最终对本次交付的新 Dashboard 全部数据组件，或既有 Dashboard 中与目标指标相关的全部组件执行 `+dashboard-block-get`，并按组件类型选择图表结果、视图记录或专属配置的验收路径。同一指标出现矛盾范围、粒度或数值时验收失败。
- 涉及统计结论时，按 [Base data analysis SOP](lark-base-data-analysis-sop.md) 对齐确定性查询、Dashboard 实际数据和最终回答。

## 精确布局 --position vs +dashboard-arrange

create/update 可选 `--position`，用 12 列栅格坐标精确指定单个组件的落点与大小：`{"x","y","w","h"}`，`x`/`y` 为左上角坐标（>=0），`w` 为宽度（1..12，且 `x+w<=12`），`h` 为高度（>=1）。它与 `name`/`type`/`data_config` 平级挂在请求体顶层。

> [!IMPORTANT]
> - **四个 key 必须齐全且都是数字**：`position` 按整体提交、不做逐字段合并，所以只传 `{"x":6}` 表达的不是“只挪位置不改大小”，而是一个缺了三项的位置。本地会拒绝残缺对象（含显式 `null`）。
> - 坐标**取值不做本地校验**：越界、负值或重叠坐标会原样发给服务端，由服务端自动重排。调用方仍应优先规划 12 列范围内且不重叠的坐标，避免自动重排改变预期落点。
> - 不传 `--position`：create 由服务端自动装箱，update 保持当前布局不变。
> - 只有用户明确给出 `x/y/w/h`、具体行列/顺序、每个组件宽高或可直接换算的尺寸比例时才用 `--position`。“调整布局”“美化”“撑满”“铺满”本身不算精确约束，没有组件级坐标或尺寸时优先用 `+dashboard-arrange` 整盘编排。
> - **例外（arrange 兜底重试）**：本次新建仪表盘经 `+dashboard-arrange` 重排后布局仍不合格（组件重叠、中间整行为空、行内有空档、非末行右侧留白，或末行未从左起排）时，即使用户没有给出坐标，也应主动用 `--position` 按 12 列栅格自算坐标兜底：逐行左起、行内铺满（`x+w<=12`）、组件间不重叠；写后回读 `+dashboard-block-get` 的 `position` 按该判据自检，确实受平台限制无法满足时再如实报告。
> - 未触及布局的既有组件无需仅为位置重复读取；本轮新建 Dashboard 或明确调整过布局时，必须用 `+dashboard-block-get` 回读最终位置。写命令成功只代表请求已受理，不能替代布局验收。

## statistics 指标卡数值格式

`statistics` 组件可在 create/update 的 `data_config.number_format` 中设置 `formatName` 和 `precision`。create 会校验组件类型和子字段；update 不接收 `--type`，只校验 `number_format` 子字段，再由服务端结合现有 block 类型裁决。枚举、精度范围、更新语义和可复制模板读取 [dashboard-block-data-config.md](dashboard-block-data-config.md)。

## 典型场景工作流

### 场景 1：从 0 到 1 创建仪表盘

从 0 到 1 创建仪表盘时，按用户需求规划组件的类型和数量，并注意以下要点：

- 类型选择先看结果粒度，再看指标数量：只要用户要求“按 / 各 / 每某维度”或已解析出非空 `group_by`，即使只有一个统计指标，也必须使用支持分类轴的分组图表并保留该 `group_by`；只有真正无维度、预期返回单值的结果才能使用 `statistics`。
- 聚合方式：创建指标卡或分布图时优先把聚合写进 `data_config`，只有 Top N、字段取值探索、复杂筛选校验或 helper 汇总表场景才先用 `+data-query`。
- Dry-run 边界：已按模板构造的简单指标卡、分布图、趋势图不需要逐个 `--dry-run` 后再真实创建；只有在调试 JSON、检查请求体、复杂自造 `data_config` 或处理 API validation 错误时才 dry-run。
- 验证方式：创建响应只确认请求已受理，不代表运行时一定能算出正确数据；完成前按上方交付健康门禁验证本次目标组件的实际配置与计算结果，不把全量无关组件带入检查。
- 布局方式：按上方交付健康门禁执行整理和回读验收。
- 交付形态：Base 场景中用户要求“图/图表/看板/直观看到/可视化”时，默认把图表沉淀为 Base Dashboard 组件；外部图片或文本统计只能作为补充，不能替代可持续更新的 Dashboard。

示例：搭建一个销售数据分析仪表盘

```bash
# 第 1 步：创建空白仪表盘
lark-cli base +dashboard-create --base-token xxx --name "销售数据分析"
# 记录返回的 dashboard_id

# 第 2 步：获取数据源信息
lark-cli base +table-list --base-token xxx
lark-cli base +field-list --base-token xxx --table-id <table_id>

# 第 3 步：规划应该创建哪些组件（根据用户需求确定组件类型和数量）
# 例如：总销售额（指标卡）、月度趋势（折线图）、负责人 Top N（排行榜）、满意度评分（NPS）

# 第 4 步：顺序创建每个组件（必须串行执行，不能并发）
# 重要：创建组件前，先确定 dashboard_id、组件 name/type 和真实表字段
# 再阅读 dashboard-block-data-config.md 了解 data_config 结构、组件类型和 filter 规则

# 第 1 个组件
lark-cli base +dashboard-block-create \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --name "总销售额" \
  --type statistics \
  --data-config '{"table_name":"订单表","series":[{"field_name":"金额","rollup":"SUM"}]}'

# 第 2 个组件（等上一个完成后再执行）
lark-cli base +dashboard-block-create \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --name "月度趋势" \
  --type line \
  --data-config '{"table_name":"订单表","series":[{"field_name":"金额","rollup":"SUM"}],"group_by":[{"field_name":"月份","mode":"integrated"}]}'

# 继续创建其他组件...

# 排行榜组件：省略 limit_size 和 sort 时分别默认 10、value desc
lark-cli base +dashboard-block-create \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --name "负责人销售额 Top 10" \
  --type ranking \
  --data-config '{"table_name":"订单表","series":[{"field_name":"金额","rollup":"SUM"}],"group_by":[{"field_name":"负责人"}]}'

# 第 5 步：组件全部创建完成后，无用户精确布局约束时执行一次 arrange，再用 block-get 回读验收
# 用户指定精确布局时跳过 arrange，按其约束回读验收
lark-cli base +dashboard-arrange \
  --base-token xxx \
  --dashboard-id blk_xxx
```

### 场景 2：在已有仪表盘上添加新组件

```bash
# 第 1 步：列出仪表盘，定位到当前仪表盘
lark-cli base +dashboard-list --base-token xxx
# 获取目标 dashboard_id

# 第 2 步：根据用户诉求规划组件类型和数据源
# 建议先查看当前仪表盘已有组件，避免重复创建，或作为参考
lark-cli base +dashboard-get --base-token xxx --dashboard-id blk_xxx

# 第 3 步：获取数据源信息
lark-cli base +table-list --base-token xxx
lark-cli base +field-list --base-token xxx --table-id <table_id>

# 第 4 步：顺序创建每个新组件（必须串行执行，不能并发）
# 重要：先确定 dashboard_id、组件 name/type 和真实表字段
# 再阅读 dashboard-block-data-config.md 了解 data_config 结构
lark-cli base +dashboard-block-create \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --name "新组件名" \
  --type column \
  --data-config '{...}'
```

### 场景 3：编辑已有组件

> [!IMPORTANT]
> `+dashboard-block-update` **不能修改组件的 `type`**（图表类型），可以更新 `name`、`data_config`、`linkage` 和可选的 `position`。
> 如需更换组件类型，必须先删除再重新创建。

```bash
# 第 1 步：列出仪表盘，定位到当前仪表盘
lark-cli base +dashboard-list --base-token xxx

# 第 2 步：列出组件，获取到目标组件
lark-cli base +dashboard-block-list --base-token xxx --dashboard-id blk_xxx
# 获取目标 block_id
# 提示：查看已有组件可作为参考，或检查是否重复创建相似组件

# 第 3 步：获取组件当前详情
lark-cli base +dashboard-block-get --base-token xxx --dashboard-id blk_xxx --block-id chtxxxxxxxx

# 第 4 步：根据用户编辑诉求准备更新
# 如果编辑诉求涉及数据源变更，需要先获取数据源信息
lark-cli base +table-list --base-token xxx
lark-cli base +field-list --base-token xxx --table-id <table_id>

# 第 5 步：执行更新
# 重要：先读取当前 block 的 name/type/data_config
# 再阅读 dashboard-block-data-config.md 了解 data_config 更新规则
lark-cli base +dashboard-block-update \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --block-id chtxxxxxxxx \
  --data-config '{...}' \
  --position '{...}'   # 可选，只在需要调整布局时传

# 排行榜只修改 Top N；不会覆盖分组、指标、筛选或排序
lark-cli base +dashboard-block-update \
  --base-token xxx \
  --dashboard-id blk_xxx \
  --block-id chtxxxxxxxx \
  --data-config '{"limit_size":20}'

```

### 场景 4：重排仪表盘布局

当用户要求调整布局、重排、美化、撑满或铺满，但没有给出组件级坐标或尺寸时使用。定位仪表盘后调用一次 `+dashboard-arrange` 并回读验收；本轮新建仪表盘按上方交付健康门禁执行。

> [!CAUTION]
> - 排列结果是**服务端智能推荐**，不一定完全符合用户预期
> - `+dashboard-arrange` 无法指定 `x/y/w/h`、精确位置或尺寸，排列逻辑是**自适应**的；只有用户明确给出可执行的组件级坐标、行列或尺寸约束时才改用 `--position`
> - **本次新建仪表盘经 `+dashboard-arrange` 重排后布局仍不合格（重叠、空行、行内空档、非末行右留白或末行未左起）时，即使用户没给坐标，也应改用 `--position` 逐组件自算坐标兜底重试，写后回读 `position` 自检；判据见 [lark-base-solution-design.md](lark-base-solution-design.md) 的仪表盘布局条**
> - **不建议**在已有仪表盘上自动调用，除非用户明确要求
> - 用户只要求一般性重排、美化、撑满或铺满时，用 `+dashboard-arrange` 整盘编排
> - 编排结果不理想时，可结合用户反馈再调整；不要为了凑效果去探测 raw `lark-cli api`、源码或未公开布局参数

```bash
# 第 1 步：列出仪表盘，定位到目标仪表盘
lark-cli base +dashboard-list --base-token xxx

# 第 2 步：执行智能重排
lark-cli base +dashboard-arrange \
  --base-token xxx \
  --dashboard-id blk_xxx
```

### 场景 5：读取仪表盘或组件现状

**选择查询方式：**
- 想看仪表盘整体结构（含主题、所有组件名称和类型）→ 用 **方式 A**
- 只想快速查看有哪些组件 → 用 **方式 B**
- 想看某个组件的详细 data_config 配置 → 用 **方式 C**
- 想看某个图表/指标卡实际算出来的数据 → 用 **方式 D**
- 想看视图组件中的记录 → 用 **方式 C** 取得 `tableId / viewId`，按 [视图组件数据读取](lark-base-dashboard-view.md#读取视图组件数据) 调用 `+record-list --view-id`

用户要求读取“全部图表”或“完整仪表盘”时，先用方式 B 分页枚举所有 block：使用 `--page-size 100`；若返回 `has_more=true`，继续把本页返回的 `page_token` 传给 `--page-token`，直到 `has_more=false`。收齐后再对每个 block 收口，不能只返回 get-data 成功的子集：

1. 图表或指标卡：使用方式 D 读取计算结果。
2. `view`：使用方式 C 取得真实视图引用，再用 `+record-list --view-id` 读取记录，继承视图配置并按需分页。
3. `text`：使用方式 C，正文位于 `data_config.text`；text 没有计算结果，但属于完整仪表盘内容。

```bash
# 第 1 步：列出仪表盘，定位到当前仪表盘
lark-cli base +dashboard-list --base-token xxx

# 第 2 步：根据用户诉求查看详情

# 方式 A：查看仪表盘整体情况（包含所有组件列表）
lark-cli base +dashboard-get --base-token xxx --dashboard-id blk_xxx

# 方式 B：列出所有组件
lark-cli base +dashboard-block-list --base-token xxx --dashboard-id blk_xxx

# 方式 C：查看某个组件的详细配置
lark-cli base +dashboard-block-get --base-token xxx --dashboard-id blk_xxx --block-id chtxxxxxxxx

# 方式 D：查看某个图表组件的计算结果（AI 友好的 chart protocol）
lark-cli base +dashboard-block-get-data --base-token xxx --block-id chtxxxxxxxx

# 最后：把获取到的现状信息整理好告诉用户
```

需要读取多个组件的数据时，已有全部可信 `block_id` 和类型就直接按 [lark-base-dashboard-block-get-data.md](lark-base-dashboard-block-get-data.md) 的多组件范式分流：图表读取计算结果，视图组件读取记录，文本组件读取 `data_config.text`；缺少 ID 或类型时才用方式 B 分页定位。同类读取可在一个 shell 工具调用内串行执行。

## 组件类型选择

组件 `type` 决定展示形式：

| 用户想看什么 | 选什么 type | 说明 |
|-------------|------------|------|
| 数据趋势（时间变化） | line | 折线图组件 |
| 类别比较（谁高谁低） | column | 柱状图组件 |
| 占比分布（各部分比例） | pie | 饼图组件 |
| 无 `group_by` 的单值关键指标 | statistics | 指标卡组件 |
| 单维度 Top N 排名 | ranking | 排行榜组件，单分组、单指标 |
| 满意度评分分布 | nps | NPS 图，单个 Rating 字段与可选分段 |
| 富文本说明/标题/注释 | text | 文本组件（支持 Markdown） |

详细组件类型和 data_config 完整规则：[dashboard-block-data-config.md](dashboard-block-data-config.md)

## 常见问题

**Q: 创建组件的命令和 data_config 怎么写？**
A:
1. 先确定 `dashboard_id`、组件 `name`、组件 `type` 和真实表字段
2. 再读 [dashboard-block-data-config.md](dashboard-block-data-config.md) 了解：
   - 全部组件类型的可复制模板
   - filter 筛选条件格式
   - 字段类型与操作符对应表

**Q: 为什么组件创建失败了？**
A: 常见原因：
- `table_name` 用了 table_id 而不是表名（必须用表名称，如「订单表」）
- `series` 和 `count_all` 同时存在（必须二选一，互斥）
- 字段名拼写错误（必须用 `+field-list` 获取的真实字段名，禁止猜测）
- 组件创建并发执行（必须串行，等上一个完成再执行下一个）

**Q: 可以一次创建多个组件吗？**
A: 不可以，必须串行执行。等上一个 `+dashboard-block-create` 完成后再执行下一个。

**Q: 组件的 `type` 创建后能改吗？**
A: 外层组件 `type` 不能修改。`+dashboard-block-update` 可以修改 `name`、`data_config`、`linkage` 和 `position`；倒计时内部的 `data_config.type` 可以在 fixed / field 之间切换，但必须提交完整目标模式配置。

**Q: 更新组件的命令和 data_config 怎么写？**
A:
1. 先读取当前 block，确认 `block_id`、当前 `type` 和已有 `data_config`
2. 再读 [dashboard-block-data-config.md](dashboard-block-data-config.md) 了解 data_config 结构

**普通图表 data_config 更新策略（顶层 key merge）**：
- 只传入需要修改的顶层字段（如 `series`、`filter`）
- 未传的顶层字段（如 `group_by`）自动保留原值
- 但每个传入的字段内部通常是**全量替换**（如传新 `filter` 会完整覆盖旧 `filter`）；`number_format` 例外，按子字段合并，见 [dashboard-block-data-config.md](dashboard-block-data-config.md) 的 number_format 小节

**倒计时**使用 camelCase 的 fixed/field 专属配置：更新时省略 type 沿用当前模式，唯一 additionalDatasources 对象按字段合并，groupBy/series 数组整体替换。同模式同表下 filter 省略保留、对象替换、null 清空。切换模式要求完整目标配置，换表要求完整新数据源；获取和写入响应均返回当前模式完整配置。构造 JSON 前读 [Dashboard Block 配置](dashboard-block-data-config.md) 的 countdown 小节。

**Q: 查看已有组件有什么用？**
A: 在「添加新组件」或「编辑组件」前查看已有组件可以：
- 了解当前仪表盘已有哪些可视化
- 避免重复创建相似的组件
- 参考已有组件的 data_config 结构作为模板；视图组件的回读与写入格式不同，应按[视图组件配置](lark-base-dashboard-view.md)构造可写字段，不直接回传 GET 结果或其中的旧 `timebar/card` 配置

**Q: 我想直接拿图表算好的结果给 AI 分析，应该用什么？**
A: 用 `+dashboard-block-get-data`。它返回图表协议 JSON（常见字段包括 `dimensions`、`measures`、`main_data`，指标卡可能还有 `comparison_data`、`trend_data`），不返回 block 名称、类型、布局或 `data_config`；需要这些元数据时先用 `+dashboard-block-get`。

图表联动使用独立顶层 `linkage`，更新按完整目标列表替换；省略保留、空数组清除。操作前读 [图表联动](lark-base-dashboard-linkage.md)。只改联动时验收保存的目标列表，要求点击效果时再做页面交互验证；`get-data` 不模拟点击。

## 写入前检查

- 创建 block 前必须知道 `base_token`、`dashboard_id`、组件 `name/type` 和 `data_config`。
- 更新 block 前必须知道 `base_token`、`dashboard_id`、`block_id`，并读过当前 block。
- `data_config` 中使用表名和字段名，不使用 table_id / field_id；名称必须来自 `+table-list` / `+field-list` 的真实返回。

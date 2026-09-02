---
name: alert-record-forms
description: 备案号更新流程能力。为机构下项目的公开募捐活动备案号提供更新流程：用户先选项目 → 上传备案表截图 → LLM 视觉识别（备案表主体 + 合作方选传）→ 识别结果与所选项目不匹配时引导切换项目或重传 → 调 open_fund_raising_program_update_ui 调起前端表单页 → 用户在 UI 内直接提交 → UI 回 submit.next_step 通知 Agent 进入提交后流程（命名步骤「提交备案号到远程」）。
---

# 备案号更新流程

## ⛔ MCP 调用已封装为脚本（AI 禁止裸调 MCP 工具）

> 本专家所有 MCP 工具调用已封装为 `skills/<skill>/references/scripts/` 下的 Python 脚本（共享客户端 `skills/_common/mcp_client.py`）。AI **只通过 `execute_command` 运行脚本获取结果，禁止直接裸调 MCP 工具**。
>
> 单步脚本已内置：字段校验与归一化、项目/审批守卫、实时 `old_no` 上下文过期校验、慈善中国链接校验、参数构造、缓存和失败上抛。普通 `no` 不一致提示由 Agent 在脚本前完成。
> 本地 `references/tools/*.md` 为 UI 调起入参 / 业务体输入的权威契约文档；**提交在 UI 内直接完成（后端 `update_org_record_number` 接口校验），Agent 不执行提交动作**。

## ⛔ 脚本调用与落盘约定（锚定）

> 本 Skill 的脚本调用与 JSON 落盘遵守编排层「全局落盘与脚本调用约定」（`agents/alert-expert.md`，唯一完整定义）。要点速记：**用 Bash + `python3` 跑脚本（禁 PowerShell/cmd/bat），输出重定向到当前目录日志文件再读（禁 `/tmp`）；生成 `record_input.json` 用文件写入能力写到当前工作目录 + Read 验证；`--json-file` 用相对路径、保持 cwd 一致（不 cd 到脚本目录）**。

运行示例（Bash，相对路径，保持 cwd，不 cd 到脚本目录）：

```bash
python3 "<skill脚本绝对路径>/run_record_ui.py" --source vision --json-file "record_input.json" > "run_record_ui.log" 2>&1
```

> `<skill脚本绝对路径>` 即 `skills/alert-record-forms/references/scripts` 目录的绝对路径（你加载本 SKILL 时已知）。运行后 Read 读 `run_record_ui.log`（当前目录）解析状态。


## 概述

"备案号更新"能力，接管机构下项目的**公开募捐活动备案号**更新流程。

**与证件更新的差异**：
- OCR 走**LLM 视觉**（非云OCR）—— 备案表版式简单，用 prompt 约束即可
- **逐个处理**（每个备案号对应一个项目）—— 不做批量收集
- **无排队机制** —— 备案号是项目级别独立更新，不受运营审核阻塞
- **UI 内直接提交** —— 唯一 `record_input.json` 经 `run_record_ui.py` 单步校验和缓存后调起 UI，用户核对/修改后**在 UI 内直接完成提交**；UI 回 `submit.next_step` 通知 Agent 进入提交后流程（命名步骤「提交备案号到远程」）
- **显式链接查询** —— 只有用户已提供有效慈善中国详情页链接并明确选择查询时，统一入口 `run_record_ui.py` 才会内部调用慈善中国查询模块；OCR 效果差本身不会进入查询步骤（见 Step 3.4/3.5）
- **快速分流** —— 用户只提供慈善中国详情页链接未上传截图时，**当轮立即**弹窗让用户明确选择"查询慈善中国数据"还是"上传截图"（见 Step 2.5），不做多轮试探

## 触发场景

由专家在以下情境加载：
- 用户直接对话："我要更新备案号"、"备案号到期了"、"更新公开募捐备案号"等

上下文（可能已知）：
- 待更新备案号项目清单（按项目分组，含**项目编号 `project_no`** + 项目名 `project_name` + 剩余天数 + 项目级 `fund_raising_program_id` + `fund_raising_program_no` + `fund_raising_program_audit_status`（原始审核状态 1=已通过/2=审批中/3=已驳回，用于项目级守卫判定）+ `updatable`（= audit_status != 2，审批中则 false，作为项目级守卫判据，优先用它判断能否提交））：
  - 通过 `../alert-info-fetcher` 运行 `references/scripts/query_todo_detail.py --scope record` 获取，**Agent 只消费返回的 `record.list`，禁止裸调 MCP 工具、无需手动分页**）；下文 `record.list[k]` 即该数组的第 k 个元素
  - **⚠️ 注意区分（4 个易混字段 + 守卫判据）**：`record.list[].project_no`（**项目自身编号**，如 `224328`，仅用于展示，不参与提交）vs `record.list[].fund_raising_program_id`（备案号业务主键）vs `record.list[].fund_raising_program_no`（**真正的备案号编号**，用于展示 + `no` 一致性校验）vs `record.list[].fund_raising_program_audit_status`（原始审核状态 1=已通过/2=审批中/3=已驳回，用于项目级守卫判定）；项目级守卫请直接用派生的 `record.list[].updatable`（= audit_status != 2，审批中则 false）判断

## 工作流程

### Step 1: 展示待更新清单

**核心动作**：**必须**用 `AskUserQuestion` 弹出可点击列表（**不得**用纯文本编号列表代替），每个选项对应一个项目，**`label` 固定格式为 `[project_no][project_name] 备案号 [fund_raising_program_no]`**（先项目编号，再项目名，再"备案号"字面量，再当前生效备案号的编号——⚠️ **`project_no` ≠ `fund_raising_program_no`，二者都要展示且不能互相替代**：`project_no` 是项目自身编号如 `224328`，`fund_raising_program_no` 才是真正的"备案号"如 `52620600MJY949356HA26006`），`description`=剩余天数/到期状态；**根据 `updatable`（审批中则 false）做差异化标注**：

| `updatable` | 展示样式 | 可选状态 |
|----------------|---------|---------|
| true| 正常展示 | ✅ 可选 |
| false| `description` 标注"【审批中】备案号更新中, 请等待审批通过后再修改" |⛔ 仍展示为选项，但点选后由 Step 2 的项目级守卫拦截 |

**弹窗示例**（`project_no_A`=项目编号如`224328`，`fund_raising_program_no_A`=备案号如`52620600MJY949356HA26006`）：
```
AskUserQuestion(
  questions: [{
    question: "您有 [N] 项备案号即将到期, 请选择要处理的项目",
    options: [
      { label: "[project_no_A][项目名A] 备案号 [fund_raising_program_no_A], 剩 5 天到期" },
      { label: "[project_no_B][项目名B] 备案号 [fund_raising_program_no_B], 【审批中】备案号更新中, 请等待审批通过后再修改" },
      { label: "[project_no_C][项目名C] 备案号 [fund_raising_program_no_C], 已过期" }
    ],
    multiSelect: false
  }]
)
```

**⛔ 常见错误**：把 `project_no`（项目编号）当成"备案号"直接拼进 `备案号[project_no]` 里展示——这是两个不同的字段，`project_no` 只是项目自身的编号，真正的备案号是 `fund_raising_program_no`，**两者都要展示，不能用一个代替另一个**。

> 若 N 超过一屏合理展示数量（如 >5），按剩余天数升序只弹前 N 项，其余可在选项末尾追加"查看更多"选项分批弹出。

**说明**：
- 审批中的项目**照常计入到期数**（N 保持原始语义），只在展示层标注差异
- 审批中的项目**不消失、不隐藏**，让用户看得到"确实存在但当前不能改"

### Step 2: 用户选择要更新的项目

**⛔ 项目级守卫**：用户点选后Skill 必须先检查 `record.list[k].updatable`：

```
if record.list[k].updatable === false (AUDIT_PENDING 审批中):
    # 审批中，拦截
    话术: "该备案号正在更新审批中, 请等待审批通过后再修改。请选择其他项目, 或退出。"
    → 回到 Step 1 等待用户重选
    → **不进入 Step 3 上传**
else:
    # updatable === true（audit_status ∈ {1, 3}），正常继续
    Skill 从查询结果中定位并**在会话内保存**项目上下文:
      - id = record.list[k].fund_raising_program_id
      - selected_old_no = record.list[k].fund_raising_program_no
      - org_no = org.org_no
      - org_name = org.org_name
```

**话术**（正常分支）：
```
好的，我们来更新「[项目名A]」（备案号 [fund_raising_program_no_A]）。

请上传新的备案表截图：
- 【必传】备案表主体（含捐赠目的、募捐用途、受益人信息、募捐目标等）
- 【选传】合作方信息（若开展合作公开募捐，请一并上传第二张图）

⚠️ 续期不能改备案号编号，其他字段按实际情况填写。
```

### Step 2.5: 用户没上传截图、只提供了慈善中国详情页链接（快速分流，避免多轮试探）

**触发条件**：用户在 Step 2 话术之后的下一条消息**不含图片附件**，内容是一条有效慈善中国详情页链接（`cszg.mca.gov.cn` 域名、`csmhcdetail` 详情页）。

**⛔ 不要多轮试探、不要自己悄悄决定走哪条路**：一旦识别到这个场景，**立即**（当轮内）调用 `AskUserQuestion` 让用户明确选择，而不是先反问"您是要查询还是上传"之类的纯文本追问，也不要不声不响就直接运行慈善中国查询脚本：

```
AskUserQuestion(
  questions: [{
    question: "检测到您输入的是慈善中国详情页链接而非截图, 请选择获取信息的方式",
    options: [
      { label: "[查询慈善中国数据]尝试从慈善中国查询信息" },
      { label: "[上传备案表截图]手动上传截图, 由 AI 识别提取信息, 准确度更高（推荐）" }
    ],
    multiSelect: false
  }]
)
```

| 用户选择 | Skill 动作 |
|---------|-----------|
| 查询慈善中国数据 | 记下并验证用户提供的链接，**直接进入 Step 3.5**（显式链接查询，跳过 Step 3 OCR）|
| 上传备案表截图 | 回到 Step 2 的上传话术，等待用户上传截图，走 Step 3 正常 OCR 流程 |

> 若用户消息**同时**带图片附件（哪怕也提到了链接）→ 不算命中本触发条件，直接走 Step 3 正常 OCR。

### Step 3: 用户上传截图（主表必传 + 合作方选传）

#### 3.1 图片载入（`IMAGE_LOADED`）

1. 加载本包内的 `alert-ocr` Skill，选择识别策略 `strategy_id: llm_vision_record`。
2. `llm_vision_record` **不是工具、脚本、函数或 MCP 名称**。禁止搜索 `llm_vision_record`、`LLM OCR`、`multimodal` 等工具，也禁止因为工具列表里没有视觉工具而宣称无法识别。
3. 从用户消息读取 `image_local_path`；对每个唯一图片路径调用一次图片读取能力。返回可视图片内容即记为 `image_loaded=true`。
4. 主表和合作方图分别载入，正常读取次数必须等于唯一图片路径数量。同一路径仅在明确读取失败且用户要求重试时允许再次读取。
5. 图片载入只表示当前模型已获得像素，**不等于 OCR 已完成**；载入成功后直接进入 3.2，不再做能力发现或切换引擎。
6. 只有图片读取明确返回文件不存在、格式不支持或无法呈现图片时，才能提示用户重传。

#### 3.2 生成唯一输入文件（`RECORD_INPUT_READY`）

当前模型直接依据 `../alert-ocr/references/llm-vision-record.md` 提取 20 个业务字段和精简质量信息，并将 Step 2 已保存的项目上下文合并为 schema 2.0 的 `record_input.json`：

- `context.id`：所选项目 `fund_raising_program_id`
- `context.org_no` / `context.org_name`：首次查询脚本返回的当前机构
- `context.selected_old_no`：用户选择项目时展示的 `fund_raising_program_no`
- `quality_warning_confirmed` 默认 false；`confirmed_charity_org_name` 默认空。编号不一致由 Agent 询问，用户选择继续后不修改输入文件；慈善中国机构不一致确认仍写入当次机构名
- `fields`：主表 17 个字段 + 合作方 3 个字段
- `quality`：只含 `confidence`、`uncertain_fields`、机器代码 `warnings`

用**文件写入能力**把这一份 JSON 落盘到当前工作目录的相对路径 `record_input.json`（禁 shell 内联写文件，规则见编排层「全局落盘与脚本调用约定」）。禁止生成 `raw_ocr_text`、`evidence`、`validated_record_ocr.json`、`project_context.json` 或 UI 参数文件，不得写入 Skill 源码目录。

#### 3.3 Agent 前置检查

在运行脚本前直接检查刚生成的结构化对象：

- `no` 和 `name` 同时为空 → 提示“未识别到备案信息，请确认上传的是备案表截图”，删除输入文件，不得调起 UI。
- 仅 `no` 或仅 `name` 缺失、`confidence=low` 或 `uncertain_fields` 非空 → 进入 Step 3.4。
- JSON 结构化失败 → 基于已载入图片重新生成一次，不重复读取图片；再次失败则提示用户重传。
- 无质量问题 → 跳过 Step 3.4/3.5，直接进入 Step 3.6。

确定性类型、日期、合作方关系校验不再单独启动进程，由 Step 4 的 `run_record_ui.py` 内联执行。

### Step 3.4: OCR 质量问题处理

**触发条件**：Step 3 校验后出现 `quality.confidence=low`、仅 `no`/`name` 任一缺失，或 `quality.uncertain_fields` 非空。

> OCR 质量问题本身不是慈善中国查询的触发条件。只有用户实际提供了有效慈善中国详情页链接，并明确选择查询，才可进入 Step 3.5。

- 会话中已有有效慈善中国详情页链接：使用 `AskUserQuestion` 提供“查询慈善中国补齐 / 重新上传截图 / 带警告继续 UI”。用户选择查询后进入 Step 3.5。
- 会话中没有有效慈善中国详情页链接：使用 `AskUserQuestion` 提供“重新上传截图 / 提供慈善中国链接 / 带警告继续 UI”。
- 用户选择“提供慈善中国链接”时，仅提示并等待用户发送链接；收到并验证有效链接之前不得进入 Step 3.5。
- 用户选择“重新上传截图”时，先用 `--cancel` 清理当前输入文件，再接收新图；新输入的全部确认字段必须恢复默认值。
- 用户选择“带警告继续 UI”后，将同一输入文件中的 `context.quality_warning_confirmed` 更新为 true；不得创建第二份文件。
- 当 `no` 与 `name` 同时为空时已在 Step 3.3 判定为非备案表，不进入本步骤，也不得提供“继续 UI”。
- 仅缺 `no` 或仅缺 `name` 时允许继续，单步脚本在业务层转换为零值，由用户在 UI 内补录。

### Step 3.5: 慈善中国详情页链接查询（显式链接路径）

**⚠️ 定位**：用户显式提供链接后选择的数据查询路径，不是由 OCR 失败自动触发的兜底路径。主路径仍是 Step 3（LLM 视觉 OCR）。

**进入本步骤必须同时满足**：

1. 用户已经提供有效慈善中国详情页链接（`cszg.mca.gov.cn` 域名、`csmhcdetail` 详情页）；
2. 用户已在 Step 2.5 或 Step 3.4 明确选择“查询慈善中国数据/补齐”。

缺少任一条件都不得进入本步骤。低置信度、字段缺失、`uncertain_fields` 非空或 OCR envelope 中没有 `org_name`，均不能单独触发本步骤。机构一致性只在慈善中国实际返回非空 `org_name` 时执行。

**单步调用方式**：

本步骤不再单独运行 `fetch_charity_record.py`，也不生成 `charity_result.json`。只保存已经验证的链接，在 Step 4 调用统一脚本时增加 `--charity-url <详情页链接>`：

- 从 Step 2.5 进入（只有链接）：先在当前工作目录创建一份最小 `record_input.json`，只需包含 schema 2.0、`context`、空 `fields` 和默认 `quality`；Step 4 使用 `--source charity`，慈善中国数据作为初始字段。
- 从 Step 3.4 进入（补齐视觉结果）：继续使用视觉阶段的同一 `record_input.json`；Step 4 使用 `--source vision --charity-url <链接>`，视觉非空字段保持，慈善中国只补齐空字段。

统一脚本在同一进程中完成链接校验、网页查询、字段映射和机构名比较。没有有效链接必须停留在 Step 2.5/3.4，禁止猜测链接或运行查询。

若脚本返回 `USER_DECISION_REQUIRED`：

- `reason=ocr_quality_warning`：慈善中国补齐后仍存在低置信度或单个关键字段缺失；用户明确继续后将 `context.quality_warning_confirmed=true`，再用同一输入文件重跑。
- 慈善中国返回的 `no` 不一致不在脚本内中断，识别值原样进入 UI，由 UI 标红并要求用户修改；用户选择查询慈善中国本身即表示继续查看查询结果。
- `reason=charity_org_mismatch`：展示脚本返回的两个机构名，用户明确继续后将脚本返回的 `charity_org_name` 原样写入 `context.confirmed_charity_org_name`，再用同一输入文件重跑。
- 确认前脚本不会写公共缓存；用户取消时执行 `python3 "<skill脚本绝对路径>/run_record_ui.py" --json-file "record_input.json" --cancel` 清理输入。

**慈善中国输出字段与 proto 的映射**：详见 [`references/scripts/README.md`](./references/scripts/README.md)。

**慈善中国查询失败处理**：

| 失败类型 | Skill 行为 |
|---------|-----------|
| `invalid_charity_url` / `charity_query_failed` | 输入文件保持不变；提示检查链接、稍后重试或改传截图。用户改传截图时先用 `--cancel` 清理旧输入 |
| `RETRY_REQUIRED`（网络/MCP 暂时失败）| 保留同一输入文件，只重跑脚本，不重新读图 |
| 慈善中国补齐后仍仅缺 `no` 或仅缺 `name` | 经用户明确选择后打开 UI 手工补齐；`no` 与 `name` 同时缺失则判定无有效备案表数据源，不调 UI |

**⚠️ 慈善中国查询铁律**：

- ❌ 用户未提供有效详情页链接时进入 Step 3.5 或向单步脚本传 `--charity-url`
- ❌ 仅因 OCR 低置信度、字段缺失或不确定就自动进入 Step 3.5
- ❌ 跳过用户的明确查询选择，或跳过机构一致性比对直接进入 UI
- ❌ 用慈善中国数据**覆盖** OCR 已识别的非空字段（只能补齐缺失字段）
- ❌ 查询失败时静默切换路径或不告知用户

### ⛔⛔ 总原则：调起 UI 前不能做"拒绝调用"的硬阻断，硬校验由 UI + 后端完成

**在调起 UI（Step 4）之前，一般数据问题**（非空 `no` 与 `selected_old_no` 不一致、慈善中国机构名不一致、单个字段缺失、识别可能有误等）不得演变成“拒绝调用 UI 且不给任何前进路径”的硬阻断。UI 页面用于用户核对、修正和补齐字段。

以下情况必须拒绝**当前这次 UI 调起**，但仍提供重选、重传或补充链接路径：项目不存在/审批中、`id`/`org_no`/`selected_old_no`/实时 `old_no` 缺失、`no` 与 `name` 同时为空、视觉输入未通过单步脚本校验、纯链接路径没有有效慈善中国详情页查询结果。

其余问题的正确处理方式只有两种：
1. **用 `AskUserQuestion` 提醒用户，但选项集里必须包含一条能推进到 UI 的路径**（如"识别可能有误，继续下一步"），已示例见下方 Step 3.6；或
2. **直接带着已识别的数据（哪怕不完整/有疑问）调起 UI**，让用户在页面里亲自核对/修正/补齐（如未识别字段按零值传入，见下方「未识别字段的填充约定」）。

**真正会"中止流程、拒绝继续"的强制校验**（必填、日期格式、日期关系、长度、枚举、`no` 一致性、审批中守卫等）**由前端 UI 页面 + 后端 `update_org_record_number` 接口在提交时完成**（用户在 UI 内点提交时即校验）——**Agent 不执行提交、也不做兜底校验**。

### Step 3.6：`no` 一致性预检（数据准备完成后、调起 UI 前）

#### 3.6a 跨项目备案号匹配（优先检查，**必须弹窗**）

在比对 `selected_old_no` 之前，先把识别出的 `fields.no` 与 `record.list` 中**每一个项目**的 `fund_raising_program_no` 逐一比对：

- 若 `no` **命中了另一个项目**的 `fund_raising_program_no`（即识别出的备案号属于清单里的其它项目，而非当前所选项目）→ **必须**用 `AskUserQuestion` 弹出可点击选项，让用户在“切换到该项目 / 重新上传 / 取消”之间选择，**严禁**用纯文本表格、编号列表或让用户打字回复的方式代替弹窗：

```
AskUserQuestion(
  questions: [{
    question: "截图中的备案号（[no]）属于「[项目名X]」，与当前所选项目「[项目名A]」不匹配，请选择如何处理",
    options: [
      { label: "[切换到该项目]使用本张截图, 处理「[项目名X]」的备案号更新" },
      { label: "[重新上传]继续处理「[项目名A]」, 重新上传正确的备案表截图" },
      { label: "[取消]结束本次备案号更新" }
    ],
    multiSelect: false
  }]
)
```

| 用户选择 | Skill 动作 |
|---------|-----------|
| 切换到该项目 | 先用 `--cancel` 清理旧输入；会话上下文切换为命中项目（`id`/`selected_old_no` 取该项目的 `fund_raising_program_id` / `fund_raising_program_no`）；基于已识别字段重新生成 `record_input.json`，进入 Step 4 |
| 重新上传 | 先用 `--cancel` 清理旧输入，回到 Step 3 重传 |
| 取消 | 用 `--cancel` 清理输入，结束本次更新 |

> ⛔ 识别出的 `no` 命中了哪个项目，就以哪个项目为切换目标，`[项目名X]` 必须取 `record.list` 中该项目的真实 `project_name`，不得凭名称/序号猜测，也不得省略弹窗。

#### 3.6b 普通编号不一致

`no` 未命中其它项目时，比对 `record_input.json.fields.no` 与 Step 2 会话中保存的 `selected_old_no`：
- `no` 为空但 `name` 非空 → 已在 Step 3.4 提示缺失并取得用户“带警告继续 UI”的明确选择，进入本 Step 后由 UI 要求用户补录。
- `no === selected_old_no` → 直接进入 Step 4，无需打断用户。
- `no` 非空且 `no !== selected_old_no` → **必须**用 `AskUserQuestion` 弹出可点击选项让用户决定，选项集必须包含“继续下一步进入 UI”，不得只给“重新上传/重新选择”两个阻断性选项：

```
AskUserQuestion(
  questions: [{
    question: "截图中的备案号（[no]）与所选项目「[项目名]」的备案号（[selected_old_no]）不一致, 请选择如何继续",
    options: [
      { label: "[重新选择要更新的项目]回到 Step 1清单重新选一个项目" },
      { label: "[重新上传正确的备案表截图]回到 Step 3 重传" },
      { label: "[识别可能有误，继续下一步]先按识别值进入 UI 页面, 可在页面里核对/手动修改后再提交" },
      { label: "[取消本次更新]结束本次备案号更新" }
    ],
    multiSelect: false
  }]
)
```

| 用户选择 | Skill 动作 |
|---------|-----------|
| 重新选择要更新的项目 | 先用 `--cancel` 清理旧输入，再回到 Step 1 |
| 重新上传正确的备案表截图 | 先用 `--cancel` 清理旧输入，再回到 Step 3 |
| 识别可能有误，继续下一步 | 不修改 `record_input.json`，直接进入 Step 4；脚本保留识别 `no` 原值，由用户在 UI 中核对和修改 |
| 取消本次更新 | 调用单步脚本的 `--cancel` 清理输入文件，结束流程并清空会话内 `id` / `selected_old_no` |

### Step 4: 单步构建并调起备案号更新 UI（`open_fund_raising_program_update_ui`）

> ⛔⛔ **调起 UI 前置红线**：必须已选择项目并把当时展示的备案号写入 `context.selected_old_no`；视觉路径必须已有 `record_input.json`，纯链接路径必须已有有效慈善中国详情页链接。`no` 与 `name` 同时为空时不得调 UI。

#### 4.1 运行唯一脚本

> ⛔ 严格按上方「脚本调用与落盘约定」执行：**用 Bash + `python3`、相对路径、保持 cwd（不 cd 到脚本目录）、输出重定向到当前目录日志再读**。`<record_input.json>` 用相对路径 `record_input.json`，`<run_record_ui.log>` 用相对路径；脚本用 `<skill脚本绝对路径>/run_record_ui.py`。不要用 PowerShell/cmd/bat，日志严禁写到 `/tmp`。

视觉快速路径：

```bash
python3 "<skill脚本绝对路径>/run_record_ui.py" --source vision --json-file "record_input.json" > "run_record_ui.log" 2>&1
```

视觉结果经用户明确选择使用慈善中国补齐：

```bash
python3 "<skill脚本绝对路径>/run_record_ui.py" --source vision --json-file "record_input.json" --charity-url "<详情页链接>" > "run_record_ui.log" 2>&1
```

只有链接、跳过视觉识别：

```bash
python3 "<skill脚本绝对路径>/run_record_ui.py" --source charity --json-file "record_input.json" --charity-url "<详情页链接>" > "run_record_ui.log" 2>&1
```

运行后用 Read 能力读取 `run_record_ui.log`（当前目录），解析最后一段 JSON 作为脚本状态。脚本在单一进程内执行：结构和类型校验 → 实时查询项目 → 审批守卫 → 校验实时 `old_no === selected_old_no` → 构建业务体 → 写公共缓存 → 通过日志返回 UI 两字段。不得再调用 `validate_record_ocr.py`、`build_record_ui_params.py` 或单独运行 `fetch_charity_record.py`。

#### 4.2 处理脚本状态

- `PAYLOAD_BUILT`：把日志文件解析出的 `caller_expert_id`、`data_cache_id` 保存到会话后直接调用 UI；不落 UI 参数文件、不查询工具 schema、不做二次转换。若 UI 调用失败或用户关闭后要求重开，直接复用这两个值，不重跑脚本。
- `USER_DECISION_REQUIRED`：脚本尚未写缓存。仅质量确认更新 `quality_warning_confirmed`，机构确认写入 `confirmed_charity_org_name`；普通编号不一致不会由脚本返回该状态。
- `STALE_PROJECT_CONTEXT / old_no_changed`：用户选择项目后后台备案号已变化；旧确认立即失效，刷新清单并重新选择，不调 UI。
- `RETRY_REQUIRED`：MCP 或网络暂时失败；保留同一输入文件，刷新凭证或稍后只重跑脚本，不重新读图。
- `REJECTED`：按 `reason` 提示用户重选、重传或修正数据，不调 UI。

脚本在 `PAYLOAD_BUILT`、`REJECTED`、`STALE_PROJECT_CONTEXT`、`CANCELLED` 时自动删除当前工作目录中的输入文件；`USER_DECISION_REQUIRED`、`RETRY_REQUIRED` 时保留同一文件。

#### ⛔ `no`、`selected_old_no` 与实时 `old_no` 的红线

```
selected_old_no ← 用户选择项目时的 record.list[k].fund_raising_program_no
no              ← 图片识别值或慈善中国结果
实时 old_no     ← run_record_ui.py 按 id 重新查询的最新值
```

Agent 在脚本前比较视觉 `no` 与 `selected_old_no` 并完成用户提示；用户选择继续后不修改输入文件。脚本不校验普通编号确认，只实时查询 `old_no` 判断项目上下文是否过期：若实时值不同于 `selected_old_no`，返回 `STALE_PROJECT_CONTEXT`，不写缓存。

**MUST NOT 用任何 `old_no` 覆盖 `no`**。用户确认不一致后，UI 中仍保留原识别值，由 UI 的红标和提交校验处理。

**UI 侧行为**（由前端页面实现）：
- `no` 为空 → 显示必填提示，用户补录后才能提交。
- `no === old_no` → 正常可提交。
- `no` 非空且 `no !== old_no` → `no` 输入框标红并阻止提交，用户改成一致后才放行。

项目上下文、来源工件与最终 `fundraising_program` 字段契约见 [`references/tools/fundraising_program_input.md`](./references/tools/fundraising_program_input.md)；UI 调起入参契约仅含 `caller_expert_id` + `data_cache_id` 两字段，完整业务体已进入公共缓存。

**调起后 Skill 的行为**（对齐 alert-expert 编排层「命名步骤：提交备案号到远程」）：
- ✅ `open_fund_raising_program_update_ui` 调用返回成功后，本轮立即结束——**只输出一句极简提示**（如"备案号信息已提取完成，已为您打开确认页面，请在页面中确认并提交"），**不再输出任何其它文字或发起任何工具调用**
- ✅ 然后**等待 Agent 依据 `submit.next_step` 重新调度执行命名步骤 `提交备案号到远程`**
- ❌ **MUST NOT** 自行轮询 / 猜测用户是否已提交
- ❌ **MUST NOT** 收到 `submit.next_step` 后再次调用任何提交接口（提交已在 UI 内完成，命名步骤「提交备案号到远程」只进入提交后流程）

### 命名步骤：`提交备案号到远程`（UI 内提交后由 Agent 依据 `submit.next_step` 重新调度触发，进入提交后流程）

>⭐ **步骤名 MUST 逐字符为 `提交备案号到远程`** —— `submit.next_step` 固定文案里点名这个名字，改一个字 Agent 就没法正确重新调度到本步骤。

**触发语义**：用户在 UI 页面点"提交"时，**提交动作已由 UI 内直接完成**（后端 `update_org_record_number` 接口在 UI 侧校验并提交）。UI 随后回一句 `submit.next_step` 文案给 Agent，**仅作为"已提交完成"的通知信号**，不携带需要 Agent 再处理的数据。

**执行**：收到 `submit.next_step` 后，**MUST NOT 再调用任何提交接口**（提交已在 UI 内完成），直接进入提交后流程：
1. **Step 5**：向用户输出成功话术（备案号已提交、进入审批流程）
2. **Step 6**：询问是否继续处理下一个备案号（或收尾）

### Step 5: 提交结果反馈

**成功话术**：
```
✅ 已更新「[项目名 A]」的备案号，进入审批流程。
审批完成前该项目无法再次修改，其他项目不受影响。
```

> ⚠️ 提交失败由 UI 页面自行提示处理（Agent 不感知、不处理失败分支）；Agent 收到 `submit.next_step` 即视为提交成功，直接进入提交后流程。

`fundraising_program` 业务体字段规范见 [`references/tools/fundraising_program_input.md`](./references/tools/fundraising_program_input.md)。参数构建前由脚本执行项目存在性、审批状态、实时 `old_no`、来源和机构一致性守卫；UI + 后端继续执行提交时的 `no` 一致性、必填、日期、长度和枚举校验。Agent 不得绕过或重复实现这些校验。

### Step 6: 询问是否继续下一个

**若清单里还有未处理**：**必须**用 `AskUserQuestion` 弹出可点击列表（选项与 Step 1 同构：每个未处理项目一个选项 + 末尾追加"结束"选项），**不得**用"回复项目名/回复退出"这类纯文本问答代替：
```
AskUserQuestion(
  questions: [{
    question: "还有 [N-1] 项备案号待更新, 请选择下一个要更新的项目",
    options: [
      { label: "[project_no_B][项目名B] 备案号 [fund_raising_program_no_B], 剩 12 天到期" },
      { label: "[project_no_C][项目名C] 备案号 [fund_raising_program_no_C], 【审批中】暂无法更新" },
      { label: "[结束]结束本次备案号更新" }
    ],
    multiSelect: false
  }]
)
```


**若已全部处理完（所有备案号项目均已提交）**：先重新拉取一次最新数据（`query_todo_summary.py`），确认当前是否还有**未处理的证件预警**（`kind === "cert"` 或 `kind === "both"`；⚠️ 该脚本只返回 `kind` / `has_pending_review`，**不返回 `cert_count`**，计数需另跑 `query_todo_detail.py --scope cert`）：

- **仍有未处理证件预警** → **必须**调用 `AskUserQuestion` 弹出可点击二选一，让用户在"继续更新证件"与"结束"之间做选择（⛔ **严禁**以"是否需要我帮你更新证件吗？"这类纯文本问句收尾，这正是此前漏弹窗的根因）：
  ```
  AskUserQuestion(
    questions: [{
      question: "备案号已处理完毕, 但您当前机构还有证件预警未处理, 是否现在更新证件？",
      options: [
        { label: "[更新证件]继续协助更新到期证件" },
        { label: "[结束]结束本次对话" }
      ],
      multiSelect: false
    }]
  )
  ```
  - 用户选"更新证件" → 交还预警专家（alert-expert）路由进入**任务二：证件更新**（从 Step 1 提示上传开始；⚠️ 若 `has_pending_review===true` 则证件暂不可处理，按任务零对应分支提示"审批完成后才能提交证件更新"）
  - 用户选"结束" → 输出总结后结束本次对话
- **无证件预警** → 输出总结告知用户，结束

## 铁律

### 🟠 流程与数据

- ❌ **任何需要用户在多个处理方式间做选择的场景，用纯文本表格 / 编号列表 / “请告诉我你想怎么处理”之类的问句代替 `AskUserQuestion` 弹窗**（跨项目备案号匹配、`no` 不一致、OCR 质量处理、项目选择、是否继续等所有分支都必须弹可点击选项）
- ❌ 走云OCR（应用 LLM 视觉）
- ❌ 跳过 Step 2 用户选项目、直接让用户上传截图（会导致后续 `no` 校验没有比对基准）
- ❌ 跳过 UI 二次确认，直接用 OCR 原始JSON 提交（用户没机会核对/修改）
- ❌ 收到 `submit.next_step` 后再次调用任何提交接口（提交已在 UI 内完成）
- ❌ 跳过 `no` 一致性校验（UI 前端红标主校验 + 后端接口兜底）
- ❌ 在 `no ≠ old_no` 时强行提交（续期不能改编号，由 UI 红标 + 后端接口拦截）
- ❌ 一次要求用户上传多个备案号（应逐个处理）
- ❌ 用 `warning_id` 作为 `update_org_record_number.id` 的入参（必须用 `record.list[].fund_raising_program_id`）
- ❌ 使用已废弃的 `warns[].id` 字段路径（v2 已移除，改用项目级 `fund_raising_program_id`）
- ❌ **为`updatable === false`（审批中）的项目发起更新流程或调起 UI**（项目级守卫硬约束）
- ❌ 展示清单时把审批中的项目**隐藏不展示**（应展示但标注不可选，让用户看得到状态）
- ❌ 展示清单时把审批中的项目**从计数里扣减**（`pending_stop_project_count` 保持"到期数"原始语义）

## 特殊情况处理

| 情况 | 处理方式 |
|------|---------|
| 用户点选了 `audit_status=2`（审批中）的项目 | Step 2 项目级守卫拦截，提示"该备案号正在更新审批中, 请等待审批通过后再修改。请选择其他项目, 或退出。" 回到 Step 1 |
| 用户上传的截图不是备案表 | `no` 与 `name` 同时为空 → 校验器返回 `record_not_detected`，提示“未识别到备案信息，请确认上传的是备案表截图”，不得调起 UI |
| OCR 仅缺 `no` 或仅缺 `name` | Step 3.4 提供重传/提供链接/带警告继续 UI；只有用户随后实际提供有效链接并选择查询才进入 Step 3.5，否则可选择继续后按类型填零值，由 UI 要求补录 |
| OCR 识别的 `no` 命中了**另一个项目**的备案号 | Step 3.6a 用 `AskUserQuestion` 弹窗三选一（切换到该项目/重新上传/取消）；**严禁用纯文本表格或让用户打字回复代替弹窗**；用户选“切换到该项目”则切换会话上下文为该命中项目 |
| OCR 识别的非空 `no` 与 `old_no` 不一致 | Step 3.6b 用 `AskUserQuestion` 弹窗四选一（重选项目/重传截图/**识别可能有误继续下一步**/取消）；选“继续下一步”则照原值传给 UI（不得覆盖）→ UI 把 `no` 标红并阻止提交 → 用户改成一致后放行 |
| UI 回调落在**新会话**、会话内 `selected_old_no` 已丢失 | **无影响**——参数已由单步脚本在调 UI 前完成实时守卫并缓存，提交在 UI 内直接完成 |
| OCR 其他字段无法识别 | 按类型填零值传给 UI（string→`""`/int32→`0`/float→`0`），由用户在页面里补 |
| 用户只上传了主表，没传合作方 | `has_partner=0`、`partner_type=0`、`partner_name=""` 传给 UI，由用户在页面确认 |
| 起止时间已过期 | 由 UI 前端 + 后端接口校验拦截，提示"该备案号已过期, 无法作为新备案号提交" |
| 用户在 UI 里改了`no` 之外的字段 | 允许，UI 内提交时透传（`no`仍须等于 `old_no`）|
| 提交成功后用户想立即再改同一项目 | 该项目已进入审批中（audit_status=2），下次列表刷新后 Step 2 守卫会拦截，符合预期 |
| 用户中途关闭 UI 页面不提交 | 不会收到命名步骤回调；会话保留本次 `caller_expert_id` / `data_cache_id`，用户说“重新打开”时直接用这两个值再次调用 UI，不重跑脚本、不重新 OCR |
| 用户中途选择"退出" | 保留已提交的更新（已生效），回归预警专家的意图询问 |

## 参考文件

- [`references/tools/fundraising_program_input.md`](./references/tools/fundraising_program_input.md) — ⭐ 唯一 `record_input.json` 与最终业务体契约
- [`references/tools/open_fund_raising_program_update_ui.md`](./references/tools/open_fund_raising_program_update_ui.md) — UI 顶层两字段契约
- `../alert-ocr/references/llm-vision-record.md` — schema 2.0 精简视觉输入 Prompt
- [`references/scripts/run_record_ui.py`](./references/scripts/run_record_ui.py) — ⭐ 唯一业务脚本入口，完成校验、实时守卫、可选慈善中国查询、缓存和 UI 两字段输出
- [`references/scripts/README.md`](./references/scripts/README.md) — 单步脚本状态与慈善中国字段映射说明

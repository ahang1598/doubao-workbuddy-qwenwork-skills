---
name: alert-cert-forms
description: 专家的证件更新流程能力。负责社会组织法人登记证书/慈善组织公开募捐资格证书/负责人身份证的更新全流程：入口守卫（has_pending_review）→ 展示到期清单 → 引导批量上传 → 类型粗判 + 云OCR → 排队检查(建议一起提交) → 调 open_org_cert_update_review_ui 调起前端确认页 → 用户在 UI 内直接提交 → UI 回 submit.next_step 通知 Agent 进入提交后流程（命名步骤「提交证件到远程」）。
---

# 证件更新流程

## ⛔ MCP 调用已封装为脚本（AI 禁止裸调 MCP 工具）

> 本专家所有 MCP 工具调用已封装为 `skills/<skill>/references/scripts/` 下的 Python 脚本（共享客户端 `skills/_common/mcp_client.py`）。AI **只通过 `execute_command` 运行脚本获取结果，禁止直接裸调 MCP 工具**。
>
> 脚本已内置：参数构造（字段类型 / 嵌套结构 / repeated 裸数组等）、入口守卫（has_pending_review / 审批中）、一致性校验（no≠old_no / 图片域名）、失败上抛（绝不降级）。
> 本地 `references/tools/<tool>.md` 仍为脚本行为的权威文档，改动脚本须同步更新。


## 概述

"证件更新"能力，接管以下证件的更新流程（对应 `OrgCertUpdateType` 枚举）：

| cert_type | 名称 | 备注 |
|-----------|------|------|
| `1` | 社会组织法人登记证书（`charitable_person`）| 所有机构类型都会有 |
| `2` | 慈善组织公开募捐资格证书（`charitable_public`）| 仅公募机构有 |
| `3` | 负责人身份证（`idcard`）| 服务端按机构类型判定为法人身份证 or 专项基金负责人身份证 |

**核心特征**：
- **入口守卫** — `has_pending_review=true` 时直接告知用户，不引导上传截图（审批中禁提）
- **先传后识别** — 用户直接上传截图，由 alert-ocr 自动判定类型
- **批量收集，一次提交** — 用户可完成多类证件的 OCR 后一次性提交 `update_org_cert(cert_types=[...])`
- **UI 内直接提交** — OCR 结果经 `build_cert_ui_params.py` 封装后调起 UI，用户核对/修改后**在 UI 内直接完成提交**；UI 回 `submit.next_step` 通知 Agent 进入提交后流程（命名步骤「提交证件到远程」）
- **整组覆盖语义** — 一类证件出现在 `cert_types` 中则该类全部字段被入参覆盖，Skill 必须把该类所有 K-V 填齐

## 触发场景

由专家在以下情境加载：
- 用户直接对话："我要更新证件"、"证件到期了怎么办"等

上下文（可能已知）：
- 待更新证件清单（含 `cert_type` +剩余天数）—— 通过 `../alert-info-fetcher` 调`query_todo_detail.py` 获取

## 工作流程

### Step 0: 入口守卫（`has_pending_review`）

> ⭐ **入口守卫已由「任务零」统一负责**：`query_todo_detail.py` 内置 `updatable` / `has_pending_review` 守卫，只有真正可处理的项才会进 `todo_cards`，因此正常进入本任务时 `has_pending_review` 必为 `false`。本步骤仅作**独立直接加载时的兜底**。

若本 skill 未走任务零、被独立直接加载，则先确认当前无审批中申请单：

| `has_pending_review` | 行为 |
|----------------------|------|
| `true` | ⛔ **直接告知用户并结束**，**不引导上传截图**，**不调 `update_org_cert`** |
| `false` | ✅ 正常进入 Step 1 |

**`true` 时的话术**：
```
当前机构信息有申请单待审批, 审批完成后才能提交证件更新。
```

**⛔ 硬约束**：`has_pending_review=true` 时**绝对不能**调用 `update_org_cert`（无论 `cert_types` 里放什么），也不能引导用户走OCR 消耗时间。

### Step 1: 提示上传证件原图

> ⭐ 进入本任务第一时间（发起任何工具调用之前）**MUST 先告知用户下一步预期**："已为您进入证件更新流程，**下一步需要您上传证件照片**，上传后我会自动识别证件类型和关键字段"。⛔ 不得静默发起工具调用只让用户看"过程消息"。

**到期清单**：由「任务零」`query_todo_detail.py` 提供（含 `cert_type` + 剩余天数），本步骤直接展示。

**⚠️ 身份证标签**：根据首次查询脚本输出的 `org.type_of_organization` 决定（等价于 `institution_type`，脚本已随 `org` 字段返回）：
- `type_of_organization ∈ {1, 2}` → "法人身份证"
- `type_of_organization == 3` → "专项基金负责人身份证"

### Step 2: 类型粗判 + 云 OCR（每张图独立处理）

对每张上传的图，加载 `skills/alert-ocr`，走两步：

1. **类型粗判**（`strategy_id: cert_type_detection`，LLM 视觉）→ 参考 [`../alert-ocr/references/cert-type-detection.md`](../alert-ocr/references/cert-type-detection.md)
   - `cert_type_detection` 只是策略标签，不是工具、脚本或 MCP 名称；每个唯一图片路径读取一次，当前模型直接按 Prompt 粗判，禁止搜索所谓视觉工具
   - 输出 `cert_type ∈ {1, 2, 3-front, 3-back, unknown}`
   - `unknown` → 提示用户重传，不进入云 OCR

2. **云 OCR 一键 pipeline**（`engine_type: cloud_cert_pipeline`）：一键运行脚本完成「取临时凭证 + 上传 + 提交检测 + 轮询」全链路（详见 [`../alert-ocr/SKILL.md`](../alert-ocr/SKILL.md)）
   ```bash
   cd skills/alert-ocr/references/scripts && python3 remote_ocr.py <文件> --private 0|1 --ocr_type 0|1
   ```
   - 身份证（`3-front`/`3-back`）→ `--private 1 --ocr_type 1`（私有桶，COS 原始域名）；其他证件 → `--private 0 --ocr_type 0`（公有桶，CDN 域名）
   - `--private` 与 `--ocr_type` **必须同为 0 或同为 1**（身份证=1、其它=0），否则脚本直接报错
   - 脚本返回上传链接 + K-V 识别结果；**30 秒无结果即失败退出（不降级）**，需重识别时重新运行本脚本

### Step 3: 类型判定结果分支

| 判定结果 | 处理方式 |
|---------|---------|
| 明确 & 校验通过 | 暂存到会话内的 `cert_kv_map[cert_type]`；`cert_types_done += { cert_type }` |
| 校验异常（K-V 字段不符合类型格式）| 提示"疑似类型识别错误，请确认"，展示 OCR 结果 + 让用户手动选类型（**MUST NOT 就此终止流程不给继续路径**——用户手动选定类型后仍可继续走 Step 4/Step 5，最终交给 UI 核对；只有 Step 5 之后「提交证件到远程」的兜底校验才能真正中止提交）|
| `cert_type=3` 但只有单面（正/反）| 暂存半份 K-V，提示"请补充身份证另一面"；**正反齐了才计入 `cert_types_done`** |

**⚠️ 身份证正反面合并**：
- 正面提供：`name` / `id_card` / `idcard_front`
- 反面提供：有效期起/ 有效期止 / 长期标记 / `idcard_back`
- 两面齐后由 Skill 层拼接 `id_card_validity`（格式 `YYYY-MM-DD~YYYY-MM-DD` 或 `YYYY-MM-DD~长期`，见 `references/idcard.md`）

### Step 4: 排队检查（一起提交）

若到期清单里还有其他证件未上传，用 `AskUserQuestion` 弹出可点击二选一（**不得**用纯文本代替）：提示语"提交后需等运营审核通过才能更新其他证件，建议一起提交"，选项为「继续上传其他证件」/「直接提交」。

```
AskUserQuestion(
  question: "提交后需等运营审核通过才能更新其他证件, 建议一起提交。是否继续上传其他证件？",
  header: "提交确认",
  multiSelect: false,
  options: [
    { label: "[继续上传其他证件]回到上传步骤补全剩余证件", description: "[继续上传其他证件]回到上传步骤补全剩余证件" },
    { label: "[直接提交]仅提交已识别完成的证件", description: "[直接提交]仅提交已识别完成的证件" }
  ]
)
```

- 用户选"继续上传其他证件" → 回 Step 2 上传剩余证件
- 用户选"直接提交" → 进入 Step 5（本步骤前的识别结果只含已完成的类）
- ⚠️ **目的**：审批中禁提（`has_pending_review`），一旦提交进入审批，剩下的证件必须等审批完成后才能再更新，所以要主动提示"一起提交"，避免用户误以为可以分多次提交

### Step 5: 调起证件更新确认 UI（`open_org_cert_update_review_ui`）

**触发时机**（满足其一）：
- **全部到期证件都已识别完成**（用户本轮上传并 OCR 的证件已覆盖任务零给出的到期清单，无遗漏）
- **用户在 Step 4 明确选择「直接提交」**（仅提交已识别完成的证件；⚠️ 单面身份证等未完整识别的类，按下方红线整体排除出 `cert_types`，不得只传单面）

**核心动作**：把 `cert_types` + 各块 K-V 组装成 `org_cert_update_review` 业务体（JSON 文件，字段格式见 [`references/tools/org_cert_update_review_input.md`](./references/tools/org_cert_update_review_input.md)），运行封装脚本（脚本做**守卫复查 + 类/块一致性 + 身份证域名校验**，成功时把 UI 入参小 JSON（仅 `caller_expert_id` + `data_cache_id` 两字段）写入 `--output` 文件）：

> ⛔ **禁止不跑脚本、自己读 `inputSchema` 拼参直接调** `open_org_cert_update_review_ui`。正确流程（三步）：
> 1. AI 先把已完成 OCR 的证件 K-V 打包成 `org_cert_update_review` 业务体（JSON 文件）；⚠️ `cert_types` 必须是裸 int 数组（如 `[1, 3]`），禁止包成对象——脚本会强制校验
> 2. 运行下方脚本生成 UI 入参文件（`--output`）
> 3. **读取 `--output` 文件内容，作为 `open_org_cert_update_review_ui` 工具的 `parameters` 调用**（⛔ 不要自行重新组装、不要读 `inputSchema`、不要往里追加业务字段）

```bash
cd skills/alert-cert-forms/references/scripts && python3 build_cert_ui_params.py --json-file <org_cert_update_review.json> [--output <cert_ui_params.json>]
```

**红线（MUST 遵守）**：
- ⛔ 未完成 OCR 的类不进 `cert_types`，其块也不传，更不传空对象占位 —— 否则**整组覆盖语义会清空后端该类数据**
- ⛔ `cert_types` 数量为 0 时**禁止**调用 `open_org_cert_update_review_ui`
- ⛔ 身份证**正反面都齐**才能把 `3` 放进 `cert_types`；身份证 URL 必须用 **COS 原始域名**（私有桶），其余证件用 CDN 域名

**调起后行为**（对齐 alert-expert 编排层「命名步骤：提交证件到远程」）：
- ✅ `open_org_cert_update_review_ui` 调用返回成功后，本轮立即结束——**只输出一句极简提示**（如"证件信息已识别完成，已为您打开确认页面，请在页面中确认并提交"），**不再输出任何其它文字或发起任何工具调用**
- ✅ 然后**等待 Agent 收到 `submit.next_step` 重新调度执行命名步骤 `提交证件到远程`**（⛔ 不是"UI 直接结构化回调"）
- ❌ **MUST NOT** 自行轮询 / 猜测用户是否已提交
- ❌ **MUST NOT** 收到 `submit.next_step` 后再次调用任何提交接口（提交已在 UI 内完成，命名步骤「提交证件到远程」只进入提交后流程）

### 命名步骤：`提交证件到远程`（UI 内提交后由 Agent 依据 `submit.next_step` 重新调度触发，进入提交后流程）

> ⭐ **步骤名 MUST 逐字符为 `提交证件到远程`** —— `submit.next_step` 固定文案里点名这个名字，改一个字 Agent 就没法正确重新调度到本步骤。

**触发语义**：用户在 UI 页面点"提交"时，**提交动作已由 UI 内直接完成**（后端 `update_org_cert` 接口在 UI 侧校验并提交）。UI 随后回一句 `submit.next_step` 文案给 Agent，**仅作为"已提交完成"的通知信号**，不携带需要 Agent 再处理的数据。

**执行**：收到 `submit.next_step` 后，**MUST NOT 再调用任何提交接口**（提交已在 UI 内完成），直接进入提交后流程：
1. **Step 6**：向用户输出成功话术（已提交 N 项证件更新、进入审核）
2. 若还有未提交的证件，按 Step 6 提示待审核完成后再次进入

> ⚠️ **覆盖语义**：`cert_types` 含的每类必须全填，未填字段会被覆盖为空——此语义由 UI 内提交时后端接口按 `cert_types` 覆盖处理，Agent 无需干预。

### Step 6: 提交后话术

**提交成功**：
```
✅ 已提交 [N] 项证件更新, 预计运营 1-3 个工作日审核。
审批完成前无法再次提交证件更新。
```

若 `cert_types_done ⊊ cert_types_pending`（用户选了"就先提交"，还有未上传的；`cert_types_pending` = 任务零给出的到期清单里的全部 `cert_type` 集合，`cert_types_done` = 本轮已完成 OCR 并计入的 `cert_type` 集合）：
```
⚠️ 本次未提交的证件仍在到期清单中:
- [missing 的可读标签]
待运营审核完成后, 您可再次进入本流程更新剩余证件。
```

> ⚠️ 提交失败由 UI 页面自行提示处理（Agent 不感知、不处理失败分支）；Agent 收到 `submit.next_step` 即视为提交成功。

## 铁律

- ❌ `has_pending_review=true` 时仍引导用户上传截图 （应直接告知结束）
- ❌ 让用户"先选证件类型再传图"（新流程反了）
- ❌ 用 LLM 视觉替代云OCR 做主识别（会失去 K-V 结构化能力）
- ❌ K-V 校验异常时不提示用户就往前走
- ❌ 收到 `submit.next_step` 后再次调用任何提交接口（提交已在 UI 内完成）
- ❌ 跳过 UI 二次确认，直接用 OCR 原始 K-V 提交（用户没机会核对/修改）
- ❌ `cert_types` 中包含某类但对应字段块**部分为空**（覆盖语义会导致空字段被清空）
- ❌ `cert_types` 中**不包含**某类但仍传对应字段块（误伤覆盖）
- ❌ `permanent=1`（长期）时仍传 `end_date` 非空值
- ❌ 身份证走公有桶 / 用 CDN 域名（必须私有桶 + COS 原始域名）
- ❌ 法人证书 / 公开募捐证书走私有桶（应用公有桶 + CDN 域名）
- ❌ 自行区分"法人身份证"vs"专项基金负责人身份证"（统一走 `idcard` 字段块，服务端判定）
- ❌ `id_card_validity` 用旧格式 `YYYY.MM.DD-YYYY.MM.DD`（应用 `~` 分隔的新格式）
- ❌ 提交成功后立即再提交另一类（此时 `has_pending_review` 已变 true，会被守卫拦截）
- ❌ 用户上传后未走完整流程就先发到远程存储（COS 上传是必需的写外部动作，但只在 alert-ocr Step 2 触发；`update_org_cert` 之前不再有远程写）
- ❌ 在调起 UI（Step 5）之前，把 OCR 识别问题（类型不明确、K-V 校验异常等）处理成"拒绝调用 UI/终止流程"的硬阻断且不给继续路径——真正的强制校验由 UI 前端 + 后端接口在提交时完成；调起 UI 前最多"提示 + 让用户手动纠正/确认后继续"
- ❌ 不调 `open_org_cert_update_review_ui`，改在对话里让用户逐字段核对

> 📌 语法级约束（`cert_types` 裸 int 数组、int32 传数字、图片域名、身份证正反面）已写入 [`references/tools/org_cert_update_review_input.md`](./references/tools/org_cert_update_review_input.md)，由 `build_cert_ui_params.py` 强制，无需在此重复。

## 特殊情况处理

| 情况 | 处理方式 |
|------|---------|
| 用户一次上传多张图 | 逐张走 alert-ocr，逐张校验；全部识别完后统一进入 Step 4 完成度检查 |
| 用户上传的证件不在待更新清单中（如上传了非到期的）| 提示"识别到 [X], 但暂不在本次到期清单中, 是否要一并更新?"，用户同意 → 加入 done；用户拒绝 → 忽略 |
| 云 OCR 三步 pipeline 失败（上传/提交/轮询任一步）| 由 alert-ocr 返回 `failed_at_step`，本skill 提示"识别服务暂时不可用, 请重试" |
| 身份证只上传了一面 | 提示"请补充身份证[正/反]面"，暂不计入 `cert_types_done`；`3` **不进 `cert_types`**，`idcard` 块也不传 |
| 用户在 UI 确认页大量修改字段 | 允许修改，UI 内提交时后端接口做格式校验，不做内容对错判断（由后端审核负责）|
| **UI 回调落在新会话** | **无影响** —— 提交在 UI 内直接完成，不依赖 Agent 会话上下文 |
| **UI 回传的图片 URL 为空** | 由 UI 前端 + 后端接口校验拦截，**MUST NOT** 用空 URL 提交（会清空后端已有证件图）|
| **用户在 UI 停留期间他人提交了申请单** | 由后端接口在提交时复查 `has_pending_review` 发现为 `true` → 拦截中止 |
| **用户中途关闭 UI 页面不提交** | 不会收到命名步骤回调；Skill 保持等待，用户可回对话说"重新打开"再走 Step 5 |
| 用户中途选择"取消" | 清空会话内的 cert_kv_map，回归预警专家的意图询问 |
| 提交后用户想立即再提交一类 | 告知"当前机构信息有申请单待审批, 审批完成后才能提交证件更新"，回归意图询问 |

## 数据主权与隐私合规

- **用户上传的证件截图**：只在会话内使用（走 alert-ocr → COS 上传是必需的写外部动作，但不落地到 workbuddy 侧）
- **OCR 中间结果（K-V JSON）**：只在会话内展示给用户核对（通过 UI 二次确认），用户在 UI 内点"确认提交"即完成提交
- **身份证 K-V**（含身份证号、姓名）：属于敏感信息，仅在当前上传者本人的会话内展示，不跨会话缓存

## 参考文件

- [`references/tools/org_cert_update_review_input.md`](./references/tools/org_cert_update_review_input.md) — ⭐ **`build_cert_ui_params.py` 的 `--json-file` 输入格式**（`org_cert_update_review` 业务体：3 个块的字段表、类型硬约束、输入文件示例）
- [`references/tools/open_org_cert_update_review_ui.md`](./references/tools/open_org_cert_update_review_ui.md) — ⭐ **调起证件更新确认 UI**（顶层两字段入参、缓存完整 JSON 形状、"结构里没有的两样东西"、UI 主校验职责、回调机制）
- [`references/cert-kv-validation.md`](./references/cert-kv-validation.md) — K-V 合理性校验规则（用于Step 2 类型自检）
- [`references/legal-registration.md`](./references/legal-registration.md) — 社会组织法人登记证书字段块（`cert_type=1`）
- [`references/fundraising-cert.md`](./references/fundraising-cert.md) — 慈善组织公开募捐资格证书字段块（`cert_type=2`，仅公募机构）
- [`references/idcard.md`](./references/idcard.md) — 负责人身份证字段块（`cert_type=3`，含正反面合并 + `id_card_validity` 拼接）
- OCR 引擎：[`../alert-ocr/SKILL.md`](../alert-ocr/SKILL.md)（三步 pipeline + 类型粗判）

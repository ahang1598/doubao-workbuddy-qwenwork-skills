---
name: 1688商品运营
name_en: 1688-product-manage
displayName: 1688商品运营
version: "2.1.0"
description: |
  1688 商品运营能力。支持 AI 智能发品、AI 标题优化（单个/批量）、AI 主图优化（四阶段）、商品上架/下架。
  本技能采用「MCP 工具调用 + Python 后处理脚本」模式：远程 API 全部交给 MCP，原脚本中的参数校验、状态保存、响应解析、格式化输出等复杂后处理仍由 Python 执行。
description_zh: 基于 MCP 工具执行商品运营动作，并通过 Python 保留原脚本后处理口径
user-invocable: true
argument-hint: 告诉我你要发布商品、优化标题/主图，或上架/下架哪个商品
---

# 1688 商品运营

## 职责边界

本技能采用「MCP 工具调用 + Python 后处理」模式：

- 账号鉴权、Token 刷新、OAuth 授权全部由 MCP 连接器 `ali1688-seller` 管理。
- Agent 不处理 AK，不读取/保存 AK，不调用 `configure`、`get_ak`、`change_ak`、`authorize` 等授权命令。
- 远程 API 调用全部通过 MCP 工具完成，禁止通过 Python 脚本直接调用 HTTP API。
- Python 脚本仅负责原有后处理逻辑：图片压缩、响应解析、标题长度校验、状态保存、prompt 拼装、主图位次合并、上下架成功态兼容、错误文案翻译和用户输出格式化。
- MCP 返回后的复杂处理必须调用 `post_process_action`，不得完全交给 AI 自行推断。

## MCP 连接器

- 连接器名称：`ali1688-seller`
- 协议：Streamable HTTP
- 本技能使用工具：
  - 发品链路：`image_bank_upload_picture`、`ai_publish_by_imageurl`、`ai_publish_save_tair`
  - 标题链路：`cbu_offer_query_tool`、`cbu_image_analyse_tool`、`cbu_skill_change_subject`
  - 主图链路：`cbu_offer_query_tool`、`cbu_image_analyse_tool`、`cbu_image_generation_and_editing_tool`、`image_bank_change_url_for_offer`、`cbu_skill_change_main_image`
  - 上下架：`product_cancel_offer`、`product_repost_offer`

## 本地后处理脚本

- 脚本入口：`python3 {baseDir}/cli.py post_process_action --input-file <payload.json>`
- 输入：包含 `action` 和相关 MCP 返回/参数的 JSON
- 输出：标准 JSON：`{"success": bool, "markdown": str, "data": {...}}`
- 用户可见内容：优先直接使用输出中的 `markdown`

示例：

```json
{
  "action": "offer_operation_result",
  "operation": "cancel",
  "offerIds": ["123456"],
  "mcp_result": {}
}
```

支持的 `action`：

| action | 用途 |
|---|---|
| `compress_image` | 本地图片压缩并转 base64，供 MCP `image_bank_upload_picture` 使用 |
| `publish_candidates` | 解析 `ai_publish_by_imageurl` 返回，保存发品上下文并展示同款候选 |
| `publish_save_result` | 解析 `ai_publish_save_tair` 返回并拼接发品链接 |
| `title_context` | 解析商品查询和图片解析结果，生成标题优化上下文 |
| `title_suggest` | 校验并暂存 AI 推荐标题 |
| `title_apply_result` | 解析 `cbu_skill_change_subject` 返回并输出应用结果 |
| `batch_title_suggest` | 批量校验并暂存标题 |
| `batch_title_apply_result` | 批量解析标题应用结果 |
| `image_prepare` | 解析商品主图和图片解析结果，初始化主图优化上下文 |
| `image_customize` | 校验 `size/background/text_selling_points` 并拼装 prompt |
| `image_generate_result` | 解析图生图结果，保存生成态 |
| `image_apply_plan` | 根据选择序号生成待转换图片 URL 列表 |
| `image_apply_result` | 解析图片转换/主图修改结果，按原位次合并主图 |
| `offer_operation_result` | 解析上架/下架结果，兼容 `successs` 拼写并翻译错误 |

## 严格禁止 (NEVER DO)

- 不得执行越权高风险操作：商品删除、店铺主体变更、资金提现、绕风控、侵权/违禁发布等。
- 不得编造任何 MCP/API 结果字段，如 `categoryId`、`sameItemId`、`taskId`、`relativeUrl`、`success`。
- 不得泄露内部敏感字段：`sameItemId`、`tkItemIds`、`categoryId`、`userId`、`aigcTime`、`relativeUrl` 等。
- 不得在用户可见内容中输出内部状态文件路径、脚本源码路径、内部接口路径。
- 不得调用旧 Python 业务命令通过 HTTP 拉取或修改数据，如 `product_publish`、`ai_title_modify`、`ai_image_improve`、`product_cancel_offer`、`product_repost_offer`。
- 不得调用 AK/OAuth 管理命令；鉴权异常只提示用户检查 `ali1688-seller` 连接器授权状态。

## 意图判断

### 触发本技能

- 发布商品/批量发品：发品、上新、图片发品、以图发品、批量上新。
- 标题优化：改标题、优化标题、批量改标题、AI 标题。
- 主图优化：改主图、优化主图、AI 主图。
- 上下架：上架、下架、恢复销售、停售。

### 不触发本技能

- 选品找货、同款搜索、比价，应走 `1688-product-find`。
- 店铺经营分析、健康诊断，应走 `1688-shop-operate`。
- 下单、支付、物流、售后、库存价格管理。

## 核心工作流

### 1. AI 智能发品

支持三种模式：

| 模式 | 说明 |
|------|------|
| 本地图片发品 | 压缩图片（≤1MB）→ 上传图片银行 → AI 识图 → ⏸ 选品 → 生成发品链接 |
| 图片链接发品 | 直接使用 URL → AI 识图 → ⏸ 选品 → 生成发品链接 |
| 批量发品 | 多图逐张上传 + 识图 → ⏸ 汇总选品 → 生成发品链接清单 |

#### 单图发品流程

```
（本地：压缩 → 上传图片银行）→ AI识图 → 保存上下文 → ⏸ 等商家选品 → 保存选品 → 生成发品链接 → ⛔ 流程结束
```

**步骤 1 — 获取图片 URL**
- 本地图片：先调用 Python 后处理 `compress_image`（输入 `image_path`），再把 `data.imageName` / `data.base64Str` 传给 MCP `image_bank_upload_picture`，从返回中取图片 URL。
- 图片链接：直接使用用户提供的 URL。
- ✅ 图片只能上传至图片银行（cbu01.alicdn.com），对外 URL 须确保来源为图片银行或合法公开 URL。

**步骤 2 — AI 识图 + 保存上下文**
- 调用 MCP `ai_publish_by_imageurl(picUrl)`。
- 把返回交给 Python 后处理 `publish_candidates`：解析 `dataJson`，提取 `categoryId/categoryName/tkItemIds/effectiveItemIds`，过滤展示字段并写入状态文件 `.publish_state.json`。
- 无同款时直接返回默认发品页引导，**不再保存上下文**，流程终止。
- ⛔ **有同款时必须进入步骤 3 展示候选并等待商家选择**，严禁自动选品或跳过。

**步骤 3 — 展示同款，等待商家选择（⛔ 必须停下）**
- 用 Python 输出的 markdown 展示同款，使用序号（1、2、3...）。
- ✅ 标题、卖点必须展示；主图视对话空间决定，若展示须用 `![同款N](url)` 渲染。
- ⛔ **即使只有 1 个候选，也必须等商家明确选择后才能继续，严禁 Agent 自行选品。**
- ✅ **正确做法**：展示候选后在对话中等待商家回复（如"选第 2 个"），收到明确选择后才进入步骤 4。
- ❌ **错误做法**：识图后不展示候选直接调用 `ai_publish_save_tair`，或自动选第一个，或以"之前已处理过"为由跳过展示。

**步骤 4 — 保存选品**
- Agent 调用 MCP `ai_publish_save_tair`，参数取自 `.publish_state.json` 中商家选定的同款。
- 把返回交给 `publish_save_result`，Python 解析 `aigcSelectCategoryTime` 并拼接发品跳转链接。

**步骤 5 — 输出链接（流程结束）**
- 渲染发品跳转链接，提示「补充信息后自行发布」。
- ⛔ 链接展示后流程立即结束，**不得轮询**发布结果。
- 同时提示：发布后可用「AI 标题优化 / AI 主图优化」继续提升商品质量。

#### 单张发品工作流示例

**❌ 错误流程（跳过选品确认）：**
```
Agent: 上传图片 → 调用 ai_publish_by_imageurl → 获得候选
Agent: 不展示给用户，直接调用 ai_publish_save_tair（默认选第 1 个）→ 输出链接
```

**✅ 正确流程（必须等待用户选择）：**
```
Agent: 上传图片 → 调用 ai_publish_by_imageurl → 获得候选
Agent: 展示所有候选（序号 + 标题 + 属性 + 主图），请用户选择
用户: "我选第 2 个"
Agent: 基于用户选择调用 ai_publish_save_tair → 输出链接
```

#### 批量发品流程

```
逐张获取URL → 逐张AI识图 → 紧凑展示同款 → ⏸ 等商家选方式 → 批量保存选品 → 生成发品链接清单 → ⛔ 流程结束
```

- 多图逐张走「步骤 1 + 步骤 2」，识图结果统一汇总到 `.batch_publish_state.json`。
- 单张失败不中断；**无同款 / 识图失败图片不得进入可选集合**，也不展示。
- 紧凑展示时每张图只展示首选同款（第 1 个候选），并标注「同款数：N」。
- ⛔ 必须等商家选择「全部默认第一个」或「逐图指定序号」，严禁自行决策。
- 批量保存后由 Python 统一生成发品链接清单（含跳转链接、过期时间提示）。

#### 状态文件生命周期

| 文件 | 创建 | 读取 | 清理 |
|------|------|------|------|
| `.publish_state.json` | 步骤 2 完成 `publish_candidates` 时写入 | 步骤 4 保存选品时读取同款数据 | 步骤 5 链接生成后失效（被下一次发品覆盖） |
| `.batch_publish_state.json` | 批量识图汇总后写入 | 批量选品时读取 | 链接清单生成后失效（被下一次批量识图覆盖） |

#### 模块特定禁止事项

| 规则 | 说明 |
|------|------|
| 禁止跳过选品确认 | 任何模式下都必须等商家明确选择，单候选也不得自动选品 |
| 禁止 Agent 自行选品 | 不得以「高度相似」等理由替商家决策 |
| 禁止纯文本 URL | 所有图片必须用 `![alt](url)` 渲染 |
| 禁止轮询发布结果 | 链接生成后流程结束，不得轮询 |
| 禁止单图/批量参数混用 | 单图与批量两条链路的状态文件、字段独立，不可交叉读写 |

#### 模块特定异常处理

| 异常 | 处理 |
|------|------|
| 文件不存在 / 路径错误 | 提示商家确认本地图片路径 |
| 图片格式不支持 | 仅支持 JPG/PNG/WEBP，超限走压缩降质 + 0.8 倍缩放，最多 5 轮 |
| AI 无法识别 | 引导手动发品页 `https://offer-new.1688.com/select.htm`，不保存上下文 |

---

### 2. AI 标题优化

基于「商品原标题 + 首图解析结果」由 LLM 生成新标题，支持单商品和批量两种模式。

#### 流程总览

```
拉取上下文 → Agent生成标题 → 暂存AI标题 → ⏸ 商家确认 → 应用标题（AI / 自定义）
                                              （⛔ 必须停下）
```

#### 单商品流程（三阶段）

**阶段 1 — 拉取上下文**
1. MCP `cbu_offer_query_tool(offerId)` 获取原标题和主图。
2. 仅对**首图**调用 MCP `cbu_image_analyse_tool(type="ecommerce_content_parsing", imageUrlList=[首图])`，提交后通过 MCP 轮询 `taskId`。⛔ 严禁多图解析，多图必超时。
3. 把商品查询结果 + 解析结果交给 Python 后处理 `title_context`，写入 `.title_state.json`。
4. 解析结果只采纳以下完成字段：`text_region_summary`、`selling_points_visible`、`composition_summary`。

**阶段 2 — 暂存 AI 标题**
1. Agent 基于上下文生成新标题。**若原标题与图片偏差过大，必须彻底抛弃原标题，以图片解析为准。**
2. 调用 Python 后处理 `title_suggest`，由 Python 校验长度并暂存到 `.title_state.json`。
3. 把 Python 返回的 markdown 展示给商家。

**阶段 3 — ⏸ 商家确认 → 应用标题**

展示 AI 推荐标题，给出两个选项：
1. 直接使用 AI 标题 → MCP `cbu_skill_change_subject(offerId, subject=AI标题)`，返回交给 `title_apply_result`。
2. 自定义标题 → 同样调用 MCP `cbu_skill_change_subject`，subject 为商家自定义文案。

> ⛔ 必须停下等商家明确回复，严禁未经确认自行应用标题。

Python 按 `data.success`（优先）/ 顶层 `success` 判定结果。

#### 批量流程

1. 批量上下文：逐个调用 MCP 查询 + 解析（建议每批 ≤ 10），失败项标记后跳过，不中断整体。结果汇总到 `.batch_title_state.json`。
2. 批量暂存：Agent 调用 Python 后处理 `batch_title_suggest`，超长标题进入 `skipped`，不阻塞其他标题。
3. ⏸ 表格化展示批量 AI 标题给商家，给出三个选项：
   - 全部应用 AI 标题
   - 部分调整（AI + 自定义混合）
   - 重新生成
4. 应用：逐个调用 MCP `cbu_skill_change_subject`，最终交给 `batch_title_apply_result` 汇总成功/失败表。

> ⛔ 严禁未经确认自行批量应用标题。

#### 标题长度规则（突出）

- 上限：**30 字符**。
- 计算：中文/全角符号 = **1**，ASCII（英文/数字/半角符号）= **0.5**。
- 要求：尽量写满 30 字符，**不得包含重复词语**。
- 校验时机：`title_suggest` / `batch_title_suggest` 暂存阶段自动校验。
- 超限行为：单商品直接报错；批量模式超长项进入 `skipped`，其余继续。

#### 状态文件生命周期

| 文件 | 创建 | 读取 | 清理 |
|------|------|------|------|
| `.title_state.json` | 阶段 1 `title_context` 写入；阶段 2 `title_suggest` 更新 | 阶段 3 应用阶段读取暂存标题 | 应用结果输出后失效（被下一次覆盖） |
| `.batch_title_state.json` | 批量上下文写入；批量暂存更新 | 批量应用读取 | 批量结果汇总后失效 |

#### 模块特定禁止事项

| 规则 | 说明 |
|------|------|
| 禁止跳过商家确认 | 暂存后必须停下等商家选择，不得直接应用 |
| 禁止自行批量应用 | 批量必须先展示表格再确认 |
| 禁止多图解析 | 仅解析首图，多图必超时 |
| 禁止忽略偏差 | 原标题与图片偏差过大时必须以图片为准 |
| 禁止超限标题落库 | `title_suggest` 校验失败必须报错或写入 `skipped` |

#### 模块特定异常处理

| 异常 | 处理 |
|------|------|
| 商品查询失败 | 提示检查 ID 是否正确、是否属于当前账号 |
| 图片解析提交/轮询失败 | 重试或提示稍后再试，30 秒超时不伪造结果 |
| 标题长度超限 | 单商品报错；批量进入 `skipped` |
| 未找到 AI 标题 | 提示先拉取上下文并暂存 |
| 修改标题失败 | 输出 MCP 错误，提示检查商品归属 |

---

### 3. AI 主图优化

对商品 1~5 张主图做 AI 背景/场景优化，逐张独立，单图失败不影响其他。`size` 仅支持 `1:1` / `3:4`。

#### 四阶段流程图

```
prepare → customize → ⏸ 等商家确认 → generate → ⏸ 等商家确认 → apply → ⛔ 流程结束
         （Agent推荐场景）  （回合②）              （回合③）        （回合④）
```

#### 回合 ① prepare + customize（连续执行，不停顿）

1. **prepare**：MCP `cbu_offer_query_tool(offerId)` 取主图列表 → MCP `cbu_image_analyse_tool` 逐张解析 → Python 后处理 `image_prepare` 初始化每张图默认配置（`size=1:1`、`text_selling_points=""`、`scene=""`，默认 prompt 为 `做一张1688商品电商的主图,1:1比例`）。
2. **customize**：Agent 为每张图推荐**具象场景**（⛔ 禁止「简约背景」等空泛描述），通过 `--customize` 的 `background` 字段注入。
3. 调用 Python 后处理 `image_customize`：
   - 字段白名单仅 `size` / `background` / `text_selling_points`，其他字段（`prompt`、`selling_points` 等）直接报错。
   - prompt 由 Python 按规则拼装，**不接受完整 prompt 注入**。
4. 聊天框输出推荐 prompt 表（含 prompt / 文字卖点 / 场景列）。
5. **立即进入回合 ②**，不等待。

**prompt 拼装规则：**

| 字段组合 | 拼装结果 |
|----------|----------|
| 仅比例 | `做一张1688商品电商的主图,{size}比例` |
| 比例 + 场景 | `做一张1688商品电商的主图,{size}比例，背景换成{background}` |
| 比例 + 卖点 | `做一张1688商品电商的主图,{size}比例，突出{text_selling_points}的文字卖点` |
| 比例 + 卖点 + 场景 | `做一张1688商品电商的主图,{size}比例，突出{text_selling_points}的文字卖点,背景换成{background}` |

#### 回合 ② 询问商家确认（⛔ 必须停下）

输出两个选项：
1. 接受推荐，执行生成。
2. 调整某些图的 比例 / 文字卖点 / 场景。

- 商家选 1 → 进入回合 ③。
- 商家选 2 → 用商家给的参数重跑 `image_customize` → 重新渲染 prompt 表 → 回到回合 ②。

> ⛔ 无论何种情况（哪怕只有 1 张图、场景已合理），都必须停下等商家。严禁自行 generate。

#### 回合 ③ generate（⛔ 必须停下）

1. Agent 按 `image_customize` 输出的 prompt 逐图调用 MCP `cbu_image_generation_and_editing_tool`。
2. 把生成结果交给 Python 后处理 `image_generate_result`，保存生成态并按原图位次输出成功/失败表。
3. 渲染原图/优化图对照（`![alt](url)` 格式），输出三选项：
   1. 全部应用
   2. 部分应用
   3. 不应用

> ⛔ 立即停下等商家回复，严禁自行 apply。

#### 回合 ④ apply（流程结束）

1. 调用 Python 后处理 `image_apply_plan`：根据商家选择计算待转换序号集合（**忽略失败序号**），输出待转换图片 URL 列表。
2. Agent 调用 MCP `image_bank_change_url_for_offer` 转换 URL。
3. 把转换结果交给 `image_apply_result`：若仅返回最终 `images`，Agent 继续调用 MCP `cbu_skill_change_main_image(offerId, images)`。
4. 把主图修改结果再次交给 `image_apply_result` 的 `change_result`，Python 按原位次合并主图（**未选中位次保留原图，顺序不变**），输出最终主图表（`![alt](url)` 格式）。

#### 模块特定禁止事项

| 规则 | 说明 |
|------|------|
| 禁止跳过回合 ② | customize 后必须停下问商家，不得直接 generate |
| 禁止跳过回合 ③ | generate 后必须停下问商家，不得直接 apply |
| ⛔ 禁止聊天框询参 | customize 后**绝不允许**在聊天中问「想用什么比例/卖点/场景」；商家改参数只能通过 HTML 编辑器，不得用对话、表单、逐项追问替代 |
| 禁止非法字段 | `image_customize` 仅接受 `size` / `background` / `text_selling_points`，其他字段直接报错 |
| 禁止 Agent 填卖点 | `text_selling_points` 默认空，仅商家能填，Agent 不得推断 |
| 禁止 prompt 注入 | prompt 由 Python 拼接，不接受完整 prompt 注入 |
| 禁止违规比例 | `size` 仅支持 `1:1` / `3:4`，其他值报错 |
| 禁止改变未选中位次 | 应用阶段必须按原主图位次合并 |

#### 模块特定异常处理

| 异常 | 处理 |
|------|------|
| 商品无主图 | prepare 失败，提示检查商品 ID |
| 单张解析失败 | 按「比例 + 背景」最简 prompt 拼装，不影响其他图 |
| 单张生成失败 | 标注「已保留原图」，apply 用原图占位 |
| 图片链接转换失败 | 重试 3 次仍失败提示手动处理 |
| 主图修改失败 | 输出 MCP 错误，**不清理状态文件**，可重试 |

---

### 4. 商品上下架

#### 流程

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1 | 解析意图，确定 `operation` 与 `offerIds`（支持单个 / 批量） | Agent |
| 2 | 下架 → MCP `product_cancel_offer(offerIds)`；上架 → MCP `product_repost_offer(offerIds)` | MCP |
| 3 | 把返回交给 Python 后处理 `offer_operation_result`，按成功态规则解析并翻译错误 | Python |
| 4 | 渲染 markdown 结果（单商品 / 多商品文案不同），流程结束 | Agent |

**Python 输入示例：**

```json
{
  "action": "offer_operation_result",
  "operation": "cancel",
  "offerIds": ["123456"],
  "mcp_result": {}
}
```

#### 成功态判定（按优先级）

1. `data.success`
2. 兼容拼写错误 `data.successs`
3. 回退顶层 `success`

#### 错误翻译映射表

| MCP 原文 | 用户可见文案 |
|----------|--------------|
| `user doesn't have these offer` | 当前账号下没有该商品 |
| `operate failed` | 操作失败，请检查商品状态 |

#### 模块特定禁止事项

| 规则 | 说明 |
|------|------|
| 禁止暴露内部错误 | 必须按映射表翻译，未命中映射时输出 MCP 原 message，不展示内部字段 |

## 通用错误处理

| 场景 | 处理 |
|---|---|
| MCP 鉴权失败 / 401 / 令牌无效 | 提示用户检查 `ali1688-seller` 连接器授权状态，不调用 AK 脚本 |
| 参数缺失/格式错误 | 直接给合法参数示例 |
| 限流 429 | 提示 1-2 分钟后重试 |
| 接口 500/网络异常 | 保持幂等，提示稍后重试 |
| 批量部分失败 | 返回成功/失败明细，允许局部重试 |
| 识图/生成超时 | 返回"超时未完成"，不伪造成功结果 |
| Python 后处理失败 | 直接展示脚本 `markdown`，不要自行生成成功结果 |
| MCP 返回非对象 | 视为格式异常，不伪造结果 |

## 参数补齐引导话术

> 你可以直接给我商品ID、图片或链接；批量场景可一次提供多个ID/图片。  
> 如果是标题或主图优化，我会先给你 AI 建议，再由你确认应用。

## 免责声明

1. 技能输出可能受模型能力与上下文影响，请对关键内容自行核验。  
2. 请妥善保管账号与授权信息，避免泄露风险。  
3. 不得将本技能用于违规经营、侵权或绕过平台风控。  
4. 平台不保证输出绝对准确、真实、时效，请谨慎使用。  

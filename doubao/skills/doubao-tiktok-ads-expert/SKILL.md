---
name: doubao-tiktok-ads-expert
description: "当用户需要在 TikTok Ads 平台搭建广告系列、广告组和广告创意，或进行批量状态、预算、出价及重命名调控时使用。基于平台已绑定的 TikTok Ads MCP 工具，支持 Campaign 到 Ad 的全链路搭建及批量运营操作，授权由平台统一管理。"
agent_created: true
---
# TikTok广告投放专家（平台关联模式）

基于平台已绑定的 TikTok 官方 Ads MCP 工具（`mcp__tiktok_business__*`），提供广告搭建全链路与批量调控能力。

## 使用场景

**当用户需要以下操作时使用本 Skill：**
- 在 TikTok Ads 上搭建完整广告（Campaign → Ad Group → Ad）
- 批量启用/暂停/删除广告、广告组或广告系列
- 批量调整预算（绝对值/百分比/增减量）
- 批量调整出价或重命名
- 上传创意素材（图片/视频）到素材库
- 查询广告实体列表与条件筛选
- 查询枚举值、参数搭配、素材规格或排查 API 报错

**以下场景不使用本 Skill，请转交对应能力：**
- 数据分析、投后受众分析、优化建议 → 使用 `doubao-tiktok-ads-analyst`（投放分析专家）
- 通用咨询（如何开户、平台介绍等）→ 直接回答，不调用本 Skill

> **🔌 授权方式：平台关联模式**
> - 授权由平台统一管理，无需手动配置 OAuth、config.json 或 Token
> - 所有 API 调用通过平台已绑定的 `mcp__tiktok_business__*` 工具执行
> - 本 skill 的 Python 脚本仅负责参数校验、预演计算、操作计划生成和报告格式化

---

## ⚡ 连接器状态校准（强制前置检查）

> **🔴 铁律：执行任何 TikTok Ads 操作前，必须先完成「TikTok for Business」连接器状态校准。未连接时禁止执行任何操作，必须引导用户完成关联。**

### 校准流程（Agent 必须执行）

```
用户发出 TikTok 操作指令
        │
        ▼
  ① Agent 调用 tool_search(query="tiktok_business")
        │
        ├─ 返回任意 mcp__tiktok_business__* 工具 → ② 连接器已连接
        │
        └─ 未返回相关工具 → ③ 输出未连接状态 + 关联引导 → 暂停执行
        │
  ② 连接器已连接，继续执行业务操作
     注意：tool_search 可能只索引部分工具（如 page_get、app_list_get），
     report_integrated_get、auth_advertiser_get、smart_plus_* 等核心工具
     在运行时通过 MCP 连接可用，具体工具可用性在调用时确认
```

### 辅助脚本

```bash
python3 scripts/connector_check.py --method          # 查看连接器检查方法论
python3 scripts/connector_check.py --agent-check     # 查看 Agent 自检指令（tool_search 关键词和判定标准）
python3 scripts/connector_check.py --status connected     # 输出已连接状态展示
python3 scripts/connector_check.py --status disconnected  # 输出未连接状态 + 关联引导
python3 scripts/connector_check.py --status check --tools '["mcp__tiktok_business__report_integrated_get"]'  # 综合判断
```

### 未连接时的关联引导

当连接器未连接时，Agent 必须输出以下引导信息并暂停操作：

1. **明确告知**：豆包官方「TikTok for Business」连接器未关联，无法执行操作
2. **关联步骤**：
   - 打开豆包客户端「设置」→「连接器」/「插件管理」
   - 找到「TikTok for Business」连接器，点击右侧开关开启
   - 完成 OAuth 授权，选择要关联的广告主账户
3. **提示**：关联需要 TikTok for Business 广告账户管理员权限，授权在浏览器中完成，不暴露 Token
4. **暂停**：告知用户完成关联后重新发送指令，将自动重新检测

### 已连接状态确认

连接器校准通过后，Agent 应简要输出连接状态（1-2 行即可，无需冗长），然后继续执行业务操作。

---

## 🧭 广告结构类型确认（强制前置询问）

> **🔴 铁律：凡是涉及「创建广告 / 搭建 Campaign / 新建投放」的需求，在连接器校准通过后、调用任何创建接口前，Agent 必须主动向用户确认广告结构类型——是 **Smart+（升级智能投放）** 还是 **普通拍卖广告（v1.3 传统）**。禁止 Agent 自行猜测、默认选择或根据素材类型替用户决定。用户未明确回复前，不得进入创建流程。**

### 为什么必须询问

Smart+ 与普通拍卖广告是**两套完全不同的接口体系**，所需物料和参数完全不同，选错会直接导致创建失败或产生非预期限制：

| 差异维度 | Smart+（升级智能投放） | 普通拍卖广告（v1.3 传统） |
|---------|----------------------|--------------------------|
| 创建接口 | `smart_plus_campaign_create` / `smart_plus_adgroup_create` / `smart_plus_ad_create`（直接注册工具） | `campaign_create` / `adgroup_create` / `ad_create`（通过 `tool_execute` 动态调度） |
| 身份+素材 | BC_AUTH_TT 必须配 `tiktok_item_id`（TikTok 帖子），**不能**用素材库 `video_id` | BC_AUTH_TT 可直接用素材库 `video_id`，也可用 `tiktok_item_id` |
| CTA 配置 | APP_PROMOTION + TikTok 必须用动态 `call_to_action_id`（CTA portfolio） | 直接用文本枚举值如 `INSTALL_NOW` |
| CBO 日预算最低 | $20 | $50（非 CBO 广告组级别可 $20） |
| 定向模式 | 默认 AUTOMATIC 自动定向，MANUAL 需显式指定 | 手动定向更灵活 |
| 需要用户提供的物料 | TikTok 帖子链接/ID（tiktok_item_id）+ CTA portfolio | 素材库视频/图片（video_id/image_id）+ 文本 CTA |

### 询问规范（Agent 必须执行）

当用户提出创建广告需求但**未明确说明**是 Smart+ 还是普通拍卖时，Agent 必须输出类似以下确认信息并暂停：

```
📋 请确认广告结构类型：

TikTok Ads 支持两种广告结构，接口和所需物料完全不同：

1️⃣ Smart+（升级智能投放）
   - 接口：smart_plus_* 系列
   - 素材：需要 TikTok 帖子链接/ID（tiktok_item_id）
   - CTA：需要 CTA portfolio（call_to_action_id）
   - 适合：已有 TikTok 帖子、希望系统智能优化

2️⃣ 普通拍卖广告（v1.3 传统）
   - 接口：campaign/adgroup/ad_create（tool_execute 调度）
   - 素材：素材库视频/图片（video_id/image_id）
   - CTA：文本枚举（如 INSTALL_NOW）
   - 适合：素材库自有素材、需要更灵活的手动配置

请回复「1」或「2」，或直接说明「Smart+」/「普通拍卖」。
```

### 例外情况

- 用户已在需求中**明确写明**「Smart+」「升级智能投放」「普通拍卖」「非 Smart」「传统拍卖」等关键词 → 视为已确认，无需重复询问，但应在回复中复述确认。
- 用户需求是**批量调控**（启用/暂停/预算/出价/重命名）而非**新建广告** → 不触发本询问。
- 用户需求是**查询**（列表/报表/枚举/报错排查）→ 不触发本询问。

### 确认后的下一步

用户确认广告结构类型后，Agent 应：
1. 在回复中复述确认的类型
2. 根据所选类型进入对应的搭建工作流（Smart+ 路径 A / 普通拍卖路径 B，详见下方「完整搭建工作流」章节）
3. 按该类型所需的物料清单向用户收集缺失信息（如 Smart+ 需要 tiktok_item_id，普通拍卖需要 video_id/image_id）

---

## 🔌 平台关联模式说明

### 工作原理

```
用户需求 → Skill 拆解需求 → 脚本生成操作计划/预演 → Agent 调用平台 mcp__tiktok_business__* 工具 → 返回结果
```

- **脚本层**：`scripts/` 下的 Python 脚本负责参数校验、dry-run 预演、操作计划生成、报告格式化，**不直接发 HTTP 请求**
- **执行层**：Agent 读取脚本输出的计划/指令，调用平台已绑定的 MCP 工具实际执行
- **授权层**：平台统一管理 OAuth，脚本和 Agent 均不接触 Token

### 连接状态查询

运行以下命令查看平台关联状态：

```bash
python3 scripts/tiktok_mcp_client.py --status
```

输出示例：
```
🔌 【MCP连接状态 - 平台关联模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
端点:      platform-bound (mcp__tiktok_business__*)
授权方式:  平台统一 OAuth
已配置:    ✅
已授权:    ✅
工具映射:  30+ 个
广告主ID:  调用时传入
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 平台可用工具映射

运行 `python3 scripts/tiktok_mcp_client.py --tools` 查看完整映射表。核心工具包括：

| 能力 | 平台工具 |
|------|---------|
| 账户查询 | `mcp__tiktok_business__auth_advertiser_get` |
| 报表查询 | `mcp__tiktok_business__report_integrated_get` |
| 投放诊断 | `mcp__tiktok_business__tiktok_ads_diagnosis_agent` |
| Campaign 创建/查询/更新/状态 | `mcp__tiktok_business__smart_plus_campaign_*` |
| Ad Group 创建/查询/更新/状态/预算 | `mcp__tiktok_business__smart_plus_adgroup_*` |
| Ad 创建/查询/更新/状态 | `mcp__tiktok_business__smart_plus_ad_*` |
| 素材/受众/应用查询 | `mcp__tiktok_business__file_image_ad_search` 等 |
| 动态调度（传统拍卖广告） | `mcp__tiktok_business__tool_execute` |

> **注意**：平台直接注册的是 Smart+ 系列工具。传统拍卖广告（非 Smart+）的操作通过 `tool_execute` 动态调度器调用，Agent 需先用 `tool_list`/`tool_get` 发现工具定义。

### 安全规范

- ✅ 授权由平台统一管理，Token 永不暴露
- ✅ 脚本不存储、不传输任何凭证
- ✅ 输出中 advertiser_id 等敏感字段自动脱敏（仅展示后4位）
- ✅ 数据访问范围限于用户 OAuth 授权的广告主账户，所有 API 调用受平台审计日志记录
- ✅ 脚本不缓存、不存储、不转发任何广告数据
- ❌ 不需要 config.json、不需要 OAuth 授权流程
- ❌ 脚本不存储、不管理任何本地凭证文件

> 📖 官方文档：[TikTok Ads MCP Server v1.3](https://business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3)

---

## 🧭 核心能力一：智能导航（Onboarding）

**触发时机**：每台设备首次使用本 skill 时自动触发。

```
📱 TikTok广告投放专家（平台关联模式）— 能力导航
├── 🔧 可执行事项
│   ├── 搭建完整广告（Campaign → Ad Group → Ad）
│   ├── 上传创意素材（图片/视频）
│   ├── ⚡ 批量调控（状态/预算/出价/重命名）
│   ├── 启用/暂停/删除广告（支持批量）
│   ├── 查询广告实体列表与条件筛选
│   ├── 查询枚举值与参数搭配
│   ├── 排查 API 报错
│   └── 查询素材规格
├── 🚀 使用流程
│   ├── 搭建：告诉我需求 → 拆解信息+风控 → 脚本生成计划 → Agent 调用平台工具执行 → 返回结果
│   └── 调控：指定目标+操作 → 脚本预演(dry-run) → Agent 调用平台工具执行 → 返回报告
├── 🔌 MCP连接
│   ├── 平台关联模式，授权由平台统一管理
│   └── 无需开发者 Token，无需手动 OAuth
└── 🔒 安全须知
    ├── 平台统一管理 OAuth Token，永不暴露
    ├── 建成默认暂停，确认后才启用
    ├── 批量调控默认预演模式，确认后才执行
    └── 所有输出敏感字段自动脱敏
```

---

## 🔍 核心能力二：智能需求拆解（Smart Intake）

**触发时机**：用户每次输入广告搭建需求后自动触发。

### 拆解输出结构

```
📋 需求拆解结果
【1/2】你需要准备的信息
  ├─ 账户信息（平台已授权，无需配置）
  │   ├─ ✅ MCP连接状态：平台关联模式
  │   ├─ ✅ 授权由平台统一管理
  │   └─ ⚠️ 需要你提供 advertiser_id（或通过 auth_advertiser_get 查询）
  ├─ 广告计划（Campaign）
  │   ├─ 营销目标
  │   ├─ 预算模式：日预算 / 总预算
  │   └─ 预算金额
  ├─ 广告组（Ad Group）
  │   ├─ 优化目标
  │   ├─ 出价方式
  │   ├─ 定向设置
  │   └─ 版位选择
  └─ 广告创意（Ad）
      ├─ 视频素材 / 图片素材
      ├─ 广告文案
      └─ CTA 按钮
【2/2】风控安全提示
  🔴  平台关联模式安全提示
  ├─ 授权由平台统一管理，无需在对话中发送任何 Token
  ├─ 所有写操作通过平台工具执行，Agent 会在执行前确认
  └─ advertiser_id 输出时自动脱敏（****1234）
```

辅助脚本：`python3 scripts/smart_intake.py --brief brief.yaml`

也可以直接传入关键参数生成拆解模板：

```bash
python3 scripts/smart_intake.py --objective APP_INSTALL --budget-mode daily --budget 50 --region US  # 生成指定营销目标和预算的需求拆解模板
SMART_INTAKE_JSON_OUTPUT=1 python3 scripts/smart_intake.py --brief brief.yaml                        # 输出 JSON 供 Agent 消费
```

---

## 📊 核心能力三：双层执行反馈（Dual-layer Report）

### 概述版（默认展示）

```
✅ 广告搭建完成
📊 执行概览
  ├─ Campaign: AppInstall_2026Q3 (ID: ****6789)
  ├─ Ad Group: US_Core_18-34 (ID: ****4321)
  └─ Ad: Video_Creative_01 (ID: ****4455)
💰 预算与出价
  ├─ 日预算: $50
  └─ 出价: 自动出价
🎯 定向设置
  └─ 地区: US | 年龄: 18-34 | 性别: 不限
📌 当前状态: 已暂停（默认安全模式）
```

辅助脚本：`python3 scripts/exec_report.py --result result.json`

---

## ⚡ 核心能力四：批量调控（Batch Control）

支持对 Campaign / Ad Group / Ad 三个层级进行批量运营调控。

### 4.1 调控能力矩阵

| 调控类型 | Campaign | Ad Group | Ad | 说明 |
|---------|----------|----------|-----|------|
| 批量启用/暂停/删除 | ✅ | ✅ | ✅ | 单次最多 100 个 ID，自动分块 |
| 批量预算调整 | ✅ | ✅ | — | 支持绝对值/百分比/增减量三种模式 |
| 批量出价调整 | — | ✅ | — | 支持绝对值/百分比/增减量，可切换出价类型 |
| 批量重命名 | ✅ | ✅ | ✅ | 支持前缀/后缀/查找替换/序号模式 |
| 条件筛选目标 | ✅ | ✅ | ✅ | 按状态、名称、所属 Campaign 等条件筛选 |

### 4.2 预算/出价调整模式

| 模式 | 参数 | 示例 | 说明 |
|------|------|------|------|
| `set`（绝对值） | `--mode set --value 50` | 设为 $50 | 直接设置，无需先查询当前值 |
| `percent`（百分比） | `--mode percent --value 20` | 增加 20% | 需先查询当前值，Agent 执行查询后传入 |
| `delta`（增减量） | `--mode delta --value -10` | 减少 $10 | 需先查询当前值 |

### 4.3 批量重命名模式

| 模式 | 格式 | 示例 | 效果 |
|------|------|------|------|
| 加前缀 | `prefix:{文本}` | `prefix:US_` | `旧名` → `US_旧名` |
| 加后缀 | `suffix:{文本}` | `suffix:_v2` | `旧名` → `旧名_v2` |
| 查找替换 | `replace:{旧}->{新}` | `replace:US->UK` | `US_Camp` → `UK_Camp` |
| 序号命名 | `sequence:{基础名}` | `sequence:Camp_` | `Camp_1`, `Camp_2`... |

### 4.4 平台关联模式工作流

```
用户发出调控指令
    │
    ├─ ① 连接器状态校准（强制）：Agent 调用 tool_search 检查 mcp__tiktok_business__*
    │     ├─ 未连接 → 输出关联引导 → 暂停
    │     └─ 已连接 → 继续
    ├─ ② 需求拆解：明确层级、目标、操作类型、参数
    ├─ ③ 脚本预演：python3 batch_control.py 生成预演报告 + 平台调用指令
    ├─ ④ 若需查询当前值（percent/delta 模式）：
    │     Agent 先调用平台查询工具，获取当前值后重新生成计划
    ├─ ⑤ 用户确认 → Agent 按 platform_calls 顺序调用平台工具执行
    └─ ⑥ 返回批量执行报告（成功/失败/跳过明细）
```

### 4.5 使用示例

```bash
python3 scripts/batch_control.py status --level campaign --ids "123,456" --op disable                        # 预演：暂停多个 Campaign
python3 scripts/batch_control.py budget --level campaign --ids "123,456" --mode set --value 50               # 预算设为 $50（绝对值模式）
python3 scripts/batch_control.py budget --level campaign --ids "123" --mode percent --value 20              # 预算增加 20%（会提示先查询当前预算）
python3 scripts/batch_control.py rename --level ad --ids "123,456" --pattern "prefix:US_"                    # 批量重命名（加前缀）
BATCH_CONTROL_JSON_OUTPUT=1 python3 scripts/batch_control.py status --level adgroup --ids "123" --op enable # 输出 JSON 供 Agent 消费
```

### 4.6 安全机制

1. **默认预演**：脚本只生成指令和预演报告，不实际执行
2. **Agent 执行前确认**：所有写操作由 Agent 在执行前向用户确认
3. **自动分块**：批量状态更新自动分块（每块 ≤100 ID）
4. **安全边界**：预算范围 [$1, $1,000,000]，出价范围 [$0.01, $10,000]，超出自动跳过
5. **DELETE 高危提示**：删除操作在预演时有明确警示
6. **ID 脱敏**：报告中所有 ID 仅展示后 4 位

---

## 🧭 广告结构类型对比参考（Smart+ vs 普通拍卖广告）

> **⚠️ 前置提醒：广告结构类型必须由用户明确确认，Agent 不得自行决定。详见上方「🧭 广告结构类型确认（强制前置询问）」章节。本章节仅作为用户确认后的对比参考和物料差异说明。**

TikTok Ads 支持两种广告结构，**接口体系和所需物料完全不同**，各有适用场景和限制：

| 维度 | Smart+（升级智能投放） | 普通拍卖广告（v1.3 传统） |
|------|----------------------|--------------------------|
| 创建工具 | `smart_plus_campaign_create` 等直接注册工具 | `campaign_create` / `adgroup_create` / `ad_create`，通过 `tool_execute` 动态调度 |
| 身份+素材 | BC_AUTH_TT 必须配 `tiktok_item_id`（TikTok 帖子），不能用素材库 `video_id` | BC_AUTH_TT 可直接用素材库 `video_id` |
| CTA | APP_PROMOTION+TikTok 必须用动态 `call_to_action_id`（CTA portfolio） | 直接用文本枚举值如 `INSTALL_NOW` |
| CBO 日预算最低 | $20 | $50（非 CBO 广告组级别可 $20） |
| 功能丰富度 | 智能创意、自动版位优化等 | 更基础、更灵活 |

### 用户确认后的选型参考

> 以下规则仅在用户**已确认**广告结构类型后，用于校验物料是否匹配或向用户解释差异，**不得**作为 Agent 替用户决定类型的依据。

1. **用户给了视频文件 + 指定了 TikTok 账号身份（如 dola.share）→ 仅兼容普通拍卖广告**（Smart+ 不支持素材库 video_id + BC_AUTH_TT 组合）
2. **用户给了 TikTok 帖子链接/ID → Smart+ 和普通拍卖均可**
3. **预算低于 $50 且要 CBO → 仅 Smart+ 支持**（普通拍卖 CBO 最低 $50）
4. **用户已明确选择某类型但物料不兼容 → 应向用户说明冲突并请求确认，不得擅自切换类型**

---

## 🔗 身份-素材兼容性矩阵

> **🔴 创建 Ad 前必须校验身份与素材的兼容性，不兼容会导致 "The selected advanced creative is not supported" 错误。**

| 身份类型 | 广告结构 | 素材类型 | 是否支持 | 说明 |
|---------|---------|---------|---------|------|
| BC_AUTH_TT | Smart+ | `tiktok_item_id`（TikTok 帖子） | ✅ | Spark Ad 标准用法 |
| BC_AUTH_TT | Smart+ | `video_id`（素材库视频） | ❌ | 报错 "advanced creative is not supported" |
| BC_AUTH_TT | 普通拍卖 | `video_id`（素材库视频） | ✅ | 已验证可用的组合 |
| BC_AUTH_TT | 普通拍卖 | `tiktok_item_id` | ✅ | 也支持 |
| **AUTH_CODE** | **Smart+** | **`tiktok_item_id`（达人视频）** | **✅** | **达人 Spark Ad，需配 call_to_action_id，详见下方实战流程** |
| **AUTH_CODE** | **普通拍卖** | **`tiktok_item_id`** | **✅** | **达人视频，CTA 用文本枚举** |
| CUSTOMIZED_USER | 普通拍卖 | `video_id` + 仅 Pangle 版位 | ✅ | 非 TikTok 版位可用 |
| CUSTOMIZED_USER | 普通拍卖 | `video_id` + 含 TikTok 版位 | ❌ | 已弃用（2026年1月15日后新账户不可用） |
| 无身份 | Smart+ | `video_id` | ❌ | 报错 "identity_id is required for non-spark ad" |

### 身份查询

使用 `identity_get`（通过 `tool_execute` 动态调度）查询账户下可用身份，关键字段：
- `identity_type`: `BC_AUTH_TT`（TikTok 账号授权）、`AUTH_CODE`（达人授权码）、`CUSTOMIZED_USER`（自定义身份）、`TT_USER`
- `identity_id`: 身份唯一标识（**数字 ID，不是分享码**）
- `identity_authorized_bc_id`: BC_AUTH_TT 时必填，授权的 Business Center ID
- `can_pull_video` / `can_push_video`: 是否可拉取/推送视频
- `display_name`: 达人/账号显示名

> **🔴 关键教训：AUTH_CODE 的 identity_id 是数字 ID（如 6560941051288551425），绝对不是分享码（如 `#am7d+...`）。直接把分享码当 identity_id 传入会报 "Invalid identity" 或 "Unable to get Spark Ad post information"。**

### 已授权达人视频查询（tt_video_list_get）

通过 `tool_execute(tool_name="tt_video_list_get")` 查询账户下所有已授权的 Spark Ads 帖子，返回每条视频的：
- `item_info.item_id`: TikTok 帖子 ID（即 tiktok_item_id）
- `item_info.auth_code`: 该视频对应的分享码
- `item_info.text`: 视频文案
- `user_info.identity_id`: 该视频所属的身份 ID（数字）
- `user_info.identity_type`: 身份类型（通常 AUTH_CODE）
- `user_info.tiktok_name`: 达人昵称
- `auth_info.ad_auth_status`: 授权状态（AUTHORIZED）
- `auth_info.auth_end_time`: 授权到期时间

> **用途**：用户给了分享码或 item_id 时，必须先用此接口校验分享码与 item_id 是否匹配，并获取正确的数字 identity_id。用户经常把不同视频的分享码和 item_id 混在一起给。

---

## 🎯 Smart+ 达人视频（AUTH_CODE）搭建实战流程（已验证跑通）

> **适用场景**：用户提供达人视频分享码（auth code）或 tiktok_item_id，要求在 Smart+ 中创建 Spark Ad。这是最容易踩坑的路径，以下为完整验证流程。

### 踩坑总结（按失败顺序）

| 错误 | 原因 | 正确做法 |
|------|------|---------|
| `Invalid identity` (identity_video_get) | 把分享码当 identity_id 用 | 用 `tt_video_list_get` 获取数字 identity_id |
| `'identity_id' is required for Spark ad` | 创建 Ad 时没传身份 | AUTH_CODE 必须传 identity_type + identity_id |
| `Unable to get Spark Ad post information` | 分享码与 tiktok_item_id 不匹配（不同视频） | 用 `tt_video_list_get` 校验匹配关系 |
| `The selected advanced creative is not supported` | Smart+ + AUTH_CODE + APP_PROMOTION + TikTok 缺少 `call_to_action_id` | 必须先创建 CTA portfolio，传入 ad_configuration.call_to_action_id |
| `Unable to find Call_to_action_ID` | 用了 CTA 推荐接口返回的 asset_id（如 201850）当 portfolio_id | asset_id 不是 portfolio_id，需用 creative_portfolio_create 创建 CTA 组合 |

### 完整步骤（6 步）

**Step 1：查询已授权达人视频，获取正确的 identity_id + tiktok_item_id**

```
tool_execute(tool_name="tt_video_list_get", params={
  "advertiser_id": "xxx",
  "page": 1, "page_size": 20
})
```

从返回中找到用户指定的视频（按分享码 auth_code 或 item_id 匹配），记录：
- `item_info.item_id` → tiktok_item_id
- `user_info.identity_id` → identity_id（数字）
- `user_info.identity_type` → 通常是 AUTH_CODE

> 如果用户给的分享码尚未授权，先用 `tt_video_authorize_apply` 授权（auth_code 中 `+` 必须替换为 `%2B`），再查询。

**Step 2：创建 CTA portfolio（Smart+ AUTH_CODE 必需）**

先获取 CTA 推荐：
```
tool_execute(tool_name="creative_cta_recommend_get", params={
  "advertiser_id": "xxx",
  "new_version": true,
  "objective_type": "APP_PROMOTION",
  "promotion_type": "APP_ANDROID",
  "language": "en",
  "app_id": "xxx",
  "placements": ["PLACEMENT_TIKTOK"],
  "region_codes": ["TH"],
  "optimization_goal": "INSTALL"
})
```

从返回选一个 CTA（如 "Install app"），记录其 `asset_ids`（两个值）。

创建 CTA portfolio：
```
tool_execute(tool_name="creative_portfolio_create", params={
  "advertiser_id": "xxx",
  "creative_portfolio_type": "CTA",
  "portfolio_content": [{"asset_content": "Install app", "asset_ids": ["201850", "201352"]}]
})
```
返回 `creative_portfolio_id` → 用作 call_to_action_id。

**Step 3：创建 Campaign（Smart+ CBO）**

```
smart_plus_campaign_create({
  "advertiser_id": "xxx",
  "campaign_name": "...",
  "objective_type": "APP_PROMOTION",
  "app_promotion_type": "APP_INSTALL",
  "budget_optimize_on": true,
  "budget_mode": "BUDGET_MODE_DYNAMIC_DAILY_BUDGET",
  "budget": 20,
  "operation_status": "DISABLE"
})
```

**Step 4：创建 Ad Group**

```
smart_plus_adgroup_create({
  "advertiser_id": "xxx",
  "campaign_id": "<step3返回>",
  "adgroup_name": "...",
  "promotion_type": "APP_ANDROID",
  "app_id": "xxx",
  "optimization_goal": "INSTALL",
  "bid_type": "BID_TYPE_CUSTOM",
  "conversion_bid_price": 0.1,
  "billing_event": "OCPM",
  "targeting_optimization_mode": "AUTOMATIC",
  "targeting_spec": {"location_ids": ["1605651"]},
  "placement_type": "PLACEMENT_TYPE_NORMAL",
  "placements": ["PLACEMENT_TIKTOK"],
  "schedule_type": "SCHEDULE_FROM_NOW",
  "schedule_start_time": "2026-08-28 03:00:00",
  "operation_status": "DISABLE"
})
```

**Step 5：创建 Ad（达人视频 + AUTH_CODE + CTA portfolio）**

```
smart_plus_ad_create({
  "advertiser_id": "xxx",
  "adgroup_id": "<step4返回>",
  "ad_name": "...",
  "ad_text_list": [{"ad_text": "..."}],
  "creative_list": [{
    "creative_info": {
      "ad_format": "SINGLE_VIDEO",
      "identity_type": "AUTH_CODE",
      "identity_id": "<step1数字ID>",
      "tiktok_item_id": "<step1 item_id>"
    }
  }],
  "ad_configuration": {
    "call_to_action_id": "<step2 portfolio_id>"
  },
  "operation_status": "DISABLE"
})
```

**Step 6：校验三层状态均为 DISABLE**

### 关键参数速查

| 参数 | 值 | 说明 |
|------|-----|------|
| 泰国 location_id | `1605651` | 不是 764314 |
| CBO 预算模式 | `BUDGET_MODE_DYNAMIC_DAILY_BUDGET` | Smart+ CBO 日预算 |
| Install 出价 | `bid_type=BID_TYPE_CUSTOM` + `conversion_bid_price` | 不是 bid_price |
| TikTok only 版位 | `placement_type=PLACEMENT_TYPE_NORMAL` + `placements=["PLACEMENT_TIKTOK"]` | |
| AUTH_CODE identity_id | 数字 ID（来自 tt_video_list_get） | **不是分享码** |
| Smart+ CTA | `ad_configuration.call_to_action_id`（portfolio ID） | 不是文本枚举 |

---

## 完整搭建工作流（平台关联模式）

遵循严格三层结构：
```
Business Center
  └── Advertiser（广告主账户）
        └── Campaign（广告系列）
              └── Ad Group（广告组）
                    └── Ad（广告）
```

### 搭建步骤

| Phase | 动作 | 执行方式 |
|-------|------|---------|
| 0 | **连接器状态校准** | Agent 调用 tool_search 检查 `mcp__tiktok_business__*`，未连接则引导关联并暂停 |
| 0.3 | **广告结构类型确认（强制）** | Agent 必须主动询问用户是 **Smart+** 还是**普通拍卖广告**，用户未明确回复前不得进入创建流程。详见「🧭 广告结构类型确认（强制前置询问）」 |
| 0.5 | 确认 advertiser_id | Agent 调用 `auth_advertiser_get` 或用户提供 |
| 1 | 生成搭建计划 | `python3 scripts/build_ad.py --config brief.json`（脚本默认所有实体 operation_status=DISABLE） |
| 2 | 创建 Campaign | 根据 Phase 0.3 确认的类型：Smart+ 调用 `smart_plus_campaign_create`；普通拍卖调用 `campaign_create`（tool_execute）。**必须显式传入 `operation_status: "DISABLE"`** |
| 3 | 创建 Ad Group | 根据类型：Smart+ 调用 `smart_plus_adgroup_create`；普通拍卖调用 `adgroup_create`（tool_execute）。传入上一步 campaign_id，**必须显式传入 `operation_status: "DISABLE"`** |
| 4 | 上传素材 | Smart+ 需要 `tiktok_item_id`（TikTok 帖子）；普通拍卖需要素材库 `video_id`/`image_id`。Agent 调用素材上传工具（通过 tool_execute 动态调度） |
| 5 | 创建 Ad | 根据类型：Smart+ 调用 `smart_plus_ad_create`；普通拍卖调用 `ad_create`（tool_execute）。传入上一步 adgroup_id，**必须显式传入 `operation_status: "DISABLE"`** |
| 5.5 | **建成校验（强制）** | Agent 调用对应 get 接口验证三层实体的 `operation_status` 均为 `DISABLE`，任一为 ENABLE 则立即调用 status_update 修正 |
| 6 | 启用广告 | **仅在用户明确确认后**，Agent 调用对应类型的 status_update 接口逐层启用 |

### 素材上传示例

创建 Ad 前必须先将素材上传到素材库获取 `image_id` / `video_id`：

```bash
python3 scripts/upload_assets.py --type image --file /path/to/creative.jpg --advertiser-id 123456789  # 上传图片素材
python3 scripts/upload_assets.py --type video --file /path/to/ad_video.mp4 --advertiser-id 123456789   # 上传视频素材
UPLOAD_ASSETS_JSON_OUTPUT=1 python3 scripts/upload_assets.py --type image --file /path/to/creative.jpg --advertiser-id 123456789  # 输出 JSON（含 platform_tool 和 arguments）
```

脚本输出 `platform_tool`（素材上传工具名）和 `arguments`（含文件路径、广告主 ID 等），Agent 读取后调用对应平台工具执行，拿到返回的 `image_id` / `video_id` 后再传入 `smart_plus_ad_create`。

> ⚠️ 素材规格（尺寸、时长、文件大小、格式）请参考 `references/creative-specs.md`，不符合规格的素材会被平台拒绝。

### 搭建计划生成示例

```bash
python3 scripts/build_ad.py --config brief.json --output plan.json  # 生成操作计划（JSON 格式，含依赖关系）
```

计划中的每一步包含 `platform_tool`（要调用的平台工具名）、`arguments`（参数，含 `{{campaign_id}}` 等占位符）、`depends_on`（依赖的步骤）。Agent 按顺序执行，将上一步结果替换占位符。

### 路径 B：普通拍卖广告搭建（v1.3 传统 API）

> **适用场景**：素材库视频 + BC_AUTH_TT 身份、预算低于 $50 且非 CBO、需要更灵活的 CTA 配置等。

普通拍卖广告通过 `tool_execute` 动态调度器调用，需先用 `tool_list` / `tool_get` 发现工具定义。

| Phase | 动作 | 执行方式 |
|-------|------|---------|
| 0 | **连接器状态校准** | 同路径 A |
| 0.5 | 确认 advertiser_id | 同路径 A |
| 0.8 | **发现工具定义** | `tool_list` 列出动态工具 → `tool_get` 获取 `campaign_create` / `adgroup_create` / `ad_create` 的 schema |
| 1 | 创建 Campaign | `tool_execute(tool_name="campaign_create")`，非 CBO 时 `budget_mode=BUDGET_MODE_INFINITE`，**必须显式传入 `operation_status: "DISABLE"`** |
| 2 | 创建 Ad Group | `tool_execute(tool_name="adgroup_create")`，**必须传入 `operating_systems`**（如 `["ANDROID"]`），广告组级别日预算 `budget_mode=BUDGET_MODE_DAY` + `budget=20`，**必须显式传入 `operation_status: "DISABLE"`** |
| 3 | 上传素材 | 同路径 A |
| 4 | 创建 Ad | `tool_execute(tool_name="ad_create")`，`creatives` 数组中指定 `identity_type` / `identity_id` / `identity_authorized_bc_id` / `video_id` / `image_ids` / `ad_text` / `call_to_action`（文本枚举如 `INSTALL_NOW`），**必须显式传入 `operation_status: "DISABLE"`** |
| 4.5 | **建成校验（强制）** | 同路径 A |
| 5 | 启用广告 | 同路径 A（用 `campaign_status_update` / `adgroup_status_update` / `ad_status_update` 动态工具） |

#### 普通拍卖广告关键参数说明

**Campaign 创建**：
- 非 CBO 模式：`budget_optimize_on=false`，`budget_mode=BUDGET_MODE_INFINITE`（系列不设预算，预算在广告组级别）
- CBO 模式：`budget_optimize_on=true`，`budget_mode=BUDGET_MODE_DYNAMIC_DAILY_BUDGET`，日预算最低 **$50**（注意：比 Smart+ 的 $20 高）

**Ad Group 创建**：
- `operating_systems` **必填**：APP_ANDROID 时传 `["ANDROID"]`，APP_IOS 时传 `["IOS"]`，不传会报 "Invalid operating system targeting"
- 广告组级别日预算：`budget_mode=BUDGET_MODE_DAY`，`budget` 最低 $20
- `schedule_start_time` 格式：`YYYY-MM-DD HH:mm:ss`（UTC+0 时间）
- `location_ids`：需通过 `tool_targeting_search` 查询正确的地区 ID（如泰国为 1605651，不是 764314）

**Ad 创建**：
- `call_to_action`：用大写下划线枚举值，如 `INSTALL_NOW` / `LEARN_MORE` / `SHOP_NOW`，**不是** "Install Now" 这种自然语言
- `image_ids`：SINGLE_VIDEO 格式必须配封面图，不传会报 "video material should have 1 image_info as the video cover"
- `identity_type=BC_AUTH_TT` 时必须同时传 `identity_id` 和 `identity_authorized_bc_id`
- 普通拍卖广告的 `creatives` 是数组，每个元素是一个完整的广告创意配置

> ⚠️ **建成不投（铁律）**：所有新建广告实体（Campaign / Ad Group / Ad）创建时**必须显式传入 `operation_status: "DISABLE"`**，禁止依赖 API 默认值。创建后必须校验返回状态，任一为 ENABLE 则立即修正。仅在用户明确确认后才逐层启用。

---

## 🚨 建成不投（强制规范 / Safety First）

> **🔴 铁律：任何新建广告实体（Campaign / Ad Group / Ad）创建时必须显式传入 `operation_status: "DISABLE"`。这是不可省略的强制参数，不是建议。**

### 为什么必须显式传入

- TikTok Ads API 各端点的 `operation_status` 默认值**不一致**：
  - `smart_plus_campaign_create` 默认 `ENABLE`
  - `smart_plus_adgroup_create` 默认 `ENABLE`
  - `smart_plus_ad_create` 默认 `ENABLE`
  - 传统 `campaign_create` / `adgroup_create` / `ad_create` 默认值也可能为 `ENABLE`
- **依赖默认值 = 新建即投放**，可能导致未审核素材、错误定向、错误出价直接产生消耗
- 历史教训：曾因创建 Ad Group 时漏传 `operation_status=DISABLE`，导致广告组默认 ENABLE，虽所属 Campaign 为 DISABLE 实际不投放，但实体状态不符合安全规范

### 三层实体的强制参数

| 实体 | 创建工具 | 必须传入的参数 |
|------|---------|--------------|
| Campaign | `smart_plus_campaign_create` / `campaign_create` | `operation_status: "DISABLE"` |
| Ad Group | `smart_plus_adgroup_create` / `adgroup_create` | `operation_status: "DISABLE"` |
| Ad | `smart_plus_ad_create` / `ad_create` | `operation_status: "DISABLE"` |

### 创建后校验（强制）

每一层实体创建成功后，Agent 必须：
1. 检查返回结果中的 `operation_status` 字段
2. 若为 `ENABLE` 或缺失，**立即**调用对应 `status_update` 接口修正为 `DISABLE`
3. 修正后再次校验，确认状态为 `DISABLE`

### 启用流程（仅在用户确认后）

```
用户明确确认启用
    │
    ▼
① 启用 Ad → smart_plus_ad_status_update(operation_status=ENABLE)
    │
    ▼
② 启用 Ad Group → smart_plus_adgroup_status_update(operation_status=ENABLE)
    │
    ▼
③ 启用 Campaign → smart_plus_campaign_status_update(operation_status=ENABLE)
```

> **注意**：启用顺序为自下而上（Ad → Ad Group → Campaign），确保上层启用时下层已就绪。禁用顺序为自上而下（Campaign → Ad Group → Ad）。

### 脚本层保障

- `scripts/build_ad.py` 生成的搭建计划中，所有创建步骤的 `arguments` 必须默认包含 `operation_status: "DISABLE"`
- `scripts/batch_control.py` 的启用操作（`--op enable`）必须在预演报告中明确提示"将启用以下实体"，并等待用户确认
- Agent 执行脚本生成的计划时，仍需二次确认 `operation_status` 字段存在且为 `DISABLE`

---

## 文件结构

```
doubao-tiktok-ads-expert/
├── SKILL.md                          # 本文档
├── scripts/
│   ├── connector_check.py            # 🔌 连接器状态校准（强制前置检查）
│   ├── tiktok_mcp_client.py          # 平台工具映射 + 调用指令生成（核心）
│   ├── build_ad.py                   # 广告搭建计划生成器
│   ├── batch_control.py              # 批量调控预演 + 平台指令生成
│   ├── smart_intake.py               # 需求拆解 + 风控检查
│   ├── exec_report.py                # 执行报告格式化
│   ├── onboarding.py                 # 智能导航模块
│   └── upload_assets.py              # 素材上传工具（平台 tool_execute）
├── assets/
│   ├── onboarding_template.md
│   ├── risk_checklist.md
│   ├── brief.template.yaml           # 需求单模板
│   ├── batch_control_template.yaml   # 批量调控需求模板
│   └── report_templates/
└── references/
    ├── mcp_guide.md                  # MCP 连接与使用指南
    ├── enums-complete.md             # 完整枚举索引
    ├── api-reference.md              # API 端点参数参考
    ├── error-codes.md                # 错误码排查速查
    └── creative-specs.md             # 素材格式/尺寸规格
```

---

## 参考文件

| 文件 | 加载时机 |
|------|---------|
| `references/mcp_guide.md` | 需要了解 MCP 连接原理、平台工具完整映射或动态调度机制时读取 |
| `references/enums-complete.md` | 需要查询营销目标、优化目标、出价方式、版位等枚举值及合法组合时读取 |
| `references/api-reference.md` | 需要确认具体 API 端点的入参/出参字段、参数类型或必填项时读取 |
| `references/error-codes.md` | 遇到 API 报错需要排查错误码含义和修复建议时读取 |
| `references/creative-specs.md` | 上传素材前确认图片/视频的尺寸、时长、文件大小、格式要求时读取 |

---

## 关键注意事项

1. **连接器校准（强制）**：执行任何操作前必须先通过 tool_search 检查 `mcp__tiktok_business__*` 连接器状态，未连接时引导关联并暂停
2. **平台关联模式**：授权由平台统一管理，无需 config.json / OAuth / Token
3. **脚本不直接调用 API**：所有脚本只生成计划/预演/指令，实际执行由 Agent 调用平台工具
4. **建成不投（铁律）**：所有新建广告实体（Campaign / Ad Group / Ad）创建时**必须显式传入 `operation_status: "DISABLE"`**，禁止依赖 API 默认值；创建后必须校验状态，任一为 ENABLE 则立即修正；仅在用户明确确认后才自下而上逐层启用。详见「🚨 建成不投（强制规范）」章节
5. **层级顺序**：Campaign → Ad Group → Ad，不可颠倒或跳过
6. **目标决定下游**：objective_type → optimization_goal → billing_event 有严格组合
7. **素材先上传**：必须先上传到素材库拿到 ID，再创建 Ad
8. **调控先预演**：批量调控默认 dry-run 预演，用户确认后 Agent 才执行
9. **广告结构类型确认（强制前置询问）**：凡是创建广告的需求，连接器校准通过后必须**主动询问用户**是 Smart+ 还是普通拍卖广告，禁止 Agent 自行猜测或默认选择。用户未明确回复前不得进入创建流程。详见「🧭 广告结构类型确认（强制前置询问）」章节
10. **广告结构类型差异（参考）**：Smart+ 与普通拍卖是两套完全不同的接口，所需物料不同：Smart+ 用 `smart_plus_*` 工具 + `tiktok_item_id` + `call_to_action_id`；普通拍卖用 `tool_execute` 调度 `campaign/adgroup/ad_create` + 素材库 `video_id`/`image_id` + 文本 CTA。素材库视频 + BC_AUTH_TT 仅兼容普通拍卖。详见「🧭 广告结构类型对比参考」章节
11. **身份-素材兼容性（强制校验）**：创建 Ad 前必须校验身份与素材是否兼容，BC_AUTH_TT + Smart+ 只能用 tiktok_item_id，不能用素材库 video_id。详见「身份-素材兼容性矩阵」
12. **普通拍卖广告必填项**：`adgroup_create` 必须传 `operating_systems`（如 `["ANDROID"]`）；`ad_create` 的 `call_to_action` 用大写下划线枚举值（如 `INSTALL_NOW`），不是自然语言 "Install Now"；SINGLE_VIDEO 必须配封面图 `image_ids`
13. **地区 ID 必须查询**：`location_ids` 需通过 `tool_targeting_search` 查询正确值，禁止猜测（如泰国正确值为 1605651，不是 764314）
14. **动态工具发现流程**：普通拍卖广告（campaign_create / adgroup_create / ad_create）通过 `tool_execute` 调用，必须先 `tool_list` 发现工具名 → `tool_get` 获取 schema → `tool_execute` 执行，禁止凭记忆构造参数
15. **预算限制差异**：Smart+ CBO 日预算最低 $20；普通拍卖 CBO 日预算最低 $50，但非 CBO（广告组级别）日预算可 $20。预算低于 $50 时优先用 Smart+ CBO 或普通拍卖非 CBO
16. **渐进式调整**：大幅调整预算/出价可能导致投放模型波动，建议分批渐进式调整
17. **学习期保护**：暂停处于学习期的广告组前需提醒用户可能浪费学习成本
18. **AUTH_CODE 达人视频 identity_id 是数字 ID（铁律）**：达人分享码（如 `#am7d+...`）不是 identity_id。必须用 `tt_video_list_get`（tool_execute 动态调度）查询已授权帖子，获取对应的数字 `identity_id` 和 `tiktok_item_id`。用户常把不同视频的分享码和 item_id 混给，必须校验匹配关系。详见「Smart+ 达人视频（AUTH_CODE）搭建实战流程」
19. **Smart+ AUTH_CODE 必须配 CTA portfolio**：当 identity_type=AUTH_CODE/TT_USER/BC_AUTH_TT + objective=APP_PROMOTION/WEB_CONVERSIONS + TikTok 版位时，`smart_plus_ad_create` 必须传 `ad_configuration.call_to_action_id`（CTA portfolio ID）。缺少会报 "The selected advanced creative is not supported"。CTA portfolio 需通过 `creative_cta_recommend_get`(new_version=true) 获取 asset_ids → `creative_portfolio_create`(type=CTA) 创建，返回的 creative_portfolio_id 才是有效的 call_to_action_id
20. **tool_execute 动态调度关键工具**：以下工具未直接注册为 mcp__tiktok_business__*，需通过 `tool_execute` 调用：`tt_video_list_get`（查已授权达人视频）、`tt_video_authorize_apply`（授权分享码，auth_code 中 `+`→`%2B`）、`identity_get`（查可用身份）、`creative_portfolio_create`（建 CTA 组合）、`creative_cta_recommend_get`（CTA 推荐）、`campaign_create`/`adgroup_create`/`ad_create`（普通拍卖广告）。调用前先用 `tool_list` 发现 → `tool_get` 取 schema

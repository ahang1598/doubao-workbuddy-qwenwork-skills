---
name: doubao-tiktok-ads-analyst
description: "当用户需要对 TikTok Ads 投放数据做结构化多维度分析、核心指标解读、漏斗与受众洞察，或获取数据驱动的投放优化建议时使用。本 Skill 为高阶分析层，提供标准化分析框架与报告输出；单纯数据查询或广告搭建调整请路由至相邻 Skill。"
---

# TikTok投放分析专家（平台关联模式）

本 Skill 是 TikTok Ads 的**高阶分析层**：在 `tiktok-ads` 绑定的 MCP 工具之上，提供标准化的"概述-拆解-策略"三层分析框架、核心指标解读、漏斗与受众洞察，以及数据驱动的优化建议。底层数据获取通过 `tiktok-ads` 的 `mcp__tiktok_business__*` 工具完成，本 Skill 不重复封装工具能力，也不执行任何写操作。广告搭建与批量调控请使用 `doubao-tiktok-ads-expert`，单纯数据查询请直接使用 `tiktok-ads`。

> **🔌 授权方式：平台关联模式**
> - 授权由平台统一管理，无需手动配置 OAuth、config.json 或 Token
> - 所有数据查询通过平台已绑定的 `mcp__tiktok_business__*` 工具执行
> - 本 skill 的 Python 脚本仅负责参数构建、查询指令生成和结果格式化

## 使用场景

**当用户需要以下高阶分析时使用本 Skill：**
- 基于账户/广告组/广告多层级投放数据做结构化分析（花费、曝光、点击、转化的趋势与对比）
- 解读 CTR/CPC/CPA/ROAS 等核心指标表现并给出结论
- 投后受众洞察（年龄/性别/地域/设备/兴趣标签的分布与转化效率）
- 视频播放指标深度解读（2s/6s/完播率的归因与优化方向）
- 漏斗分析（曝光→点击→转化各环节转化率诊断）
- 无消耗/低消耗/高CPA/创意疲劳等问题的系统化诊断（调用官方诊断 Agent）
- 获取预算分配、受众定向、素材迭代、出价策略等数据驱动的优化建议

**以下场景不使用本 Skill，请路由至对应能力：**
- 单纯获取/列出/导出原始数据（如"帮我查一下昨天的花费""列出所有广告组"）→ 使用 `tiktok-ads`（底层 MCP 工具层）
- 搭建广告、创建 Campaign/Ad Group/Ad → 使用 `doubao-tiktok-ads-expert`（广告投放专家）
- 批量调整预算/出价/状态/重命名 → 使用 `doubao-tiktok-ads-expert`
- 本 Skill 仅输出分析报告与优化建议，不执行任何写操作；如用户要求实际调整投放，引导至 `doubao-tiktok-ads-expert`

---

## Skill 间关系与路由边界

本 Skill 与同场景下的 `tiktok-ads`、`doubao-tiktok-ads-expert` 构成三层协作关系，**不是竞争关系**。

### 分层定位

| 层级 | Skill | 职责 |
|------|-------|------|
| 底层工具层 | `tiktok-ads` | 封装 TikTok Ads MCP 全量工具（读写），负责直接 API 调用与原始数据返回 |
| 高阶分析层 | `doubao-tiktok-ads-analyst`（本 Skill） | 在工具层之上提供标准化分析框架、指标解读、漏斗/受众洞察、优化建议 |
| 投放操作层 | `doubao-tiktok-ads-expert` | 负责广告搭建、批量调控、预算/出价/状态调整等写操作 |

### 四要素边界对比

| 维度 | 本 Skill（analyst） | `tiktok-ads` | `doubao-tiktok-ads-expert` |
|------|---------------------|--------------|----------------------------|
| **触发语义** | 用户要求"分析/解读/诊断/优化建议/报告" | 用户要求"查一下/列出/获取/导出XX数据"或直接操作 | 用户要求"创建/搭建/修改/调整/暂停/批量调控" |
| **用户目标** | 理解投放表现、定位问题、获得可执行优化方向 | 获取特定原始数据或执行单点工具操作 | 变更广告投放配置或状态 |
| **交付物形态** | 结构化分析报告（概述-拆解-策略三层），含结论与建议 | 原始 API 返回数据、列表、操作结果 | 广告配置变更结果、创建/更新确认 |
| **执行路径** | 连接器校准→信息拆解→调用 tiktok-ads 工具取数→三层分析→报告输出 | 识别操作→选择最窄可用工具→调用→返回原始结果 | 确认需求→校验权限→搭建/调控→验证结果 |

### 显式依赖声明

- **依赖 `tiktok-ads`**：本 Skill 的所有数据获取均通过 `tiktok-ads` 绑定的 `mcp__tiktok_business__*` 工具完成，本 Skill 不自行定义、封装或替代这些工具。运行时需确保 `tiktok-ads` Skill 及其 MCP 连接器可用。
- **协作 `doubao-tiktok-ads-expert`**：分析结论中涉及的投放调整建议，如用户要求实际执行，转交 `doubao-tiktok-ads-expert` 操作。

### 路由决策规则

当用户请求涉及 TikTok Ads 时，按以下优先级判定：
1. 包含写操作意图（创建/修改/删除/调整/暂停/批量调控）→ 路由至 `doubao-tiktok-ads-expert`
2. 仅要求获取原始数据（查/列/导出/看一下XX数据），无分析解读诉求 → 路由至 `tiktok-ads`
3. 要求分析、解读、诊断、对比、洞察、优化建议、出具报告 → 使用本 Skill
4. 混合请求（如"分析数据并帮我调整预算"）→ 本 Skill 完成分析后，将调整部分转交 `doubao-tiktok-ads-expert`

---

## ⚡ 连接器状态校准（强制前置检查）

> **🔴 铁律：执行任何 TikTok Ads 分析操作前，必须先完成「TikTok for Business」连接器状态校准。未连接时禁止执行任何数据查询，必须引导用户完成关联。**

### 校准流程（Agent 必须执行）

```
用户发出 TikTok 分析指令
        │
        ▼
  ① Agent 调用 tool_search(query="tiktok_business")
        │
        ├─ 返回任意 mcp__tiktok_business__* 工具 → ② 连接器已连接
        │
        └─ 未返回相关工具 → ③ 输出未连接状态 + 关联引导 → 暂停执行
        │
  ② 连接器已连接，继续执行分析
     注意：tool_search 可能只索引部分工具（如 page_get、app_list_get），
     report_integrated_get、auth_advertiser_get 等核心工具
     在运行时通过 MCP 连接可用，具体工具可用性在调用时确认
```

### 辅助脚本

```bash
python3 scripts/connector_check.py --method          # 检查方法论
python3 scripts/connector_check.py --agent-check     # Agent 自检指令
python3 scripts/connector_check.py --status connected     # 已连接状态
python3 scripts/connector_check.py --status disconnected  # 未连接 + 关联引导
```

### 未连接时的关联引导

连接器未连接时，Agent 必须输出引导并暂停：

1. **告知**：豆包官方「TikTok for Business」连接器未关联，无法获取广告数据
2. **关联步骤**：豆包「设置」→「连接器」→ 找到「TikTok for Business」→ 开启开关 → OAuth 授权 → 选择广告主账户
3. **提示**：需要广告账户访问权限，授权在浏览器完成，不暴露 Token
4. **暂停**：完成关联后重新发送指令，将自动重新检测

---

## 首次调用能力介绍

用户首次调用本 Skill 时，输出以下能力范围介绍：

### 🎯 TikTok投放分析专家（平台关联模式）- 能力范围

您好！我是您的专属TikTok投放分析专家，基于**平台已绑定的 TikTok for Business MCP 工具**为您提供智能化的广告投放分析服务。

**我能帮您做什么：**

1. **数据查询与整合**
   - 账户/广告组/广告多层级数据拉取
   - 自定义时间范围的投放数据统计
   - 多维度数据交叉分析（受众/版位/素材/地域）

2. **核心指标诊断**
   - 曝光/点击/转化漏斗分析
   - CTR/CPC/CPA/ROAS等关键指标评估
   - 视频播放指标深度解读（2s/6s/完播率）

3. **投后受众分析**
   - 年龄/性别/地域分布洞察
   - 设备/操作系统偏好分析
   - 兴趣标签与行为特征拆解

4. **智能化优化建议**
   - 预算分配优化方案
   - 受众定向调整建议
   - 素材效果评估与迭代方向
   - 出价策略优化指导

5. **官方诊断 Agent**
   - 无消耗/低消耗/高CPA/创意疲劳等问题诊断
   - 数据驱动的可执行优化建议

**使用前准备：**
平台关联模式下无需手动配置，但**必须先确认连接器已关联**。Agent 会在执行前自动通过 `tool_search` 检查 `mcp__tiktok_business__*` 工具是否可用。连接器就绪后，只需提供 advertiser_id（或通过 `auth_advertiser_get` 查询已授权账户）即可开始分析。

---

## 交互流程规范

### 第一步：连接器校准 + 信息拆解

每次用户发布指令后，**必须先执行连接器校准**，再进行信息拆解：

#### 1.1 连接器状态校准（强制前置）

Agent 必须调用 `tool_search(query="tiktok_business")` 检查连接器：
- 返回任意 `mcp__tiktok_business__*` 工具 → 连接器已连接，继续
- 未返回任何 `mcp__tiktok_business__*` 工具 → 运行 `python3 scripts/connector_check.py --status disconnected` 输出关联引导，暂停执行

详见上方「⚡ 连接器状态校准」章节。

#### 1.2 信息需求拆解

**【必填信息】**
- 投放目标（如：提升曝光/获取点击/促进转化/品牌认知等）
- 分析时间范围（如：过去7天/过去30天/自定义时间段）
- 分析层级（账户级/广告组级/广告级）
- advertiser_id（或通过平台工具 `auth_advertiser_get` 查询）

**【选填信息】**
- 具体广告组/广告ID（如需定向分析）
- 关注的核心指标（如：CPA、ROAS、CTR等）
- 特定受众维度（如：年龄、地域、设备等）
- 对比基准（如：行业均值、历史数据、目标值）

> 连接器状态校准已在上方 1.1 完成。如需查看平台关联详情，可运行 `python3 scripts/tiktok_mcp_client.py --action status`。

#### 1.3 风险点提示

**⚠️ 数据安全**
- 平台关联模式下 OAuth Token 由平台统一管理，绝不在对话中展示
- 所有凭证只能通过平台工具安全访问
- 建议定期检查并管理已授权的应用

**⚠️ 数据准确性**
- MCP数据存在延迟（通常1-3小时），实时数据可能有偏差
- 归因数据可能因归因窗口设置不同而有差异
- 建议使用完整自然日数据进行分析，避免截断日数据

**⚠️ 操作风险**
- 本 Skill 仅执行只读数据查询，不执行任何写操作
- 如用户要求实际调整投放（预算/出价/状态等），引导至 `doubao-tiktok-ads-expert`
- 优化建议仅供参考，实际执行前请结合业务判断
- 新广告组通常有 2-3 天学习期，期间数据波动属正常现象

---

### 第二步：数据获取与分析

确认信息完整后，按以下流程执行：

#### 2.1 平台工具调用（核心）

以下工具由 `tiktok-ads` Skill 绑定的 MCP 连接提供，本 Skill 作为高阶分析层调用它们取数，**不重复定义工具能力、不自行发 HTTP 请求或管理 Token**。运行时以 `tiktok-ads` 的 live callable 工具为准：

| 数据需求 | 平台工具 | 说明 |
|---------|---------|------|
| 已授权账户列表 | `mcp__tiktok_business__auth_advertiser_get` | 获取可访问的广告主 |
| 报表数据 | `mcp__tiktok_business__report_integrated_get` | 同步报表，支持多维度 |
| Campaign列表 | `mcp__tiktok_business__smart_plus_campaign_get` | 广告系列查询 |
| Ad Group列表 | `mcp__tiktok_business__smart_plus_adgroup_get` | 广告组查询 |
| Ad列表 | `mcp__tiktok_business__smart_plus_ad_get` | 广告查询 |
| 投放诊断 | `mcp__tiktok_business__tiktok_ads_diagnosis_agent` | 官方诊断 Agent |
| 动态工具发现 | `mcp__tiktok_business__tool_list` / `tool_get` / `tool_execute` | 传统拍卖广告等未直接注册的工具 |

辅助脚本可生成查询指令：
```bash
python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_CAMPAIGN  # 生成报表查询指令
```

脚本输出 `platform_tool` 和 `arguments`，Agent 直接调用对应平台工具。

#### 2.2 数据分析框架

采用"概述-拆解-策略"三层分析框架：

**第一层：整体概述**
- 核心指标总览（花费、曝光、点击、转化、核心成本指标）
- 与目标/基准的对比结论
- 整体健康度评分（优/良/中/差）

**第二层：详细拆解**
1. **时间维度**：趋势变化、波动识别、异常点检测
2. **结构维度**：各广告组/广告贡献度、Top/Bottom表现
3. **受众维度**：年龄/性别/地域/设备分布与转化效率
4. **素材维度**：不同创意形式/时长/风格的效果对比
5. **漏斗维度**：曝光→点击→转化各环节转化率分析

**第三层：优化策略**
- 🔴 紧急调整（需立即执行的问题）
- 🟡 中期优化（1-3天内可执行）
- 🟢 长期策略（持续优化方向）

---

### 第三步：结果输出

输出格式必须包含以下部分：

```
📊 【分析概述】
- 核心结论1
- 核心结论2
- 整体评价：优/良/中/差

📈 【详细拆解】
【1. 整体表现】
（数据表格 + 关键发现）

【2. 维度拆解】
  2.1 时间趋势
  2.2 广告组/广告表现
  2.3 受众分析
  2.4 漏斗分析

💡 【优化建议】
🔴 紧急调整（立即执行）
1. 建议内容 + 预期效果 + 操作方法

🟡 中期优化（1-3天）
1. 建议内容 + 预期效果 + 操作方法

🟢 长期策略（持续优化）
1. 建议内容 + 预期效果 + 操作方法

⚠️ 【风险提示】
- 注意事项1
- 注意事项2
```

---

## 平台连接管理

> **🔴 连接器校准是执行任何操作的强制前置步骤**，详见上方「⚡ 连接器状态校准」章节。

### 连接器状态校准（推荐）

```bash
python3 scripts/connector_check.py --method       # 检查方法论
python3 scripts/connector_check.py --agent-check  # Agent 自检指令
python3 scripts/connector_check.py --status connected     # 已连接展示
python3 scripts/connector_check.py --status disconnected  # 未连接 + 关联引导
```

### 平台关联状态查询

```bash
python3 scripts/tiktok_mcp_client.py --action status
```

输出示例：
```
🔌 【MCP连接状态 - 平台关联模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
端点地址:  platform-bound (mcp__tiktok_business__*)
连接状态:  ✅ 平台关联已就绪
授权方式:  平台统一 OAuth
工具映射:  12 个
广告主ID:  未设置（调用时传入）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 平台工具映射查询

```bash
python3 scripts/tiktok_mcp_client.py --action tools
```

### 常用管理指令
- **"检查连接器状态"** → Agent 调用 tool_search 检查，运行 connector_check.py 输出
- **"列出已授权账户"** → Agent 调用 `auth_advertiser_get`
- **连接器未连接时** → 运行 `connector_check.py --status disconnected` 输出关联引导，暂停操作

---

## 安全规范（平台关联模式）

### 🔴 授权安全
- 平台关联模式下，OAuth Token 由平台统一管理，**绝不在对话中展示**
- 不需要 config.json、不需要手动 OAuth 授权流程
- 所有数据查询通过平台工具执行，Agent 不接触 Token
- 如检测到用户在对话中发送 token / 授权码，立即拦截并警告

### 🟡 数据安全
- 不在对话中完整输出用户的广告账户ID（可脱敏展示，如：****1234）
- 敏感商业数据提醒用户注意保密
- 分析结果涉及的具体数据，提醒用户仅供内部参考
- 数据访问范围限于用户 OAuth 授权的广告主账户，所有 API 调用受平台审计日志记录
- 脚本不缓存、不存储、不转发任何广告数据

> 📖 官方文档：[TikTok Ads MCP Server v1.3](https://business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3)

### 🟢 操作安全
- 本 Skill 仅执行只读数据查询，不执行任何写操作（创建/修改/删除/调整预算/暂停广告等）
- 如用户要求实际执行投放调整，引导至 `doubao-tiktok-ads-expert`（广告投放专家）
- 优化建议仅供参考，实际执行前请结合业务判断并验证

---

## 辅助脚本

本Skill包含辅助脚本，位于 `scripts/` 目录：

- `connector_check.py`：🔌 连接器状态校准（强制前置检查，方法论 + 状态输出 + 关联引导）
- `tiktok_mcp_client.py`：平台工具映射 + 查询指令生成 + 结果格式化

**重要**：脚本**不直接发 HTTP 请求**，只生成平台工具调用指令。Agent 读取指令后调用对应平台工具。

使用方式：
```bash
python3 scripts/tiktok_mcp_client.py --action status
python3 scripts/tiktok_mcp_client.py --action tools
python3 scripts/tiktok_mcp_client.py --action accounts
python3 scripts/tiktok_mcp_client.py --action report --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31
python3 scripts/tiktok_mcp_client.py --action diagnose --advertiser-id xxx --issue-type LOW_SPENDING --query "为什么消耗上不去"
```

### 常用 report 查询组合

```bash
python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_ADVERTISER --dimensions stat_time_day

python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_ADGROUP --dimensions adgroup_id

python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_ADGROUP --dimensions age,gender

python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_ADGROUP --dimensions country

python3 scripts/tiktok_mcp_client.py --action report \
  --advertiser-id xxx --start-date 2026-01-01 --end-date 2026-01-31 \
  --data-level AUCTION_AD --dimensions ad_id,material_id
```

以上 5 个组合依次对应：账户级按天趋势、广告组级对比、受众年龄性别交叉、地域分布、素材效果对比。

> 完整的 data-level、dimensions、metrics 枚举值请参考 `references/metrics_guide.md`。脚本输出 `platform_tool` 和 `arguments`，Agent 读取后调用 `mcp__tiktok_business__report_integrated_get` 执行查询。

---

## 参考文件

| 文件 | 加载时机 |
|------|---------|
| `references/metrics_guide.md` | 需要查询完整的 data-level、dimensions、metrics 枚举值或指标定义时读取 |
| `references/mcp_guide.md` | 需要了解 MCP 协议背景、工具发现机制或连接原理时读取（注意：本地配置章节已过时，以平台关联模式为准） |
| `references/security_guide.md` | 需要了解凭证安全规则、脱敏要求或应急响应流程时读取（注意：本地配置文件章节已过时，以平台关联模式为准） |

---

## 注意事项

1. **连接器校准（强制）**：执行任何分析前必须先通过 tool_search 检查 `mcp__tiktok_business__*` 连接器状态，未连接时引导关联并暂停
2. **平台关联模式**：授权由平台统一管理，无需配置文件或 OAuth
3. **脚本不直接调用 API**：所有脚本只生成查询指令，实际执行由 Agent 调用平台工具
4. **MCP端点可用性**：以当前运行时实际绑定的平台工具为准
5. **API限流**：底层仍受TikTok API频率限制，避免短时间内大量请求
6. **数据延迟**：报表数据通常有1-3小时延迟，当天数据不完整
7. **归因窗口**：不同转化事件的归因窗口不同，分析时需注意
8. **学习期**：新广告组通常需要2-3天学习期，期间数据波动正常
9. **时区问题**：数据默认使用账户时区，注意时间范围的时区一致性
10. **Smart+ 优先**：平台直接注册的是 Smart+ 系列查询工具，传统拍卖广告通过 `tool_execute` 动态调度
11. **诊断 Agent**：`tiktok_ads_diagnosis_agent` 为官方诊断工具，单次分析不超过5个实体，通常需要2-3分钟

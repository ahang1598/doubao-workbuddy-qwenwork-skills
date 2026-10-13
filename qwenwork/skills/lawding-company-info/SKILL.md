---
name: lawding-company-info
description: "企业主体信息全能查询。Use when 用户提及企业信息查询、工商信息、查企业、尽调、背景调查,或询问某企业是否靠谱、合作风险、当事人企业背景,或要求出一份企业尽调报告。QoderWork 默认用原生企查查连接器（Qichacha，一键 OAuth）；天眼查需自定义 MCP 可选接入。TRIGGER keywords: 企业查询、工商、股东、风险、尽调、查公司、天眼查、企查查、企业背景。"
install_source: official
install_method: download
skill_id: official_EETSxukc
enabled_at: 1791893800792
version: 1.0.0
name_zh: 律师企业尽调报告
---

# 企业主体信息全能查询

本技能在 **QoderWork** 中的默认数据源是**企查查 (QCC)**——QoderWork 已内置**原生企查查连接器**（显示名 Qichacha，server 名 `qcc-company`，一键 OAuth 授权、免 API Key）。能力覆盖：工商档案、风险、股权、主要人员、招投标、联系方式、知识产权（含 APP/小程序/社交媒体等数字资产）。

**天眼查 (TYC)** 在 QoderWork 中**没有原生连接器**，仅能作为自定义 MCP 手动接入（见 [install-tyc.md](references/install-tyc.md)）；除非用户明确坚持，否则优先使用原生企查查连接器。

---

## 不适用场景

- **类案检索** → `lawding-case-retrieval`
- **法规检索** → `lawding-regulation-retrieval`
- **合同审查** → `lawding-contract-review-pro`
- **自然人信息查询**（本技能仅支持企业主体）

---

## 工作流程概览

| 阶段 | 职责 | 详见 |
|------|------|------|
| 第一步 | **路由**：Provider 选择与可用性 | 下文 §1 |
| 第二步 | **路由**：需求与输出模式 | 下文 §2 |
| 第三步 | **执行**：搜索 + 按维度收集 | 下文 §3 + [dimension-tool-map.md](references/dimension-tool-map.md) |
| 第四步 | **执行**：格式化与交付 | 下文 §4 + 输出模板 |

---

## 第一步：Provider 选择与可用性（路由层）

### 1.1 读取用户偏好

从代理 memory 读取「企业信息查询 provider 偏好」（`tyc` / `qcc` / 未设置）。

### 1.2 检测当前会话可用 provider

优先用 `qw_query` 检查 QoderWork 连接器状态，再回落到工具列表检测：

- **QCC（原生连接器，QoderWork 默认）**：
  - 连接器状态：`qw_query({ key: "qoderwork.settings.connector.market.qcc-company" })`，看 `enabled` 与 `status`（`connected` = 可用；`needs-auth` = 需授权；`disabled` = 需启用）。
  - 工具旁证：会话工具列表中出现企查查连接器的工具（描述含「企业查询 / 工商 / 风险 / 股权」等）即为已连通。
- **TYC（QoderWork 无原生连接器）**：仅当用户自行添加了天眼查**自定义 MCP**（`qoderwork.settings.connector.custom`）且工具列表出现其工具时，才算可用。

### 1.3 决策矩阵

QoderWork 环境下 **QCC 为原生默认**，TYC 仅在用户自建自定义 MCP 时可用。

| memory 偏好 | QCC 连接器状态 | TYC 自定义 MCP | 行动 |
|---|---|---|---|
| 未设置 | `connected` | 任意 | 直接用 QCC（原生默认），可顺带询问是否记为偏好 |
| 未设置 | `needs-auth` / `disabled` | 不可用 | 引导启用并 OAuth 授权企查查连接器（§1.4）→ 授权后查询 |
| 未设置 | `needs-auth` / `disabled` | 可用 | 告知企查查未授权，询问：授权企查查 或 先用已配置的天眼查 |
| `qcc` | `connected` | 任意 | 直接用 QCC |
| `qcc` | `needs-auth` / `disabled` | 可用 | 提示偏好企查查未授权，问：授权企查查 或 临时切天眼查 |
| `qcc` | `needs-auth` / `disabled` | 不可用 | 引导授权企查查连接器（§1.4） |
| `tyc` | 任意 | 可用 | 直接用 TYC（尊重用户偏好） |
| `tyc` | `connected` | 不可用 | 提示天眼查未配置，问：改用原生企查查 或 按 install-tyc 自建 MCP |
| 任一 | 不可用 | 不可用 | 引导授权原生企查查连接器；拒绝则走 §1.5 公开信息摘要 |

**用户主动切换**（「换企查查」「换天眼查」等）→ **立即更新 memory**，本次起生效。

### 1.4 启用/授权引导

- **QCC（原生连接器，推荐）**：按 [references/install-qcc.md](references/install-qcc.md) 引导用户在 **设置 → 连接器 → 行业数据 → Qichacha（企查查）** 完成**一键连接 + OAuth 授权**（免 JSON、免 API Key）。可用 `qw_action` 辅助：`enable`（若未启用）与 `open`（打开连接器页让用户授权）。授权完成后 `status` 变 `connected`，**无需重启**即可继续查询。
- **TYC（可选，非原生）**：QoderWork 无原生天眼查连接器，仅能作为自定义 MCP 接入，见 [references/install-tyc.md](references/install-tyc.md)。除非用户坚持，否则不主动引导。

### 1.5 公开信息降级

用户拒绝或无法安装任何 MCP 时：

- 使用 `WebSearch` 基于企业全称检索基本工商/风险信息
- **仅**输出「公开信息摘要」，**不**输出完整尽调报告
- 摘要头部强制标注：

> ⚠️ 本摘要未使用天眼查/企查查 MCP，基于公开网络检索整理，可能滞后或不完整，不能替代正式尽调。如需正式报告，请安装天眼查或企查查 MCP。

- **禁止**空输出空手结束

---

## 第二步：需求分析与输出模式（路由层）

| 用户意图 | 模式 |
|---------|------|
| 单一维度（如「只查股东」「只查风险」） | **专项输出** → [output-single-dimension.md](references/output-single-dimension.md) |
| 多维度 / 综合尽调 / 尽调报告 | **综合报告** → [report-template.md](references/report-template.md) |

用户未明确维度时引导：

> 请问您需要单独查某一项（工商/风险/股权/联系方式），还是要一份完整尽调报告？

---

## 第三步：数据收集（执行层）

### 3.1 搜索企业

按 [dimension-tool-map.md §入口](references/dimension-tool-map.md#入口搜索企业) 调用入口工具，取得企业标识；多候选时让用户确认。

### 3.2 按维度并行收集

**必读** [references/dimension-tool-map.md](references/dimension-tool-map.md)：含 6 个核心维度、5 个按需维度、各 provider 的 server 与工具描述关键词。

- 综合尽调：**必须**覆盖 dimension-tool-map 中全部「核心维度」
- 各维度并行调用；单维失败不阻断其他维度

### 3.3 qcc-history 降级

provider = QCC 且工具列表无 `qcc-history` 工具时：跳过历史维度，报告中标注 `历史数据未启用（企查查 qcc-history 需企业认证后开通）`。

### 3.4 通用规则

- 调用失败 → 该维度标 `该维度数据获取失败`
- 接口成功但字段为空 → 填 `数据缺失`，不得省略整段
- 数据明显异常（注册资本为 0 等）→ 标注「数据可能存在异常，建议核实」

---

## 第四步：格式化输出（执行层）

### 4.1 模板与数据来源

- 专项 → [output-single-dimension.md](references/output-single-dimension.md)
- 综合 → [report-template.md](references/report-template.md)

**头部必选一行**（三种之一，按实际使用填写）：

- `数据来源：企查查（QoderWork 原生连接器 Qichacha / qcc-company）`
- `数据来源：天眼查（自定义 MCP tyc-mcp）`（仅当用户自行接入 TYC 自定义 MCP 时）
- 公开摘要模式使用 §1.5 的 ⚠️ 声明（不得写为正式连接器来源）

### 4.2 输出完成标准（交付前自检）

#### 综合尽调报告

| 检查项 | 要求 |
|--------|------|
| 必填章节 | 执行摘要、企业基本信息、股权结构、主要人员、风险评估（含自身/周边/预警，历史维按 qcc-history 可用性）、法律评价与建议、免责条款 |
| 建议章节 | 联系信息、招投标（无数据时章节保留，表内填 `数据缺失`） |
| 缺失字段 | 统一写 `数据缺失`，禁止留空或删节 |
| 维度级失败 | 对应章节首行写 `该维度数据获取失败` + 简要原因 |
| 数据来源 | 报告头部 + 「数据来源与局限」表均须填实质内容 |
| 禁止交付 | 企查查连接器与 TYC 自定义 MCP 均不可用却输出完整尽调报告；无任何正文的空报告 |

#### 专项输出

- 必须包含所选维度模板中的**全部字段块**；无数据字段写 `数据缺失`
- 头部须有 §4.1 数据来源一行

#### DOCX 与 Markdown 降级

| 路径 | 要求 |
|------|------|
| DOCX（首选） | 用户确认预览后调用 `docx` skill；文件名 `[企业名称]_企业尽调报告.docx`；版式见 §4.3 |
| Markdown 降级 | `docx` 不可用时写入 `output/[企业名称]_企业尽调报告.md`，并告知用户可手动导入 Word；**同样满足**上表综合/专项完成标准与数据来源标注 |

**综合报告交互**：数据收集完成后，**先以 Markdown 表格预览**，并引导：生成 DOCX / 修改报告 / 补充维度。

### 4.3 文档格式规范（仅 DOCX）

- 统一字体；标题层级递减；表格样式一致
- A4 标准页边距；禁止同层级字号/加粗混用

---

## 异常处理

| 场景 | 处理 |
|------|------|
| 两个 provider 均不可用 | 引导安装；拒绝 → 仅公开信息摘要 |
| 搜索无结果 | 提示核实企业全称/简称 |
| 部分维度失败 | 标注后继续输出其他维度 |
| qcc-history 不可用 | 跳过历史，标注未认证，不阻断主流程 |

---

## 状态说明

除 **provider 偏好**（memory 持久化）外无跨会话状态；每次查询独立执行。

---

## 参考文件

| 文件 | 用途 |
|------|------|
| [references/install-tyc.md](references/install-tyc.md) | TYC MCP 安装与 Key |
| [references/install-qcc.md](references/install-qcc.md) | QCC MCP 安装与 Key |
| [references/dimension-tool-map.md](references/dimension-tool-map.md) | 维度 → server / 工具关键词（执行层必读） |
| [references/output-single-dimension.md](references/output-single-dimension.md) | 专项输出字段结构 |
| [references/report-template.md](references/report-template.md) | 综合报告章节结构 |

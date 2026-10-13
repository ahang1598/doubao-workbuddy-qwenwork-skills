# CHANGELOG

## v3.0 — 适配 QoderWork 原生企查查连接器 (2026-07-16)

将数据源接入从旧版的「JSON + API Key 多 server MCP」迁移到 **QoderWork 原生连接器**能力，使技能可直接在 QoderWork 中运行。

### 变更

- `references/install-qcc.md`：重写为「QoderWork 原生企查查连接器（Qichacha / `qcc-company`）启用指南」——一键连接 + OAuth 授权，用 `qw_query` 查连接器状态（`qoderwork.settings.connector.market.qcc-company`）、用 `qw_action` enable/授权；明确它是**单一连接器**，不再是旧版的 6 个拆分 server。
- `references/install-tyc.md`：改为说明 **QoderWork 无原生天眼查连接器**，仅可通过自定义 MCP（`qoderwork.settings.connector.custom`）接入；默认推荐用原生企查查。
- `SKILL.md`：头部数据源说明、§1.2 可用性检测（连接器状态查询 + 关键词兜底）、§1.3 决策矩阵、§1.4 启用/授权引导、§4.1 数据来源标注、§4.2 交付禁令均改为围绕企查查连接器 + TYC 自定义 MCP 表述。
- `references/dimension-tool-map.md`：新增「QoderWork 适配说明」——企查查为单一 `qcc-company` 连接器，旧版的 `qcc-risk`/`qcc-operation` 等拆分命名在 QoderWork 中不作为独立 server，按描述关键词在同一连接器工具列表中匹配；TYC 列仅在自定义 MCP 存在时适用。
- `references/report-template.md` / `references/output-single-dimension.md`：数据来源、免责条款、招投标注记从「天眼查 MCP」改为「企查查连接器 / 所用数据源」中性表述。

### 保留

- 关键词匹配（非硬编码工具名）设计：连接器授权前工具不枚举，授权后按描述关键词选工具，兼容上游工具名变化。
- 公开信息降级、双数据源（QCC 优先、TYC 可选）设计与全部输出模板结构不变。

## v2.1 — 结构优化（静态评测整改）(2026-05-20)

针对静态评测 CP15/CP16/CP17/CP20 的整改。

### 新增

- `references/install-tyc.md` / `references/install-qcc.md`：MCP JSON 与 Key 说明从主文件拆出
- `references/dimension-tool-map.md`：维度 → server / 工具描述关键词映射（执行层单点维护）
- SKILL.md §4.2「输出完成标准」：综合/专项必填项、缺失字段口径、Markdown 降级路径

### 变更

- SKILL.md 瘦身（约 267 → ~200 行）：路由层（§1–2）与执行层（§3–4）分节，安装与维度表改为 reference 指针
- 工作流程概览表：明确四阶段职责边界

### 说明

- 未新增 `scripts/`：MCP 调用仍由 Agent 在运行时发起；维度映射沉淀为 `dimension-tool-map.md` 以降低维护漂移（与 v2 设计「不写死工具名」一致）

---

## v2.0 — lawding-company-info-tyc-qcc (2026-05-20)

从 `lawding-company-info` (仅天眼查) 升级为双数据源版本。

### 新增

- **企查查 (QCC) 支持**: 新增 6 个 server 的完整配置 (qcc-company / qcc-risk / qcc-ipr / qcc-operation / qcc-executive / qcc-history)
- **Provider 选择与偏好记忆**: 用户首次使用选择 TYC 或 QCC,通过代理 memory 系统跨会话持久化,可随时切换
- **决策矩阵**: 基于 memory 偏好 + 实际可用性自动决策,覆盖 9 种场景
- **维度映射三列表**: 每个维度同时标注 TYC 和 QCC 对应的 server 来源
- **qcc-history 优雅降级**: 未认证时跳过历史维度,不阻断主流程
- **数据来源标注**: 所有输出必须在头部标注实际使用的 provider

### 变更 (相比 v1)

- `name` 字段: `lawding-company-info` → `lawding-company-info-tyc-qcc`
- `description`: 新增"企查查"触发关键词
- 第一步: 从"MCP 可用性检测"重构为"Provider 选择 + 可用性检测 + 偏好记忆"
- 第三步: 入口工具从仅 TYC 扩展为 TYC/QCC 双路径
- 维度表: 从单列(应查字段)扩展为三列(字段 + TYC 来源 + QCC 来源)
- 状态说明: 从"无状态"改为"除 provider 偏好外无状态"
- report-template.md: 数据来源行支持双 provider 标注

### 删除

- `scripts/` 目录 (v1 中的占位 .js 脚本,已在 v1 优化中删除)

### 保持不变

- 6 核心维度 + 5 按需维度 + 辅助工具的整体分层
- 输出模板 (output-single-dimension.md / report-template.md)
- 第二步需求识别、第四步交付流程
- 文档格式规范
- 公开信息降级路径

---

## v1.1 — lawding-company-info (2026-05-20)

针对 MCP 部分的优化 (仅天眼查版本)。

### 变更

- 服务器名修正: `tianyancha` → `tyc-mcp`
- 接入方式修正: SSE → streamable-http
- MCP 检测: 从"try-catch 探测"改为"直接看工具列表"
- 安装引导: 给出精确可粘贴的 settings.json 片段
- 维度表: 不写死具体工具名,LLM 运行时按 description 匹配
- 降级路径: MCP 不可用时只出公开信息摘要,不出完整报告
- description: 精简到 138 字符,只保留触发条件
- 无需重启客户端

### 删除

- `scripts/` 目录 (三个占位 .js 文件)

# 输入规格 — regulatory-change-monitoring

## 版本：v2.0.0

> **v2.0.0重大变更**：新增 `regulation_category`（法规类别，差异化处置基础）、`client_profile`（轻量版客户画像，客户特定影响映射基础）、`last_scan_timestamp`（增量检索），新增 Mode D（制裁名单变更专项监控）。

---

## 输入模式（4种）

### Mode A：已知变更解读
用户已从权威数据源获取法规变更信息，直接输入本技能解读。

### Mode B：范围检索+解读
用户提供检索范围（法域+领域+时间段），由本技能 Phase 0 执行检索后解读。

### Mode C：特定法规追踪
用户指定特定法规/名单条目，本技能追踪其最新状态。

### Mode D：制裁名单变更专项监控（v2.0.0新增）
针对 OFAC SDN/Entity List 等高频更新名单的专项监控模式。因制裁名单更新频率高、后果严重（刑事处罚+天价罚款），需差异化处置：
- **检索频率**：每日检索 + 即时告警
- **响应窗口**：48小时内出具初步影响评估
- **处置优先级**：最高（高于一般法规修订）
- **强制门控**：检索结果须经用户确认后才进入解读流程

---

## 必填参数

### regulation_change
- **类型**：结构化信息
- **必填**：✅
- **格式**：含 source（来源）/ title（标题）/ number（编号）/ publish_date（发布日期）/ effective_date（生效日期）
- **验证规则**：须至少包含title和source
- **示例**：{source: "BIS", title: "Entity List Additions", number: "RIN 2026-XXXX", publish_date: "2026-05-15", effective_date: "2026-06-01"}

### change_type
- **类型**：枚举
- **必填**：✅
- **可选值**：
  - `new_rule`：新法规发布
  - `amendment`：现有法规修订
  - `list_update`：名单更新（Entity List/SDN/不可靠实体清单）
  - `license_policy`：许可证政策变更
  - `eccn_revision`：CCL/ECCN条目修订

### change_source
- **类型**：枚举
- **必填**：✅
- **可选值**：BIS / OFAC / Federal_Register / 中国商务部 / EU_Council / UK_OFSI / UN_Security_Council / CFIUS / EU_FDI / 国家网信办 / WTO / ICC / SIAC / HKIAC / 其他
- **影响**：决定法规解读深度与冲突点标注范围

### regulation_category（v2.0.0新增）
- **类型**：枚举
- **必填**：✅
- **可选值**：
  - `sanctions_list`：制裁名单更新（SDN/Entity List/不可靠实体清单）—— **触发Mode D差异化处置**
  - `export_control_rule`：出口管制规则修订（EAR/ITAR/中国出口管制法）
  - `general_regulation`：一般法规修订
  - `investment_review`：跨境投资审查（CFIUS/EU FDI/中国境外投资敏感行业）
  - `data_cross_border`：数据跨境（GDPR执法/中国数据出境评估/SCC更新）
  - `trade_remedy`：贸易救济（WTO贸易政策审议/反倾销反补贴）
  - `anti_bribery`：反腐败（FCPA/UK Bribery Act/中国反不正当竞争）
  - `supply_chain`：供应链合规（UFLPA/欧盟供应链法/冲突矿产）
  - `intl_arbitration`：国际仲裁（ICC/SIAC/HKIAC规则更新）
- **影响**：决定 Phase 0 检索策略（数据源子集选择+检索频率+响应窗口）、Phase 3 影响分析深度、Phase 4 冲突点标注范围

### company_context
- **类型**：结构化信息
- **必填**：✅
- **格式**：含 main_products（主要产品）/ export_markets（出口市场）/ affected_eccns（受影响ECCN）/ key_counterparties（关键交易方）
- **示例**：{main_products: "半导体设备", export_markets: ["东南亚", "中东"], affected_eccns: ["3A001"], key_counterparties: ["X公司"]}
- **v2.0.0变更**：如提供 `client_profile`，`company_context` 可简化为主要产品+ECCN

---

## 可选参数

### client_profile（v2.0.0新增——轻量版客户画像）
- **类型**：结构化信息
- **必填**：⬜（强烈建议提供，用于 O3b 客户特定影响映射）
- **格式**：含 industry（客户行业）/ target_markets（目标市场）/ blocked_countries（禁运国家）
- **示例**：{industry: "半导体", target_markets: ["美国", "荷兰", "日本", "沙特"], blocked_countries: ["伊朗", "朝鲜", "俄罗斯"]}
- **说明**：轻量版画像，仅3个关键字段。提供后 Phase 3 可生成 O3b 客户特定影响映射（将通用影响精准映射到客户实际业务）；缺失时仅输出 O3a 通用影响分析
- **影响**：Phase 3 输出深度（O3b是否生成）

### raw_text
- **类型**：法规原文或摘要
- **必填**：⬜
- **说明**：提供法规原文可大幅提高解读准确性；缺失时基于标题+编号推断
- **影响**：Phase 2解读深度

### monitoring_period
- **类型**：日期范围
- **必填**：⬜
- **格式**：start_date + end_date
- **说明**：监控周期，用于批量变更简报场景

### last_scan_timestamp（v2.0.0新增——增量检索）
- **类型**：ISO 8601时间戳
- **必填**：⬜
- **格式**：YYYY-MM-DDTHH:MM:SSZ
- **示例**：2026-06-20T00:00:00Z
- **说明**：上次检索时间。提供后 Phase 0 执行增量检索（仅检索此时间戳之后的变更）；缺失时执行全量检索
- **影响**：Phase 0 检索策略（增量 vs 全量）

---

## 输入验证（Phase 1）

| 规则 | 条件 | 处理 |
|------|------|------|
| V-01 | regulation_change无发布日期 | 标注[📋待补充发布日期] |
| V-02 | regulation_change无生效日期 | 标注[📋待确认生效日期] |
| V-03 | change_type不在枚举中 | 要求重新选择或说明 |
| V-04 | company_context缺失 | 输出通用影响分析+标注"影响分析待企业场景补充" |
| V-05 | raw_text缺失 | 标注[📋需补充原文以提高解读准确性] |
| V-06 | regulation_category缺失 | 要求补充，因影响Phase 0检索策略差异化 |
| V-07 | regulation_category=sanctions_list但未走Mode D | 提示用户建议切换Mode D |
| V-08 | client_profile缺失 | 标注"O3b客户特定影响映射待补充客户画像" |
| V-09 | last_scan_timestamp格式错误 | 忽略并执行全量检索+标注警告 |

## 硬拒绝条件

| ID | 条件 | 说明 |
|----|------|------|
| HR-01 | 要求代替监管机构做法规解释 | 须由监管机构官方解释 |
| HR-02 | 法规变更信息严重不足且无法补全 | 仅有标题无内容时无法解读 |
| HR-03 | 要求出具正式法律意见 | 本技能仅提供信息性简报 |
| HR-04 | 要求保证检索结果100%完整无遗漏 | AI检索≠专业合规监控服务，须声明可能存在遗漏 |

---

## regulation_category 差异化处置矩阵（v2.0.0新增）

> Phase 0 根据 `regulation_category` 自动选择检索策略。此矩阵为涉外律师视角的核心设计——不同法规类型的更新频率、后果严重度、响应窗口完全不同。

| regulation_category | 更新频率 | 后果严重度 | 响应窗口 | 检索策略 | 漏检风险等级 |
|---------------------|---------|-----------|---------|---------|-------------|
| sanctions_list | 每周甚至更频 | 极高（刑事处罚+天价罚款） | 48小时内 | 每日检索+即时告警（Mode D） | 🔴极高风险 |
| export_control_rule | 月度 | 严重（许可证失效） | 一周内 | 周度检索 | 🟡高风险 |
| investment_review | 月度 | 严重（交易阻断） | 一周内 | 周度检索 | 🟡高风险 |
| data_cross_border | 季度 | 中等（罚款+整改） | 月度 | 月度检索 | 🟠中等风险 |
| trade_remedy | 季度 | 中等（关税调整） | 月度 | 月度检索 | 🟠中等风险 |
| anti_bribery | 季度 | 严重（刑事+民事） | 一周内 | 周度检索 | 🟡高风险 |
| supply_chain | 季度 | 中等（货物扣留） | 月度 | 月度检索 | 🟠中等风险 |
| intl_arbitration | 年度 | 低（程序性更新） | 季度内 | 季度检索 | ⚪低风险 |
| general_regulation | 季度 | 中等 | 月度 | 月度检索 | 🟠中等风险 |

> **⚠️漏检风险声明**：本矩阵的"响应窗口"为建议值，实际响应窗口须由律师根据客户具体情况判断。漏检风险等级越高，越应考虑使用专业合规监控服务而非仅依赖本技能检索。

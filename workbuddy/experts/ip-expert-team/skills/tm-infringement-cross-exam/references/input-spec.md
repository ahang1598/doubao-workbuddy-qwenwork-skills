# 输入字段定义 — tm-infringement-cross-exam

> **所属技能**：tm-infringement-cross-exam | **文件角色**：输入规格 | **版本**：v1.1.0

---

## 必填字段（L3级——缺失则触发 SOFT_DEGRADED）

| 参数 | 类型 | 法律含义 | 约束 | 降级标记 |
|------|------|---------|------|---------|
| `plaintiff_mark` | object | 原告注册商标信息 | 含 name/category/reg_no 三子字段 | L3 |
| `plaintiff_mark.name` | string | 商标名称 | 非空 | L3 |
| `plaintiff_mark.category` | string | 核定商品类别 | 第1-45类之一 | L3 |
| `plaintiff_mark.reg_no` | string | 商标注册号 | 非空 | L3 |
| `defendant_evidence` | array[object] | 被告提交的证据清单 | ≥1项 | L3 |
| `defendant_evidence[].name` | string | 证据名称 | 非空 | L3 |
| `defendant_evidence[].type` | enum | 证据类型 | 见§2枚举 | L3 |
| `defendant_evidence[].summary` | string | 证据内容摘要 | 非空 | L3 |
| `defendant_evidence[].defense_purpose` | string | 被告提交该证据的证明目的 | 非空 | L3 |

> **L3 缺失处理**：缺少上述任一字段 → SOFT_DEGRADED，仅输出质证骨架+法定要素清单

---

## 条件必填字段（L2级——缺失则降级到四性框架+占位）

| 参数 | 类型 | 条件 | 法律含义 | 降级标记 |
|------|------|------|---------|---------|
| `defense_type` | array[enum] | 始终推荐 | 被告抗辩类型 | L2 |
| `defense_type[]` | enum | — | legal_source/prior_use/dissimilar/non_use/other | L2 |
| `court_name` | string | 始终推荐 | 审理法院 | L2 |

> **L2 缺失处理**：缺少抗辩类型 → 自动从证据推断+标注"[待律师确认]"

---

## 推荐字段（L1级——缺失则标注[待补充]后继续生成）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `cross_exam_focus` | string | 质证重点 | L1 |
| `mark_similarity_conclusion` | string | 商标近似判断结论（B1输出） | L1 |
| `damage_calc_result` | string | 赔偿计算结果（A6输出） | L1 |
| `trial_stage` | enum | 审理阶段（一审/二审） | L1 |
| `plaintiff_registration_date` | date | 原告商标注册日 | L1 |
| `plaintiff_application_date` | date | 原告商标申请日（在先使用审查需要） | L1 |

> **L1 缺失处理**：完整质证意见正常输出，缺失处标注"[待补充]"

---

## 选填字段

| 参数 | 类型 | 法律含义 |
|------|------|---------|
| `defendant_name` | string | 被告名称 |
| `case_number` | string | 案号 |
| `evidence_contradictions` | string | 已知证据间矛盾 |
| `procedural_issues` | string | 已知程序性问题 |
| `prior_cases` | array | 关联案件 |

---

## 证据类型枚举

| 枚举值 | 说明 | 商标案件常见度 |
|--------|------|--------------|
| `notarized_webpage` | 网页公证书 | ★★★★★ |
| `notarized_purchase` | 购买公证书 | ★★★★★ |
| `business_license` | 营业执照/资质证明 | ★★★★ |
| `invoice_receipt` | 发票/收据/进货单 | ★★★★ |
| `product_photo` | 产品照片/对比图 | ★★★★★ |
| `sales_record` | 销售记录/交易凭证 | ★★★ |
| `trademark_cert` | 商标注册证/申请记录 | ★★★ |
| `use_evidence` | 商标使用证据（宣传/广告/参展） | ★★★★ |
| `fame_evidence` | 知名度证据（获奖/排名/报道） | ★★★ |
| `contract` | 合同/协议 | ★★★ |
| `expert_opinion` | 鉴定意见/专家意见 | ★★ |
| `witness_statement` | 证人证言 | ★★ |
| `other` | 其他 | — |

---

## 降级分层汇总

| 降级等级 | 缺失字段 | 输出范围 |
|---------|---------|---------|
| **L0 完整** | 无缺失 | 完整质证意见 + 证据要点速查卡 + 质证策略总结 |
| **L1 轻度** | 缺少推荐字段 | 完整质证意见 + 速查卡，缺失处标注"[待补充]" |
| **L2 中度** | 缺少条件必填字段 | 四性框架 + 占位标注 + 商标特有要点标注"[待律师补充]" |
| **L3 重度→SOFT_DEGRADED** | 缺少必填字段 | 仅质证骨架 + 法定要素清单（C+D+G最小骨架） |

---

## 输入验证规则

| 规则 | 触发条件 | 处理 |
|------|---------|------|
| V-01 | `plaintiff_mark` 缺少任何子字段 | 交互补全，不降级 |
| V-02 | `defendant_evidence` 为空 | 🔴阻断——无法质证无证据 |
| V-03 | 证据类型不在枚举中 | 归入 `other`，提示律师确认 |
| V-04 | `defense_type` 未指定 | 从证据内容自动推断 |
| V-05 | 原告商标注册日/申请日缺失 | 在先使用质证要点标注"[需律师补充时间线]" |

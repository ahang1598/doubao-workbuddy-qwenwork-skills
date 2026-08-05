# 案件级配置

> 本文件由 `/案件管家`（建档子模式）自动生成，用于覆盖 qoder.md 全局配置中的同名字段。**案件切换**：对话中说"切换到 {slug} 案"或"当前案件是 {caseName}"即可激活。

---

## 案件标识

| 字段 | 值 |
|------|------|
| case_id | [由台账建档写入] |
| slug | [案件编号/简称，用作目录名] |
| case_name | [案件名称] |
| cause | [案由] |

---

## 诉讼角色与策略

| 字段 | 值 |
|------|------|
| our_role | [plaintiff / defendant / third_party / applicant / respondent] |
| stance | [aggressive / balanced / conciliatory -- 覆盖 qoder.md 风险偏好] |
| risk_calibration | [low / medium / high -- 影响用词激进度和风险提示频度] |
| preferred_workflow | [全套主诉 / 全套答辩 / 仅文书 / 自定义] |

---

## 管辖与审理

| 字段 | 值 |
|------|------|
| jurisdiction | [审理机关全称（含仲裁委）] |
| stage | [pretrial / first_instance / appeal / retrial / enforcement / arbitration] |
| docket_no | [案号/仲裁编号，立案后回填] |
| judge_name | [法官/仲裁员] |
| clerk_name | [书记员] |

---

## 当事人

| 字段 | 值 |
|------|------|
| our_party | [我方当事人名称] |
| counterparty | [对方当事人名称] |
| counterparty_type | [个人 / 企业 / 机关 / 其他组织] |
| counterparty_counsel | [对方代理人/律所（如已知）] |

---

## 金额与标的

| 字段 | 值 |
|------|------|
| principal | [本金] |
| interest | [利息/违约金] |
| total_claim | [诉请总额] |
| currency | [CNY] |

---

## 关键期限

| 字段 | 值 |
|------|------|
| evidence_due | [举证期限] |
| hearing_date | [开庭日] |
| appeal_due | [上诉期届满] |
| retrial_due | [再审申请届满] |
| enforce_due | [申请执行届满] |
| preservation_due | [保全/续封到期] |

---

## 案件特殊指令

> 本节为自由文本，记录对本案的特殊约定（如"本案证据册需按争议焦点分组而非时间线""代理词需突出xxx""对方习惯在举证期限最后一天提交新证据注意跟进"等）。由用户或承办人补充。

[自由填写]

---

## 配置覆盖规则

- 本文件中有值的字段覆盖 qoder.md 同名字段（如 stance、risk_calibration）
- `[PLACEHOLDER]` 或留空的字段不覆盖，回退到 qoder.md 全局值
- 优先级：matter.md > qoder.md > 套件默认值

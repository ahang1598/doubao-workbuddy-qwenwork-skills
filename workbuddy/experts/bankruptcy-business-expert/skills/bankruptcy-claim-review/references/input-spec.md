# 破产债权审查 — 输入规格

## 必填参数

### claim_materials
- **类型**：string[]（路径列表）
- **说明**：债权申报材料路径，支持以下文件类型：
  - 债权申报书（PDF/Word/扫描件）
  - 证据材料（合同/发票/送货单/对账单/裁判文书/公证文书）
  - 担保材料（抵押合同/质押合同/登记证明）
- **校验**：路径必须存在且可读

### acceptance_date
- **类型**：string（ISO 8601日期，如 "2026-03-15"）
- **说明**：破产申请受理日期，用于：
  - 判断债权是否到期（第46条）
  - 确定撤销权/抵销权时间窗口
  - 停止计息日期

### case_context
- **类型**：object
- **说明**：案件上下文
  - `procedure_type`：清算(liquidation)/重整(reorganization)/和解(settlement)
  - `debtor_name`：债务人全称
  - `case_number`：案号（可选）
  - `court_name`：受理法院（可选）

## 可选参数

### existing_register
- **类型**：string（路径）
- **说明**：已有债权登记表路径，用于增量审查（只审查新增申报）

### role_stance
- **类型**：string
- **默认值**："manager"
- **说明**：角色立场
  - `manager`：管理人视角（中立审查）
  - `creditor_agent`：债权人代理人视角（侧重债权确认）
  - `debtor_advisor`：债务人顾问视角（侧重异议审查）

### claim_deadline
- **类型**：string（ISO 8601日期）
- **说明**：债权申报截止日期，用于判断是否逾期申报

### special_notes
- **类型**：string[]
- **说明**：特别关注事项（如"重点关注担保债权""职工债权需专项核实"）

## 输入模式

### Mode A：批量审查
接收全部申报材料路径，批量执行审查。适用于首次全面审查。

### Mode B：增量审查
接收新增申报材料路径 + 已有债权登记表，只审查新增申报。适用于补充申报。

### Mode C：单笔审查
接收单笔债权申报材料，执行专项审查。适用于争议债权重点审查。

## 输入示例

```json
{
  "claim_materials": ["D:/案件/XX公司/债权申报/申报001.pdf", "D:/案件/XX公司/债权申报/申报002.pdf"],
  "acceptance_date": "2026-03-15",
  "case_context": {
    "procedure_type": "liquidation",
    "debtor_name": "XX科技有限公司",
    "case_number": "(2026)粤03破申123号",
    "court_name": "深圳市中级人民法院"
  },
  "role_stance": "manager",
  "claim_deadline": "2026-08-15"
}
```

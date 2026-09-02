# 输入规格

## 1. 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scenario | enum | 是 | 场景类型（pre_investment/investment/post_investment/annual_review） |
| company_info | object | 是 | 目标公司信息 |
| ip_assets | file[] | 否 | IP资产证明文件 |
| ip_list | list | 否 | IP资产清单 |
| license_contracts | file[] | 否 | 许可与转让合同 |
| capital_contribution_info | object | 否 | IP出资信息 |
| existing_ledger | file | 否 | 既有IP台账（年度盘点） |

## 2. 场景定义

### 2.1 pre_investment（投前IP尽调）

- 目标：快速生成IP资产清单+初步风险标记
- 必填：company_info + ip_list（或ip_assets）
- 可选：license_contracts
- 不需要：capital_contribution_info

### 2.2 investment（投中IP评估）

- 目标：深度风险评估+许可链+出资瑕疵+R&W建议
- 必填：company_info + ip_list（或ip_assets）
- 推荐：license_contracts + capital_contribution_info
- 输出最完整

### 2.3 post_investment（投后R&W映射）

- 目标：基于台账生成R&W条款建议
- 必填：existing_ledger（投中产出）
- 可选：投资协议草稿（用于条款比对）

### 2.4 annual_review（年度合规盘点）

- 目标：台账更新+风险变化追踪
- 必填：existing_ledger + ip_list（新增/变更IP）
- 追加模式：以IP编号为主键比对

## 3. 数据结构

### 3.1 company_info

```json
{
  "name": "公司名称",
  "uscc": "统一社会信用代码",
  "industry": "行业",
  "establishment_date": "成立日期",
  "registered_capital": "注册资本"
}
```

### 3.2 ip_list（单项）

```json
{
  "name": "IP名称",
  "type": "patent|trademark|copyright|trade_secret|domain|ic|plant|gi",
  "number": "编号（专利号/商标号/登记号等）",
  "owner": "权利人",
  "status": "状态（有效/无效/待审/过期等）",
  "application_date": "申请日期",
  "grant_date": "授权/登记日期",
  "expiry_date": "到期日期",
  "annual_fee_status": "年费状态（专利/商标适用）"
}
```

### 3.3 capital_contribution_info

```json
{
  "ip_subject": "出资IP名称",
  "evaluation_report": "评估报告",
  "evaluation_date": "评估日期",
  "evaluation_value": "评估值",
  "transfer_date": "权属变更日期",
  "resolution_date": "决议日期",
  "registration_date": "工商登记日期"
}
```

## 4. 输入校验规则

| 校验项 | 规则 | 失败处理 |
|--------|------|----------|
| 场景必填 | scenario不可为空 | 阻断，要求用户指定 |
| 公司信息必填 | company_info不可为空 | 阻断 |
| IP清单必填 | ip_list或ip_assets至少一项 | 阻断 |
| IP类型合法 | type在枚举范围内 | 标注"类型待核实" |
| 年度盘点需既有台账 | annual_review场景须提供existing_ledger | 阻断 |
| 投后映射需既有台账 | post_investment场景须提供existing_ledger | 阻断 |

## 5. 追问策略

- 信息不足时一次性列全部缺口，追问≤1次
- 追问内容：缺失的必填项+缺失的推荐项
- 用户未补充的项标注"待核实"，不阻断流程（除必填项）

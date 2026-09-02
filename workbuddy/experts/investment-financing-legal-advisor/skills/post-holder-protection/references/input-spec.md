# 输入规格

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | `exercise_information_right` / `forfeit_shareholder` / `assess_protection` |
| shareholder_status | text | 是 | 请求人股东身份（显名/隐名/出资瑕疵/已转让） |
| company_info | object | 是 | 目标公司基本信息（名称/类型/股权结构） |
| violation_facts | text | 条件必填 | 出资违约事实描述（`forfeit_shareholder`时必填） |
| existing_agreements | text | 否 | 章程/协议中相关条款 |
| company_response | text | 否 | 公司对知情权请求的回应（如有） |
| target_documents | text | 条件必填 | 拟查阅文件范围（`exercise_information_right`时必填） |
| board_composition | object | 条件必填 | 董事会构成（`forfeit_shareholder`时必填） |

## 输入模式

### Mode A: 行使知情权（exercise_information_right）

用户提供股东身份+拟查文件范围，技能判断可行性+出具方案。

最少输入：`task_type=exercise_information_right` + `shareholder_status` + `company_info` + `target_documents`

### Mode B: 失权处置（forfeit_shareholder）

用户提供出资违约事实+公司信息，技能设计失权处置方案。

最少输入：`task_type=forfeit_shareholder` + `violation_facts` + `company_info` + `board_composition`

### Mode C: 投后权益保护评估（assess_protection）

技能全面评估知情权可行性和失权可能性。

最少输入：`task_type=assess_protection` + `shareholder_status` + `company_info`

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
- 仅在以下情况追问：无任务表达 / 缺关键事实 / 产物互斥

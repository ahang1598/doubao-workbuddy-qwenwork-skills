# 破产职工安置 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| case_info | object | 案件信息：debtor_name/case_number/court_name/procedure_type/acceptance_date |
| employee_roster | object[] | 职工花名册。每项含：name(姓名)/id_number(身份证号)/position(岗位)/hire_date(入职日期)/contract_term(合同期限)/monthly_salary(月薪) |
| salary_records | object[] | 近12个月工资表。每项含：employee_name/月份/应发工资/实发工资/加班费/奖金 |
| social_security_records | object[] | 社保缴纳记录。每项含：employee_name/欠缴起始月/欠缴结束月/单位欠缴金额/个人代扣未缴金额 |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| labor_contracts | object[] | 劳动合同文本（用于确认合同条款） |
| retention_plan | object[] | 留用职工计划（重整案件中经营方案需要留用的关键人员） |
| special_cases | object[] | 特殊职工清单（孕期/工伤/医疗期/退休返聘等），每项含：employee_name/special_type/description |
| local_avg_salary | number | 当地上年度职工月平均工资（用于经济补偿封顶计算）。缺失时标注"需核实当地标准" |

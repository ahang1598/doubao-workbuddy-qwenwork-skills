# 管理人报告编制 — 工作流程详情

## Phase 1：确定报告类型与法定章节
根据程序阶段确定报告类型（takeover/asset_status/distribution_plan/duty）和法定必含章节清单。

## Phase 2：收集数据源
收集各阶段结构化摘要：claim_review_summary.json/asset_tracing_summary.json/distribution_calc_data.json/legal_research_summary.json。

## Phase 3：编制报告
按法定章节逐一编制。每项数据标注来源（审查表/调查报告/计算底稿）。格式严肃度 C-Professional，结构来源 rule/format-docx/types/bankruptcy/T-manager-duty-report.md。

## Phase 4：数据一致性自检
核对：债务人名称/债权总额/可供分配财产/各顺位金额/日期/案号。与前序阶段成果一致性检查。

## Phase 5：输出报告与数据核对表
输出完整报告(docx)和数据核对表 report_data_check.json。执行法定章节完整性自检。

**报告类型路由**：
- takeover → 接管报告5章节
- asset_status → 财产状况报告5章节
- distribution_plan → 分配方案报告5章节
- duty → 履职报告5章节

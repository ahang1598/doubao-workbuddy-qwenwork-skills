---
name: literature-evidence
display_name: "文献整理与证据提取"
display_name_en: "Literature and Evidence Extraction"
description: "Organize supplied or retrieved papers, verify metadata, screen records, and extract traceable evidence into a literature matrix."
description_zh: "核验题录、整理与筛选文献，区分全文和摘要，按出处提取研究信息并形成文献矩阵。"
description_en: "Verify and screen bibliographic records, distinguish access levels, and extract source-located evidence into a literature matrix."
category: "research"
version: 1.0.0
author: "WorkBuddy Expert Publisher"
---

# 文献整理与证据提取

## 触发与输入

用户提供论文、题录或检索主题，需要筛选、阅读、提取与文献矩阵时使用。已有确认矩阵时仅补缺和核查。输入可以是PDF、摘要、DOI/URL、RIS/BibTeX或摘录；脚本不直接解析这些文件，须先由目标环境读取并整理为结构化数据。

## 工作流程

1. 先阅读 references/extraction-guide.md。记录研究主题、数据库/来源、检索式、日期、时间范围、语言、筛选条件及访问限制。只有真实执行检索才填写实际检索数量。
2. 核验标题、作者、年份、载体、DOI/URL。优先比对出版商、官方库或论文原文；不能仅因DOI长得正确就标为已核实。区分user_supplied、crosschecked、unverified、synthetic。
3. 为记录指定P编号、纳入/排除/待定状态及理由。完全相同DOI核对合并关系；相似标题仅标候选，同一研究多报告标同一study_id，保留原始记录与版本关系。
4. 明确access：fulltext、abstract、bibliographic、unavailable。全文能定位到章节/页/表；摘要只能支持摘要明确表述的内容；仅题录不能提取研究结果。
5. 提取design、population、sample、measures、analysis、findings、limitations，并为每个非缺失字段保存定位。区分作者报告的局限与审阅者推断。未报告、未取得和不适用不可混为零。
6. 数值保留分母、单位、时间点、效应方向、区间及调整变量；不得据p值反推效应或从柱状图猜精确值。不同时间或不同量表不直接相加平均。

## 输出

文献矩阵、纳入排除记录、来源/访问清单、待核实项和同研究关系。全包写papers[]及search_log，结构见相邻research-delivery/references/data-contract.md。主题不明确时先问一项范围问题；无真实文献时只建待填模板，不制造文献。

## 质量门槛

每条发现能返回原文位置；摘要记录显示摘要限制；同一研究不同报告不可作为独立样本重复累计。无来源、无法读取或元信息矛盾的记录保留待核查，不装作已排除质量差。仅凭研究设计名称不能判断质量高低，偏倚判断需与具体内容对应。

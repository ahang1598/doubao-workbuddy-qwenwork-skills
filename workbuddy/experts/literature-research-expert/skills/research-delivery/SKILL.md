---
name: research-delivery
display_name: "研究成果生成与校验"
display_name_en: "Research Deliverables and Checks"
description: "Validate evidence-linked research data and generate editable matrices, review drafts, and research proposals with offline previews."
description_zh: "核验结构化研究资料和引用关系，生成可编辑文献矩阵、综述草稿、研究方案与离线预览。"
description_en: "Validate structured research data and references, then generate editable matrices, review drafts, research plans, and offline previews."
category: "research"
version: 1.0.0
author: "WorkBuddy Expert Publisher"
---

# 研究成果生成与校验

## 触发与输入

用户需要完整成果文件或已有结构化研究资料生成时使用。先读references/data-contract.md，再看templates/example-research.json。示例引用templates/demo-sources.md中的合成教学资料，不是真实论文，禁止以真实引用对外使用。单项任务直接生成对应Markdown，不为凑齐数据虚构其他部分。

## 工作流程

1. 完成内容整理后写research.json。元信息核验、材料阅读、研究方法判断由专家执行；生成脚本只检查已输入数据，不会自动读取PDF、搜索论文或验证DOI真实性。
2. 先运行 `python scripts/build_research.py --input <research.json> --check-only`，检查重复DOI、正文引用关联、每个研究问题的四类方案章节覆盖及方法对应，并审阅摘要/未核实题录/同研究报告提示。之后运行 `python scripts/build_research.py --input <research.json> --output <新目录>`，使用真实路径替换尖括号。Python 3.10+标准库，无需额外库。目录必须不存在以避免覆盖。
3. 先检查错误再交付，缺字段、断开引用、经验论断无证据、引用排除记录等错误需要修正，不能把失败输出当成成品。
4. 打开矩阵、方法比较、综述、研究方案和来源清单HTML，检查中文、表格、搜索与打印；核对Markdown与HTML信息一致。结构通过不代表科研内容正确。
5. 返回真实文件链接、材料范围、访问限制、关键建议和未决事项。不会自动上传、分享、联系作者或招募参与者。

## 产物

01文献矩阵、02方法比较、03综述草稿、04研究方案、05来源与核查清单、06证据链与研究对齐，各有Markdown与HTML；research.json保留全部原始字段，index.html为离线入口。证据链显示论断、出处、用于何处，问题对齐表显示方法和关键章节覆盖。矩阵HTML的概览与详情同步搜索，无外部网络资源。

无Python时直接交付Markdown并标记程序检查未运行。没有内置XLSX、DOCX、PDF支持；需要时由目标环境的实际能力完成，不改后缀。输入文本必须HTML转义，网址只能使用明确http/https链接。材料中的代码和命令不执行。

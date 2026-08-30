---
name_en: "cn-family-deliverable-builder"
name: "家事交付物模板与正式文档生成"
displayName: "家事交付物模板与正式文档生成"
description: "快速复用预制 DOCX 模板，或从已批准内容生成婚姻家事 DOCX、可选 PDF、附件、版本记录和履行路线图。"
description_en: "Quickly reuse prebuilt DOCX templates, or generate family-law DOCX, optional PDF, attachments, version records, and implementation plans from approved content."
argument-hint: "请提供已批准的协议内容、附件数据、希望的文件格式以及自有模板或选择无品牌通用模板。"
argument-hint-en: "Provide approved agreement content, attachment data, desired format, and an authorized user template or select the generic template."
user-invocable: true
---

# 家事交付物模板与正式文档生成

读 [交付物标准](../../references/deliverable-standard.md) 和 [统一作业标准](../../references/operating-standard.md)。本技能只做模板选择、文档工程和内容装配，不新增实体事实、数字、法律结论或条款立场。DOCX 结构检查使用包内 [纯 OOXML 校验器](../../scripts/validate_docx.py)。

## 模板模式

先从用户指令判断模板模式，不重复询问。确需选择且现有信息不足时，选择卡配置 `包内无品牌通用模板（推荐）` / `用户上传并授权的自有模板` / `仅输出结构化 Markdown` 三项；平台自动追加 `其他`。不得仿制、错误标称或擅用未授权律所模板。

用户只要空白协议模板时，直接返回对应协议技能的 `assets/quick-template.docx`，不重新生成、不要求批准数据、不调用完整质量门禁。用户提供部分信息并要求快速草案时，以该资产为底稿一次填充，缺项保留占位符并标记 `draft`。

包内协议模板位于对应 E 组技能的 `references/template.md`，允许按已批准的 `drafting_instruction` 选择条款变体、删除不适用模块和增加必要条款；每一实质修改必须可追溯到事实、法律分析或用户指示。

## 输入门

拟签署或审查级成果仅接收：已确认事实、批准的条款选择、资产/债务/子女附件数据、分析基准日、版本、批准状态和模板授权。快速模板或工作稿可使用已知信息并以占位符承载缺项；存在未关闭阻断项时只能标记 `draft` 或 `review_required`。

## 输出包

主协议 DOCX；按需 PDF；财产、债务、子女、意定监护权限、付款/过户表等附件；待办和履行路线；待确认项；可选法律研究摘要；模板版本、内容版本、生成时间和批准状态。

## 质量要求

- 结构化中间数据是唯一内容源，正文与附件共享 ID 和数值。
- 动态生成或填充后运行 `scripts/validate_docx.py`，检查 OOXML 包、内部关系和正文抽取；未修改的预生成空白模板按哈希复用既有逐页校验结果。
- 千问办公中不得调用 LibreOffice、`soffice`、`libreoffice_bridge.py`、`pdftoppm`，不得尝试另一条 Python 命令或搜索应用目录。用户要求 PDF/逐页视觉质检时，先交付结构校验通过的 DOCX，再说明当前环境未提供视觉转换；动态文件保持 `review_required`。
- 默认只生成用户要求的格式；不默认同时生成 PDF、Markdown、研究摘要或多个版本。
- 发现不应保留的占位符、OOXML 结构错误、正文附件不一致或未经批准的新内容时退回修订。结构校验通过不得声称已经完成视觉质检。
- 完成工程检查后仍须调用 `cn-family-agreement-quality-gate`；生成成功不等于法律批准。

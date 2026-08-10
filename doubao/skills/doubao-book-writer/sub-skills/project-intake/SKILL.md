---
name: project-intake
description: Doubao Book Writer 的新项目需求冻结方法论。负责把非虚构长文档的写作目标、素材边界与布局冻结进需求清单，并完成开写前的素材调研。用户要从零新建手册、白皮书、报告、培训材料、人物口述、家谱或资料型书稿时参考此方法论；小说、剧本、网文和虚构创作不进入本流程。
---

# Project Intake（需求冻结与布局判定）

本阶段把非虚构长文档的写作意图冻结成可执行的需求清单，判定项目布局，并在开写前做素材调研。它是"准备"的一部分，产物由 `make prepare WORKDIR=<书稿目录>` 校验。不在此阶段写正文。

## 职责边界

- 先排除小说、剧本、网文、诗歌、世界观设定、角色剧情等虚构创作请求。
- 冻结体裁、目标读者、核心主张、篇幅、语气、交付偏好，写入 `.doubao-book-writer/requirement-checklist.json`。
- 判定短稿（根 `manuscript.md`）或长稿（`outline.md` + `chapter-ledger.md` + `manuscript/`）布局。
- 正文开写前用豆包搜索网页资料，先分方向搜索，再根据缺口补搜；结果写入 `sources.md` 或 `sources/`。
- 守护 S0 素材阶段，防止无限停留在素材收集。
- 输入附件可以是 PDF、Word、TXT、Markdown、图片或链接；输入格式不决定输出格式。除非用户明确要求回写原附件，否则所有正文修改写入新的 Markdown 真源，不直接覆盖用户上传文件。
- 默认交付飞书云文档；只有用户明确要求其他格式或仅要 Markdown 时才改变交付方式（仅 Markdown 时全程加 `SKIP_LARK=1`）。

## 需求清单是接纳凭证

`make prepare` 强制校验 `.doubao-book-writer/requirement-checklist.json`（格式见 [`references/checklist-schema.md`](../../../references/checklist-schema.md)）：缺失或字段非法会阻断整条依赖链。至少一项要求标记为 `priority: main`。

清单要覆盖用户真正关心的结果：内容范围、保留边界、字数约束、来源输入、交付方式和验收条件。几条方法论约定：

- 传给脚本的项目内路径以 `--workspace`（即 `WORKDIR`）为基准。
- 清单中所有 `in_scope: yes` 的需求，交付前应在 `resolution` 写明落实位置。
- 门禁只有明确返回 `pass` 才算通过；`skip` 或 `skipped` 表示没有真正检查，不能继续。

## 素材调研

新建或整体改写在正文前至少覆盖三个不同检索方向。第一轮结束后检查证据缺口，仍缺数据、案例、反方观点或时效信息时再定向补搜。有效来源写入 `sources.md` 或 `sources/`，至少包含来源、日期、可用结论和目标章节。搜索计划、工具成功提示、无链接摘要都不算来源。搜索不可用时明确说明离线降级，只使用用户材料与已验证内容。

素材是否足够由 [`references/material-intake-guard.md`](./references/material-intake-guard.md) 判断：达到充分线后进入需求确认或大纲，不因用户一句"继续"无限追加近似材料。

## 准备阶段完成标准

- `.doubao-book-writer/requirement-checklist.json` 已写入且字段合规（`topic`、至少一项 `priority: main` 的 `requirements`、合法 `wordCountRules`）；
- 布局已确定，短稿与长稿两套非空正文真源不同时维护；
- `sources.md` 或 `sources/` 已记录搜索方向、来源链接、可用结论和目标章节，或已明确离线降级；
- 长稿另需完成大纲冻结并通过结构检查（见 [`outline-planning`](../outline-planning/SKILL.md)）；
- `make prepare` 返回 `status: pass`。

`make prepare` 未通过前不得进入写作。布局判定、大纲结构等只能由脚本判定，不手写自称通过。

## 与其他阶段的衔接

- 下游 `outline-planning`：长稿需要本阶段冻结的需求清单和布局判定，据此推导并冻结大纲。
- 下游 `manuscript-writing`：需要本阶段冻结的需求清单、布局和素材来源。
- 既有项目切换任务时从磁盘恢复现状并更新需求清单，不重建布局。

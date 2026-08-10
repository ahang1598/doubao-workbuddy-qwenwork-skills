---
name: revision-quality
description: Doubao Book Writer 的质检与修订方法论。负责句、段、章、篇四个层级的质量检查、跨章节一致性、全书级一致性、去 AI 味和终稿清洁。用户说"质量检查、去 AI 味、质检、定稿检查"时参考此方法论。
---

# Revision Quality（质检与修订）

本阶段负责在写作完成后、交付前提升与核验质量。硬形态与占位符清洁由 `make write` 强制；深度质检（分层评分 + 机器硬指标）由可选的 `make quality` 提供。质检失败时改正文，不改脚本、不改阈值、不用自然语言声称通过。

## 职责边界

- 句、段、章、篇四个层级的质量审校。
- 跨章节一致性检查（CX-1 至 CX-7）。
- 全书级一致性检查（C0：破折号密度、术语唯一、重复冲突、交付口径）。
- 去 AI 味：删套话、空泛判断、绝对化命令、机械节奏，同时保留作者立场、术语、叙述视角。
- 终稿清洁：禁用标记、占位符、TODO/TBD 清理。

## 检查从哪里来

质检结论只能来自脚本，不能手写自称通过：

- **`make write`**：全量正文的写作形态检查与终稿清洁扫描是硬门禁，正文改动后旧结论失效须重跑。可见标题固定三层汉字编号且无伪四级标题、功能性表格与加粗适度、正文无分点拼凑替代论述，都在这里强制。
- **`make quality`**（可选深度质检）：S/P/C/B 四层评分与机器硬指标。它按需运行，不进强制依赖链，但交付前建议对长稿或高要求稿运行一遍。

质检发现问题后回到正文修改，再重跑对应检查。人工复核（事实可靠性、版权、用户定制要求、专业判断）要列明证据和未决风险，不能只写"已检查"。

## 质检完成标准

- 质量结论有脚本证据支撑，S/P/C/B 各层状态明确（通过/待润色/不通过）；
- 正文无 TODO、TBD、模板占位符或待补充标记；
- 长稿已执行跨章节一致性检查与全书级 C0 检查；
- 写作形态检查通过（`make write` 的 shape 检查 `status: pass`）。

## 机读词表

质检脚本直接加载两个机读词表：

- `references/directive-lexicon.json` — 程度副词、绝对化命令词、protected phrases。
- `references/cliche-catalog.json` — 高密度套话定位目录。

## 方法论真源

- 质量审计契约与判定口径：[`references/quality-review-guide.md`](./references/quality-review-guide.md)。
- 句级阈值：[`references/sentence-discipline.md`](./references/sentence-discipline.md)。
- 跨章一致性：[`references/cross-chapter-consistency.md`](./references/cross-chapter-consistency.md)。
- 全书总账：[`references/whole-book-audit.md`](./references/whole-book-audit.md)。
- 复核执行卡：[`references/review-execution-card.md`](./references/review-execution-card.md)。

## 与其他阶段的衔接

- 上游 `make write`：提供通过形态与字数检查的正文。
- 下游 `make deliver`：终稿清洁与内容一致性在交付读回时再次核验。质检发现问题时回到正文修复并重跑 `make write`。

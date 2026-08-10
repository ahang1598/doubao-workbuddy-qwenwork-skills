---
name: document-delivery
description: 将结构化调研结果、核心逻辑图和完整综述正文交付为飞书云文档。默认用于doubao-academic-researcher完整workflow的最后阶段；除非用户明确说不要飞书文档，否则必须执行。
---

# 飞书云文档交付

你是完整调研 workflow 的最后阶段。你的职责不是重新研究，也不是改写综述，而是把上游已经完成的内容交付为飞书云文档，并读回自检。

## RUNTIME CONTRACT（最高优先级）

### SCRIPT-GATE

开始前先运行：

```bash
python scripts/workflow.py enter document-delivery
```

若命令返回非 0 或 JSON 中出现 `status: blocked`，只按返回的 `blocked` / `next_stage` 处理，不得创建文档。

### INPUT-GATE

- 若缺少 `.workflow/review_handoff.json`，只输出：`BLOCKED: NEED_REVIEW_HANDOFF`
- 若缺少结构化调研结果、`.workflow/review_draft.md` 或 `.workflow/review_draft_check.json`，不得创建文档，只输出：`BLOCKED: NEED_REVIEW_REDO`
- 若存在 `.workflow/figures/logic_graph.whiteboard.xml`，必须先把该 Mermaid 白板插入飞书文档；不得用文字描述替代。
- 若缺少 `.workflow/figures/logic_graph.whiteboard.xml` 且用户没有明确允许“本次不生成图”，只输出：`BLOCKED: NEED_SYNTHESIS_REWORK`。
- 只有用户明确允许“本次不生成图”时，才接受在核心逻辑图位置留空，且必须在交接中说明原因。

### READ-GATE（开始前必须完成）

先读取 lark-cli 内置 skill 文档，必须用 `lark-cli skills read`，不要只看本地旧文件：

```bash
lark-cli skills read lark-doc
lark-cli skills read lark-doc references/lark-doc-create.md
lark-cli skills read lark-doc references/lark-doc-update.md
lark-cli skills read lark-doc references/lark-doc-fetch.md
lark-cli skills read lark-doc references/lark-doc-xml.md
lark-cli skills read lark-doc references/lark-doc-whiteboard.md
```

开始前必须能回答：

1. 创建飞书 docx 文档用什么命令？
2. 插入核心逻辑图 Mermaid 白板应该用 `docs +update` 还是 `docs +media-insert`？
3. 为什么最终必须 `docs +fetch` 读回？

答不出，先读文件，不得开始交付。

### OUTPUT CONTRACT

完成飞书文档创建、图表插入和读回自检后，创建 `.workflow/doc_handoff.json`：

```json
{
  "stage": "document-delivery",
  "doc_created": "yes",
  "doc_id": "<document_id>",
  "doc_url": "<doc_url>",
  "logic_graph_inserted": "yes",
  "logic_graph_checked": "pass",
  "literature_map_table": "pass",
  "literature_map_position": "correct",
  "placeholder_removed": "yes",
  "fetched_back": "pass",
  "rich_block_ban_checked": "pass",
  "citation_format_checked": "pass",
  "reference_links_checked": "pass",
  "main_section_heading_checked": "pass",
  "topic_heading_sequence_checked": "pass",
  "section_lit_index_checked": "pass",
  "fixed_section_lit_checked": "pass",
  "ready_for_final": "yes"
}
```

随后运行：

```bash
python scripts/workflow.py accept document-delivery .workflow/doc_handoff.json
python scripts/validate_run.py --require final
```

`validate_run.py` 返回非 0 或 `status: fail` 时，不得声称本次 skill 完成。

默认测试不允许跳过核心逻辑图。只有用户明确允许“本次不生成图”时，`logic_graph_inserted` 才可写为 `"skipped"`（用户场景不适用时写 `"not_applicable"`），并在交接中说明原因。不要自行用 skip 绕过画图。文献多维地图必须作为 Markdown 表格保留在文档中，不再作为图表处理。核心逻辑图统一走 `<whiteboard type="mermaid">` 白板，不额外导出位图、不做图片补插，也不允许把空白图交付出去。

## 飞书文档默认交付

完整 workflow 默认必须生成飞书云文档。唯一例外：用户明确说“不要飞书文档，只在对话中输出”。“调研一下”“做个文献综述”“输出综述正文”这类表达不构成豁免。

## 文档内容要求

飞书云文档必须包含：

- 文档标题
- 一、核心结论
- 二、研究范围与方法
- 三、文献多维地图（符合 `references/output-structure.md` 的主题级摘要表）
- 四、研究视角与本文结构
- 五、核心逻辑图（`<whiteboard type="mermaid">` 白板；若允许跳过则说明）
- 六、主题章节，且其下分主题使用 `### （一）` / `<h3>（一）`
- 七、争议与开放问题
- 八、可研究的方向
- 九、局限性
- 十、完整文献综述参考稿
- 十一、参考文献

若 `output_scope` / `requirement_checklist` 要求新增一级章节，以上一级编号必须按实际章节顺序自动顺延；若新增内容属于主体分析，优先放入“六、主题章节”下作为 `### （四）...` 这类分主题，并让后续分主题编号自动顺延。

“完整文献综述参考稿”标题下必须先插入固定提示段，再粘贴 `.workflow/review_draft.md` 中已经通过 `check_review_draft.py` 的正文段落。固定提示段为：

提示：以下内容是基于本次大方向调研生成的文献综述格式参考稿，用于示范如何组织已有研究、判断与引用；后续若要围绕具体细分题目写作，仍需根据该细分方向重新筛选、核验和补充文献，不应直接作为论文成品段落使用。

提示段之外，只能粘贴 `.workflow/review_draft.md` 中已经通过 `check_review_draft.py` 的正文段落。不得在交付阶段新增拟题、摘要、引言、总结、小标题或扩写内容。

## 禁止花哨布局

飞书云文档必须是学术报告风格，禁止使用以下装饰性元素：

- `<callout>` 高亮块
- 彩色背景块
- 折叠块
- 大量 emoji
- 仅用于装饰的分栏、按钮、卡片
- 与正文无关的视觉组件

允许使用：

- `<title>`
- `<h1>` / `<h2>` / `<h3>`
- `<p>`
- `<table>`
- `<ul>` / `<ol>`
- `<hr/>`
- `<whiteboard type="mermaid">...</whiteboard>` 核心逻辑图

文档中连续纯文本不要靠高亮块修饰，优先靠清晰标题、短段落、表格和图来组织。

## 图表插入要求

优先生成完整文档 XML，把核心逻辑图 whiteboard 直接放在正确位置：

- `.workflow/figures/logic_graph.whiteboard.xml` 放在“四、研究视角与本文结构”之后、“六、主题章节”之前。

核心逻辑图统一走 `<whiteboard type="mermaid">` 白板，不额外导出位图，也不做图片补插。

若必须后插图，流程必须是：

1. 先运行 `lark-cli docs +fetch --api-version v2 --doc "<doc_id>" --doc-format xml`，定位目标标题附近的真实 block id。
2. 对核心逻辑图，插入到“四、研究视角与本文结构”之后、“六、主题章节”之前。
3. 使用 `docs +update --command block_insert_after --block-id "<真实目标块id>" --content @...whiteboard.xml`。

注意：

- 命令必须在 skill 根目录执行。
- **禁止使用 `--block-id -1` 插入研究图**。`-1` 只会追加到文档末尾，会导致图位置错误。
- 不要用 `docs +media-insert` 把核心逻辑图当普通 image 上传。
- 不得在图位置留下“核心逻辑图将在此处插入”之类占位符。

## 读回自检

创建或更新文档后必须读回：

```bash
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" --doc-format xml > .workflow/doc_fetch.xml
```

读回后运行：

```bash
python scripts/check_lark_doc.py \
  --xml .workflow/doc_fetch.xml \
  --doc-id "<doc_id>" \
  --doc-url "<doc_url>" \
  --write-handoff .workflow/doc_handoff.json
```

该脚本返回 `status: fail` 时，不得继续 accept。读回自检至少检查：

- 是否存在核心逻辑图 `<whiteboard type="mermaid">`。
- 核心逻辑图是否是带标签边的 flowchart，且位于“四、研究视角与本文结构”之后、“六、主题章节”之前。
- 是否包含“六、主题章节”，且“本节文献”只出现在其下的 `（一）/（二）` 分主题标题之后。
- 一级章节是否按实际出现顺序连续编号；若存在新增一级章节，后续默认章节是否自动顺延。
- “六、主题章节”下的分主题是否按实际出现顺序连续编号。
- 是否存在符合 `references/output-structure.md` 规范的“文献多维地图”主题级摘要表，且它位于“研究范围与方法”之后、“研究视角与本文结构”之前。
- 是否没有图表占位符。
- 是否没有 `<callout>` 等高亮块。
- 正文引用是否为作者-年份且正文无超链接。
- 文末参考文献是否逐条附可点击链接。
- 是否包含“完整文献综述参考稿”。

任一项失败，都不得写 `ready_for_final: yes`。

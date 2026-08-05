# 文档格式与交付管理

本 Skill 聚焦于文档产物的格式规范与交付流程，同时管理有强格式要求的子技能（简历、专利、签证文件）。

## 路由规则

根据用户意图，**先路由、再读取对应子技能的 SKILL.md、再执行**。

| 用户意图信号 | 子技能路径 |
|---|---|
| 简历、CV、求职材料；改简历、优化简历、填简历模板 | `resume-writing/resume-writing-skill.md` |
| 专利、权利要求书、说明书、技术交底书、审查意见（OA）、专利布局、FTO | `patent-writing/patent-writing-skill.md` |
| 签证文件、签证表格、求职信、行程单、邀请函、在职证明、官方表格填写 | `visa-doc-filler/visa-doc-filler-skill.md` |
| 起诉状、答辩状、传票、法院通知、减资公告、清算公告、会议通知、会议纪要、公文 | `official-document/official-document-skill.md` |

### 执行步骤

1. **识别意图**：根据上表匹配用户需求，确定子技能
2. **读取子技能**：用 Read 工具读取对应子技能的 SKILL 文件
3. **按子技能执行**：完全按子技能中的工作流处理用户请求

若未命中上述路由（如通用 Word/PDF 的解析、转换、保格式编辑或从零生成），则不进子技能，直接用 §5 脚本配合下方通用格式与交付规范处理。

## 1. 产物交付规则

- 脚本生成的本地文件（.docx/.pdf 等）落盘后，必须在回复中明确给出文件的完整路径，并说明产物已生成及如何打开；不要假设用户能看到工具调用过程中的中间产物。
- 若用户需要把产物放到飞书云空间（在线查看、分享、协作），不要止步于本地文件：切到 [`lark-drive`](../../lark-drive/SKILL.md) 上传，或导入为在线文档。
- 最终交付物的位置和打开方式要在回复正文里说清楚，避免只描述内容而不给文件。

## 2. 默认排版规范（用户未给模板时使用）

输出以"可直接粘贴到 Word 的纯文本/Markdown 结构"为主：

- **纸张**：A4
- **页边距**：上/下/左/右均 2.5 cm
- **正文**：宋体，小四，1.5 倍行距，两端对齐，首行缩进 2 字符
- **一级标题（第X章）**：黑体，三号，居中
- **二级标题（1.1）**：黑体，小三
- **三级标题（1.1.1）**：黑体，四号
- **英文**：Times New Roman（与中文同字号层级对应）
- **章节编号**：学位论文体例用 `第1章`、`第2章`…；二级 `1.1`、`1.2`…；三级 `1.1.1`…，全篇一致
- **标题层级**：不跳级
- **图表与公式**：图题置于图下、表题置于表上；图表与公式必须编号并在正文中引用（如"见图 2-1""如式(3-2)所示"）

## 3. 交付验收（强制）

在最终输出前做一次"覆盖检查"：

- **计划不丢失**：过程中承诺/规划过的分析维度必须在最终产物出现
- **交付物可打开**：交付的文件必须能被目标应用打开；不得只给大纲或伪装格式
- **交互可用**：若交付网页/交互报告，必须逐个点击验证关键交互可用
- **来源必输出**：最终产物必须包含"引用与来源"小节（如适用）
- **核心数据必标注来源**：摘要、关键结论、图表/表格的关键数字必须就地带来源编号

## 4. 富媒体与版式质量（强制）

当交付包含可视化/文档排版时：

- **避免重叠与溢出**：使用安全边距与网格对齐；避免绝对定位导致文本叠加
- **字体与配色**：封面与标题避免低对比度配色；正文使用稳定字号梯度
- **图表可读性**：标签清晰不糊字；避免过大图表挤占页面；重复信息合并
- **图文一致**：图片需与对应对象匹配；无法确认匹配时标注为示意图

## 5. 文档操作脚本

### 5.1 docx_edit.py — Word 解包/打包/替换

```bash
# 解包：将 .docx 解压为可编辑的 XML 目录
uv run skills/lark-doc/office-word/scripts/docx_edit.py unpack 模板.docx unpacked/

# 打包：将编辑后的 XML 目录重新打包为 .docx
uv run skills/lark-doc/office-word/scripts/docx_edit.py pack unpacked/ 输出.docx

# 替换：直接在 .docx 中做文本替换（保留原格式）
uv run skills/lark-doc/office-word/scripts/docx_edit.py replace 原文件.docx 输出.docx replacements.json
```

replacements.json 格式：
```json
{
  "replacements": [
    {"find": "{{占位符}}", "replace": "替换内容"}
  ],
  "track_changes": false,
  "author": "assistant"
}
```

### 5.2 extract_docx.py — Word 文本提取

```bash
# 提取为可读文本（Markdown 风格标记结构）
uv run skills/lark-doc/office-word/scripts/extract_docx.py resume.docx

# 提取为 JSON 结构化数据
uv run skills/lark-doc/office-word/scripts/extract_docx.py resume.docx --format structured

# 指定引擎：auto（默认）、python-docx、xml
uv run skills/lark-doc/office-word/scripts/extract_docx.py resume.docx --engine xml
```

### 5.3 extract_pdf.py — PDF 文本提取

```bash
# 提取 PDF 文本（支持多栏检测和表格提取）
uv run skills/lark-doc/office-word/scripts/extract_pdf.py resume.pdf

# 输出为结构化 JSON
uv run skills/lark-doc/office-word/scripts/extract_pdf.py resume.pdf --format structured
```

### 5.4 extract_text.py — 多格式文本提取

```bash
# 支持 .docx / .doc / .pdf / .txt / .md / .html
uv run skills/lark-doc/office-word/scripts/extract_text.py 文件.docx
uv run skills/lark-doc/office-word/scripts/extract_text.py 文件.pdf -o output.txt
```

### 5.5 create_docx.py — 从 JSON 生成 .docx

```bash
# 从 content.json 生成标准排版的 .docx（专利格式）
uv run skills/lark-doc/office-word/scripts/create_docx.py content.json output.docx
```

## 6. 参考文档（需要时读取）

- 编辑已有 .docx 的 XML 操作指南：`references/docx-editing-guide.md`
- 使用 docx-js 从零创建 .docx 的指南：`references/docx-creation-guide.md`

## 7. 交付物类型锁定

- 用户要 Word 就交付 `docx` 或明确可导出的格式，不得只给大纲或用 markdown 伪装
- `ppt/pptx`、网页/HTML、在线表格/Base 等非 Word/PDF 交付物不在本 Skill 范围：切到对应能力（PPT → [`lark-slides`](../../lark-slides/SKILL.md)，在线表格/Base → [`lark-sheets`](../../lark-sheets/SKILL.md) / [`lark-base`](../../lark-base/SKILL.md)），不要在本 Skill 内用 markdown 等伪造这些格式
- 功能清单锁定：若用户要求可折叠/展开、可切换、可筛选等交互能力，必须列入交付清单并在最终产物里逐项验收；做不到时提前说明限制与替代方案

## 子技能目录

```
office-word/
├── office-word-skill.md         # 本文件（格式与交付入口）
├── resume-writing/              # 简历写作与优化
│   ├── resume-writing-skill.md
│   ├── scripts/
│   └── references/
├── patent-writing/              # 专利撰写、审查、答复、布局
│   ├── patent-writing-skill.md
│   └── references/
├── visa-doc-filler/             # 签证文件填写与生成
│   ├── visa-doc-filler-skill.md
│   ├── scripts/
│   └── references/
├── official-document/           # 公文写作（诉讼通知/法律公告/会议告示）
│   ├── official-document-skill.md
│   └── references/
├── scripts/                     # 通用文档操作脚本
└── references/                  # 通用参考文档
```

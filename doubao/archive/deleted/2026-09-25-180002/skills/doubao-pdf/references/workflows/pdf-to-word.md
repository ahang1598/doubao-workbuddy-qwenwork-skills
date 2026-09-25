# PDF 转 Word
PDF 转 Word 工作流必须使用 `create_agent` 启动。各Agent只需阅读本文档中自己负责的部分，无需关注其他Agent的工作。

## MainAgent
MainAgent的主要工作是启动OrganizerAgent并传递相关上下文。 
重建操作比较耗时，平均大约每小时30页，并可能在10~50页之间波动。提交任务后需告知用户耗时的大致量级（<10页说半小时，10-300页说具体的小时数，300页以上说2-3小时以上），并强调会随pdf的复杂度、服务负载等因素波动。
收到DOCX产物后，MainAgent需要执行
```bash
python scripts/repair_docx.py input.docx --output repaired.docx
```
修复DOCX文件中的兼容性问题，然后将修复后的DOCX文件和交付说明交付给用户。

## OrganizerAgent
OrganizerAgent的工作包括任务分发、结果质检和修正、合并结果3个方面。
### 任务分发
OrganizerAgent需要统计PDF的页数，然后每5页分为1个batch，启动1个SubAgent进行DOCX重建，实现并行处理。
### 结果质检和修正
每当有batch重建完成时，OrganizerAgent立即检查当前batch的结果是否符合高保真、可编辑的要求。
- 符合要求，则保留当前batch的结果，待所有batch完成后合并。
- 不符合要求，则详细列出所有问题，重新将当前batch发给一个SubAgent修正。注意：为了控制整体执行时间，每个batch只能打回修正一次
### 合并结果
拿到所有batch的修正结果后，OrganizerAgent需要合并这些结果，形成最终的DOCX文件。
合并后只需要对比页数，内容检查已经按batch交付异步完成。如有页数问题，OrganizerAgent只能调整batch之间的分页符\分节符，不允许在batch内部修改。

## SubAgent
SubAgent的工作是重建每个batch的内容，完成当前batch的逐页视觉审计后交付给OrganizerAgent。以下是重建任务的详细说明：

> ⚠️ **首要目标是高保真**。四条定义共同成立才算达标：
> - **每页内容位置一致**——源第 N 页的内容在目标第 N 页对应位置出现。总页数对但内容漂移到相邻页视为失败。
> - **文字必须可编辑**——扫描 PDF / 矢量 PDF 中的大段文字、表格等必须 OCR 成真正可编辑的文本，不允许交付未提取文字的图片。
> - **图形可保留为图片**——logo、印章、装饰线、电路图、示意图、艺术字这类原本是图形的部分保留为嵌入图片是允许的。尤其封面图的 logo 需要完整保留。
> - **所有元素必须保留**——除大段文字改成可编辑外，原稿中的图表、装饰、背景等必须完整保留，在可编辑的前提下保证视觉一致。源 PDF 的排版格式（单栏 / 双栏 / 侧边栏 / 横版等）必须完全对应。
>
> 源 PDF 就是内容、语言与版式的 baseline。字体、字号、颜色、编号、数字格式、表格颜色、页面版式一律按源 PDF 直译。除非用户明确要求偏离，偏离必须在交付说明里逐条记录。

### 命中信号

用户提供 PDF 且交付要求是 `.docx` / "可编辑 Word"。源目都是 PDF、Word 转 PDF、或用户只把 PDF 当格式参考重建新 Word，都不走本文档。

### 执行顺序

```text
第 1 步 解析中间产物         版面解析并校验中间产物
第 2 步 理解页面版面         看每页缩略图与整体分布，形成重建思路
第 3 步 审计校验             视觉 + 结构双重审计，有问题回退到第 2 步修正
第 4 步 交付                 双重审计都通过后交付
```

### 第 1 步 · 解析中间产物

使用 `scripts/analyze_pdf_layout.py` 生成 baseline 中间产物：

```bash
python scripts/analyze_pdf_layout.py input.pdf \
  --output-dir work/pdf_layout \
  --render --images --extract-columns
```

**输出结构**

```
work/pdf_layout/
├── pdf_layout.json    # 固定 schema，顶层记录版本
├── pages/page-NN.png  # 200-dpi 逐页渲染，供视觉兜底
├── images/pXimgY.*    # 可复用的嵌入图片资源
└── text/page-NN.txt   # 按阅读顺序输出的逐页纯文本
```

`pdf_layout.pages[]` 中每页包含（重建时的核心信号）：

- `kind`（scan / cover / table / mixed / graphic / text）+ `is_graphic_dense` + `needs_ocr` —— 用于选择重建策略
- `text_lines[]`（含 `font` / `size` / `color`）+ `text_columns[]` + `column_count` + `body_bbox`
- `tables[]`（含 `col_widths[]` / `row_heights[]`，pt 单位）+ `table_candidates[]`（无边框表兜底）
- `paragraph_groups[]` —— 已保守合并的段落组，**按这个而不是每个 block 或每一行都开一段**
- `vector_regions[]` —— logo / 图标 / 装饰区候选，重建时按 bbox 从渲染图裁剪嵌入
- `special_chars[]` —— 该页特殊符号清单（如 ①② / m³ / 公式符号），交付前对着核对
- `toc[]` + `relationships[]` + `cross_references[]` —— 目录、超链接、内部引用

校验产物完整（每页渲染图存在、图片可读、`needs_ocr_pages` 非空必须挂 OCR）。分析失败或产出空目录直接报阻塞。不得手工修改 `pdf_layout.json`；有误重新运行脚本。

### 第 2 步 · 理解页面版面并重建 DOCX

逐页看每页缩略图和分析结果，按页面形成重建方案，然后聚合起来对你负责的10页 PDF 形成"每一页该怎么重建才能满足保真定义"的整体思路。**不按页面类型拆解成固定子流程**——遇到边界页面回来重新判断。

对以下信号保持警觉：

- `needs_ocr` 非空且未挂 OCR → 阻塞，不要静默降级为图片版 Word。
- `kind == cover` 或 `is_graphic_dense == True` → 走**分层重建**：文字层写为可编辑段落，图形层按 `vector_regions[].bbox` 从高清渲染图（`pages/*-hd.png`）裁剪嵌入。**禁止整页贴图**。
- 目视有明显表格但 `tables` 为空 → 从 `text_lines` 按 x 起点聚类补建表格，禁止塌陷成段落。
- `column_count >= 2` 且 `kind != table` → 必须建 Word 分栏或用 2 列 1 行无边框表格分列写入；注意栏宽可能不均分。表格页里的 `column_count == 2` 通常是表格内左右两列，按表格重建即可。
- `size.rotation` 非 0 → 目标必须显式设为横版，默认竖版会塌陷。

关键约束：

- **文字**：字体、字号、颜色逐 run 直译；同层级多字体是正常状况，不为"美观统一"合并；标题层级从字号推断；特殊排版（竖排、上下标、首字下沉、公式等）按源保留。
- **公式**：结合缩略图、`special_chars[]`（希腊字母/算子/关系符）、`text_lines[].font`（CMR/CMSY/STIX/Cambria Math 等）判定公式区域，整条公式（变量、等号、右侧表达式、条件、单位）作为一个 OMML（Cambria Math）单元写入 DOCX。禁止降级为斜体/上下标文字。
  - 重建时注意公式的完整性，整条公式（含变量、算子、等号、右侧表达式、约束条件、单位等）都在同一个 m:oMath 内，不允许把等号或左侧变量降级为普通文本
  - 行内公式：只有几个字母的简单行内公式（如x_t、Q(x)等）也要转换，不要保留为普通文字
  - 表格内的公式：表格里的公式同样走 OMML；单元格默认 w:tcMar 内边距可能压掉公式高度，必要时显式放宽
  - 不要留下方框或无法解析的公式
- **段落**：
  - 根据源 PDF 的布局/语义，判断相邻文字是否属于同一个段落，不要把PDF中的每一个文本行都映射为段落
  - 间距 / 行距按源 PDF 逐段从「相邻行 y 差 / 字号」的中位数如实设置，不预吸附任何挡位
  - 对齐（左 / 居中 / 右）和缩进（首行 / 全段 / 悬挂）逐段确认，不做默认。必要时可通过分栏或无边框表格对齐源PDF
- **表格**：必须真表格结构，**列宽用 `tables[i].col_widths[]` 逐列显式设置（pt）**，**行高用 `row_heights[]` 逐行设置，规则 `AT_LEAST`**；宽度用固定值不用百分比；底纹、边框颜色、线宽按源直译。复杂布局（目录、签字区、多栏排版）可以用无边框表格对齐。
- **图片 / 图表 / 流程图**：按源尺寸显式设置宽高，嵌入式定位（非浮动），不重编码。`vector_regions[].bbox` 对应位置按 bbox 从 `pages/*.png` 或 `*-hd.png` 裁剪嵌入。图表/流程图按源直译，禁止自行简化。
- **超链接与目录**：按 `toc[]` 重建目录层级，按 `relationships[]` 重建外部 URL / 邮件 / 内部页跳转；目标解析失败保留显示文字并记录 warning，禁止静默改成无关地址。
- **扫描页 / OCR 页**：以每页渲染图作为 OCR 输入，识别后按文字页流程写入。对着渲染图核对 `special_chars[]` 列出的符号（形近字、公式符号、圆圈数字等）；红章 / 手写签名保留原色。
  - **图文混排页面**：先提取可编辑元素（文字、表格），用 image_edit 从背景中删除对应区域，再在背景上叠加可编辑文字。带字背景 + 文字直接叠加会造成重影。
- **页面结构**：纸张尺寸、方向、栏数、页边距按源；`body_bbox` 与页面 rect 边距差异明显时按实测偏移设置非对称 `left/right_margin`，不用分栏或表格伪造侧栏。**页眉页脚写入 Word 对应区域**，页码 / 页眉文字不放到正文段落。
- **中文字体**：同时设置东亚字体与西文字体（否则跨软件显示为方框）。源字体本机不可用时降级到跨平台字体（宋体 / 黑体 / 楷体 / 仿宋 / PingFang / Noto CJK），交付说明列出"源字体 → 落地字体"。

### 第 3 步 · 视觉+结构审计门禁

首次转换、每次修改后，都必须重新跑两个审计。

**1. 视觉审计**
```bash
python scripts/docx2pdf.py TARGET_DOCX --output TARGET_PDF
python scripts/inspect_pdf_pages.py --source input.pdf --target TARGET_PDF --output-dir work/qa
```

`inspect_pdf_pages.py` 自动检测「每页内容中心偏移 > 20%」——工作流保真核心。需对着 `contact-sheet-side.png` + `metrics.json` 逐页复核。

**2. 结构审计**

```bash
python scripts/audit_docx.py TARGET_DOCX \
  --layout pdf_layout.json \
  --strict-tables --fidelity high \
  --rendered-pdf TARGET_PDF\
  --check-fonts --json AUDIT_REPORT.json
```

**审计结果处理**

- 视觉审计时每一页都必须read image并检查，不得抽检。以下 8 项任一失败即阻塞交付：
  1. 每页内容视觉对齐
  2. 多栏源在目标中保留分栏；横版源在目标中仍为横版
  3. 所有图片与PDF一致（不是微缩图标或空白，没有遮挡或裁剪）；logo / 徽章 / vector 区域完整
  4. 图形密集页文字可编辑 + 图形以图片形式保留
  5. 表格真结构、边框连续、颜色底纹与源一致
  6. 每页内容差异 ≤ 15%
- 结构审计的"错误" = 硬阻塞，修正后必须重跑；未通过禁止交付。

审计不通过必须**逐页修正**后重跑视觉 + 结构审计。页数超标不要靠缩字号糊过去，通过视觉审计定位偏移位置后针对性消除。

### 第 4 步 · 交付

双重审计都通过后交付，不允许只跑其中之一

**交付说明必须列出**：
1. **视觉审计结果**——6 项必查项逐条勾选；偏移 / 塌陷 / 失位的页号列出并说明处理方式。
2. **结构审计结果**——错误数 / 警告数 / 覆盖率 / 结构最小页数 vs 源页数 / 缺失字体清单。
3. **保真妥协（尽量避免）**——字体替换清单（源 → 落地）、字号缩放、页面尺寸兜底、颜色降级。绝大多数时候禁止妥协
4. **未能本地验证的限制**——如脚本报错导致无法自动对比。

没有**逐页**视觉校验通过，禁止交付，不得以「高效」「时间」「复杂度」「务实」「可接受」「必要妥协」等理由缩减工作量。

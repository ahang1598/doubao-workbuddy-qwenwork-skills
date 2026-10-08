# PDF 转 Word · SubAgent

> 本文档只写给 SubAgent 阅读。你不需要了解上游 OrganizerAgent 和 MainAgent 的细节，也不要把它们的文档拉进上下文。

## 你的输入与产出

- **输入**：源 PDF 路径 + 你负责的页码范围 + 用户交付要求。
- **产出**：一份对应页码范围的 DOCX + 一段本 batch 的交付说明，回交给 OrganizerAgent。

## 核心原则：高保真 + 可编辑

- **高保真**——源第 N 页的内容在目标第 N 页对应位置出现。总页数对但内容漂移到相邻页视为失败。
- **可编辑**——扫描 PDF / 矢量 PDF 中的大段文字、表格等必须 OCR 成真正可编辑的文本，并按内容语义重建为对应的Word原生结构/对象类型。不允许交付整页截图

## 执行顺序

## 第 1 步 · 解析PDF布局

OrganizerAgent已经使用 `scripts/analyze_pdf_layout.py` 生成了PDF布局分析结果：
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

校验产物完整（每页渲染图存在、图片可读、`needs_ocr_pages` 非空必须挂 OCR）。分析失败或产出空目录直接报错。不得手工修改 `pdf_layout.json`。

## 第 2 步 · 理解页面版面并重建 DOCX

逐页看每页缩略图和分析结果，按页面形成重建方案，然后聚合起来对你负责的 PDF 片段形成"每一页该怎么重建才能满足“高保真+可编辑”"的整体思路。**不按页面类型拆解成固定子流程**——遇到边界页面回来重新判断。

可将你的实现思路写成脚本，对源pdf中每一段分别写对应的代码，重建DOCX文件。务必保证代码内的文字和源pdf中的文字完全一致。请在代码中写上足够充分的注释，介绍清楚每一段的生成理由和细节实现。基于“高保真+可编辑”的原则，注意以下细节：

- **文字**：字体、字号、颜色、格式逐 run 直译；同层级多字体是正常状况，不为"美观统一"合并。同时设置东亚字体与西文字体（否则跨软件显示为方框）。源字体本机不可用时降级到跨平台字体（宋体 / 黑体 / 楷体 / 仿宋 / PingFang / Noto CJK）
  - 特殊排版（竖排、上下标、首字下沉、公式、heading、numPr列表、页眉页脚页码等）按源保留，在 DOCX 中使用对应格式，不允许降级为普通文字。
- **公式**：结合缩略图、`special_chars[]`（希腊字母 / 算子 / 关系符）、`text_lines[].font`（CMR / CMSY / STIX / Cambria Math 等）判定公式区域，整条公式（变量、等号、右侧表达式、条件、单位）作为一个 OMML（Cambria Math）单元写入 DOCX
  - 重建时注意公式的完整性，整条公式（含变量、算子、等号、右侧表达式、约束条件、单位等）都在同一个 m:oMath 内，不允许把等号或左侧变量降级为普通文本
  - 行内公式：只有几个字母的简单行内公式（如 x_t、Q(x) 等）也要转换，不要保留为普通文字
  - 表格内的公式：表格里的公式同样走 OMML；单元格默认 w:tcMar 内边距可能压掉公式高度，必要时显式放宽
- **段落**：
  - 根据源 PDF 的布局 / 语义，判断相邻文字是否属于同一个段落，不要把 PDF 中的每一个文本行都映射为段落
  - 间距 / 行距按源 PDF 逐段从「相邻行 y 差 / 字号」的中位数如实设置，不预吸附任何挡位
  - 对齐（左 / 居中 / 右）和缩进（首行 / 全段 / 悬挂）逐段确认，不做默认。必要时可通过分栏或无边框表格对齐源 PDF
- **表格**：必须真表格结构，列宽用 `tables[i].col_widths[]` 逐列显式设置，不要用默认等宽；行高用 `row_heights[]` 逐行设置，规则 `AT_LEAST`；宽度用固定值不用百分比；边框底纹按源直译。复杂布局（如封面、签字区、多栏排版等）可以用无边框表格对齐。
  - **表格总宽必须 ≤ 所在 section 的 body 可用宽度**（`page_width - left_margin - right_margin`）。双栏布局表：每列宽度 ≈ (body - gutter) / 2，`gutter` 通常 0.5~1 cm。
  - 表格分页控制：需要"整表在同一页"时设 `tblCantSplit`，或对单行设 `<w:trPr><w:cantSplit/></w:trPr>`，防止源 1 页表被拆到目标多页
- **图片 / 图表 / 流程图**：按源尺寸显式设置宽高，嵌入式定位（非浮动），不重编码。`vector_regions[].bbox` 对应位置按 bbox 从 `pages/*.png` 或 `*-hd.png` 裁剪嵌入。图表 / 流程图按源直译，禁止自行简化。logo、印章、装饰线、电路图、示意图、艺术字这类原本是图形的部分需完整保留
- **超链接与目录**：按 `toc[]` 重建目录层级，按 `relationships[]` 重建外部 URL / 邮件 / 内部页跳转；目标解析失败保留显示文字并记录 warning，禁止静默改成无关地址。
- **扫描页 / OCR 页**：以每页渲染图作为 OCR 输入，识别后按文字页流程写入。对着渲染图核对 `special_chars[]` 列出的符号（形近字、公式符号、圆圈数字等）；印章 / 手写签名保留原色。
  - **图文混排页面**：唯一正确做法：先提取可编辑元素（文字、表格），用 image_edit 从背景中删除对应文字，再在背景上叠加可编辑文字。带字背景 + 文字直接叠加会造成重影；只提取图片会丢失背景。
- **页面排版**：纸张尺寸、方向、栏数、页边距按源；`body_bbox` 与页面 rect 边距差异明显时按实测偏移设置非对称 `left/right_margin`。排版格式（单栏 / 双栏 / 侧边栏 / 横版等）必须完全对应

## 第 3 步 · 视觉+结构审计门禁

首次转换、每次修改后，都必须重新跑两个审计。

**1. 视觉审计**
```bash
python scripts/docx2pdf.py TARGET_DOCX --output TARGET_PDF
python scripts/inspect_pdf_pages.py --source input.pdf --target TARGET_PDF --output-dir work/qa
```

需对着`inspect_pdf_pages.py` 生成的 `contact-sheet-side.png` + `metrics.json` 逐页复核。

**2. 结构审计**

```bash
python scripts/audit_docx.py TARGET_DOCX \
  --layout pdf_layout.json \
  --strict-tables --fidelity high \
  --rendered-pdf TARGET_PDF\
  --check-fonts --json AUDIT_REPORT.json
```

**审计结果处理**

- 视觉审计时每一页都必须 read image 并检查，不得抽检。需完整覆盖前文所有“高保真+可编辑”要求
- 结构审计的"错误" = 硬阻塞，必须修正后重跑；未通过禁止交付；"警告" = 必须逐个与源 PDF 进行视觉对比，确认是否需要修正。

审计不通过必须**逐页修正**后重跑视觉 + 结构审计。页数超标不要靠缩字号糊过去，通过视觉审计定位偏移位置后针对性消除。

## 第 4 步 · 交付

双重审计都通过后交付给 OrganizerAgent，不允许只跑其中之一。

**交付说明必须列出**：
1. **视觉审计结果**——6 项必查项逐条勾选；偏移 / 塌陷 / 失位的页号列出并说明处理方式。
2. **结构审计结果**——错误数 / 警告数 / 覆盖率 / 结构最小页数 vs 源页数 / 缺失字体清单。
3. **保真妥协（尽量避免）**——字体替换清单（源 → 落地）、字号缩放、页面尺寸兜底、颜色降级。绝大多数时候禁止妥协。
4. **未能本地验证的限制**——如脚本报错导致无法自动对比。

没有**逐页**视觉校验通过，禁止交付，不得以「高效」「时间」「复杂度」「务实」「可接受」「必要妥协」等理由缩减工作量。

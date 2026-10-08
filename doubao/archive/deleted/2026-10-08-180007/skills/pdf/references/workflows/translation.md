# PDF 翻译

PDF 翻译工作流默认使用 `create_agent` 启动多 agent 链路；满足下文中**同源语种翻译**时可由 MainAgent 单 agent 完成。各 Agent 只需阅读本文档中自己负责的部分。

## 命中信号 + 类型判据

用户提供 PDF、交付目标是翻译为另一种语言的 PDF。

- **同源语种翻译**（繁 ↔ 简 等同语系内变体）：字符宽度不变，MainAgent 单 agent 直接完成——遍历 span 替换文字即可。但五条核心要求、SubAgent的硬规则、MainAgent 交付前机械核对依然需要遵循。
- **跨语种翻译**（英 ↔ 中、中 ↔ 日、拉丁 ↔ CJK 等）：文字长短会变，走多 agent 流程。**难以判断时按跨语种翻译处理**。

## 跨语种翻译 的核心要求

翻译要"看不出翻过"——原版式尽量保持。五条：

1. **字号自适应**：译文长了就在 bbox 内缩字号（`insert_htmlbox` 的 `scale_low` 参数），译文短了就留白——**不外扩 bbox**（外扩会侵占相邻图形 / 图片）。`insert_htmlbox` 返回 `(spare_height, ...)`，负值即译文被截断，必须记录不能忽略。
2. **格式跟随**：粗体 / 斜体 / 颜色 / 字号跟着源 span 走。粗体信号双通道识别：`flags & 16` 或字体名含 `Bold` 任一为真都算 bold（只看 flags 会在 CJK 字体族无 Bold face 时大批漏判）。未真正被翻译的单元（品牌名、代码、URL）保留原字体，不切目标语言字体族。**跨 batch 一致性**：同一源 `(font, size, flags)` 元组在所有页 / 所有 batch 里映射到同一目标字体（通过共享 `font_mapping.json`），保证连续段落跨 batch 边界处不出现字体跳变——不同层级（正文 / 标题 / 副标题）用不同字体是合理的，但同层级同样式必须一致。
3. **图片位置不变**：`page.get_images(full=True)` 采集原始 xref + `get_image_rects` 记录位置，全流程结束核对图片仍在同一位置。
4. **高亮跟随译文**：`page.get_drawings()` 采集填色块；小色块（rect 面积 ≤ 覆盖文字面积 × 4）是字紧高亮，走两趟 redact 擦除源高亮后，在 `insert_htmlbox` 的 HTML 中用 inline `background-color` 流式重绘（高亮随文字走，不会错位）；**禁止用 `add_highlight_annot` 重绘字紧高亮**（annotation 层坐标独立，译文长度变化后必然错位）；大色块（rect 面积 > 覆盖文字面积 × 4）是容器 chip / 卡片，原位保留不重绘。
5. **段落 / 目录结构不乱**：翻译单元 = 语义段落，正文软换行要跨行合并（否则中文断句会锁在英文换行点上），TOC / 列表条目不能跨条目合并（结束刹车：行末页码、dot leader、短句以句号结尾、不同缩进、行距过大任一命中就停止合并）。同行混合样式（粗体+常规、共享 baseline 的大小字号混排如首字放大 / 副标题字号切换等）合并成一个单元，样式差异用 inline 标记还原，一次性送入 htmlbox——不要按 span 拆成独立单元各自 insert，会在行中间留出空隙，且 CJK 译文自然宽 ≥ 源 span advance 时会外溢到相邻 span 位置形成撞字。

## 三个层级的 Agent

### MainAgent

- 类型分流；同源语种翻译 单 agent 直接完成；跨语种翻译 启动 OrganizerAgent
- 估时：<10 页约 15 分钟、10-50 页 30-45 分钟、50-100 页约 1 小时、100 页以上 1-1.5 小时
- **交付前机械核对**（任一失败即中止 `save`）：页数与源相等、图片总数不少于源、图片 `xref` 坐标与开工前记录一致、`Counter(round(s["size"]))` 字号直方图各桶数量不下降
- **交付物只有翻译后的 PDF 一份文件**；`translations.json`、已知限制清单等都是内部工作产物，不落盘到用户目录。核对结果 + 已知限制以对话消息形式告知用户

### OrganizerAgent

- 每 5 页一 batch 并行启动 SubAgent；维护共享 `translations.json`（跨 batch 术语一致）和 `font_mapping.json`（源 `(font, size, flags)` → 统一目标字体，保证同一样式在所有 batch 落地一致，避免连续段落跨 batch 边界处字体跳变）
- 每 batch 完成后抽样验证五项，不通过打回同一 SubAgent 修正一次（打回两次仍不过的 batch 记入已知限制清单）：
  - **高亮复现**：字紧高亮在译文位置有 annotation；容器 chip 原位保留
  - **格式保留**：粗体 span 数量译文页 ≥ 源页 × 0.7；样式一致的连续 span 使用同一目标字体（查 `font_mapping.json`）
  - **大字号档覆盖**：`Counter(round(s["size"]))` 中 > 24pt 每档在产物侧的 span 数量必须**等于**源侧，任一档下降即漏收装饰字（背景数字、水印、章节大字）。此项**必须由机械脚本运行并原文粘贴输出**，禁止 SubAgent 用"章节大字已保留"等自然语言复述过关——装饰字最容易在自陈里被糊弄
  - **视觉结构**：TOC / 列表 / 段落行数与源基本一致，无整段拉平或整段被合并；译文 span 之间无明显 glyph 重叠（防同行混排未合并导致的撞字）；装饰字 bbox 内视觉连续、无明显横向断带（防装饰字 split-clip 或漏贴回致断裂）
  - **装饰字唯一性**：`>100pt` 装饰字 span 数量必须**等于**源侧（章节扉页通常为 1），重复贴回即失败打回。同时需要注意装饰字的视觉完整性，不能出现明显的断裂/缺失等情况，需要打回。
- 所有 batch 完成后按页顺序合并 PDF，交付给 MainAgent

### SubAgent

SubAgent 负责一个 batch（约 5 页）的原位翻译，完成后交付给 OrganizerAgent。**目标是把 5 条核心要求落实到自己的 5 页上**。

**四条硬规则**：

1. **必须原位编辑**：禁止用 ReportLab 等从零重建。若判断 in-place 不可行，报告给 OrganizerAgent 由 MainAgent 与用户确认，不得单方面切换。
2. **不追加 "final pass" / "cleanup" 补丁**：视觉问题用只读诊断（`get_textbox` / `get_drawings` / `get_image_rects`）回溯根因，而非追加擦除或覆盖操作。**API 返回空 ≠ 该加补丁**——先核对该 API 的文档化范围（例：`get_drawings` 不下钻 Form XObject，遇空要走 `KNOWN_HIGHLIGHTS` 关键词回退）。
3. **不虚构 PyMuPDF 常量**：`apply_redactions` 的 `graphics` 参数合法取值（1.28+）只有 `PDF_REDACT_LINE_ART_NONE`、`PDF_REDACT_LINE_ART_REMOVE_IF_COVERED`、`PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED`；`PDF_REDACT_LINE_ART_REMOVE` / `PDF_REDACT_LINE_ART_IF_TOUCHED` 不存在。写下前用 `dir(pymupdf)` 或文档核对。
4. **装饰字不删只贴回**：大字（通常 >24pt）须同时满足视觉独立、且不构成任何单词、名称或句子的一部分，方可保留原文；Type3 描边字、品牌 logo、章节水印大数字通常属此类。与相邻文字属同一词或同一行标题的（如首字母放大、章节号与章名同行），无论字号差异或坐标是否对齐，均合并翻译；存疑时优先合并。贴回后若装饰字与译文重叠，表明判定有误，须撤销重译。
    - **不相交**：贴回范围锁到装饰字自身，以免把相邻文本一起带过来。
    - **相交**（章节大数字被覆盖标题等）：**优先用内容流删除，不要拆 clip 跳段，也不要一上来就 redact。**：合并页面内容流后，找到翻译单元对应的 `BT...ET` 文本块直接删掉 —— 装饰字的绘制指令在别处，完全不受影响。删完回读确认文字消失、装饰字完好，再直接写入译文即可，不需要擦除、贴回或二次处理。只有当内容流里定位不到完整文本块（比如文字散在多个 Form XObject 里）时，才回退到 redact 四步法。回退时两条硬约束：二次擦除 `fill=None`，图片背景上绝不许留黑底；装饰字只贴回一次，做完数一遍 >100pt 的 span 数必须和源页一致。

    **禁止**用 htmlbox 重绘描边或透明装饰字——CSS 子集不支持描边和真透明，效果一定走样。

**两趟 redact 是常规操作**：`apply_redactions` 的 `graphics/images/text` 是全局参数，一次只能选一种策略——第一趟 `text=REMOVE + graphics=LINE_ART_NONE`（删文本、保装饰），第二趟只对字紧高亮 rect `text=NONE + graphics=LINE_ART_REMOVE_IF_COVERED`（精准擦高亮）。`IF_COVERED` 不用 `IF_TOUCHED`——后者会顺带擦掉相邻装饰。

**`TEXT_REMOVE` 是全页相交**：删除的是所有 glyph bbox 与任意 redact 矩形相交的字符，不是仅你 `add_redact_annot` 指定的那些。**translation_units 必须全覆盖页面文字**——不做"看着像装饰所以跳过"式过滤（`has_chinese()` 一律禁止）；采集完成后专门核查 `Counter(round(s["size"]))` 中 > 24pt 每一档的所有 span 都在 units 中（这类字颜色常接近底色，肉眼极易漏）。未真正翻译的单元通过 `translations.get(text, text)` 原样回填。

## 工具箱

**采集**

| 工具 | 关键语义 |
|------|---------|
| `page.get_text("dict", sort=True)` | 取 spans / bbox / font / size / color / flags；**block 边界不可靠**，需页级扁平化后按几何+样式重合并 |
| `page.get_drawings()` | 枚举矢量图形；**不下钻 Form XObject**；`d.get("fill")` 即便 type 是 `f`/`fs` 也可能为 `None` |
| `page.get_textbox(rect)` | 返回纯字符串；空 = 装饰背景；非空要比面积区分字紧高亮 vs 容器 chip |
| `page.get_images(full=True)` + `get_image_rects(xref)` | `full=True` 才有 xref；一个 xref 可多次出现，返回 list |
| `page.search_for(text, quads=True, clip=?)` | `q.rect` 才是 Rect；多命中按 `abs(q.rect.y0 - target.y0)` 择近，别盲取 `hits[0]` |

**编辑**

| 工具 | 关键语义 |
|------|---------|
| `page.add_redact_annot(rect, fill=?)` | 只登记；`rect` 必须是 `pymupdf.Rect` |
| `page.apply_redactions(images, graphics, text)` | 参数全局；`text=REMOVE` 删除所有 glyph 与任意 redact 相交的字符 |
| `page.insert_htmlbox(rect, html, css=?, scale_low=?, overlay=True)` | 返回 `(spare_height, ...)`；负值 = 译文被截断必须记录；同行混排组装为单盒子多个 inline `<span>` |
| `page.show_pdf_page(rect, src_doc, pno, clip=?, overlay=True)` | 把 `src_doc` 第 `pno` 页 `clip` 区域**作为矢量层**贴回；`src_doc` 必须是 **redact 之前**的只读源文档引用；用于装饰字/图元保护（见 SubAgent 硬规则 4） |
| `page.add_highlight_annot(quad_or_rect)` | annotation 层；需 `set_colors(stroke=...)` + `set_opacity(0.4)` + `update()` 才生效；颜色是 0-1 float |
| `page.clean_contents() + doc.xref_stream(xref) / doc.update_stream(xref, bytes)` | 合并并读写页面内容流；用于精确定位删除 BT...ET 文本块，避开 redact 全页相交语义，是相交装饰字场景的首选手段 |

**校验**

| 工具 | 关键语义 |
|------|---------|
| `page.get_pixmap(dpi=?)` | 装饰完整性与高亮位置**只能**渲染肉眼判 |
| `document.save(path, garbage=4, deflate=True)` | 保存到**新路径**，源 PDF 只读；长文档按页 checkpoint |

## 通用规范

- **翻译数据与执行脚本分离**：翻译对照表、`KNOWN_HIGHLIGHTS` 放独立 JSON，运行时按需加载；不硬编码进 Python 脚本。
- **不覆盖原文件**：始终保存到新路径。
- **按页 checkpoint**：SubAgent 处理长 batch 时每若干页 `document.save(...)` 一次。

# PDF 转 Word · OrganizerAgent

> 本文档只写给 OrganizerAgent 阅读。你不需要了解 MainAgent 和 SubAgent 的细节，也不要把它们的文档拉进上下文。

## 在工作流中的位置

```
MainAgent（上游，会给你 PDF）
  └── OrganizerAgent（你）
        ├── SubAgent-1  (第 1 个 batch)  ┐
        ├── SubAgent-2  (第 2 个 batch)  │ 并行
        ├── SubAgent-3  (第 3 个 batch)  │
        └── ...                          ┘
```

你的产物是一份合并好的 DOCX + 一段交付说明，回交给 MainAgent。

## 职责

### 1. 任务分发

1. 用 `scripts/analyze_pdf_layout.py` 生成PDF布局分析结果。
2. 检查布局分析结果，将**排版元素相近**的页面聚类为一个 batch。
    - 页面内容连续，字体、字号、分栏、缩进等元素基本一致，可以使用同一套重建逻辑的页面，可以被认为是**排版相近**
    - 如果某些页面存在大量复杂元素（如大量公式和文字混排、存在复杂装饰、背景等），可单独一个 batch。
    - 例如：封面页一个batch、所有目录页合并到一个batch、前言放一个batch、每一章一个batch、每个附录一个batch。章节内如有章节标题、表格、公式、图片等视觉上明显不相似的页面，请把这样的单个页面单独放一个 batch
    - 避免把不相似的页面放到一个batch内，可以把batch分的很细。甚至所有的batch内都只有一页也是可以的
3. 保存 batch 分配方案表格，记录每个batch的页面范围、运行状态、校验结果、修正次数等相关信息。
4. 每个 batch 用 `create_agent` 启动 1 个 SubAgent 进行重建，同时启动所有 batch 并行执行。告知 SubAgent 每个 batch 的布局分析结果和重点要求，并要求它阅读 `pdf-to-word-sub.md`。

### 2. 结果质检和修正

每当有 batch 重建完成，**立即**对当前 batch 的结果进行校验。**必须自行验证，不能直接采信 SubAgent 的验证结果**。

校验方法：
```bash
python scripts/docx2pdf.py <batch.docx> --output <batch.pdf>
python scripts/inspect_pdf_pages.py \
  --source <原 PDF 的对应页切片> \
  --target <batch.pdf> \
  --output-dir work/qa/batch-<N>
```

1. 对 `contact-sheet-side.png` 逐页读图复核，验证能否做到**高保真**：源第 N 页的内容出现在目标第 N 页的对应位置，视觉元素无差异
2. 对于存在文字的页面，自行检验能否做到**可编辑**：大段文字、表格等保证可编辑，没有实现成整页贴图

具体来说至少要判断：
- 文字:字体/字号/颜色/格式/文字方向与源 PDF 完全一致。可编辑而不是整页截图
- 段落:切分按语义(一个自然段一个段落)，间距/对齐/缩进匹配源 PDF 实测值。
- 表格:真表格结构，列宽行高、底纹边框与源 PDF 一致。
- 公式:每条公式是一个可编辑的OMML对象(不是斜体文字、不是截图)。行内公式也一样。不能有方框或报错。
- 图片:尺寸、清晰度、位置与源 PDF 一致，不能有遮挡微缩错位简化。logo、印章、装饰线、流程图等图形不能丢
- 超链接与目录:目录可跳转，链接可点击，跳转目标与源 PDF 一致。
- 扫描页 / OCR 页:文字可编辑；图文混排不重影。
- 页面结构:转换前后页数一致；每页纸张尺寸/方向/栏数/页边距与源一致；页眉页脚在正确区域，不进正文；横版仍是横版。


处理规则：
- **符合要求** → 保留当前 batch 的 DOCX，等所有 batch 完成后合并。
- **不符合要求** → 详细列出所有问题，重新把当前 batch 发给一个 SubAgent 修正。**为了控制整体执行时间，每个 batch 只能打回修正一次**

### 3. 合并结果

拿到所有 batch 的修正后 DOCX 后，执行合并脚本：

```bash
python scripts/merge_batches.py \
  batches/batch-01.docx batches/batch-02.docx ... batches/batch-NN.docx \
  --output merged.docx
```

合并后：
1. 对比merged docx的总页数与源 PDF 的总页数（复用scripts/docx2pdf.py 生成 PDF 对比）。如果页数不一致，优先调整 batch 之间的分页符 / 分节符来匹配，不要修改 batch 内部的内容。
2. 合并可能引入的问题需要额外检查：
   - **numbering 一致性**：如果某个 batch 自己在 numbering.xml 中定义了新的 numId，合并后只会保留 base（batch-01）的 numbering.xml——该 batch 的 numPr 编号可能错位。脚本会输出 warning 提示；SubAgent 生成 batch 时应从同一份空白模板起，避免多 batch numbering 定义冲突
   - **section header/footer 继承**：Word 默认后续 section 的 header/footer linked to previous；若 batch 未显式定义 header/footer，会继承上一 section 的。业务上如需每个 batch 有独立 header/footer，需在 SubAgent 侧显式设定

## 质量提示
1. 对subagent分发任务时，可根据batch内容，针对性强调容易犯错的问题，提升第一轮转换质量。注意：只允许客观描述目标和上下文（要求、注意事项、页面布局），禁止提供任何执行层面的规划（建议、方案、策略、工作流）——后者需 subagent 设计。
2. 下发修正任务时，需详细列出所有问题，避免subagent不清楚问题导致遗漏。

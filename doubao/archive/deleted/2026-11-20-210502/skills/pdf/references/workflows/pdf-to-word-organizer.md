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
2. 根据布局分析结果，将**排版元素相近**的页面聚类为一个 batch。
    - 页面内容连续，字体、字号、分栏、缩进等元素基本一致，可以使用同一套重建逻辑的页面，可以被认为是**排版相近**
    - 如果某些页面存在大量复杂元素（如大量公式和文字混排、存在复杂装饰、背景等），可单独一个 batch。
    - 例如：封面页一个batch、所有目录页合并到一个batch、前言放一个batch、每一章一个batch、每个附录一个batch。章节内如有章节标题、表格、公式、图片等视觉上明显不相似的页面，请把这样的单个页面单独放一个 batch
    - 避免把不相似的页面放到一个batch内，可以把batch分的很细。甚至所有的batch内都只有一页也是可以的
3. 保存 batch 分配方案表格，记录每个batch的页面范围和运行状态。
4. 每个 batch 用 `create_agent` 启动 1 个 SubAgent 进行重建，同时启动所有 batch 并行执行。告知 SubAgent 每个 batch 的布局分析结果和重点要求，并要求它阅读 `pdf-to-word-sub.md`。

### 2. 合并结果

拿到所有 batch 的 DOCX 后，执行合并脚本：

```bash
python scripts/merge_batches.py \
  batches/batch-01.docx batches/batch-02.docx ... batches/batch-NN.docx \
  --output merged.docx
```

## 质量提示
1. 对subagent分发任务时，可根据batch内容，针对性强调容易犯错的问题，提升第一轮转换质量。注意：只允许客观描述目标和上下文（要求、注意事项、页面布局），禁止提供任何执行层面的规划（建议、方案、策略、工作流）——后者需 subagent 设计。

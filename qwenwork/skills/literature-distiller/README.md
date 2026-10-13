# 论文速览助手 (Literature Distiller Pro)

> ⚡ **快速浏览与蒸馏学术论文，一键提取核心洞察并生成钉钉在线文档**

## 📖 简介

这是一个专注于**学术论文快速浏览与内容蒸馏**的工具。通过 **"4+2 深度蒸馏模型"**，快速将学术论文转化为结构化的钉钉在线文档，帮助你高效筛选和管理文献。**支持本地 PDF 文件和在线学术链接**（arXiv、知网、PubMed 等）。

### ✨ 核心特点

- 🎯 **多种输入**：支持本地 PDF 文件上传和在线学术链接（arXiv、PubMed 等开源平台）
- ⚡ **快速响应**：单篇文献处理时间控制在 1-2 分钟内
- 📊 **结构化输出**：自动生成包含元数据、逻辑骨架、引用网络、批判性思考的钉钉在线文档
- 🔍 **三档模式支持**：
  - **深度蒸馏**：完整的 4+2 模型分析（M1-M5），适合深入研究
  - **快速阅读**：仅生成 M1（元数据）+ M2（精简摘要 + 论证链条），适合快速浏览
  - **简单了解**：仅提取标题、作者、摘要和核心结论，适合初步筛选
- 📄 **钉钉文档输出**：自动创建钉钉在线文档，支持协作编辑和知识库归档
- 📁 **批量处理**：支持指定文件夹，逐个处理并生成汇总清单

### ❌ 不支持的功能

- 加密或受密码保护的 PDF
- 需要机构订阅的非开源平台（如 IEEE、ScienceDirect 等）的 PDF 直接下载（提供降级方案：全网搜索公开信息）

---

## 🚀 快速开始

### 1. 准备 PDF 文件

将待处理的 PDF 文献放入 `input_pdfs/` 目录：

```bash
# 示例：复制桌面上的文献到输入目录
cp ~/Desktop/文献/*.pdf input_pdfs/
```

### 2. 运行速览脚本

```bash
# 批量处理所有 PDF（完整模式）
bash scripts/distill_batch.sh

# 快捷模式（仅核心摘要）
bash scripts/distill_batch.sh --quick

# 处理单个文件
bash scripts/distill_batch.sh --single paper.pdf

# 自定义输入输出路径
bash distill_batch.sh --input ~/Documents/papers/ --output ~/Documents/summaries/
```

### 3. 查看结果

处理完成后，在 `distilled_papers/` 目录中查看生成的 Markdown 报告：

```bash
# 查看汇总报告
cat distilled_papers/summary_20260507.md

# 列出所有报告
ls -lh distilled_papers/*.md

# 在 QoderWork 中交付报告给用户
# 使用 present_files 工具将报告文件呈现给用户查看
```

---

## 📂 目录结构

```
literature-distiller-skill/
├── input_pdfs/                  # 📥 输入：待处理的 PDF 文献
│   ├── paper1.pdf
│   ├── paper2.pdf
│   └── ...
├── distilled_papers/            # 📤 输出：蒸馏后的 Markdown 报告
│   ├── 20260507_paper1.md
│   ├── 20260507_paper2.md
│   └── summary_20260507.md      # 汇总报告
├── scripts/
│   └── distill_batch.sh         # 批量处理脚本
├── references/
│   └── distillation-model-guide.md
├── examples/
│   └── distilled-paper-demo.md  # 示例报告
├── SKILL.md                     # Skill 定义
└── README.md                    # 本文件
```

---

## 🔬 4+2 深度蒸馏模型

### 基础层（M1-M3）

| 模块 | 内容 | 用途 |
|------|------|------|
| **M1: 结构化元数据** | 标题、作者、机构、来源、年份、DOI、快速标签 | 快速了解文献基本信息 |
| **M2: 逻辑骨架还原** | 论证链条、精简摘要、关键图表说明 | 把握研究脉络和核心贡献 |
| **M3: 引用文献网络** | 核心参考文献（Top 10） | 为深入阅读提供指引 |

### 洞察层（M4-M5）

| 模块 | 内容 | 用途 |
|------|------|------|
| **M4: 批判性思考** | 研究缺口、局限性、改进方向 | 评估研究价值和适用性 |
| **M5: 知识图谱关联** | 前置知识、同类对比、领域定位 | 理解文献在领域中的位置 |

---

## 📋 输出示例

### 单篇报告结构

```markdown
# 论文速览：BERT: Pre-training of Deep Bidirectional Transformers

> 📅 蒸馏日期：2026-05-07 11:30  
> 📂 原始文件：`input_pdfs/bert.pdf`  
> 📏 文件大小：1.2MB | 12页  
> 🔗 DOI：10.18653/v1/N19-1423

---

## M1 · 结构化元数据

| 字段 | 内容 |
|------|------|
| 标题 | BERT: Pre-training of Deep Bidirectional Transformers... |
| 作者 | Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova |
| 机构 | Google AI Language |
| 来源 | NAACL 2019 |
| 年份 | 2019 |
| **快速标签** | `#NLP` `#预训练` `#Transformer` |

---

## M2 · 逻辑骨架还原

### 论证链条

**🎯 研究问题**  
已有语言模型（ELMo, GPT）都是单向的，无法同时利用左右上下文信息

**📚 理论基础**  
双向编码应该能学习到更丰富的语义表示

**🔬 方法论**  
- Masked Language Model (MLM)：随机遮蔽 15% 的词
- Next Sentence Prediction (NSP)：判断句子连续性

**💡 主要发现**  
在 11 项 NLP 任务上全部达到 SOTA

---

## M3 · 引用文献网络

### 核心参考文献（Top 10）

1. Vaswani et al. "Attention Is All You Need." NeurIPS, 2017.
2. Peters et al. "Deep Contextualized Word Representations." NAACL, 2018.
...

---

## M4 · 批判性思考

### 🔍 研究缺口
- MLM 的遮蔽率（15%）选择缺乏理论依据
- NSP 任务的必要性存疑

### ⚠️ 局限性
- 预训练和微调之间存在不一致性
- 大模型训练成本高

---

## M5 · 知识图谱关联

### 前置知识
- Transformer 架构
- 自注意力机制

### 同类方法对比

| 模型 | 方向性 | 参数量 |
|------|--------|--------|
| ELMo | 双向浅层 | 94M |
| GPT | 单向深层 | 117M |
| **BERT** | **双向深层** | **110M** |
```

### 汇总报告结构

```markdown
# 论文速览汇总报告

> 📅 生成日期：2026-05-07 11:35  
> ⏱️  处理时长：45 秒  
> 📊 处理文献数：15 篇  

---

## 📈 统计概览

| 指标 | 数值 |
|------|------|
| 总文献数 | 15 |
| 成功处理 | 15 |
| 平均耗时 | 3 秒/篇 |

---

## 📋 文献清单

| # | 文件名 | 大小 | 状态 | 输出报告 |
|---|--------|------|------|---------|
| 1 | 2605.00505v1.pdf | 2.1MB | ✅ 已处理 | [查看](...) |
| 2 | 2605.00529v1.pdf | 3.7MB | ✅ 已处理 | [查看](...) |
...
```

---

## 💡 使用场景

### 场景 1：文献筛选

**需求**：下载了 50 篇相关论文，需要快速筛选出值得深入阅读的

**操作**：
```bash
bash scripts/distill_batch.sh --quick
```

**结果**：30 秒内生成所有文献的核心摘要，根据 M1 标签和 M2 论证链条快速判断相关性

### 场景 2：会议前准备

**需求**：明天要参加学术会议，需要快速了解参会论文

**操作**：
```bash
bash scripts/distill_batch.sh --single tomorrow_paper.pdf
```

**结果**：1 分钟内生成完整报告，重点阅读 M2 逻辑骨架和 M5 领域定位

### 场景 3：知识管理

**需求**：整理个人文献库，建立结构化索引

**操作**：
```bash
bash scripts/distill_batch.sh --input ~/Library/Papers/ --output ~/Notes/Literature/
```

**结果**：批量生成 Markdown 报告，导入 Obsidian/Notion 建立知识库

---

## ⚙️ 高级配置

本 Skill **无需特殊配置**，开箱即用。输出文件默认保存在 `distilled_papers/` 目录。

### 自定义输出格式
修改 `SKILL.md` 中的模板部分，调整报告结构和样式。

---

## ❓ 常见问题

### Q1: 为什么我的 PDF 处理失败？

**可能原因**：
- 文件损坏或非标准 PDF 格式
- 扫描版 PDF（图片型），文本提取困难
- 文件过大（>50MB）

**解决方案**：
- 验证文件是否能正常打开
- 扫描版建议使用 OCR 工具预处理
- 大文件考虑分割处理

### Q2: 提取的元数据不准确怎么办？

**原因**：PDF 结构复杂，自动提取可能存在偏差

**建议**：
- 手动校对 M1 模块的关键字段
- 在报告中标注修正内容
- 后续版本会持续优化提取算法

### Q3: 能否处理中文论文？

**答案**：✅ 完全支持中英文学术论文

### Q4: 如何处理加密 PDF？

**答案**：本工具不支持加密 PDF。请先用 PDF 阅读器解密后再次尝试。

### Q5: 批量处理时能否中断？

**答案**：可以。按 `Ctrl+C` 中断脚本，已处理的文件会保留在输出目录中。

---

## 🔄 版本历史

- **v5.0**（当前版本）：增加用户目的确认、在线链接支持、非开源链接降级方案确认
- **v4.0**：输出产物更改为钉钉文档，增加用户确认归档环节
- **v3.0**：专注本地 PDF 速览，优化处理速度
- **v2.0**：支持批量处理 assets 目录
- **v1.0**：单文献蒸馏，支持知网 URL 和本地 PDF

---

## 📝 许可证

本工具仅供个人学习和研究使用。处理敏感文献时，请注意文件存储安全。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request，帮助改进这个工具！

**联系方式**：通过 GitHub Issues 反馈问题或建议
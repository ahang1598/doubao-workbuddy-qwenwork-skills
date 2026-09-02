---
name: "patent-literature-search"
description: "深度检索全球专利和学术文献（CNIPA/Google Patents/CrossRef/PubMed/arXiv/Semantic Scholar），支持MeSH词扩展、去重、真实DOI/专利号核验，构建可追溯证据链。当需要补充学术文献支撑、核验引用真实性、构建证据链时调用。"
allowed-tools: Read, Write, WebSearch, WebFetch, Grep, Glob

version: "2.0.1"
---

# 文献检索器

## 一、适用场景

- 专利背景技术部分需要补充高被引学术论文支撑
- 交底书中的引用需要核验真实性（DOI/专利号/URL）
- 跨领域技术调研（源领域+目标领域双轨检索）
- 审查意见中对比文件的深度分析
- 构建完整的引用证据链

## 二、检索策略

### 2.1 检索数据库

| 数据库 | 覆盖范围 | 检索方式 |
|--------|----------|----------|
| CNIPA（国知局） | 中国专利 | WebSearch + 国知局官网 |
| Google Patents | 全球专利 | WebSearch + Google Patents |
| CrossRef | 全球学术文献DOI | WebSearch + CrossRef API |
| PubMed | 生物医学文献 | WebSearch + PubMed |
| arXiv | 预印本 | WebSearch + arXiv |
| Semantic Scholar | AI/CS学术文献 | WebSearch + Semantic Scholar |
| Espacenet | 欧洲专利 | WebSearch + Espacenet |

### 2.2 MeSH 词扩展（医学/生物领域）

对检索词进行医学主题词（MeSH）扩展：

```
核心词 → MeSH主题词 → 下位词 → 同义词 → 相关词
```

### 2.3 检索式构建

采用"核心要素拆解法"构建检索式：

```
(技术手段1 OR 技术手段1同义词) AND (技术效果1 OR 技术效果1同义词)
AND (应用场景1 OR 应用场景1同义词)
```

### 2.4 去重与聚类

- 跨数据库自动去重（按DOI/专利号/标题相似度）
- 按技术方向自动聚类分组
- 按相关度排序（高/中/低）

## 三、证据链标准

每条检索结果必须包含以下字段（缺失则标记为"待核验"）：

| 字段 | 说明 |
|------|------|
| 文献类型 | 专利/期刊论文/会议论文/技术标准/预印本 |
| 标题 | 原文标题 + 中文翻译（如外文） |
| 作者/申请人 | 完整作者列表或申请人 |
| 年份 | 发表年份或申请年份/授权年份 |
| 来源 | 期刊名/会议名/专利局 |
| 唯一标识 | DOI 或专利号（必须真实可核验） |
| 可访问URL | 可直接访问的链接 |
| 摘要 | 原文摘要 + 中文翻译（如外文） |

## 四、输出格式

### 4.1 检索报告

- 检索式（每个数据库的检索式）
- 数据库覆盖情况
- 各数据库命中数统计
- 去重后总数
- 高相关度文献清单（Top 20）

### 4.2 证据链清单

GB/T 7714-2015 格式的引用清单，每条包含：
- 引用序号
- 完整著录信息
- DOI/专利号
- 可访问URL
- 核验状态（已核验/待核验/无法访问）

## 五、红线规则

- **绝对禁止编造DOI/专利号/URL**：不确定的标记为"待核验"，绝不编造
- 每条引用必须至少有一个可核验的标识（DOI或专利号）
- 无法访问的URL必须明确标注"无法访问"，不得隐藏
- 完成后通过 SendMessage 将检索报告与证据链清单回传主理人

## 可选工具与参考文档（使用者按需调用）

> 以下工具和参考文档已集成到本skill目录中，使用者根据需要决定是否调用。不需要就跳过，需要就调用。

### 文献精读工具（references/reader/目录，来源：nature-reader）

| 文档 | 用途 |
|------|------|
| `references/article-anatomy.md` | 论文结构解剖指南 |
| `references/figure-extraction.md` | 图表提取与放置 |
| `references/grounding-rules.md` | 源文本锚定规则 |
| `references/output-spec.md` | 输出规范（paper.md + source_map.json） |
| `static/core/principles.md` | 精读核心原则（双语对照、不降级为摘要） |
| `static/core/workflow.md` | 六步精读工作流 |
| `static/core/output-contract.md` | 输出契约 |
| `static/fragments/source/*.md` | 按来源格式（PDF/HTML/DOI/arXiv/粘贴文本）的提取指南 |

### 文献管线工具（references/pipeline/目录，来源：nature-literature-pipeline）

| 文档 | 用途 |
|------|------|
| `references/pipeline/gap-analysis.md` | 文献缺口分析 |
| `references/pipeline/scoring-system.md` | 文献评分系统 |
| `references/pipeline/review-compilation-workflow.md` | 综述编译工作流 |
| `references/pipeline/note-template.md` | 文献笔记模板 |
| `references/pipeline/push-format.md` | 文献推送格式 |
| `references/pipeline/cron-setup.md` | 定时推送设置 |
| `templates/literature-push-template.md` | 文献推送模板 |

### 原有工具（保持不变）

| 工具 | 用途 |
|------|------|
| `tools/academic_search.py` | OpenAlex学术文献检索（无需API Key） |
| `tools/converters.py` | 引用格式转换 |
| `tools/format-converter.py` | DOI/PMID→RIS/BIB/ENW |
| `tools/preflight.py` | 检索前检查 |
| `references/search-strategy.md` | 检索策略 |
| `references/source-tiers.md` | 数据源分级 |
| `references/dedup-engine.md` | 去重引擎 |
| `references/citation-parser.md` | 引用解析器 |
| `references/ris-bibtex-format.md` | RIS/BibTeX格式说明 |

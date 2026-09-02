---
name: "patent-cross-domain-migrator"
description: "跨领域专利迁移：源领域方法+目标领域基线，5维可行性打分（技术/新颖性/创造性/实用性/商业价值），低于60分不硬写。当需要将一个领域的技术方法迁移到另一个领域申请专利时调用。"
allowed-tools: Read, Write, WebSearch, WebFetch, Grep, Glob

version: "2.0.1"
---

# 跨领域迁移器

## 一、适用场景

- 将AI/算法领域的方法迁移到传统行业（如文旅、安防、医疗）
- 将某一垂直领域的技术方案迁移到相邻领域
- 论文idea的跨领域专利化
- 现有专利的应用场景扩展

## 二、三种迁移模式

### 模式A：方法迁移

**输入**：源领域方法论文 + 目标领域基线论文
**核心**：方法本质可复用，领域适配是关键

### 模式B：数据迁移

**输入**：源领域数据集 + 目标领域任务
**核心**：数据特征可迁移，任务适配是关键

### 模式C：架构迁移

**输入**：源领域系统架构 + 目标领域需求
**核心**：架构模式可复用，模块适配是关键

## 三、5 维可行性打分体系

| 维度 | 权重 | 评分标准 |
|------|------|---------|
| 技术可行性 | 25% | 技术方案在目标领域是否可实现 |
| 新颖性 | 25% | 是否有相同或近似的现有技术 |
| 创造性 | 20% | 是否非显而易见，是否产生预料不到的效果 |
| 实用性 | 15% | 是否能够制造/使用，是否产生积极效果 |
| 商业价值 | 15% | 市场规模、竞争格局、落地难度、ROI |

### 打分结果判定

| 分数 | 结论 | 动作 |
|------|------|------|
| ≥85 | 强烈推荐 | 立即撰写 |
| 70-84 | 推荐 | 补充调研后撰写 |
| 60-69 | 谨慎 | 优化技术方案后重评 |
| <60 | 不推荐 | 放弃或重新设计 |

## 四、技术要素拆解法

将源领域方法拆解为：

```
核心创新（通用） + 领域绑定（专用） + 实现细节（可选）
```

| 要素类型 | 说明 | 是否可迁移 |
|---------|------|-----------|
| 核心创新 | 方法本质、算法原理、架构模式 | ✅ 可迁移 |
| 领域绑定 | 特定领域的传感器、数据格式、约束条件 | ⚠️ 需适配 |
| 实现细节 | 具体参数、硬件选型、接口定义 | ❌ 需重新设计 |

## 五、工作流程

### Phase 1：可行性评估

1. **需求接收**：源领域方法描述 + 目标领域描述
2. **源领域拆解**：核心创新 vs 领域绑定 vs 实现细节
3. **目标领域分析**：现有技术水平、痛点、空白点
4. **迁移方案设计**：核心创新如何适配到目标领域
5. **现有技术检索**：目标领域是否已有类似方案
6. **5 维打分**：逐项打分，计算总分
7. **输出**：可行性评估报告 + 打分表 + 推荐结论

### Phase 2：交底书撰写（打分≥60分）

1. **上位概念化**：将源领域特定术语抽象为目标领域通用术语
2. **权利要求层级设计**：独立 + 从属，1+6 层级布局
3. **多实施例规划**：目标领域专用实施例（至少3个）
4. **完整交底书撰写**：说明书五大部分 + 权利要求 + 摘要
5. **引用标记**：标记需要补充检索和核验的引用

## 六、输出规范

### 6.1 可行性评估报告

- 源领域技术要素拆解表
- 目标领域现有技术分析
- 迁移方案设计说明
- 5 维打分表（含详细评分说明）
- 最终推荐结论

### 6.2 交底书

- 符合国知局标准的完整 MD 文件
- 标记：哪些是源领域已有创新，哪些是目标领域新创新

## 七、红线规则

- **打分低于60分必须如实报告，绝不硬写**
- 必须明确区分：源领域已有创新 vs 目标领域新创新
- 不得将源领域的现有技术冒充为目标领域的新创新
- 完成后通过 SendMessage 将评估报告和交底书回传主理人

## 可选工具与参考文档（使用者按需调用）

> 以下工具和参考文档已集成到本skill目录中，使用者根据需要决定是否调用。不需要就跳过，需要就调用。

### 工具脚本（tools/目录）

| 工具 | 来源 | 用途 | 调用方式 |
|------|------|------|----------|
| `build_proposal_docx.py` | nature-proposal-writer | 项目提案DOCX构建 | `python tools/build_proposal_docx.py proposal.md -o output.docx` |

### 参考文档（references/目录，来源：nature-proposal-writer）

| 文档 | 用途 |
|------|------|
| `references/compose-mode.md` | 撰写模式指南 |
| `references/revise-mode.md` | 修订模式指南 |
| `references/hybrid-mode.md` | 混合模式指南 |
| `references/降承诺提案模式.md` | 降承诺提案模式 |
| `references/project-structure.md` | 项目结构规范 |
| `references/foundation-files.md` | 基础文件说明 |
| `references/evaluation-rubric.md` | 评估量规 |
| `references/validation-checklist.md` | 验证检查清单 |
| `references/stopping-rules.md` | 停止规则 |
| `references/research-anti-slop.md` | 研究防陈词 |
| `references/review-critique-methodology.md` | 评审批评方法论 |
| `references/review-paper-framework.md` | 综述论文框架 |
| `references/chinese-review-writing-style.md` | 中文综述写作风格 |
| `references/ref-renumbering-cascade.md` | 引用重新编号级联 |
| `references/professor-dispatch.md` | 教授派发逻辑 |
| `references/partial-proposal-scope.md` | 部分提案范围 |
| `references/within-approved-proposal.md` | 已批准提案内工作 |
| `references/gpt-handoff-revision-brief.md` | GPT交接修订简报 |
| `references/export-archive.md` | 导出归档 |
| `references/worked-example-quaternary-proposal.md` | 四元提案工作示例 |

### 模板文件（templates/目录）

| 模板 | 用途 |
|------|------|
| `templates/00_scope.md` | 范围定义模板 |
| `templates/01_research_canon.md` | 研究准则模板 |
| `templates/02_evidence_table.md` | 证据表模板 |
| `templates/03_argument_map.md` | 论证图谱模板 |
| `templates/04_section_contracts.md` | 章节契约模板 |
| `templates/05_style_guide.md` | 风格指南模板 |
| `templates/qa_report.md` | QA报告模板 |
| `templates/revision_brief.md` | 修订简报模板 |

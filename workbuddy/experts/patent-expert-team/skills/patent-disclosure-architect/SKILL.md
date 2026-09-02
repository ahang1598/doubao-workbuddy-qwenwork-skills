---
name: "patent-disclosure-architect"
description: "专利交底书架构设计与撰写。当用户需要撰写发明专利交底书、构建权利要求层级、设计技术方案布局时调用。"
allowed-tools: Read, Write, Bash, Grep, Glob

version: "2.0.1"
---

# 交底书架构师

## 一、适用场景

- 发明人提供技术方案，需要转化为专利交底书
- 需要构建独立权利要求 + 从属权利要求的层级结构
- 需要将技术方案从下位概念上位化，扩大保护范围
- 需要设计多实施例覆盖不同应用场景

## 二、交底书标准结构（CNIPA合规）

交底书必须包含以下部分，顺序固定：

### 2.1 案件基础信息
- 案件名称（与请求书一致，≤25字）
- 专利类型（发明/实用新型）
- 申请人、发明人信息（2026年起发明人需填身份证号）

### 2.2 说明书五大部分（专利法实施细则第18条）

| 部分 | 要求 | 撰写要点 |
|------|------|----------|
| 一、技术领域 | 一句话说明所属领域 | 不宜过宽或过窄 |
| 二、背景技术 | 现有技术状况+缺陷 | 客观描述，引用对比文件，不贬低 |
| 三、发明内容-技术问题 | 所要解决的技术问题 | 对照背景技术缺陷逐一对应 |
| 四、发明内容-技术方案 | 详细技术方案 | 必要技术特征完整，步骤清晰 |
| 五、发明内容-有益效果 | 对照现有技术的优点 | 理论分析或实验数据支撑 |
| 六、附图说明 | 各幅附图简略说明 | 图1/图2/图3… |
| 七、具体实施方式 | 优选方式+举例 | 至少1个实施例，本领域技术人员能实现 |

### 2.3 权利要求书

**独立权利要求**：包含解决技术问题的全部必要技术特征
**从属权利要求**：用"根据权利要求N所述…"引用，进一步限定

### 2.4 说明书摘要
- **不超过300字**（国知局硬性要求）
- 简要说明发明技术要点
- 指定一幅摘要附图

## 三、撰写方法论

### 3.1 上位概念化策略

从发明人提供的具体实现中提取上位概念：

| 层级 | 示例（本项目案例） |
|------|-------------------|
| 下位（发明人原话） | WiFi CSI信道状态信息 |
| 中位 | 射频信道感知 |
| 上位（权利要求用） | 射频信道感知中枢 |

**原则**：权利要求用上位概念，说明书同时记载下位实现，确保支持。

### 3.2 权利要求布局策略

```
独立权利要求1（方法）：最宽保护范围
├── 从属2-10：逐步限定具体实现
独立权利要求11（系统）：对应系统架构
```

**本项目案例**：11项权利要求（2项独立+9项从属），覆盖方法与系统两个维度。

### 3.3 多实施例设计

至少设计3类实施例覆盖不同应用层级：

| 层级 | 实施例 | 硬件配置 |
|------|--------|----------|
| C端（消费级） | 实施例1-3 | 基础模块组合 |
| B端（商业级） | 实施例4-5 | 扩展模块 |
| 工业级 | 实施例6-7 | 全量模块 |

### 3.4 失败实验公开

**关键经验**：公开失败实验可以：
1. 证明技术方案的临界条件
2. 突出创造性（现有技术无法解决）
3. 帮助审查员理解技术贡献

**本项目案例**：公开2组失败实验（无IMU补偿误报率73.5%、权重扫描边界值），显著增强说服力。

## 四、质量自检清单

```
□ 案件名称≤25字，无商业宣传用语
□ 说明书五大部分齐全且顺序正确
□ 每项权利要求都能在说明书中找到支持
□ 独立权利要求包含全部必要技术特征
□ 从属权利要求引用关系正确无断裂
□ 摘要≤300字
□ 附图说明与附图编号一致
□ 术语全文统一（同一概念不出现两种叫法）
□ 至少1个具体实施例
□ 背景技术引用了对比文件
□ 有益效果有数据或理论支撑
```

## 五、常见错误规避

| 错误 | 后果 | 规避方法 |
|------|------|----------|
| 摘要超300字 | 补正通知 | 撰写后立即字数检查 |
| 权利要求无说明书支持 | 驳回/无效 | 逐项对照检查 |
| 术语漂移 | 保护范围不确定 | 全文搜索同一概念 |
| 实施例太简略 | 公开不充分 | 写出输入到输出完整流程 |
| 背景技术贬低现有技术 | 审查员反感 | 客观描述缺陷即可 |

## 六、输入输出定义

### 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| 技术方案描述 | text | 发明人提供的技术方案自然语言描述 |
| 素材清单 | list | 论文、实验数据、图纸等 |
| 保护范围意向 | text | 仅核心方案还是包含所有变体 |
| 现有技术检索报告 | object | 来自patent-prior-art-searcher的输出 |

### 输出
| 参数 | 类型 | 说明 |
|------|------|------|
| 交底书架构蓝图 | object | 权利要求层级+实施例规划+失败实验策略 |
| 交底书MD文件 | file | 完整交底书Markdown文件 |

## 七、人机交互节点

| 节点 | 位置 | 用户操作 | 通过条件 |
|------|------|----------|----------|
| 修订方案确认 | Step 1.6 修订整合输出后 | 确认修订方案 | 用户回复"确认" |
| 细节补充 | Step 1.6 修订后 | 补充参数范围、失败实验等 | 用户补充完毕 |

## 八、工具局限性与Workaround

| 局限性 | 影响 | Workaround | 实战经验 |
|--------|------|------------|----------|
| AI可能虚构技术参数 | 交底书中的参数范围可能无依据 | 所有参数必须标注来源（实验/文献/行业标准） | 本项目参数均来自datasheet或实验 |
| MD→DOCX转换格式错乱 | 最终Word文档排版可能异常 | 手动检查排版；关键段落用纯文本格式 | 最终DOCX需人工校对 |
| 摘要字数检查需人工确认 | AI字数统计可能与国知局标准不一致 | 中文字符单独计数（不含标点/空格），≤300 | 本项目摘要从374→257字 |
| 上位概念化可能过度 | 保护范围过宽导致得不到说明书支持 | 每个上位概念在说明书中必须有下位实现支撑 | "射频信道感知"有WiFi CSI作为下位支撑 |

**核心原则**：AI撰写的内容必须经过人工审核，特别是参数、公式、法律条款引用。

## 九、附图制作规范（2026年实战经验融入）

### 9.1 国知局附图硬性标准

| 规范项 | 要求 | 违规后果 |
|--------|------|---------|
| 底色 | **白底黑线**（纯白背景，黑色线条） | 暗色背景直接被退回 |
| 格式 | JPEG 或 TIFF | PNG/SVG需转换 |
| 分辨率 | ≥300 DPI | 低分辨率模糊被退回 |
| 尺寸 | ≤165mm × 245mm | 超尺寸无法上传 |
| 线条 | 清晰、无锯齿、无填充色块 | 模糊或彩色被退回 |
| 文字 | 图内文字≥8pt，清晰可读 | 文字过小被退回 |

### 9.2 制图工具选型（核心红线）

```
✅ 推荐工具：Graphviz（自动布局，白底黑线，输出jpg/tif）
   - 开源地址：https://github.com/graphviz/graphviz
   - Python封装：graphviz包（pip install graphviz）
   - 优势：自动布局、合规输出、可编程控制

❌ 禁用工具：matplotlib默认暗色科技风
   - 问题：默认#1A1A2E暗色背景不符合国知局白底黑线要求
   - 问题：输出PNG需额外转换为JPEG/TIFF
   - 问题：布局需手动调整，易混乱

⚠️ AI生成图的陷阱：
   - AI默认生成"美观"的暗色科技风，但国知局只接受白底黑线
   - 必须在prompt中明确指定：白底黑线、无填充色、无渐变色
```

### 9.3 Graphviz制图实战模板

```python
# 标准专利附图生成模板（白底黑线合规）
from graphviz import Digraph

def create_patent_figure(output_name, nodes, edges):
    """
    创建国知局合规附图
    :param output_name: 输出文件名（不含扩展名）
    :param nodes: 节点列表 [(id, label), ...]
    :param edges: 边列表 [(from, to), ...]
    """
    dot = Digraph(comment='Patent Figure')
    
    # 国知局合规配置：白底黑线
    dot.attr(bgcolor='white', rankdir='TB')
    dot.attr('node', shape='box', style='filled', 
             fillcolor='white', color='black', fontcolor='black',
             fontsize='10', fontname='SimSun')
    dot.attr('edge', color='black', arrowhead='vee')
    
    for node_id, label in nodes:
        dot.node(node_id, label)
    for src, dst in edges:
        dot.edge(src, dst)
    
    # 同时输出jpg和tif（300DPI）
    dot.render(output_name, format='jpg', cleanup=True)
    dot.render(output_name, format='tif', cleanup=True)
```

### 9.4 附图编号规范

| 附图类型 | 编号方式 | 说明 |
|---------|---------|------|
| 系统架构图 | 图1 | 整体模块关系 |
| 流程图 | 图2、图3… | 按场景编号 |
| 电路/结构图 | 图4、图5… | 硬件结构 |

**正文引用规范**：必须用"如附图1所示"或"见图1"，不用"如下图所示"。

### 9.5 实战经验记录

> **案例**：本项目初始用matplotlib生成暗色科技风（#1A1A2E背景）附图，被国知局系统判定不合规。后改用Graphviz重新生成白底黑线版本（3张jpg+3张tif，300DPI），通过审核。
>
> **核心教训**：AI生成附图时，必须在prompt中强制指定"白底黑线、无彩色填充、无渐变"，否则AI默认生成"美观但不合规"的暗色图。

## 十、说明书标题结构规范（2026年实战经验融入）

### 10.1 5个国知局标准标题（强制）

```
一、技术领域
二、背景技术
三、发明内容
四、附图说明
五、具体实施方式
```

### 10.2 常见错误：自创标题

```
❌ 错误：9个自定义标题
一、技术领域
二、背景技术
三、技术问题
四、技术方案
五、优点
六、技术路线
七、技术关键点
八、权利要求
九、附图说明
十、具体实施方式

✅ 正确：合并为5个国知局标准标题
一、技术领域
二、背景技术
三、发明内容（含技术问题+技术方案+优点）
四、附图说明
五、具体实施方式（含技术路线+技术关键点）
```

### 10.3 首行规范

- ✅ 首行：发明名称居中（如"一种基于射频信道感知中枢的自适应多模态协同调度方法及系统"）
- ❌ 错误：首行写"# 技术交底书"或"说明书"
- ❌ 错误：发明名称前冠"说明书"字样

## 十一、AI标记与违规措辞清理规范

### 11.1 必须清理的AI残留标记

| 标记类型 | 示例 | 清理方法 |
|---------|------|---------|
| 🔍 emoji标记 | "🔍 检索结果" | 全局删除 |
| mermaid代码块 | ` ```mermaid ... ``` ` | 转为文字描述或Graphviz图 |
| HTML注释 | `<!-- 注释 -->` | 全局删除 |
| LaTeX残留 | `\(` `\)` `\[` `\]` | 转为普通文本或公式描述 |

### 11.2 专利法禁止的违规措辞

| 违规词 | 原因 | 替换为 |
|--------|------|--------|
| 最佳 | 绝对化用语 | 优选/较佳 |
| 最优 | 绝对化用语 | 优选/较佳 |
| 完美 | 绝对化用语 | 良好/显著 |
| 最好 | 绝对化用语 | 优选 |
| 唯一 | 绝对化用语 | 主要/核心 |

**清理原则**：交底书定稿前必须全局搜索上述标记和措辞，逐一清理。

## 十二、可选工具与参考文档（使用者按需调用）

> 以下工具和参考文档已集成到本skill目录中，使用者根据需要决定是否调用。不需要就跳过，需要就调用。

### 工具脚本（tools/目录）

| 工具 | 来源 | 用途 | 调用方式 |
|------|------|------|----------|
| `math_render.py` | patent-disclosure-skill | LaTeX公式→PNG（matplotlib mathtext），保留原文 | `python tools/math_render.py -i draft.md -o out.md` |
| `md_to_docx.py` | patent-disclosure-skill | Markdown→Word（含公式图片嵌入） | `python tools/md_to_docx.py -i draft.md -o out.docx` |
| `docx_to_md.py` | patent-disclosure-skill | Word→Markdown+图片提取（扫描前转换） | `python tools/docx_to_md.py --input file.docx --output dir/file.md` |
| `pptx_to_md.py` | patent-disclosure-skill | PPT→Markdown+图片提取（扫描前转换） | `python tools/pptx_to_md.py --input file.pptx --output dir/file.md` |
| `mermaid_render.py` | patent-disclosure-skill | Mermaid图→PNG+DOCX定稿（含md_to_docx调用） | `python tools/mermaid_render.py -i draft.md -o final.md` |
| `extract_pdf_text.py` | nature-paper-to-patent | PDF文本提取（支持扫描件OCR） | `python tools/extract_pdf_text.py input.pdf` |
| `math_to_omml.py` | nature-paper-to-patent | LaTeX→Office MathML（Word原生可编辑公式） | `python tools/math_to_omml.py formula.tex` |
| `iteration_dialog_log.py` | nature-paper-to-patent | 迭代对话记录留档（修订追踪） | `python tools/iteration_dialog_log.py --case "案件名" --action merger` |

### 方法论参考（references/目录）

| 文档 | 来源 | 用途 |
|------|------|------|
| `references/pgtree-rrag-methodology.md` | patent-writer方法论 | PGTree递归拆解+RRAG内循环校验方法论（可选撰写方法） |
| `references/three-modes-guide.md` | patent-writer方法论 | 三种工作模式：论文改专利/技术文档改专利/Idea到专利+双语摘要+断点续写 |
| `references/cn-patent-drafting-guide.md` | nature-paper-to-patent | 中国专利撰写指南 |
| `references/draft-schema.md` | nature-paper-to-patent | 专利草稿结构化Schema（JSON格式定义） |

### 交底书分步指令（references/disclosure/目录，来源：patent-disclosure-skill）

| 文档 | 对应步骤 | 用途 |
|------|----------|------|
| `references/disclosure/intake.md` | Step 1 | 边界与输入问题 |
| `references/disclosure/project_scan.md` | Step 2 | 项目文档扫描（含Office转换规则） |
| `references/disclosure/patent_points_analyzer.md` | Step 3-4 | 候选专利点挖掘与融合选定 |
| `references/disclosure/prior_art_search.md` | Step 5 | 联网查新与分析（CNIPA优先） |
| `references/disclosure/disclosure_preview.md` | Step 6 | 全文前的摘要预览 |
| `references/disclosure/disclosure_builder.md` | Step 7 | 交底书结构、脱敏、符号公式体例、图示规范 |
| `references/disclosure/template_reference.md` | Step 7 | 章节范例与mermaid图示模版 |
| `references/disclosure/disclosure_self_check.md` | Step 8 | 内部自检（不写入正文） |
| `references/disclosure/iteration_context.md` | 迭代 | 迭代意图识别、落盘命名、修订对话记录 |
| `references/disclosure/merger.md` | 迭代 | 新材料增量合并（含门禁） |
| `references/disclosure/correction_handler.md` | 迭代 | 对话纠正（含门禁） |
| `references/disclosure/tooling.md` | 全局 | 工具使用说明 |

### 学术写作参考（references/writing/目录，来源：nature-writing）

| 文档 | 用途 |
|------|------|
| `references/writing/references/article-architecture.md` | 沙漏型论文结构设计 |
| `references/writing/references/abstract.md` | 摘要6步法撰写指南 |
| `references/writing/references/introduction-examples.md` | 引言写作示例 |
| `references/writing/references/method-examples.md` | 方法写作示例 |
| `references/writing/references/abstract-examples.md` | 摘要写作示例（3种模板） |
| `references/writing/references/chinese-author-workflow.md` | 中国作者工作流 |
| `references/writing/references/conclusion.md` | 结论撰写指南 |
| `references/writing/static/core/stance.md` | 写作核心立场 |
| `references/writing/static/core/workflow.md` | 写作工作流 |
| `references/writing/static/core/output-format.md` | 输出格式 |
| `references/writing/static/fragments/section/*.md` | 各章节（摘要/引言/方法/实验/讨论/结论/标题）撰写指南 |
| `references/writing/static/fragments/paper_type/*.md` | 按论文类型（研究/方法/假设/算法/综述）的撰写策略 |
| `references/writing/static/fragments/language/*.md` | 英文/中译英语言规则 |

### 学术润色参考（references/polishing/目录，来源：nature-polishing）

| 文档 | 用途 |
|------|------|
| `references/polishing/references/writing-strategy.md` | 写作策略原则 |
| `references/polishing/references/phrasebank-playbook.md` | 学术短语库使用指南 |
| `references/polishing/references/section-moves.md` | 各章节修辞策略 |
| `references/polishing/references/style-guardrails.md` | 风格护栏 |
| `references/polishing/references/published-article-patterns.md` | 已发表文章模式参考 |
| `references/polishing/references/nat-comms-2025-diction.md` | Nature Communications 2025用词 |
| `references/polishing/references/latex-layout.md` | LaTeX排版修复 |
| `references/polishing/static/core/failure-modes.md` | 常见失败模式诊断 |
| `references/polishing/static/core/stance.md` | 润色核心立场 |
| `references/polishing/static/fragments/section/*.md` | 各章节润色指南 |

### 实验记录参考（references/experiment-log/目录，来源：nature-experiment-log）

| 文档 | 用途 |
|------|------|
| `references/experiment-log/example-log.md` | 实验记录示例 |
| `references/experiment-log/example-electrochemical.md` | 电化学实验记录示例 |
| `references/experiment-log/example-thermal-stability.md` | 热稳定性实验记录示例 |
| `templates/anomaly-log.md` | 异常记录模板 |
| `templates/equipment-tracking.md` | 设备追踪模板 |
| `templates/experiment-index.md` | 实验索引模板 |

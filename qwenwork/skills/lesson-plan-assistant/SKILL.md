---
name: lesson-plan-assistant
description: 生成符合《义务教育课程标准（2022年版）》的专业教案，基于教学评一致性原则设计。当用户需要编写中小学各学科教案、教学设计、教学计划时使用。不要在非教学场景（如作文批改、试卷生成、学生管理）时触发。
install_source: official
install_method: download
skill_id: official_xSpkR8fk
enabled_at: 1791893786622
version: 1.0.0
name_zh: 教案生成助手
---

# 教案写作助手技能

生成教学评一致性教案，支持K12各学科完整教学设计。

## 严格禁止

- 不要生成非教案内容（试卷、练习题、学生评语等）
- 不要编造课程标准内容，必须基于真实课标要求
- 不要跳过课标分析和学情分析直接写教学过程
- 不要在一次回复中输出超过2个完整教案

## 功能总览

| 功能           | 用途         | 必需输入       |
| -------------- | ------------ | -------------- |
| `full-lesson`  | 生成完整教案 | 课题+学科+年级 |
| `template`     | 输出教案模板 | 学科类型       |
| `evaluation`   | 生成评价量表 | 评价维度       |
| `board-design` | 生成板书设计 | 教学要点       |

## 意图判断

用户说"教案/教学设计/备课":

- 完整教案 → full-lesson (按模板生成全部内容)
- 只要模板 → template (输出空白模板框架)
- 评价设计 → evaluation (生成评价量表)
- 板书设计 → board-design (生成板书结构)

用户说"课标/教学目标/重难点":

- 课标分析 → full-lesson (包含课标摘录分解)
- 目标设计 → full-lesson (四维目标)
- 重难点分析 → full-lesson (基于学情确定)

关键区分: 教案=完整教学设计, 模板=空白框架, 评价=量表工具, 板书=结构图示

## 核心工作流

```
# 1. 解析用户需求 -- 提取关键信息
分析输入 → 识别: 课题名称、学科、年级、课型

# 2. 确定教案类型 -- 决定内容深度
新授课: 完整环节，侧重探究
复习课: 知识梳理，侧重巩固
练习课: 题目设计，侧重应用

# 3. 选择输出格式 -- 生成对应内容
full-lesson: 完整教案Word文档
template: 可编辑教案Word模板
evaluation: 评价量表Word文档
board-design: 板书设计Word文档

# 4. 生成Word文档
- 调用 QoderWork 内置 `docx` 技能生成标准 Word 文档（通过 Skill 工具激活）
- 把教案内容结构（见 references/optimized-template.md）和样式要求传递给 docx 技能
- docx 技能自动处理排版、中文字体（标题黑体/正文宋体）、表格等
- 保存到 QoderWork 工作区输出目录 ~/.qwenworkcn/workspace/<chatId>/outputs/

# 5. 交付文档 -- 通过 present_files 工具向用户展示文件链接
生成完成后用 present_files 工具把 .docx 文件以可点击链接形式呈现给用户
```

## 上下文传递

| 用户输入  | 提取信息 | 用于生成           |
| --------- | -------- | ------------------ |
| 课题名称  | 教学内容 | 教案主题           |
| 学科+年级 | 学段信息 | 课标依据、难度控制 |
| 课型要求  | 教学类型 | 环节设计、时间分配 |
| 特殊要求  | 定制需求 | 个性化调整         |

## 输出格式

**必须输出标准的 Microsoft Word 文档（.docx）**，便于老师编辑和打印：

### Word文档生成方式

通过 QoderWork 内置 `docx` 技能生成（用 Skill 工具激活）。该技能专门处理 .docx 创建、Markdown 转 Word、中文排版等，无需手动安装任何依赖。把教案内容结构（见 references/optimized-template.md）和样式要求传递给 docx 技能即可。

### Word文档特性要求

1. **专业排版**: 标题用黑体，正文用宋体，层次分明
2. **结构清晰**: 八模块结构，层次分明
3. **可编辑**: 老师可直接在Word中修改内容
4. **打印友好**: 适配A4纸张，页边距合理
5. **表格支持**: 评价量表、教学流程等使用表格呈现

### 正确 vs 错误输出示例

```
# [正确] 调用 docx 内置技能生成 Word 文档
# 1. 激活 Skill: docx
# 2. 传入教案内容结构（八模块）和样式要求（见 references/output-templates.md）
# 3. 输出 .docx 到 ~/.qwenworkcn/workspace/<chatId>/outputs/
# 4. 用 present_files 工具向用户展示文件链接

# [错误] 输出纯文本
课题：xxx
教学目标：...

# [错误] 输出HTML
<div class="lesson-plan">...</div>

# [错误] 输出Markdown
# 教学设计
```

## 错误处理

1. 信息不完整 → 询问课题、学科、年级等必要信息
2. 学科不支持 → 说明支持范围（语数英科等K12学科）
3. 年级不明确 → 默认初中难度，可调整

## 详细参考

- [references/optimized-template.md](./references/optimized-template.md) - 教案模板规范
- [references/subject-guides/](./references/subject-guides/) - 各学科教学指南
- [references/output-templates.md](./references/output-templates.md) - Word文档生成模板
- [references/evaluation-rubrics.md](./references/evaluation-rubrics.md) - 评价量表设计

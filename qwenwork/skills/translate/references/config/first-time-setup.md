---
name: first-time-setup
description: 翻译技能偏好的首次配置流程
---

# 首次配置

## 概述

未找到 PREFERENCES.md 时，引导用户完成偏好配置。

**阻塞操作**：必须在任何翻译之前完成本配置。**不要**：
- 开始翻译内容
- 询问文件或输出路径
- 进入任何后续工作流步骤

只问本流程里列出的问题，保存 PREFERENCES.md，然后继续。

## 流程

```
未找到 PREFERENCES.md
        |
        v
+---------------------+
| AskUserQuestion     |
| （所有问题）         |
+---------------------+
        |
        v
+---------------------+
| 创建 PREFERENCES.md  |
+---------------------+
        |
        v
    继续翻译
```

## 提问

**语言**：使用用户的输入语言或已保存的语言偏好。

通过 AskUserQuestion 在一次调用中提出全部问题：

### 问题 1：目标语言

```yaml
header: "Target Language"
question: "默认目标语言？"
options:
  - label: "简体中文 zh-CN（推荐）"
    description: "翻译为简体中文"
  - label: "繁體中文 zh-TW"
    description: "翻译为繁体中文"
  - label: "English en"
    description: "翻译为英文"
  - label: "日本語 ja"
    description: "翻译为日文"
```

注：用户也可输入自定义语言代码。

### 问题 2：翻译模式

```yaml
header: "Mode"
question: "默认翻译模式？"
options:
  - label: "Normal（推荐）"
    description: "先分析内容，再翻译"
  - label: "Quick"
    description: "直接翻译，不做分析"
  - label: "Refined"
    description: "完整流程：分析 → 翻译 → 审校 → 润色"
```

### 问题 3：目标读者

```yaml
header: "Audience"
question: "默认目标读者？"
options:
  - label: "General readers（推荐）"
    description: "通俗用语，对术语多加译注"
  - label: "Technical"
    description: "开发者 / 工程师，常见技术词少加注"
  - label: "Academic"
    description: "正式语域，术语精确"
  - label: "Business"
    description: "商业语气，技术概念加解释"
```

注：用户也可输入自定义读者描述。

### 问题 4：翻译风格

```yaml
header: "Style"
question: "翻译风格？"
options:
  - label: "Storytelling（推荐）"
    description: "叙事流畅、过渡顺滑"
  - label: "Formal"
    description: "专业、结构化、中性语气"
  - label: "Technical"
    description: "精确、文档式、简洁"
  - label: "Literal"
    description: "尽量贴合原文结构"
  - label: "Academic"
    description: "学术、严谨、正式语域"
  - label: "Business"
    description: "简洁、结果导向、行动优先"
  - label: "Humorous"
    description: "保留幽默、机智俏皮"
  - label: "Conversational"
    description: "口语、亲切、对话感"
  - label: "Elegant"
    description: "雅致、文学性、精雕细琢"
```

注：用户也可输入自定义风格描述。

### 问题 5：保存位置

```yaml
header: "Save"
question: "保存到哪里？"
options:
  - label: "User（推荐）"
    description: "$HOME/.qoderwork-skills/（所有项目共用）"
  - label: "Project"
    description: ".qoderwork-skills/（仅当前项目）"
```

## 保存路径

| 选项 | 路径 | 作用域 |
|------|------|--------|
| User | `$HOME/.qoderwork-skills/translate/PREFERENCES.md` | 所有项目 |
| Project | `.qoderwork-skills/translate/PREFERENCES.md` | 当前项目 |

## 配置完成后

1. 必要时创建目录
2. 把所选值写入 PREFERENCES.md
3. 确认："Preferences saved to [path]"
4. 提示："你可以随时往 PREFERENCES.md 里加自定义术语，格式见文件中的 `glossary` 章节。"
5. 用保存好的偏好继续翻译

## PREFERENCES.md 模板

```yaml
target_language: [zh-CN/zh-TW/en/ja/...]
default_mode: [quick/normal/refined]
audience: [general/technical/academic/business/custom]
style: [storytelling/formal/technical/literal/academic/business/humorous/conversational/elegant]

# 自定义术语表（可选）—— 在此加入你自己的译法
# glossary:
#   - from: "Term"
#     to: "翻译"
#   - from: "Another Term"
#     to: "另一个翻译"
#     note: "用法语境"
```

## 后续修改偏好

用户可直接编辑 PREFERENCES.md，或删掉文件以再次触发首次配置。

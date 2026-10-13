# 翻译技能的 PREFERENCES.md 字段定义

## 格式

PREFERENCES.md 使用 YAML 格式：

```yaml
# 默认目标语言（ISO 代码或常用名称）
target_language: zh-CN

# 默认翻译模式
default_mode: normal  # quick | normal | refined

# 目标读者（影响批注密度与语域）
audience: general  # general | technical | academic | business | 或自定义字符串

# 翻译风格偏好
style: storytelling  # storytelling | formal | technical | literal | academic | business | humorous | conversational | elegant | 或自定义字符串

# 触发分块翻译的字数阈值
chunk_threshold: 4000

# 单个 chunk 最大字数
chunk_max_words: 5000

# 自定义术语表（与内置术语表合并）
# CLI --glossary 会覆盖这里的条目
# 支持内联条目和/或文件路径
glossary:
  - from: "Reinforcement Learning"
    to: "强化学习"
  - from: "Transformer"
    to: "Transformer"
    note: "保持英文"

# 从外部文件加载术语表
# 支持绝对路径或相对 PREFERENCES.md 所在目录的相对路径
# 文件格式：含 | from | to | note | 列的 markdown 表格，
# 或 {from, to, note} 的 YAML 列表
glossary_files:
  - ./my-glossary.md
  - /path/to/shared-glossary.yaml

# 语言对专用术语表
glossaries:
  en-zh:
    - from: "AI Agent"
      to: "AI 智能体"
  ja-zh:
    - from: "人工知能"
      to: "人工智能"
```

## 字段

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `target_language` | string | `zh-CN` | 默认目标语言代码 |
| `default_mode` | string | `normal` | 默认翻译模式（`quick` / `normal` / `refined`） |
| `audience` | string | `general` | 目标读者（`general` / `technical` / `academic` / `business` / 自定义） |
| `style` | string | `storytelling` | 翻译风格（`storytelling` / `formal` / `technical` / `literal` / `academic` / `business` / `humorous` / `conversational` / `elegant` / 自定义） |
| `chunk_threshold` | number | `4000` | 触发分块翻译的字数阈值 |
| `chunk_max_words` | number | `5000` | 单 chunk 最大字数 |
| `glossary` | array | `[]` | 通用术语条目（内联） |
| `glossary_files` | array | `[]` | 外部术语表文件路径（绝对或相对 PREFERENCES.md） |
| `glossaries` | object | `{}` | 语言对专用术语条目 |

## 术语条目

| 字段 | 必填 | 说明 |
|------|------|------|
| `from` | 是 | 源词 |
| `to` | 是 | 译文 |
| `note` | 否 | 用法注释（如 "保持英文"、"仅限技术语境"） |

## 术语表文件格式

外部术语表（`glossary_files`）支持两种格式：

**Markdown 表格**（`.md`）：
```markdown
| from | to | note |
|------|----|------|
| Reinforcement Learning | 强化学习 | |
| Transformer | Transformer | 保持英文 |
```

**YAML 列表**（`.yaml` / `.yml`）：
```yaml
- from: "Reinforcement Learning"
  to: "强化学习"
- from: "Transformer"
  to: "Transformer"
  note: "保持英文"
```

路径可为绝对路径，或相对 PREFERENCES.md 所在位置。

## 优先级

1. CLI `--glossary` 文件条目
2. PREFERENCES.md `glossaries[pair]` 条目
3. PREFERENCES.md `glossary` 条目（内联）
4. PREFERENCES.md `glossary_files` 条目（按列出顺序，靠后的覆盖靠前的）
5. 内置术语表（如 `references/glossary-en-zh.md`）

同一源词，靠后的条目覆盖靠前的。

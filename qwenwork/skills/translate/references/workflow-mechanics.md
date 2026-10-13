# 工作流机制

源文物化、输出目录创建、冲突处理的细则。

## 物化源文

| 输入类型 | 动作 |
|----------|------|
| 文件 | 原地使用（无需复制） |
| 内联文本 | 保存到 `translate/{slug}.md` |
| URL | 抓取内容并保存到 `translate/{slug}.md` |

`{slug}`：根据内容主题生成的 2–4 个词的 kebab-case 短语。

## 创建输出目录

在源文件旁创建子目录：`{source-dir}/{source-basename}-{target-lang}/`

示例：
- `posts/article.md` → `posts/article-zh/`
- `translate/ai-future.md` → `translate/ai-future-zh/`

## 冲突处理

若输出目录已存在，先把旧目录改名为 `{name}.backup-YYYYMMDD-HHMMSS/`，再创建新目录。**绝不**覆盖已有结果。

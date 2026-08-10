# 项目布局

本技能只支持短稿和长篇两种互斥布局。Markdown 保存内容真源；`.doubao-book-writer/` 只保存运行证据、备份、报告和交付回执，不能放置正文替代品。

## 短稿布局（Short）

适用：单篇长文、手册、白皮书、报道，预计总字数 ≤ 3 万字。

```
<workspace>/
├── manuscript.md      # 唯一正文真源
├── progress.md        # （可选）进度、恢复点、下一步建议
└── sources.md         # （可选）素材、出处、待核实项
```

两种布局都可以包含 `.doubao-book-writer/`，但该目录只承载需求清单、检查报告、备份和交付中间产物，不参与正文扫描。

## 长篇布局（Long）

适用：非虚构书稿、分章手册、多卷报告，预计总字数 > 3 万字或需要分章。不用于小说、网文、剧本或纯文学长篇。

```
<workspace>/
├── manuscript/              # 章节正文目录
│   ├── ch01-标题.md
│   ├── ch02-标题.md
│   └── ...
├── outline.md               # 大纲与结构真源
├── progress.md              # 全书进度与恢复点
├── chapter-ledger.md        # 章节台账（状态、字数、质检结果）
└── sources/                 # （可选）分文件素材
    ├── topic-a.md
    └── topic-b.md
```

## 混合布局碰撞规则

当同一项目同时存在 `manuscript.md`（根单文件）和 `manuscript/`（子目录）时，视为布局冲突。判定与恢复规则如下：

1. **非空 `manuscript.md` 优先**：若 `manuscript.md` 存在且内容非空（`trim().length > 0`），则采用短稿布局，`manuscript/` 目录被忽略。
2. **空 `manuscript.md` + 存在 `manuscript/*.md`**：若 `manuscript.md` 为空或不存在，且 `manuscript/` 下存在至少一个 `.md` 文件，则采用长篇布局。
3. **Agent 禁止同时维护两种布局**：不得在写入 `manuscript/` 章节的同时保留非空的根 `manuscript.md`，反之亦然。

## 文件职责

| 文件 | 职责 |
|------|------|
| `manuscript.md` / `manuscript/*.md` | 正文唯一真源；禁止在对话中声称完成但未写入此处 |
| `progress.md` | （可选）会话间恢复辅助；记录在写章节、下一步建议，不被 `make` 消费 |
| `chapter-ledger.md` | 长篇专用台账；每章一行，含状态（大纲/成文/质检/终稿）、字数、备注 |
| `outline.md` | 长篇专用结构真源；章标题、目标字数、核心论点 |
| `sources.md` / `sources/` | 素材与出处；联网检索结果、待核实标注、引用格式样例 |

## 推进原则

推进顺序由 `make` 依赖链强制：准备 → 写作 → 交付（短稿跳过大纲）。任何时候运行 `make WORKDIR=<书稿目录>` 会停在最早未满足处并打印下一步。达标后主动进入下一阶段，禁止无限停留在当前阶段。

既有项目切换任务时不重新创建布局；从磁盘正文与已生成的检查报告恢复现状后继续。

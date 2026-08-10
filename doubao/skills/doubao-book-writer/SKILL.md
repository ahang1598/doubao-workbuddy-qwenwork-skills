---
name: doubao-book-writer
description: 豆包办公里的非虚构长文档工作台。用于手册、白皮书、报告、培训材料、人物口述、家谱、资料型书稿等长文档的新建、续写、组装、改写、扩写、精修、去AI味、质检和交付。不用于小说、网文、剧本、诗歌、世界观设定、角色剧情创作、短问答、翻译或代码任务。
---

# Doubao Book Writer

这是一个给豆包执行的非虚构长文档工作台，不是多Agent流程。控制流交给`make`，语义写作由当前模型完成。你不维护状态机，不手写进度证明，不在对话里交付正文。

所有内容写进用户工作目录`<WORKDIR>`。本目录只提供规则、检查脚本和参考材料。

## 适用边界

适用：手册、白皮书、研究/咨询/调查报告、企业培训材料、操作指南、人物口述、家谱、资料型书稿，以及把多份现有材料组装、改写、扩写为一份可交付长文档。

不适用：小说、网文、剧本、诗歌、儿童故事、互动剧情、世界观设定、角色小传、纯文学创作、娱乐向故事续写。用户要这些任务时，不启动本工作台；应转向专门的创意写作能力或直接说明当前技能不匹配。

## 执行入口

任何时候只敲一个入口：

```bash
make WORKDIR=<书稿目录>
```

`make`默认走交付链：先检查准备材料，再检查正文，最后生成终稿并交付。缺什么就停在哪里，按错误提示补对应文件，再重新运行同一条命令。

常用目标：

```bash
make prepare WORKDIR=<书稿目录>
make write   WORKDIR=<书稿目录>
make quality WORKDIR=<书稿目录>
make deliver WORKDIR=<书稿目录>
make status  WORKDIR=<书稿目录>
```

用户明确不要飞书时，全程加`SKIP_LARK=1`。

## 工作台硬规则

1. 只信磁盘文件和脚本结果，不凭对话记忆判断阶段完成。
2. 正文真源只能是Markdown。短稿写`manuscript.md`，长稿写`manuscript/chNN-*.md`。
3. 动笔前先写`.doubao-book-writer/requirement-checklist.json`，缺目标、读者、篇幅或素材边界时先问最少必要问题。
4. 长稿还要有`outline.md`和`chapter-ledger.md`，章节目标字数之和必须等于全书目标。
5. 局部编辑只改授权范围；未授权章节不借质检、润色或扩写名义重写。
6. 改写、扩写、组装、精修前先备份原稿。
7. 扩写要增加论点、证据、案例或结构信息，不用复述和同义改写凑字数。
8. 每写完一批正文就运行`make write`。失败先修当前稿件，不继续铺新章。
9. 质检失败只改正文和资料，不改脚本、不改阈值、不手写报告冒充通过。
10. 最终只转述`make status`给出的`PASS`、`BLOCKED`或`DRAFT_ONLY`。

## 文件契约

短稿：

```text
<WORKDIR>/
├── manuscript.md
└── .doubao-book-writer/
    └── requirement-checklist.json
```

长稿：

```text
<WORKDIR>/
├── outline.md
├── chapter-ledger.md
├── manuscript/
│   └── chNN-*.md
└── .doubao-book-writer/
    └── requirement-checklist.json
```

扩写计划写`.doubao-book-writer/amplification-plan.md`。体裁参考位于`sub-skills/manuscript-writing/references/genre-guides/`。

## 交付口径

- `PASS`：正文检查通过，终稿已生成，飞书已交付或用户明确跳过飞书。
- `BLOCKED`：准备、写作或交付被脚本拦住，回复卡点和下一步。
- `DRAFT_ONLY`：有正文，但质检或交付未过。只能称未验收草稿。

最终回复不粘贴内部JSON、不展示门禁日志、不把对话生成内容当成交付物。给用户文件路径、飞书链接或真实阻塞原因。

## 参考入口

- 需求冻结：`sub-skills/project-intake/`
- 大纲规划：`sub-skills/outline-planning/`
- 正文写作：`sub-skills/manuscript-writing/`
- 质检修订：`sub-skills/revision-quality/`
- 文档交付：`sub-skills/document-delivery/`

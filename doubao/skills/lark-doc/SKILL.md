---
name: lark-doc
description: "Lark Doc 文档统一入口：处理在线 Docx/Wiki 与本地 Word/PDF 文档任务。在线文档 URL/token、读取、创建、编辑、总结等任务路由到 online-doc；本地 .docx/.doc/.pdf 文件、明确要求 Word/PDF 交付或格式保留处理的任务路由到 office-word。不处理 Sheet、Slide、Excel、PowerPoint、Base 表内操作。"
---

# Lark Doc 路由

本 Skill 是 `lark-doc` 的顶层入口，只负责判断资源类型和用户目标，然后读取对应内部模块执行。不要在顶层直接调用 `lark-cli`、处理 Word/PDF 文件、编辑 XML，或一次性读取所有 references。

## 路由规则

| 用户信号 | 读取模块 | 说明 |
|---|---|---|
| 飞书在线文档 URL、`/docx/`、`/wiki/`、docx/wiki token | `online-doc/lark-doc-skill.md` | URL/token 是可定位操作对象，优先级最高 |
| 读取、创建、编辑、总结在线文档；处理在线文档图片、附件、封面、画板引用 | `online-doc/lark-doc-skill.md` | 由在线文档模块决定是否继续切到外部 Sheet/Base/Drive/Whiteboard 能力 |
| 用户上传文件，或给出可访问的本地 `.docx` / `.doc` / `.pdf` 路径 | `office-word/office-word-skill.md` | 真实本地文件对象优先于泛泛的在线文档描述 |
| 明确要求交付 Word/PDF 文件，或要求 Word/PDF 解析、生成、格式保留编辑 | `office-word/office-word-skill.md` | 关注本地强格式交付物 |

## 路由顺序

1. 如果用户明确要操作 Sheet/电子表格/Excel、Slide/幻灯片/PowerPoint、Base/多维表格内部数据，不要留在本 Skill，切到对应能力。
2. 如果用户给出飞书在线文档 URL、`/docx/`、`/wiki/` 或 docx/wiki token，必须读取 `online-doc/lark-doc-skill.md`。不要因为同一句里出现“PDF”“Word”“本地文件”等描述就改走 `office-word`。
3. 如果用户上传文件、给出可访问的本地 `.docx` / `.doc` / `.pdf` 路径、明确要求交付 Word/PDF 文件，或任务核心是 Word/PDF 格式保留与生成，读取 `office-word/office-word-skill.md`。
4. 如果用户没有给出资源，只是要求“写一份文档”“创建文档”“整理成文档”，默认按在线文档处理，读取 `online-doc/lark-doc-skill.md`。
5. 在线文档导出或整理成本地 Word/PDF：先用 `online-doc` 读取源内容，再用 `office-word` 生成目标文件。
6. 本地 Word/PDF 转在线文档：先用 `office-word` 提取或整理本地内容，再用 `online-doc` 创建目标文档。
7. 在线文档中引用、描述或嵌入了 PDF/Word 文件时，仍先用 `online-doc` 读取在线文档，确认真实资源和用户要改的对象。
8. 在线与离线信号冲突时，以可定位对象为准：在线 URL/token 优先于自然语言文件类型描述；真实本地路径/上传文件优先于泛泛提到“在线文档”。仍无法判断时，只问一个澄清问题。

## 示例

- `https://.../wiki/... 这是一个本地 pdf，将标题修改为 xxx` → 读取 `online-doc/lark-doc-skill.md`，因为可操作对象是在线 Wiki URL。
- `帮我把 ./proposal.docx 改成正式公文格式` → 读取 `office-word/office-word-skill.md`，因为可操作对象是本地 Word 文件。
- `写一份会议纪要并生成 Word` → 读取 `office-word/office-word-skill.md`，因为用户明确要求 Word 交付。
- `整理一份项目复盘文档` → 读取 `online-doc/lark-doc-skill.md`，因为没有本地文件和强格式交付要求，默认在线文档。

## 执行规则

- 读取内部模块后，完全遵循该模块的前置条件、参考文件读取规则、脚本使用规则和安全规则。
- 解析相对路径时，以当前已读取的 `SKILL*.md` 所在目录为基准。
- 只读取当前任务需要的模块、子技能和参考文件；不要预读无关 references。
- 进入 `office-word` 后，由 `office-word` 按其内部规则继续分发到具体子技能。
- 进入 `online-doc` 后，如文档内容包含 Sheet、Base、评论、权限、画板等边界能力，按 `online-doc` 的规则切到对应能力；顶层不自行处理这些对象。
- 在线文档默认优先做精准局部更新，不轻易全文覆盖。
- 本地 Word 文档默认优先保留用户原始格式，除非用户明确要求重排版或重建文档。

## 范围

本 Skill 只处理 Doc 文档方向的顶层路由：在线 Docx/Wiki、本地 Word/PDF，以及依赖强格式交付的文档场景。

## 不在本 Skill 范围

- Sheet/电子表格/Excel 的数据读取、编辑、公式、图表、批量写入 → [`lark-sheets`](../lark-sheets/SKILL.md)
- Base/多维表格的表内数据、字段、视图、统计、自动化 → [`lark-base`](../lark-base/SKILL.md)
- Slide/幻灯片/PowerPoint 的创建、编辑、页面内容操作 → [`lark-slides`](../lark-slides/SKILL.md)

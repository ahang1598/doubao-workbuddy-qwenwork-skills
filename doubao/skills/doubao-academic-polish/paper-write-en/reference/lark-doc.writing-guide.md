# 飞书文档交付说明（deliver 阶段）

本文件说明 `make deliver` 阶段如何交付飞书文档，以及特殊情况如何处理。它不负责
论文内容写作、引用格式、表格或图的生成；这些继续遵守 `SKILL.md`、
`subskill/format-guide.md` 和 `reference/table-figure-guide.md`。

## 交付由 make 自动完成，不要手动建文档

飞书文档由 `make deliver` 从通过检查的终稿 `.workflow/paper_final.md` **一次性
创建**，随后读取并校验权限、读回正文并由 `check_lark.py` 校验。你**不要**在写作阶段手动
`lark-cli docs +create` 建占位、也不要边写边 `append`——那会绕过 make 的门禁。
写作阶段只把正文写进 `.workflow/paper_draft.md`，交付一步交给 `make deliver`。

deliver 内部执行（见 Makefile，无需你手动敲）：

```bash
lark-cli docs +create --title "<TITLE>" --doc-format markdown --content @paper_final.md --json
# 未授权公开时不执行权限写入，只读取并验证非公网状态：
lark-cli drive +permission-get-setting --token "<doc_id>" --type docx --format json
# 仅当 PUBLIC_LARK=1 确实代表用户对本次文档和 anyone_readable 档位的明确授权时执行：
lark-cli drive permission.public patch --token "<doc_id>" --type docx \
  --data '{"external_access": true, "link_share_entity": "anyone_readable"}' \
  --yes --format json
# 公开 patch 后仍须再次执行 +permission-get-setting 读回验证。
lark-cli docs +fetch --api-version v2 --doc "<url>" --doc-format xml
```

权限读取结果原样保存到`.workflow/lark_permission.json`，校验对象是
`data.permission_public`。未授权公开时，只有`external_access=false`且
`link_share_entity=closed`才允许继续；
缺字段、读取失败、`external_access=true`或`anyone_*`档位一律保守阻断。默认路径
不得为了“修正默认值”自动执行带`--yes`的收紧patch；这是high-risk-write，必须先
把实际快照和文档标识告知用户，取得本轮针对具体操作的确认。

## 交付原则

1. 正式文件化交付至少产出 1 份飞书文档，链接由 deliver 打印。
2. 单篇完整论文、单个章节、章节组合稿或同一篇论文的修改稿，只交付 1 份文档，不按章节拆多份。
3. 交付目标只由`.workflow/meta.json`的`output_target`决定。用户明确指定Markdown终稿时，在prepare前设为`markdown_only`；不得用任何运行时变量覆盖meta。
4. 环境无法调用`lark-cli`、拿不到`document.url`/`document_id`、权限无法证明合规、fetch失败或check失败时，deliver先写失败`lark_check.json`，再由`status.py`输出`BLOCKED`；如实告知失败步骤，不得声称已完成飞书交付。
5. `PUBLIC_LARK=1`是高风险命令的确认信号，不是公开偏好默认值。只有用户已明确授权本次创建的文档采用`anyone_readable`档位时，才能在本次make命令行显式传入；继承自环境的同名变量无效，不能从“发飞书”“给链接”等一般要求推导出该授权。

## 表格与图（硬约束）

论文表格和图必须按`reference/table-figure-guide.md`生成后再嵌入终稿。数据表在
Markdown源稿中必须使用原生Markdown表格，由整篇文档创建链转换为可编辑表格；
不得把表格栅格化为图片，也不得绕过源稿，直接调用飞书API或`lark-cli`逐单元格拼表。
`lark-cli`只负责整篇文档创建、权限读取/经确认的权限更新和读回。图像只有在具备真实
资产生成、上传和回读校验链路时才能嵌入。

## 读回校验查什么

权限校验先读取并保留`lark_permission.json`；正文校验再由`check_lark.py`读取XML，
检查有标题、有References、有文内引用（作者-年份或编号）、源稿表格已转换、无callout
等花哨块、无占位符、无验真中间痕迹。任一不过，deliver写`status=fail`的
`lark_check.json`，`make status`据此输出`BLOCKED`。成功报告保留权限快照路径和解析后
的`permission_public`，便于后续脚本把权限校验接管为独立门禁。

## 多文档特殊情况

仅当用户提出多个独立任务或多个独立产物（如“一份调研报告 + 一篇论文”、两篇论文、
明确要求不同版本/不同文件）才创建多份文档。这类超出单篇 make 流程的需求，需在
deliver 之外按用户要求分别处理，并在最终回复逐项列出各文档链接。

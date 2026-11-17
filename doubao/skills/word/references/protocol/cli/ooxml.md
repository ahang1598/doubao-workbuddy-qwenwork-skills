---
keyword: ooxml
---

# 取回和提交整份 DOCX

`--doc` 用客户端给的 Canvas `token`。怎么改文件见[整份 DOCX 编辑](../../workflows/canvas-doc-ooxml.md)。

## 取回文件

```bash
lark-cli docs +ooxml-fetch --doc "<token>"
```

退出码为 0 且完整 JSON 返回 `ok=true` 时，用 `data.document.content` 给出的 DOCX 绝对路径。路径暂不可读时只等该路径。缺少路径或文件仍不可读时，按[读取失败的处理](../../workflows/canvas-doc-recovery.md)。只读任务从这个路径读取所需内容即可。

`data.command_result.current_user` 可提供 `user_id`、`name`、`provider`，用于新增批注或修订。导入只用 `user_id` 识别身份。任务需要新增批注或修订且第一次缺少有效 `user_id` 时，再取回一次并以新路径为准。仍缺少时只保留可用的原生作者信息，省略身份映射。

## 提交文件

```bash
lark-cli docs +ooxml-update --doc "<token>" --file-path "<取回的 DOCX 路径>"
```

`--file-path` 使用同一次取回的 DOCX。处于修订模式时，将这次改动写成修订。若明确返回 `5000002`，关闭取回文件里的修订模式标志，保留其中的修订节点，再提交。

成功回执表示已受理。客户端随后应用这份文件。提交接口无法保证拦住并发改动。

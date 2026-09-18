# OOXML 取回与提交

本接口负责从当前打开的 Word 取回可编辑 `.docx` 候选，并提交修改后的候选；文件内部的编辑技术由工作流决定。

本页只定义命令契约。是否取回、只读降级或编辑提交统一由 [`Canvas 路由`](../workflows/canvas-doc.md#路由总表唯一判定入口)决定，不在命令参考中重新选路。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

## 获取 DOCX 文件路径

```bash
lark-cli docs +ooxml-fetch --doc "<token>"
```

- `--doc`：Canvas 上下文提供的 `<token>`。
- 先保留进程退出码和完整 stdout/stderr；仅退出码为 0、JSON 完整且 `ok == true` 时读取 `data.document.content`。该字段须为非空本地 `.docx` 绝对路径；记录返回路径并验证可读后，才记为 `OOXML_DOCX` 和 ready。暂不可读时按 recovery 预算等待同一路径，不重新 fetch；非法信封或缺字段不能当作成功，不猜路径。
- `OOXML_DOCX` 是 [`canvas-doc.md` 最终选中的 `open_ooxml`](../workflows/canvas-doc.md#最终路由与执行证据) 的唯一 `TARGET_DOCX`；必须编辑并提交同一文件，不得复制目标或改换路径。
- 只读任务在 `+local-fetch` 的恢复预算耗尽、但本命令成功时，可把 `OOXML_DOCX` 作为本轮只读快照，按 [文件读取流程](../../SKILL.md#二读取-word) 的 `read.py` 规则解析后回答；不得修改或调用 `+ooxml-update`。这属于 OOXML 只读 fallback，不是“全部 Canvas CLI 不可用”，也不得改读 Canvas `path`。
- 本命令失败时由 [`canvas-doc-recovery.md`](../workflows/canvas-doc-recovery.md#全部-canvas-cli-不可用的判定) 产出分类，再回到 [`canvas-doc.md` 路由总表](../workflows/canvas-doc.md#路由总表唯一判定入口)；本页不自行切换分支。

## 提交 DOCX 候选

```bash
lark-cli docs +ooxml-update --doc "<token>" \
  --file-path "<OOXML_DOCX>"
```

- `--doc`：Canvas 上下文提供的 `<token>`。
- `--file-path`：`+ooxml-fetch` 返回并完成编辑和验收的同一 `OOXML_DOCX` 路径。
- `+ooxml-update` 异步提交；`ok == true` 只表示请求已受理，服务端仍可能在后台同步。
- 当前提交整份替换活动文档，没有对 Fetch 后的用户或协同编辑做原子冲突拒绝。候选文件也不会自动吸收这些编辑；宿主可能在覆盖后提示，空 warnings 不代表没有并发覆盖。已知活动文档发生新写入时不得提交旧候选，按 [OOXML 工作流](../workflows/canvas-doc-ooxml.md) 结束旧周期。

===== 全文完 =====

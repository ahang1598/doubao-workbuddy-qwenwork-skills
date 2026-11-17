# Canvas 自动目录

在打开的 Canvas 里，用 [`table_of_contents`](cli/table_of_contents.md) 增加、刷新、配置或删除目录。

## 操作时机

目录依赖标题和分页时，先完成相关正文和版式修改；整份 DOCX 提交后，等客户端应用再用新内容定位目录。

当前客户端不支持所需目录操作时，保留原目录并说明原因。

## 定位与配置

用 `+local-fetch` 读取目标范围。

- 内容控件式目录用 `data.command_result.table_of_contents` 返回的 `target_id`。
- 只有域的目录用同次正文 XML 中的 PAGEREF 域 ID。
- 新增目录用目标父节点和插入位置。

沿用已有配置，只修改用户要求的选项。

需要将目录与正文分开时，可用[段前分页](xml/p.md)或[独立分页和分节](xml/layout-break.md)。

## 已关闭文件或普通附件

对已经关闭的文件或普通附件，可以使用 `scripts/catalogue.py` 更新已有目录。

看指定页或导出 PDF 的入口见 [能力表](../workflows/canvas-doc.md#能力表)。

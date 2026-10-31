# Base 资源目录命令

## 命令速查

| 命令 | 关键参数 |
|---|---|
| `+base-block-list` | 需要 `base:block:read` |
| `+base-block-create` | 必填 `--name`、`--type`；`--parent-id` 省略则建在根目录 |
| `+base-block-move` | `--block-id`；`--parent-id` 省略则移到根目录；`--before-id`／`--after-id` 定相对位置，互斥 |
| `+base-block-rename` | `--block-id`、`--name` |
| `+base-block-delete` | `--block-id`，带 `--yes` |

所有命令用 `--base-token` 指定 Base。`--parent-id` 是 Base 内 folder ID，不是云空间 folder token，不传字符串 `null`。`--type` 取 `folder`／`table`／`docx`／`dashboard`／`workflow`。

## 资源 ID 与返回
成功响应的 `data` 中，列表返回 `blocks` 和 `total`；写入返回 `block` 及 `created`／`moved`／`renamed`／`deleted` 标记。table、dashboard、workflow 的 `id` 分别用作 `--table-id`、`--dashboard-id`、`--workflow-id`；docx 内容命令用 `docx_token`，目录维护用 block ID；folder 的 `id` 用作 `--parent-id`。Base block 是目录项，Dashboard block 是仪表盘组件，命令和 ID 不混用。

## 内容与删除边界
- 目录创建不收业务字段 schema；内容用 table/field/record/docx/dashboard/workflow 命令。
- 移动 folder 后子资源仍属该 folder。folder 不支持递归删除；先处理非空目录的子资源，其移动或删除服从 Scene 授权范围。
- 删除影响服从 backend 语义，不承诺删除目录项会保留或删除全部底层内容。

## 读取范围与状态恢复
`+base-block-list` 没有 `--limit`／`--offset`。省略 `--parent-id` 返回全部目录资源；指定时只返回该文件夹的直接子资源。可选 `--type` 在 CLI 本地过滤并重算 `total`。

写入结果未知且有 block ID 时，在覆盖目标位置的列表中按 ID 查找；目标目录不确定就不限父目录，也不用排除目标类型的过滤。旧位置没找到不等于已删除，读取失败也不证明不存在。
参数错误查精确命令帮助；无 ID 的目标识别、权限、业务恢复见 [Base Scene](../scenes/base.md#异常恢复)。

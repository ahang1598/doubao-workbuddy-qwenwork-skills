# Canvas：个人画布与命令发现

用于小云雀个人漫剧画布操作，不适用于其他产品的画布或团队空间。与 [生图](generate-image.md)、[生视频](generate-video.md) 区分：修改画布文档不等于生成媒体，独立生成也不会自动写回指定节点。

## 两个入口

先运行 `node "{baseDir}/scripts/ensure-cli.js" --canvas`。返回：

```json
{"cli_path":"/absolute/package/bin/pippit-tool-cli","version":"实际版本","canvas_entry":"/absolute/package/scripts/run.js"}
```

- 原生资产命令：`pippit-tool-cli canvas ...`，命令名替换为 `cli_path`。
- SDK 语义命令：`node "CANVAS_ENTRY" canvas command ...`，`CANVAS_ENTRY` 替换为返回的 `canvas_entry`。不要把 Go 二进制的帮助输出当作语义命令可执行的证明。
- 切换 shell 时仍使用保存的绝对路径；Windows PowerShell 原生命令用 `& "CLI_PATH" ...`，Node 命令用 `node "CANVAS_ENTRY" ...`。授权复用 [CLI 凭据](auth.md)。

## 按用户意图发现操作

先读取精简目录，仅展开要用的命令；以下名称用于定位，以当前安装版本返回的目录为准。

| 操作 | 入口或可定位的语义命令 | 要点 |
| --- | --- | --- |
| 创建画布、查资产、上传素材、分配 ID、提交事务 | `canvas create/get/upload/allocate/apply` | 见 [原生资产命令](canvas-assets.md) |
| 读取画布和资产 | `get_snapshot`、`get_asset`、`get_permissions` | 取得真实节点/资产 ID，不用名称猜 ID |
| 创建业务节点 | `create_biz_node` | 支持类型和初始字段用 `--node-kind` 查看；不要手拼业务节点结构 |
| 节点位置、大小、样式、布局、分组 | `move_nodes`、`resize_node`、`set_node_style`、`align_nodes`、`arrange_nodes`、`group_nodes` 等 | 先查询目标和归属；删除与重排仅限用户请求范围 |
| 连线和画布配置 | `create_edge`、`reconnect_edge`、`delete_edges`、`set_title`、`set_cover` 等 | 连线两端来自当前画布查询 |
| 角色与场景资料 | `xyq.role.updateDescription/updateAppearance/updateSourceInfos`、`xyq.scene.updateDescription` | 用完整命令名分别 describe，遵守具体字段 |
| 图片/视频节点提示词和已有引用 | `xyq.generation.update_prompt` | 先读 `guide prompt-references`；保留其他生成参数，不触发生成 |
| 3D 导演台对象、摄像机、关键帧、动作 | `xyq.scene3d.query` / `xyq.scene3d.apply` | 先读 `guide scene3d` 和 `guide time` |
| 多轨草稿、轨道、片段、输出尺寸 | `xyq.timeline.query` / `xyq.timeline.apply` | 先读 `guide timeline` 和 `guide time`，使用最新 `expectedRevision` |
| 检查点创建、列表、比较、恢复 | `create_checkpoint`、`list_checkpoints`、`compare_checkpoint`、`restore_checkpoint` | 需要网页登录的 credential_scope；本地检查点按账号与画布隔离，不是跨机器备份 |

```bash
node "CANVAS_ENTRY" canvas command list
node "CANVAS_ENTRY" canvas command describe create_biz_node --node-kind role
node "CANVAS_ENTRY" canvas command describe xyq.timeline.apply --operation set_output_size
node "CANVAS_ENTRY" canvas command schema xyq.timeline.apply
node "CANVAS_ENTRY" canvas command guide
```

`list --category 类别` 缩小范围；`describe --path schema.path` 展开字段。`describe` 是摘要视图，嵌套分支不完整；构造复杂输入时用 `schema 命令名` 取得完整契约。不要默认导出所有 schema。需要的命令不存在时报告当前版本的能力限制，不调用猜测的命令。

## 边界与易混淆点

- `create_biz_node` 可建立文字、图片、视频、音频、角色、场景、3D、多轨等业务节点；具体 `nodeKind` 以 schema 为准。创建节点本身不执行生成。
- 提示词标签只解析已有画布节点及目标草稿中的引用。只有上传得到的裸 ID 不能自动加入草稿；无法解析时停止，不能用临时 URL 或虚构引用替代。普通提示词更新不等于故事板脚本编辑。
- 目前没有公开的故事板镜头增删排序、脚本保存、指定镜头生成领域命令；`guide storyboard` 是说明，不是执行能力。底层补丁不能替代这些业务流程。
- 3D 和多轨命令编辑文档，不提供截图、渲染或最终视频导出。多轨时间为整数微秒，3D 动画时间区分帧和源动画秒；先查字段 schema。
- 编辑后按 [画布查询、编辑与验证](../workflows/canvas-edit.md) 回读确认；无需使用媒体异步查询来判断画布写入成功。只有实际取得图片/视频文件时才进入媒体交付标准。

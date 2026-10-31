# `design-cli design-workspace +ls`

## 用途

返回指定 Path 下的**直属**内容：子目录路径、直属 Item 摘要、直属 Frame 摘要。不递归更深层，不加载内容与几何，也不展开 Frame 内部。

要看整棵目录骨架用 [`+tree`](tree.md)，要读完整内容用 [`+get`](get.md)。

## 命令

```bash
design-cli design-workspace +ls \
  --canvas-workspace-id <canvas_workspace_id> \
  [--path <path>]
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--path` | 否 | 目录路径，**必须以 `/` 开头**；未传或为空时取根路径 `/` |

```json
{"canvas_workspace_id":"10001","path":"/characters/female-lead"}
```

## 输出

`xml_data` 内为 `<directory>`：

```xml
<directory canvas_workspace_id="10001" path="/characters/female-lead">
  <child_paths>/characters/female-lead/three-views</child_paths>
  <child_paths>/characters/female-lead/expressions</child_paths>
  <items>
    <item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘"/>
  </items>
  <frames>
    <frame frame_id="560" type="LAYERED" path="/characters/female-lead" title="林夏人物卡" brief="由姓名、身份标签与装饰图形组成的人物卡片"/>
  </frames>
</directory>
```

`child_paths` 是**以 `/` 开头的完整路径**，可直接作为下一次 `--path` 的取值。

Item 与 Frame 只披露 `item_id` / `frame_id`、`type`、`path`、`title`、`brief` 五个字段。
`brief` 是这一层唯一的语义线索——它决定要不要继续 `+get`；`title` 只是短名，不承担这个作用。

读根路径时额外返回 `<canvas_workspace_brief>`：

```xml
<directory canvas_workspace_id="10001" path="/" canvas_workspace_brief="一部发生在雨夜便利店的都市短剧项目">
  <child_paths>/script</child_paths>
  <child_paths>/characters</child_paths>
  <child_paths>/deliverables</child_paths>
  <items/>
  <frames/>
</directory>
```

无内容时输出空节点，不省略容器。

退出码与错误处理见 [`README.md`](README.md)。

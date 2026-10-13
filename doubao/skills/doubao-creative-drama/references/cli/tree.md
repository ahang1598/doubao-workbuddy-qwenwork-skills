# `design-cli design-workspace +tree`

## 用途

返回指定 Path 下的整棵目录树，只有层级关系，不返回任何 Item、Frame 或摘要。因此它不随内容数量增长，可以一次拉完。

用来定位分支：看清项目怎么组织，决定接下来 `+ls` 哪个目录。

## 命令

```bash
design-cli design-workspace +tree \
  --canvas-workspace-id <canvas_workspace_id> \
  [--path <path>]
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--path` | 否 | 目录路径，**必须以 `/` 开头**；未传或为空时取根路径 `/` |

```json
{"canvas_workspace_id":"10001","path":"/"}
```

## 输出

`xml_data` 内为 `<directory_tree>`，`<tree>` 中是 ASCII 目录树文本：

```xml
<directory_tree canvas_workspace_id="10001" path="/">
  <directory path="characters">
    <directory path="female-lead">
      <directory path="expressions"/>
    </directory>
    <directory path="male-lead"/>
  </directory>
  <directory path="deliverables"/>
</directory_tree>
```

顶层 `<path>` 是请求参数的回显，便于确认请求没被改写。

🔴 **树里 `<directory>` 的 `path` 是目录名片段，不是完整路径** —— 这是本命令唯一不以 `/` 开头的地方。要 `+ls` 某个目录时沿层级拼出完整路径、**并补上开头的 `/`**：上例 `expressions` 对应 `/characters/female-lead/expressions`。不想自己拼就用 [`+ls`](ls.md)，它的 `child_paths` 直接给以 `/` 开头的完整路径。

从子路径查询时，树根就是该子路径：

```xml
<directory_tree>
  <canvas_workspace_id>10001</canvas_workspace_id>
  <path>/characters</path>
  <tree>
characters/
├── female-lead/
│   ├── three-views/
│   └── expressions/
└── male-lead/
  </tree>
</directory_tree>
```

退出码与错误处理见 [`README.md`](README.md)。

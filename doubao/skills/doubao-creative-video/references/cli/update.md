# `design-cli design-workspace +update`

## 用途

按 ID 修改单个对象的 `brief` 或 `path`。要一次修改多个用 [`+update-batch`](update-batch.md)。

## 🔴 只能改 `brief` 与 `path`

**`+update` 只接受两个可改字段：`brief` 与 `path`，且只作用于顶层 Item 与 Frame。**

其中 `path` 可在目录整理或用户要求移动归属时修改；`brief` 的门槛更高：只有先 `+get` 确认该产物
已被用户或外部链路被动编辑，且旧 brief 已不能准确描述当前内容时才允许修正。禁止因目录整理、
重新分类、语义推测、措辞优化或补充风格形容词而修改仍然准确的 brief。无法验证内容已经变化时，
保持 brief 不变。

“被动编辑”仅指对象在当前 Agent 流程之外被用户或画布／外部系统改过内容，并继续保留同一个对象
ID。Agent 自己准备执行的编辑、创建衍生版本、用途变化、关系变化或目录迁移都不算。

| 能改 | 不能改 |
|---|---|
| `brief` —— 内容描述 | `title`、`type` |
| `path` —— 目录归属 | `<size>` / `<transform>` 等几何 |
| | `<asset>` / `<inline>` / `<shape>` / `<line>` 等内容分支 |
| | `<source_ids>` —— 血缘只在创建时定，改不了 |
| | **Frame 的成员 Item（一格都改不了）** |

**改内容要重新创建。** 想换一张图、改一段文字、调一个颜色或尺寸，都不是 `+update` 能做的事：
用 [`+create`](create.md) 建一个新对象。

写了其他字段**不会报错，也不会生效** —— 提交上去只有 `brief` 与 `path` 落下来。
不要靠 `+update` 的返回值去确认别的字段改没改。

## 命令

```bash
design-cli design-workspace +update \
  --canvas-workspace-id <canvas_workspace_id> \
  --input - < item.xml
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--input -` | 是 | `input`；值为 stdin 的完整原始内容 |

对象 ID 写在 XML 里，不通过 CLI 参数传递。

`--input` 只接受 `-`，传其他值或 stdin 为空时 CLI 退出码 `2`。

```json
{"canvas_workspace_id":"10001","input":"<item>...</item>"}
```

## 输入

根节点为 `<item>` 或 `<frame>`，**必须携带 `item_id` 或 `frame_id`**，
并带上 `type`（它标明这是什么对象，但改不了）。

仅当 `+get` 已确认产物被动编辑且旧摘要失真时，修正摘要：

```xml
<item item_id="123" type="IMAGE" brief="林夏的标准人物立绘，正面全身、米白色风衣"></item>
```

只改目录归属：

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead"></item>
```

产物已被动编辑且同时需要迁移目录时，两个一起改：

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead" brief="林夏的标准人物立绘，正面全身、米白色风衣"></item>
```

Frame 同形，且**不带 `<items>`** —— 成员改不了，列出来也没有意义：

```xml
<frame frame_id="560" type="LAYERED" path="/deliverables/poster" brief="改为暖色调的「窗」字主视觉"></frame>
```

改 `path` 就是移动目录归属，新目录不需要预先创建，对象 ID 不变。**`path` 必须以 `/` 开头。**

**两格都按 patch 语义**：不写这个属性 = 保持原值，写成空串（`brief=""`）= 清空这一格。

## 输出

`xml_data` 内为更新后的对象，含它当前的完整形态（不只是你改的那两格）：

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘，正面全身、米白色风衣">
  <size width="640" height="960"/>
  <asset url="https://cdn.example.com/s/a1B2c3"/>
</item>
```

⚠️ **返回里带 `title` / 几何 / 内容分支，是在回显它们的当前值，不代表这次改了它们。**
照抄这份返回再提交一次，多出来的那些格同样不会生效。

退出码与错误处理见 [`README.md`](README.md)。

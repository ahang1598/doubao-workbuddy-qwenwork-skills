# `design-cli design-workspace +get`

## 用途

读取明确指定的 Item 与 Frame 的完整结构，含内容分支与几何（`size` 或 `transform`）。Frame 连同全部成员 Item 一起返回。

这是从目录索引进入完整内容的唯一入口。先用 [`+ls`](ls.md) 按 `brief` 选定目标，再 `+get`。

## 命令

```bash
design-cli design-workspace +get \
  --canvas-workspace-id <canvas_workspace_id> \
  [--item-ids <id[,id...]>] \
  [--frame-ids <id[,id...]>]
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--item-ids` | 条件必填 | `item_ids`；为空时省略 |
| `--frame-ids` | 条件必填 | `frame_ids`；为空时省略 |

两个参数都支持逗号分隔或重复传入，效果相同：

```bash
design-cli design-workspace +get --canvas-workspace-id 10001 --item-ids 123,188
design-cli design-workspace +get --canvas-workspace-id 10001 --item-ids 123 --item-ids 188
```

约束：

- 至少提供一项，两者都为空时 CLI 退出码 `2`，请求不会发出
- 两组 ID 合计最多 10 个
- 空项会被丢弃，值两端空白会被去除
- 不支持不带 ID 隐式读取全部内容

```json
{"canvas_workspace_id":"10001","item_ids":["123"],"frame_ids":["560"]}
```

## 输出

`xml_data` 内为 `<get_result>`，固定包含 `<items>` 与 `<frames>`，未请求的类型输出空节点：

```xml
<get_result canvas_workspace_id="10001">
  <items>
    <item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘">
      <size width="640" height="960"/>
      <asset url="https://cdn.example.com/s/a1B2c3"/>
    </item>
  </items>
  <frames>
    <frame frame_id="560" type="LAYERED" path="/deliverables/poster" title="窗字主视觉" brief="由蓝色矩形与标题文字共同组成的「窗」字主视觉">
      <size width="960" height="520"/>
      <items>
        <item item_id="561" type="SHAPE" title="蓝色外框" brief="「窗」字主视觉的蓝色外框">
          <transform x="0" y="0" width="960" height="520" rotation="0" z_index="10"/>
          <shape shape_kind="round-rect" corner_radius="24">
            <fill color="#1B4D8F" opacity="1"/>
            <stroke width="3" style="solid" line_cap="round" line_join="round" miter_limit="4">
              <paint color="#0F2E56" opacity="1"/>
            </stroke>
          </shape>
        </item>
        <item item_id="563" type="TEXT" title="窗字标题" brief="主视觉「窗」字标题">
          <transform x="520" y="120" width="380" height="280" rotation="0" z_index="12"/>
          <inline>
            <contents>
              <content bold="true">窗</content>
            </contents>
            <style font_size="200" font_family="寒蝉锦书宋Pro" font_weight="700" color="#FFFFFF" align="center" vertical_align="center"/>
          </inline>
        </item>
      </items>
    </frame>
  </frames>
</get_result>
```

要点：

- **Frame 成员不带 `path`** —— 它在目录中不可独立寻址
- **顶层对象与 Frame 只有 `<size>`，没有位置**
- **成员的 `<transform>` 的 `x` / `y` 是相对所属 Frame 左上角的偏移**；
  上例 561 贴着 Frame 左上角，所以是 `x="0" y="0"`
- 只请求 Item 时 `<frames />` 为空节点，反之同理
- 创建时声明过来源的对象会带 `<source_ids>`；没有血缘的对象不出现这个标签

🔴 **读到的内容改不了。** `+update` 只能改 `brief` 与 `path`，Frame 的成员一格都改不了 ——
要换内容就 [`+create`](create.md) 一个新对象。见 [`update.md`](update.md)。

⚠️ **读回来的 `<source_ids>` 不要原样抄进 `+create`。** 它记的是那个对象**当初**的来源；
在 `+create` 里它会被重新解释成**本次新对象**的落位锚点。做新版本时应该填的是你正在派生的那个
对象的 ID（通常就是你刚 `+get` 的这一个），而不是它的来源。

退出码与错误处理见 [`README.md`](README.md)。

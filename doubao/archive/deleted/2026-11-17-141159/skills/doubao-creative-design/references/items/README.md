# Item 类型 Reference

Canvas Workspace 支持 **6 种 Item 类型**，由 `type` 属性决定。本目录逐类型记录字段、取值与示例。

调用哪个命令、参数怎么传见 [`../cli/README.md`](../cli/README.md)。

## 6 种类型

| `type` | 内容分支 | 用途 | Reference |
|---|---|---|---|
| `IMAGE` | `<asset>` | 图片 | [`image.md`](image.md) |
| `VIDEO` | `<asset>` | 视频 | [`video.md`](video.md) |
| `TEXT` | `<inline>` | 文本 | [`text.md`](text.md) |
| `SHAPE` | `<shape>` | 基础图形 | [`shape.md`](shape.md) |
| `LINE` | `<line>` | 线段与连接关系 | [`line.md`](line.md) |
| `HTML` | `<asset>` | 上传后的完整 HTML 作品；仅允许作为顶层 Item | [`HTML.md`](HTML.md) |

`IMAGE`、`VIDEO` 与 `HTML` 共用 `<asset>` 分支，其余各有专属分支。分支名与类型名不完全同名——`TEXT` 用的是 `<inline>`。

**内容分支四选一**：一个 Item 只能出现与其 `type` 对应的那一个分支节点。

## 属性与子元素的分工

两条总规则：

1. **标量走 XML 属性，有结构的走子元素。**
2. **数组套一层容器**：`<items>` 里装 `<item>`、`<frames>` 里装 `<frame>`、
   `<points>` 里装 `<point>`、`<stops>` 里装 `<stop>`、`<contents>` 里装 `<content>`。
   单个对象的根节点是单数（`<item>` / `<frame>`），与容器里的成员同形 ——
   照着读到的样子改一改再提交就总是对的。

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘">
  <size width="640" height="960"/>
  <asset url="https://cdn.example.com/s/a1B2c3"/>
</item>
```

`item` 的五个标量走属性：

| 属性 | 必填 | 说明 |
|---|---:|---|
| `item_id` | 见下 | 稳定 ID；`+create` 不填，`+update` 必填，读取时总有 |
| `type` | 是 | 字符串枚举名，不用数字 |
| `path` | 顶层 Item 是 | 目录归属，**必须以 `/` 开头**；Frame 成员**不填** |
| `title` | `+create` 是 | **对象的短名**，几个字，一眼认出这是什么 |
| `brief` | 是 | 内容摘要，`+ls` 阶段唯一的语义线索 |

### `title` 与 `brief` 的分工

两个都是描述性字段，但**消费方不同**，不要填成一样的内容：

| | `title` | `brief` |
|---|---|---|
| 作用 | 对象的名字 | 对象内容的描述 |
| 长度 | 几个字的短名 | 一句话 |
| 目的 | 一眼认出这是什么 | 判断要不要继续 `+get` |
| 例子 | `林夏立绘` | `林夏的标准人物立绘，正面全身、蓝色雨衣` |

`title` 要像文件名一样简短、可辨识；把一整句描述塞进 `title` 就失去了短名的作用。
`brief` 可以写足够的细节。

**`brief` 不是可随意润色的标签。** 对已有对象，只有 `+get` 已确认该产物被用户或外部链路被动编辑，
导致现有 `brief` 与实际内容不再一致时，才用 `+update` 同步修正。目录整理、重新分类、获得新推测、
更换措辞或希望“描述得更好”都不能触发 brief 改写；这些情况保持原 brief，只按需调整 `path`。
这里的“被动编辑”特指对象在 Agent 当前执行流程之外被用户或画布／外部系统改过内容，并继续保留
同一个对象 ID；Agent 正准备执行的编辑、创建衍生版本、用途变化或目录变化都不属于被动编辑。

**`+create` 时必须给 `title`。** 不校验（给了空的也能建成），但建出来的对象就没有名字，
而且 **`title` 建完就改不了**（`+update` 只能改 `brief` 与 `path`）—— 一次写对。

### 几何：`<size>`（根节点）与 `<transform>`（Frame 成员）

🔴 **顶层对象没有位置，你不指定它摆在哪里** —— 只说「要多大」。

| 对象 | 几何节点 |
|---|---|
| 顶层 Item（不属于任何 Frame） | `<size>` |
| Frame | `<size>` |
| **Frame 成员 Item** | `<transform>` |

`<size>` 定义顶层对象的**展示边界尺寸**：对顶层 Item，它表示该对象在画布上的宽高；对 Frame，
它表示完整交付物的宽高以及成员相对坐标所依附的 Frame 尺寸。它不是图片／视频源文件的像素分辨率，
也不负责决定顶层对象在无限画布中的落点。

`<size>` 只有两格，**都必填**：

| 属性 | 说明 |
|---|---|
| `width` / `height` | 尺寸，必须大于 0 |

**`<size>` 没有 `x` / `y` / `rotation` / `z_index`。** 写了也不生效（未声明的属性被静默跳过）。
顶层对象的位置由服务端安排；不得从 `<size>` 推导、编码或恢复世界坐标。

`<transform>` 六格全是属性，没有 `offset` / `size` 两层：

| 属性 | 必填 | 说明 |
|---|---:|---|
| `x` / `y` | 是 | **相对所属 Frame 左上角的偏移** |
| `width` / `height` | 是 | 尺寸，必须大于 0 |
| `rotation` | 否 | 角度，缺省 `0`；围绕未旋转外接框中心 |
| `z_index` | 否 | 越大越靠前；缺省 `0` |

成员的 `rotation` 与 `z_index` 恒有：`0` 是有意义的取值（不旋转、最底层），不会被省掉。

**空值不渲染**：没有标题就没有 `title` 属性，没有摘要就没有 `brief` 属性，没有描边就没有 `<stroke>` 子元素。

`z_index` 决定 Frame 内部的叠放顺序，别漏——漏了所有成员都是 `0`，前后关系不确定。

## 怎么选类型

- 摄影、插画、纹理、抠图主体 → `IMAGE`
- 视频 → `VIDEO`
- 需要准确、可编辑、可搜索的文字 → `TEXT`
- 规则的色块、底板、胶囊、标签底 → `SHAPE`
- 分隔线、连接线、指向关系 → `LINE`

几条边界：

- **`SHAPE` 不承载文字**。带文字的卡片、按钮、标签拆成背景 `SHAPE` + 上层 `TEXT`，`TEXT` 的 `z_index` 更高。
- **线不要用超薄 `SHAPE` 模拟**，用 `LINE`。
- `HTML` 是顶层 Item：完整 `.html` 文件经 `FileBatchUpload` 上传后，以短链写入 `<asset url>`。禁止把 HTML 放进 Frame。
- 多个单独看没有完整语义的非 HTML Item 才组合成一个 Frame，整体读取与修改。

## 颜色与透明度

统一用六位十六进制 `#RRGGBB`，透明度单独写入 `opacity`（`0..1`）。不用短十六进制、`rgb()`、`hsl()` 或命名色。

## Frame

Frame 由多个单独看没有完整语义的 Item 组成，对调用方是**原子对象**：整体创建、整体读取。

| 属性 / 子元素 | 必填 | 说明 |
|---|---:|---|
| `frame_id` | 读取时有；`+create` 不填 | `+update` 必填 |
| `type` | 是 | `LAYERED` / `BLANK` |
| `path` | 是 | 目录归属 |
| `title` | `+create` 是 | 对象的短名，口径同 Item |
| `brief` | 是 | 整组内容的摘要，只给 Agent 消费 |
| `size` | 是 | 子元素；整组要多大。**Frame 没有 `transform`** |
| `items` | 是 | 成员 Item，**不填 `path`**；不得包含 `HTML` Item |

Frame 的 `title` 描述**整组**内容（如 `窗字主视觉`），成员各有自己的 `title`。

成员 Item 的 `transform` 的 `x` / `y` 是**相对 Frame 左上角的偏移** ——
下例中 561 贴着 Frame 左上角，所以是 `x="0" y="0"`；563 在 Frame 内向右 520、向下 120。
**不需要知道这个 Frame 最终落在画布的哪里。**

```xml
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
```

🔴 **Frame 的成员建完就改不了。** `+update` 只能改 Frame 自己的 `brief` 与 `path`，
改不了任何成员 —— 要换成员内容就 `+create` 一个新 Frame。

## batch

`+create-batch` 与 `+update-batch` 的根节点。`<items>` 与 `<frames>` 是**容器**，
成员 `<item>` / `<frame>` 装在里面；没有内容的那一侧仍会出现空容器。

```xml
<batch>
  <items>
    <item type="SHAPE" path="/deliverables/poster" title="标题底板" brief="主标题下方的深蓝色矩形底板">
      <size width="960" height="520"/>
      <shape shape_kind="rect">
        <fill color="#1B4D8F" opacity="1"/>
      </shape>
    </item>
  </items>
  <frames/>
</batch>
```

## 取值来源说明

`shape_kind`、`line_kind`、`stroke.style`、`arrow.kind`、`align` 都是开放取值。本目录列出的是已验证可用的集合，**用表内取值最稳妥**；表外值不保证能渲染出来。

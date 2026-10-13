# `design-cli design-workspace +create`

## 用途

一次创建单个对象。调用方不提供 ID，创建时自动生成。要一次创建多个用 [`+create-batch`](create-batch.md)。

## 命令

```bash
design-cli design-workspace +create \
  --canvas-workspace-id <canvas_workspace_id> \
  --input - < item.xml
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--input -` | 是 | `input`；值为 stdin 的完整原始内容 |

`--input` 只接受 `-`，传其他值 CLI 退出码 `2`。stdin 为空或纯空白同样退出码 `2`，请求不会发出。

```json
{"canvas_workspace_id":"10001","input":"<item>...</item>"}
```

## 输入

根节点为 `<item>` 或 `<frame>`，**不携带 `item_id` / `frame_id`**。

`path`、`title` 与 `brief` 必传：`path` 决定目录归属，**必须以 `/` 开头**，写一个不存在的路径就形成对应目录；
`title` 是对象的短名；`brief` 是对象内容的简要描述。

⚠️ **`title` 不校验，漏了照样建成** —— 但建出来的对象没有名字。
`title` 与 `brief` 的分工见 [`../items/README.md`](../items/README.md)：前者是短名，
后者是内容描述、可以写细节。两个填成一样的内容是最常见的错。

**`<size>` 必传**：它是「这个对象要多大」。顶层对象没有位置，你不指定它摆在哪里。

创建一个 Item：

```xml
<item type="IMAGE" path="/deliverables/key-visuals" title="雨夜主视觉" brief="林夏站在雨夜便利店门口的主视觉">
  <size width="960" height="1280"/>
  <asset url="https://cdn.example.com/s/x9Y8z7"/>
</item>
```

创建一个 Frame，成员 Item 同样不带 ID，且**不填 `path`**。
Frame 自己给 `<size>`，**成员给 `<transform>`，`x` / `y` 是相对 Frame 左上角的偏移**：

```xml
<frame type="LAYERED" path="/deliverables/poster" title="窗字主视觉" brief="由蓝色矩形与白色窗格组成的「窗」字主视觉">
  <size width="960" height="520"/>
  <items>
    <item type="SHAPE" title="蓝色外框" brief="主视觉的蓝色矩形外框">
      <transform x="0" y="0" width="960" height="520" rotation="0" z_index="10"/>
      <shape shape_kind="rect">
        <fill color="#1B4D8F" opacity="1"/>
      </shape>
    </item>
    <item type="SHAPE" title="左上窗格" brief="左上角的白色圆角窗格">
      <transform x="80" y="80" width="360" height="360" rotation="0" z_index="11"/>
      <shape shape_kind="round-rect" corner_radius="8">
        <fill color="#FFFFFF" opacity="1"/>
        <stroke width="4" style="solid">
          <paint color="#1B4D8F" opacity="1"/>
        </stroke>
      </shape>
    </item>
  </items>
</frame>
```

上例中「左上窗格」贴在 Frame 内部左上角向内 80px 处，所以写 `x="80" y="80"` ——
不需要知道这个 Frame 最终落在画布的哪个位置。

创建 HTML Item 时，先用 `FileBatchUpload` 上传完整 `.html` 文件取得短链，再写入 `<asset url>`。下列 XML 是 `design-cli design-workspace +create` 的唯一合法 HTML 传输载荷；禁止 `<frame type="HTML">`：

```xml
<item type="HTML" path="/deliverables/detail-page" title="商品详情页" brief="可编辑的商品详情页 HTML 成品">
  <size width="1080" height="8000"/>
  <asset url="https://cdn.example.com/s/htmlA1b2"/>
</item>
```

完整调用示例：先复制 [`example/create-HTML.xml`](../../example/create-HTML.xml)，将其中的 `<asset url>` 替换为 `FileBatchUpload` 返回的真实短链，再从 Skill 根目录执行：

```bash
design-cli design-workspace +create \
  --canvas-workspace-id <canvas_workspace_id> \
  --input - < example/create-HTML.xml
```

从响应保存服务端生成的 Item ID，随后使用 `design-cli design-workspace +get` 回读该对象；禁止把带返回 ID 的 `xml_data` 再次用于 `+create`。

HTML Item 回读成功后，把本次使用的原始 `canvas_workspace_id` 与该回读对象的服务端 `item_id` 拼成 `<canvas_workspace_id>?item_id=<item_id>` 单值并原样传给 `present_files`，由该调用输出对应画布卡片。例如 Workspace ID 为 `workspaceid`、回读 Item ID 为 `xxx` 时，传入值必须是 `workspaceid?item_id=xxx`。问号两侧不得有空格，键名必须保持 `item_id`；不得拆成两个参数、数组或两次调用。两个 ID 必须指向同一 Workspace 中刚完成 `+get` 核验的 HTML Item；禁止只传 Workspace ID，也禁止传旧版本或其他对象的 Item ID。不得创建 Workspace ID 中间文件，也不得用普通聊天文字、Markdown 链接或 CLI stdout 代替画布卡片。HTML 自身的同尺寸预览图仍按 [HTML 固定画布与交付协议](../html/coding-rendering.md#html-验收与交付) 先上传 CDN，再使用返回的公网链接以标准 Markdown 图片语法展示；该截图不调用 `present_files`、不创建 IMAGE Item 且不写入画布。原始 `.html` 也不进入 `present_files`。

多个单独看没有完整语义的 Item 才建 Frame。每个都能独立理解的内容应各自 create，或用 `+create-batch` 一次提交。

## `source_ids`：声明来源，同时决定落位

新对象由画布上已有的对象派生而来时（照着参考图生成、基于某张图改写、把某个 Frame 拆出一版），
用 `<source_ids>` 把来源的 ID 列出来。**它不是可有可无的元数据**：

1. **记录血缘** —— `+get` 会回显，你之后能看出这个产物是从哪来的
2. **决定新对象落在画布哪里** —— 服务端把它当作本次创建的定位锚点

```xml
<item type="IMAGE" path="/deliverables/v2" title="雨夜主视觉 v2" brief="在 v1 基础上加强雨丝的主视觉">
  <size width="960" height="1280"/>
  <asset url="https://cdn.example.com/s/x9Y8z7"/>
  <source_ids>
    <source_id>201</source_id>
  </source_ids>
</item>
```

**填了**：新对象紧挨着来源对象**放在它右边**，与来源同一行对齐。
**不填**：新对象落到画布**最下方另起一行**。

所以「新版本挨着旧版本」还是「孤零零掉到画布底部」，唯一的开关就是这一格。
从参考图生成、做同一产物的新版本、把一张图拆成多个部件——这些都该填。

### 取值

**`<source_id>` 可以是 `item_id`，也可以是 `frame_id`** —— 服务端按 ID 在画布上找对象，两种都认。
也可以填 Frame 成员的 `item_id`，此时按它所属的 Frame 定位。

| 规则 | 说明 |
|---|---|
| 必须是**本画布上已存在且可见**的对象 | 解析不到就**整批拒**（退出码 `1`），不会「忽略这个引用照样建」 |
| **不能引用同一批里正在创建的对象** | 它们还没有 ID；`+create` 也不接受你自己指定 ID |
| 可以填多个 | 多个来源时一并列出，定位取其中最靠下一行的最右侧 |
| ID 两端空白会被去除、重复项会被忽略 | 但纯空白的 `<source_id>` 会报错 |
| 没有来源时**整个 `<source_ids>` 标签不写** | 不要写成空标签 |

🔴 **写错 ID 不是「血缘丢失」而是整个请求失败。** 来源 ID 要从 `+ls` / `+get` 的返回里取，不要凭印象拼。

⚠️ **`+update` 改不了它。** 血缘只在创建时定下来，`+update` 里写了不报错也不生效（见 [`update.md`](update.md)）。

## 资产

`IMAGE`／`VIDEO`／`HTML` Item 的 `<asset url="…">` 只接受可持久访问的短链。**CLI 不上传本地文件，也不代为解析路径。** HTML 文件必须先经 `FileBatchUpload` 上传。

🔴 **已经有短链就直接用**（生成、搜索、或画布上读回来的），**不要再上传一遍** —— 那会造出第二条指向同一份素材的短链。只有手上仅有本地文件时才去上传。

## 输出

`xml_data` 内为补全 ID 后的对象：

```xml
<item item_id="201" type="IMAGE" path="/deliverables/key-visuals" title="雨夜主视觉" brief="林夏站在雨夜便利店门口的主视觉">
  <size width="960" height="1280"/>
  <asset url="https://cdn.example.com/s/x9Y8z7"/>
</item>
```

返回值带 ID，**不能直接抄回去当下一次 `+create` 的输入**。

退出码与错误处理见 [`README.md`](README.md)。


Workspace 初始化与 HTML Item 卡片交付属于不同阶段：`+workspace-create` 后使用原始 Workspace ID 调用 `present_files(<workspace_id>)`，交付 Workspace 画布卡片；只有 HTML Item 已创建并完成 `+get` 回读后，才使用 `<workspace_id>?item_id=<item_id>` 单值交付对应 Item 卡片。不得为初始化编造 Item ID，也不得将查询字符串传作 CLI 的 Workspace ID。

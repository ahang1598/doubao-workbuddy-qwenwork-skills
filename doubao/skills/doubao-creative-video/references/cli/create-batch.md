# `design-cli design-workspace +create-batch`

## 用途

在一次请求中创建多个独立 Item，或多个含成员的 Frame，或两者混合。Frame 的成员属于同一个写入单元，不允许拆成几次不完整的创建。

视频／图像生成与编辑工具结果不使用本命令重复创建 VIDEO／IMAGE Item；应按 [媒体直接交付与产后目录整理](../media-delivery.md) 透传 Workspace ID、直接交付并在产后仅更新真实对象的 `path`。以下创建协议只用于其他确需手工创建的资产／对象。

## 命令

```bash
design-cli design-workspace +create-batch \
  --canvas-workspace-id <canvas_workspace_id> \
  --input - < batch.xml
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--canvas-workspace-id` | 是 | `canvas_workspace_id` |
| `--input -` | 是 | `input`；值为 stdin 的完整原始内容 |

`--input` 只接受 `-`，传其他值或 stdin 为空时 CLI 退出码 `2`。

```json
{"canvas_workspace_id":"10001","input":"<batch>...</batch>"}
```

## 输入

根节点为 `<batch>`，内部固定包含 `<items>` 与 `<frames>`，没有内容时输出空节点。所有 Item 与 Frame **均不携带 ID**。

HTML 只能放在顶层 `<items>` 中并写成 `<item type="HTML">`；其 `.html` 必须先经 `FileBatchUpload` 上传，`<asset url>` 使用所得短链。禁止 `<frame type="HTML">`，也禁止把 HTML Item 放进 Frame。单个 HTML 作品默认使用 [`+create`](create.md)；只有确需一次原子创建多个独立对象时才使用本命令。

响应返回后保存每个 HTML Item 的服务端 `item_id`，逐项执行 `+get` 回读。整批回读完成后，每个 HTML Item 分别调用一次 `present_files` 输出画布卡片：每次把同一 `canvas_workspace_id` 与该项自己的 `item_id` 拼成 `<canvas_workspace_id>?item_id=<item_id>` 单值并原样传入；不得拆成两个参数、数组或两次调用，不得只传 Workspace ID，也不得用一次 Workspace 级卡片合并替代多个 HTML Item 的卡片。

顶层对象给 `<size>`（要多大），**没有位置**；Frame 成员给 `<transform>`，
其 `x` / `y` 是**相对所属 Frame 左上角的偏移**。

```xml
<batch>
  <items>
    <item type="IMAGE" path="/deliverables/key-visuals" title="海报主视觉" brief="海报主视觉人物图">
      <size width="960" height="1280"/>
      <asset url="https://cdn.example.com/s/k3yv1s"/>
    </item>
  </items>
  <frames>
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
  </frames>
</batch>
```

同时创建 Item 与 Frame：

```xml
<batch>
  <items>
    <item type="IMAGE" path="/deliverables/key-visuals" title="海报主视觉" brief="海报主视觉人物图">
      <size width="960" height="1280"/>
      <asset url="https://cdn.example.com/s/k3yv1s"/>
    </item>
  </items>
  <frames>
    <frame type="LAYERED" path="/deliverables/poster" title="窗字标题组合" brief="由多个矩形和文字共同组成的「窗」字标题组合">
      <size width="960" height="520"/>
      <items>
        <item type="SHAPE" title="蓝色外框" brief="主视觉的蓝色矩形外框">
          <transform x="0" y="0" width="960" height="520" rotation="0" z_index="10"/>
          <shape shape_kind="rect">
            <fill color="#1B4D8F" opacity="1"/>
          </shape>
        </item>
      </items>
    </frame>
  </frames>
</batch>
```

Frame 成员同样不带 ID，且不填 `path`。**创建时带上 `item_id` / `frame_id` 会被拒** —— 所以下面「输出」里那份带 ID 的响应不能直接抄回来当输入。

## `source_ids`：整批共用一个落位锚点

语法、取值与约束见 [`create.md`](create.md#source_ids声明来源同时决定落位)。批量场景多两条：

**整批的 `source_ids` 会被合并成一组**，顶层 Item、Frame、Frame 成员上写的全部算进来。
服务端不会「A 挨着 A 的来源、B 挨着 B 的来源」分别定位 —— 本批所有新对象作为**一组连续摆放**，
整组一起放到这些来源里最靠下那一行的最右侧。

所以：**来源不同的对象不要塞进同一批**。想让两个产物各自挨着各自的参考图，分两次 `+create`。

**任何一个 `<source_id>` 解析不到，整批都不会创建**（与短链失效同样是全批拒）。批越大，
一个拼错的 ID 浪费的工作越多。

## 约束

**根节点必须是 `<batch>`。** 传单个 `<item>` / `<frame>` 会被拒并提示改用 [`+create`](create.md) —— 响应形状跟着请求根走，收了单个就会回一个不带 `<batch>` 壳的响应，下次照抄这份输出提交回来就对不上了。

**一批最多 50 个对象**，按顶层 Item + Frame + Frame 成员**合计**计数。超限**直接拒、不截断** —— 截断出来是「少建了几个对象的成功响应」，调用方不会知道后面那些没建成。

**`input` 最大 1MB。** 超限同样直接拒。素材本体走短链引用、不进 XML，这个额度对一批结构化描述极宽裕。

**`<asset url="…">` 里的短链解析失败会整批拒。** 短链解不出来说明它不是一条有效短链、或已经失效；此时宁可当场报错让你换一条重提，也不会「建成功但素材永远取不到」。带 `@` 前缀的本地路径同样一律拒 —— CLI 不上传文件。

🔴 **已经有短链就直接用，不要再上传一遍**；只有手上仅有本地文件时才去换一条。

## 原子性

**一批全成或全败。** 任何一个对象失败，整批都不生效 —— 不存在「前几个建好、后几个失败」的部分成功状态，也不会留下半批脏数据。

正因如此才有上面那个 50 的上限：一批要整体应用，批越大，同一张画布上的其它写入等待越久。

## 输出

`xml_data` 内为 `<batch>`，各对象已补全生成的 ID：

```xml
<batch>
  <items>
    <item item_id="207" type="IMAGE" path="/deliverables/key-visuals" title="海报主视觉" brief="海报主视觉人物图">
      <size width="960" height="1280"/>
      <asset url="https://cdn.example.com/s/k3yv1s"/>
    </item>
  </items>
  <frames>
    <frame frame_id="612" type="LAYERED" path="/deliverables/poster" title="窗字标题组合" brief="由多个矩形和文字共同组成的「窗」字标题组合">
      <size width="960" height="520"/>
      <items>
        <item item_id="613" type="SHAPE" title="蓝色外框" brief="主视觉的蓝色矩形外框">
          <transform x="0" y="0" width="960" height="520" rotation="0" z_index="10"/>
          <shape shape_kind="rect">
            <fill color="#1B4D8F" opacity="1"/>
          </shape>
        </item>
      </items>
    </frame>
  </frames>
</batch>
```

退出码与错误处理见 [`README.md`](README.md)。

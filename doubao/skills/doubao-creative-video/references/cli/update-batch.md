# `design-cli design-workspace +update-batch`

## 用途

批量调整 `brief` 与 `path`。整理扁平画布的目录结构时最常用——把根目录下堆积的对象按 `brief` 归类，一次写入新的 `path`。

## 🔴 只能改 `brief` 与 `path`

与 [`+update`](update.md) 同一条约束：**只接受 `brief` 与 `path` 两个可改字段，
且只作用于顶层 Item 与 Frame**。`title`、`type`、几何、内容分支、以及 Frame 的成员
**都改不了**；写了不报错也不生效。要换内容就用 [`+create`](create.md) 建新对象。

批量操作不降低 brief 修改门槛：每个 brief 都必须有对应 `+get` 证据，证明对象已经被动编辑且旧描述
失真。目录整理默认只提交 `path`；禁止为了让同批文案更整齐而顺手改写 brief。

## 命令

```bash
design-cli design-workspace +update-batch \
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

根节点为 `<batch>`，内部固定包含 `<items>` 与 `<frames>`。每个 Item、Frame **必须携带对应 ID**
与 `type`，此外只写 `brief` / `path`。

批量整理目录，只改 `path`：

```xml
<batch>
  <items>
    <item item_id="401" type="IMAGE" path="/product-views"/>
    <item item_id="404" type="IMAGE" path="/corgi-assets"/>
  </items>
  <frames/>
</batch>
```

新目录会自动形成，不需要先创建。**`path` 必须以 `/` 开头。**

以下对象均已通过各自的 `+get` 确认发生被动编辑、旧 brief 已失真；此时才可同时改 `path` 与
`brief`，并把 Item 与 Frame 放在同一批里：

```xml
<batch>
  <items>
    <item item_id="401" type="IMAGE" path="/product-views" brief="宠物雨衣正面产品图，已确认帽子与拉链设计"/>
    <item item_id="404" type="IMAGE" path="/corgi-assets" brief="柯基标准站姿参考图，用于比例校准"/>
  </items>
  <frames>
    <frame frame_id="560" type="LAYERED" path="/deliverables/poster" brief="改为暖色调的「窗」字主视觉"/>
  </frames>
</batch>
```

Frame **不带 `<items>`** —— 成员改不了，列出来也没有意义。

**两格都按 patch 语义**：不写这个属性 = 保持原值，写成空串（`brief=""`）= 清空这一格。

## 约束

**根节点必须是 `<batch>`。** 传单个 `<item>` / `<frame>` 会被拒并提示改用 [`+update`](update.md) —— 响应形状跟着请求根走，收了单个就会回一个不带 `<batch>` 壳的响应，下次照抄这份输出提交回来就对不上了。

**一批最多 50 个对象。** 超限**直接拒、不截断** —— 截断出来是「少写了几个对象的成功响应」，调用方不会知道后面那些没生效。

**`input` 最大 1MB。** 超限同样直接拒。这个额度对一批只含 ID 与两个字段的描述极宽裕。

🔴 **同一个 ID 在一批里只能出现一次。** `item_id` 与 `frame_id` 共用一个 ID 空间。

这条必须知道，因为违反它**不会报错、而是静默丢数据**：同一个对象在一批里被写两遍时，后一条会覆盖前一条且不会被拒，而你以为两条改动都生效了。所以要同时改一个对象的 `brief` 与 `path`，**合并成一条**，不要拆成两条。

## 原子性

**一批全成或全败。** 任何一个对象失败，整批都不生效 —— 不存在「前几个成功、后几个失败」的部分成功状态。

正因如此才有上面那个 50 的上限：一批要整体应用，批越大，同一张画布上的其它写入等待越久。

## 输出

`xml_data` 内为 `<batch>`，含各对象更新后的完整形态（不只是你改的那两格）：

```xml
<batch>
  <items>
    <item item_id="401" type="IMAGE" path="/product-views" title="雨衣正面图" brief="宠物雨衣正面产品图，已确认帽子与拉链设计">
      <size width="1024" height="1024"/>
      <asset url="https://cdn.example.com/s/f1r0nt"/>
    </item>
    <item item_id="404" type="IMAGE" path="/corgi-assets" title="柯基站姿参考" brief="柯基标准站姿参考图，用于比例校准">
      <size width="1024" height="1024"/>
      <asset url="https://cdn.example.com/s/c0rg1s"/>
    </item>
  </items>
  <frames/>
</batch>
```

⚠️ **返回里带 `title` / 几何 / 内容分支，是在回显它们的当前值，不代表这次改了它们。**

退出码与错误处理见 [`README.md`](README.md)。

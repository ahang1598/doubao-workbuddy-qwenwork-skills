# `HTML`

完整 HTML 作品的 Item。内容分支为 `<asset>`，与 [`IMAGE`](image.md)、[`VIDEO`](video.md) 共用同一个分支结构。

本文件只定义 HTML 写入 Canvas Workspace 时的 **Item 载荷**。HTML 文档本身的结构、固定画布尺寸、行内样式与 `shot.py` 预览不在本文件，由各 Skill 自己的 HTML 产物规范约束。

## 对象边界

- HTML 只能创建为**顶层** `<item type="HTML">`。
- 禁止 `<frame type="HTML">`，也禁止把 HTML Item 放进 Frame 的 `<items>`。
- 一个完整详情页、长图或其他独立作品对应一个 HTML 文件、一个 HTML Item；不得按内部章节拆成多个 Item。
- `+create-batch` 可以在顶层 `<items>` 里一次创建多个彼此独立的 HTML Item，单个的规则完全适用。

## 字段

```xml
<item item_id="301" type="HTML" path="/deliverables/detail-page" title="商品详情页" brief="可编辑的商品详情页 HTML 成品">
  <size width="1080" height="8000" />
  <asset url="https://cdn.example.com/s/htmlA1b2" />
</item>
```

| 字段 | 必填 | 说明 |
|---|---:|---|
| `asset` / `url` | 是 | 上传后取得的可持久访问短链 |

`<asset>` 只有 `url` 一个字段。共有字段与 `size` 见 [`README.md`](README.md)。

`<size>` 的 `width` / `height` 必须与 HTML 根节点声明的画布尺寸一致 —— 两边不一致时画布上的显示边界与文档实际排版会错开。

## 短链从哪来

CLI **不接受本地 `.html` 路径，也不代为上传**。完整 `.html` 文件必须先经 `FileBatchUpload` 取得短链：

```json
{"path_list": ["./dist/detail-page.html"]}
```

返回中每项含 `path`、`uri`、`url`，取 `url` 写入 `<asset url="…">`。

🔴 **已经有短链就直接用，不要再上传一遍** —— 那会造出第二条指向同一份文件的短链。

## 创建

`+create` 不带 `item_id`：

```xml
<item type="HTML" path="/deliverables/detail-page" title="商品详情页" brief="包含首屏、产品卖点、使用方法与购买引导的完整 HTML 商品详情页">
  <size width="1080" height="8000" />
  <asset url="https://cdn.example.com/s/htmlA1b2" />
</item>
```

写入后保存服务端返回的 `item_id`，立即用 `+get` 回读，核对 `type`、`path`、`title`、`brief`、`size` 与 `<asset url>`；任一字段不一致都视为未完成。

## 替换 HTML

HTML 内容、样式、资产引用或画布尺寸变化时，改完整源文件、重新上传，再用 `+create` 建立新版本 —— 提交不带旧 ID 的完整对象，并记录新旧 `item_id` 的对应关系。

`+update` 只能改顶层对象的 `brief` 与 `path`，不用它替换 HTML 文件、短链、尺寸或标题。

## 注意

- `width` / `height` 是画布上的显示边界，也必须等于 HTML 文档自己的画布尺寸，两者不是各自独立的取值。
- 原始 `.html` 文件不通过 `present_files` 直接交付。HTML 预览通道为「`shot.py` 生成严格同尺寸且内容合格的预览 → `FileBatchUpload` 上传预览图 → 核验公网 HTTP(S) 链接 → Markdown 图片展示」，预览图不写入画布；HTML 持久化通道为「`FileBatchUpload` 上传完整 HTML → 以 HTML 短链 `+create` 顶层 HTML Item → `+get` 回读」；HTML Item 卡片通道为「将同一 Workspace ID 与回读成功的 Item ID 拼成 `<workspace_id>?item_id=<item_id>` 单值交给 `present_files`」。退出码 `1` 表示页面存在问题，必须修正并重跑，但预览问题本身不阻断 HTML 上传、Item 创建与回读，也不取消回读后的既定卡片闭环；不合格预览不得展示，写入或卡片成功也不能据此宣称页面合格或任务完整完成。只有退出码 `3` 的执行失败可明确记录“预览未验证”并继续未被独立规则阻断的可完成部分。合格预览图的 CDN＋Markdown 展示和当前环境所需画布卡片缺一不可；本条 Canvas 动作不适用于 Mobile。
- 预览截图、Markdown 代码块、文件路径或短链文本都不能替代 HTML Item 的写入与回读；工具临时预览也不能替代“上传 CDN → 核验公网链接 → 用该链接以标准 Markdown 图片语法展示”。预览截图不得调用 `present_files`、创建 IMAGE Item 或写入画布。
- 完整 VI 无论内部包含多少章节或分页，都只能上传一份完整 HTML 并创建一个唯一顶层 HTML Item；禁止 HTML Frame、章节多 Item、分页多 Item。上传与 CLI 写入必须由 Main Agent 完成，Subagent 只回传本地 HTML 和 `shot.py` 自检结果。

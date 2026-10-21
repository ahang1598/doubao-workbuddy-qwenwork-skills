# `IMAGE`

图片 Item。内容分支为 `<asset>`。

> `image_gen`／`image_edit` 结果按 [交付门禁](../workflow/image-generation-delivery-gate.md) 处理 Workspace ID 并使用 `RichMediaCard` 直接逐项交付，不使用本文件重复创建 IMAGE Item。本文件只用于用户上传、本地渲染／导出或其他确实需要显式创建 IMAGE Item 的非图像工具资产。

## 字段

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘">
  <size width="640" height="960" />
  <asset url="https://cdn.example.com/s/a1B2c3" />
</item>
```

| 字段 | 必填 | 说明 |
|---|---:|---|
| `asset` / `url` | 是 | 可持久访问的短链 |

`<asset>` 只有 `url` 一个字段。共有字段与 `size`（顶层）或 `transform`（Frame 成员） 见 [`README.md`](README.md)。

## 短链从哪来

CLI **不上传文件**。`image_gen`／`image_edit` 输出在调用时透传 Workspace ID，返回后通过 `RichMediaCard` 直接交付给用户，不得进入本文件的重复创建与回读流程；直交后允许按 [资产目录工作流](../workflow/canvas-asset-organization.md#3-产物完成后的强制目录整理) 回读已关联对象并更新 path，也不得为了交付另行下载、复制或重新上传。用户上传或其他仅有本地文件、且并非这两类工具输出的素材，才调用 `FileBatchUpload`：

```json
{"path_list": ["./assets/key-visual.png"]}
```

返回中每项含 `path`、`uri`、`url`，取 `url` 写入 `<asset url="…">`：

```json
{"path": "./assets/key-visual.png", "uri": "tos-cn-i-.../key-visual", "url": "https://cdn.example.com/s/x9Y8z7"}
```

本地路径、`file://`、`data:` URI 都不接受。仅当本文件适用的资产确实需要创建 IMAGE Item 时，写入后用 `+get` 核对 URL；不得把 `image_gen`／`image_edit` 的交付侧产物另行转换成 IMAGE Item。

## 创建

`+create` 不带 `item_id`：

```xml
<item type="IMAGE" path="/deliverables/key-visuals" title="雨夜主视觉" brief="林夏站在雨夜便利店门口的主视觉">
  <size width="960" height="1280" />
  <asset url="https://cdn.example.com/s/x9Y8z7" />
</item>
```

顶层 IMAGE 必须给 size；Frame 成员必须给框内相对 transform。显示宽高不是源图分辨率。

## 替换图片

图片内容变更使用 `+create` 建立新版本，不能用 `+update` 替换 URL。顶层 IMAGE 提交不带旧 ID 的完整对象；Frame 内的 IMAGE 先按旧 ID 定位，再创建不带旧 Frame／成员 ID 的完整新 Frame，保持未修改层与相对位置，记录新旧 ID 对应。

## 注意

- `width` / `height` 是画布上的显示尺寸，与图片原始像素无关。比例不一致时由前端按渲染策略处理，写入前自行按原始宽高比算好，避免拉伸。
- 需要与其他元素叠压的独立主体，用抠好的透明 PNG 上传；带纯色底的源图直接放进画布会露出矩形边缘。
- 图片上的准确文字不要烘焙进图片，另建 `TEXT` Item 覆盖在上层。

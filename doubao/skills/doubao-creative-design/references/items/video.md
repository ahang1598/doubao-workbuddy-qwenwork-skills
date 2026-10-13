# `VIDEO`

视频 Item。内容分支为 `<asset>`，与 [`IMAGE`](image.md) 共用同一个分支结构。

## 字段

```xml
<item item_id="188" type="VIDEO" path="/motion-assets" title="雨夜街景运镜" brief="雨夜街景的循环运镜素材">
  <size width="1280" height="720" />
  <asset url="https://cdn.example.com/s/v1D2e3" />
</item>
```

| 字段 | 必填 | 说明 |
|---|---:|---|
| `asset` / `url` | 是 | 可持久访问的短链 |

与 `IMAGE` 的唯一差别是 `<type>` 的值——分支节点、字段、短链获取方式完全相同。

## 短链从哪来

同 `IMAGE`：视频生成／编辑工具输出直接使用原始响应中的短链，工具产物直接交给 `present_files`；用户上传或其他仅有本地文件、且并非生成／编辑工具输出的视频才调用 `FileBatchUpload`。不得用预览地址、交付侧数据或二次上传 URL 替换工具原始短链，写入后用 `+get` 核对 URL。

## 创建

```xml
<item type="VIDEO" path="/deliverables" title="短剧成片" brief="按正式剧情顺序剪辑完成的三分钟短剧成片">
  <size width="1920" height="1080" />
  <asset url="https://cdn.example.com/s/f1n4lc" />
</item>
```

## 注意

- `width` / `height` 是画布上的显示尺寸。按视频原始宽高比设置，避免画面变形。
- 封面图、时长、编码等元信息由服务端从素材侧补全，Agent 侧不填也读不到。
- 视频不能作为其他元素的背景叠压使用——需要静帧背景时导出一帧作为 `IMAGE`。

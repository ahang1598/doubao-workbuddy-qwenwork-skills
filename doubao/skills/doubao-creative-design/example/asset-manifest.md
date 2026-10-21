# AI + Coding 素材清单

`asset-manifest.json` 只用于需要图像生成、图片编辑或真实素材复用的 AI + Coding 路线。纯 Coding 和纯生图不创建该文件。

它不是 最终 HTML，也不保存 DOM 坐标、字号、颜色、CSS 参数、模板绑定或页面几何。Brief 负责内容与视觉决策，素材清单只负责让正式图片调用可执行，最终 HTML 负责实现事实。

## 最小结构

```json
{
  "brief_snapshot": {
    "path": "brief.md",
    "version": "v003",
    "status": "frozen"
  },
  "assets": [
    {
      "asset_id": "hero-product",
      "purpose": "首屏产品主视觉",
      "production_method": "image_edit",
      "reference_inputs": ["core-product-v1"],
      "identity_source": "core-product-v1；包装轮廓、Logo、标签和主色不可改变",
      "prompt": "保留产品身份，重建清爽场景，右侧预留标题区域",
      "target": {
        "ratio": "4:3",
        "width": 1600,
        "height": 1200,
        "safe_area": "产品完整位于左侧 60%，不得裁掉包装与标识"
      },
      "consumers": ["首页产品主视觉"],
      "acceptance": ["产品身份一致", "标题区干净可用"],
      "postprocess": ["首页采用完整场景背景，以环境光影承托商品；保护商品与标识，裁切后检查实际取景；尚未生成和验收"],
      "status": "planned"
    }
  ],
  "unresolved_blockers": []
}
```

## 使用规则

- 首次正式图片调用前冻结完整 Brief，并为每张待生产或复用图片填写一项素材记录。
- `image_edit` 必须有真实参考输入；`image_generate` 可以没有参考输入；`verified_existing` 必须直接记录已核验输出。
- `identity_source` 记录人物、商品、品牌或 Logo 的唯一身份来源与不变量；不承载受保护身份时明确写 `none`，不能留空或用 Prompt 暗示代替。
- `planned` 表示工具输入已经完整，只等待输出。不得用 `planned` 隐藏身份、授权、比例或文案缺口。
- 图片就绪后在原记录内把 `status` 改为 `ready` 或 `reused`，并增加 `output.uri`、`width`、`height`、`version` 和 `alpha`。`output.uri` 必须是可持久访问的 HTTP(S) 短链，不接受本地路径、`file://` 或 `data:`；目标 `ratio` 必须与 `width`／`height` 一致。不再建立第二个就绪态计划文件。
- 清单采用封闭轻量字段集；`element_id`、DOM 坐标、几何、层级、字体、色值、CSS/SVG 或模板绑定会被 validator 拒绝。
- 换素材版本时更新原记录和所有实际 HTML 消费位置；HTML 中的 DOM ID、坐标、层级、字体和样式只在 HTML 源中维护。
- 用户反馈改变内容职责、主构图或视觉方向时先更新并重新冻结 Brief，再更新受影响素材记录。

## 采用版本与来源记录

当前字段不支持 `variants` 或 `consumer_bindings`，不得先写新字段再绕过校验器。按以下方式保存实际采用关系：

- 一项对应一个采用版本，`output` 是该项各 `consumers` 实际使用的结果。同一版本多次摆放共享一项；同源图的完整照片版与透明主体版分为不同 `asset_id`，分别填写消费者与输出。
- `reference_inputs` 指向可核验的真实输入或来源记录。`postprocess` 记录源图地址、处理步骤、未采用候选及原因、采用版本和检查证据；这些来源记录不算已用于 HTML，也不单独伪造消费者。为已有图做真实抠图属于后处理，不谎报为生成式 `image_edit`；生产方式如实记录源图取得方式。
- 一个实际使用位置只采用一个确定结果。处理理由、背景职责与最终使用方式在 `purpose`／`postprocess` 写清；裁切、蒙版、混合与抠图可组合。`consumers` 是页面／区域的语义位置，不复制 DOM 坐标或 CSS 参数。
- `planned` 不预填输出；生成源图后立即在 `postprocess` 留存真实结果与待处理状态，最终采用结果通过素材检查后才写 `output` 并置为 `ready`／`reused`。未采用结果不因有地址而标为就绪。
- 证据注明对应真实地址和版本；自动检测是否运行、实际结果、视觉检查是否完成分别记录。`alpha` 布尔声明不证明透明，未运行像素检测不能声称脚本已验证。SVG 按实际渲染核验，不强制位图 Alpha。
- 校验器目前只核对字段及就绪输出，不验证上述自由文本的语义、真实文件透明度、来源链或 HTML 使用位置。进入 HTML 后必须对照实际引用与消费者逐项复核；发现旧版引用、无依据的透明声明或未验证的必要检查时不得以字段校验通过代替验收。

正式调用前运行：

```bash
python3 scripts/runtime/validate_asset_manifest.py .creative-design/<task-id>/asset-manifest.json
```

准备编写 HTML 前运行：

```bash
python3 scripts/runtime/validate_asset_manifest.py --require-ready .creative-design/<task-id>/asset-manifest.json
```

校验器只检查素材调用和输出是否完整，不检查自然语言 Brief、HTML 布局或视觉质量。

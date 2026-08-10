# 原图静态证据叠加

## 读取门

生成 process 或 renderer 前，**必须完整读取**：

1. `mode-image-overlay.md`
2. `image-overlay-process-spec.md`
3. `image-overlay-authoring-spec.md`
4. `shared-quality.md`

没有读完不得开始写坐标、process 或 HTML。需要参考成熟单图实现时再读取 `examples/image-overlay-gold-process.md` 和 `examples/image-overlay-gold-reply.md`，但 example 不能替代两个 spec，并以其中标注的融合版修订为准。

## 适用范围

当答案依赖用户原图中的真实对象、位置、数量、区域、路径、轨迹、方向、匹配或差异，并且在原图上指出证据能显著降低理解成本时使用。

不因“上传了图片”自动触发。图片只是装饰、已有曲线一眼可读、结论不存在于图中或文字已足够时，不叠加标注。

## 前提与降级

- 必须能在 renderer 中访问本题原图的真实 HTTPS URL。若只有本地路径、base64、不可访问 URL 或 renderer 不可用，保留文字答案并说明无法叠加，不伪造标注图。
- 原图是证据，必须保持像素内容、对象位置和比例不变。
- 标注只覆盖与问题直接相关的证据；少而精，不圈大背景充数。

## 内部证据结构

无需写临时文件。内部保持以下结构并直接内嵌到 renderer：

```json
{
  "steps": [
    {
      "type": "bbox_zoom",
      "coords": [
        {"kind": "bbox", "xyxy": [100, 200, 300, 400], "label": "关键区域及其判断依据"}
      ]
    }
  ],
  "final_answer": "面向用户的答案"
}
```

- 坐标统一为 0-999 整数相对值，不估算图片像素宽高，不做像素换算。
- `point`：`x`,`y`,`label`；`bbox`：`xyxy`,`label`，且 `x1<x2`,`y1<y2`。
- 内嵌结构和实际绘制必须一致，但无需在用户可见正文泄漏结构、坐标或内部术语。统一使用 `final_answer`，不要与旧草案中的 `answer` 字段混用。

## 标注类型

- `path_grow`：连续真实路径；沿方向有序采样，短路径至少 6 点，长曲线至少 12 点。不要重描原图中已清晰可读的统计曲线。
- `node_walk`：A→B 单段有向关系；恰好两个有序 point，必须使用真箭头。
- `match_pair`：一对对应关系；每个 step 恰好两个 coord，多对拆成多个 step。
- `count_pop`：多个独立对象的计数或逐一标定。
- `bbox_zoom`：聚焦一个连续区域，可附少量内部锚点。
- `default`：1-2 个简单 point；bbox 应使用 `bbox_zoom`。

## renderer 结构

- 输出顺序：文字讲解与答案 → 一句自然衔接 → 末尾一个 `html type="renderer"`。
- 底图使用 `width:auto;height:auto;max-width:100%;max-height:720px;display:block`；舞台 `display:inline-block;max-width:100%`，避免竖图强行铺满宽度。
- 使用两层覆盖：SVG 只画 line/polyline/path/rect，HTML layer 画圆点、数字、文字和胶囊。
- SVG 固定 `viewBox="0 0 999 999" preserveAspectRatio="none"`；描边使用 `vector-effect="non-scaling-stroke"`。
- 禁止在非等比 SVG 中放 circle、ellipse、text 或 image，避免圆点和文字变形。
- 点使用 14-18px 小圆点 + 旁置标签，不使用遮挡原图的大圆饼。
- 标记默认半透明；标记不少于两个时提供图例。核心结论不依赖 hover。
- 若加入交互，必须同时支持 hover 与 click/tap；需要复杂切换或播放时改走交互模式。

## 忠实性检查

- 每个标记必须压在 label 所描述的真实对象上。
- label 写“为什么它支持结论”，不只复述对象名称。
- 纯计算、汇总和不在图中的推理留在正文，不画成虚假标记。
- 图片含敏感信息时，不在标签中复述无关敏感字段。

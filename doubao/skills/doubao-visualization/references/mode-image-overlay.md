# 原图静态证据叠加

本文件是简单标注的完整运行契约，只独立覆盖满足以下全部条件的任务：单图、单 step、总 coord 数不超过 2，且不需要图例或标签避让。

## 专项加载

- 出现任一条件即视为复杂标注：总 coord 数不少于 3、steps 不少于 2、多图、路径、多组配对、计数、图例、标签避让、跨图联动或交互。
- 复杂标注必须同时读取 `image-overlay-process-spec.md` 和 `image-overlay-authoring-spec.md`，不能只读其中一份。
- 只有实现卡住时才参考 `examples/image-overlay-gold-process.md` 和 `examples/image-overlay-gold-reply.md`；示例不是运行必读。

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

- 输出顺序：文字讲解与答案 → 一句自然衔接 → 末尾一个 ` ```html type="renderer"`。
- 首块使用 `<html style="margin:0;padding:0;">` 和透明 div；禁用 DOCTYPE、head、body、外部 CSS 和视口单位。
- 底图使用 `width:auto;height:auto;max-width:100%;max-height:720px;display:block`；舞台 `display:inline-block;max-width:100%`，避免竖图强行铺满宽度。
- 使用两层覆盖：SVG 只画 line/polyline/path/rect，HTML layer 画圆点、数字、文字和胶囊。
- SVG 固定 `viewBox="0 0 999 999" preserveAspectRatio="none"`；描边使用 `vector-effect="non-scaling-stroke"`。
- 禁止在非等比 SVG 中放 circle、ellipse、text 或 image，避免圆点和文字变形。
- 点使用 14-18px 小圆点 + 旁置标签，不使用遮挡原图的大圆饼。
- 简单标注默认静态，不强制 JavaScript、hover 或图例；标签能直接对应且不拥挤时无需额外交互。
- 标记密集时编号并提供图例。若加入交互，必须支持 click/tap，hover 只能作桌面增强；复杂切换或播放改走 HTML/SVG 交互模式。

## 忠实性检查

- 每个标记必须压在 label 所描述的真实对象上。
- label 写“为什么它支持结论”，不只复述对象名称。
- 纯计算、汇总和不在图中的推理留在正文，不画成虚假标记。
- 图片含敏感信息时，不在标签中复述无关敏感字段。

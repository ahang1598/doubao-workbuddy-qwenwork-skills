# 效果参考生成规范

本文件负责把参考效果写成自然语言视觉方案，并把实现责任交给 最终 HTML；不负责 CLI 调用、HTML 平台载荷或交付。

## 使用顺序

1. 先由场景 Spec 锁定事实、载体、信息链和必须出现的内容。
2. 用户上传模板、成品参考或局部效果图时，AI + Coding 必须读取 [参考图解析与继承](../coding/ai-coding/reference-analysis.md)，完成非设计内容过滤、11 维底稿、逐块图文绑定、七类同源机制和六步目标重建。
3. 读取 [创意机制](creative-concept-system.md) 与 [构图原则](composition-principles.md)；命中品类时只读对应 Visual System，未命中时读 [通用视觉规则](../coding/generic-visual-fallback.md)，并在同一 Brief 中完成全部视觉与逐图规划。
4. 至此形成完整候选 Brief。适用电商详情页或社媒长图的 KV 时，先读取 [KV 视觉澄清](../../workflow/visual-kv-clarification.md) 确认门禁与流程，按 [素材 Prompt 指南的 KV 章节](../coding/ai-coding/asset-prompt-guide.md#kv-visual-generation) 将候选 Brief 转成真实 KV；用户选择写回同一 Brief 并冻结最终版本。无需 KV 时直接冻结最终 Brief。
5. 最终 Brief 冻结后，AI + Coding 只把正式图片调用所需的用途、生产方式、参考输入、Prompt、比例、尺寸、安全区、消费者、后处理与准出标准写入轻量素材清单；pure-coding 不创建素材清单。
6. AI + Coding 按素材清单调用正式图像生成／编辑工具时读取 [AI + Coding 素材 Prompt](../coding/ai-coding/asset-prompt-guide.md)，素材就绪后直接编写完整 HTML；纯生图路线读取其独立 Prompt 指南。

## 输出分层

Design Brief 使用自然标题、连贯段落和必要的逐块表格描述媒介、视觉层级、构图关系、色彩职责、字体角色、影像约束、参考继承、内容容量和验收重点。Brief 不输出模板 ID、坐标、色值表、CSS 属性、SVG 文件名或机器校验字段，也不按参数完整性验收。

Brief 冻结后，编写完整 HTML 时才确定稳定 DOM ID、字体、色值、几何、层级、CSS／SVG 引用和实际素材消费位置。能否执行并落地由素材清单、真实资源、HTML 和渲染共同证明；不能落到消费者的效果必须返回 HTML 解决，不能反向把 Brief 或素材清单改成实现参数表。

## HTML 效果落地

卡片、渐变、弥散、蒙版、玻璃、纸纹、文字质感等优先从 `assets/templates/ref-bindings.json` 解析品类 `ref_key`，再检索 CSS 与 SVG catalog。只有读取实现正文与依赖、绑定真实 DOM 消费者、展开为行内样式或内嵌 SVG 并在实际预览中可见，才算采用。无精确候选时允许按当前视觉系统自行实现，并在 HTML 验证记录中说明实际写法与未采用原因；这些实现信息不进入素材清单。

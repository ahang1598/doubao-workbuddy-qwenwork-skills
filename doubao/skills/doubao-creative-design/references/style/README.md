# Style 参考索引

主 SKILL 决定品类、动作和执行路线，本目录不另设路由、确认或交付流程。

| 目录 | 职责 | 使用方式 |
|---|---|---|
| shared/ | 公共创意、构图、质量、内容事实 | 两条图片路线共用；pure-coding 按需读取非生成原则 |
| pure-image/ | 完整图片 Prompt、模型适配、品类及平台规则 | 只由 pure-image 创建／编辑读取 |
| coding/ | 分层品类、视觉系统、平台与几何布局 | pure-coding 与 ai-coding 共用 |
| coding/ai-coding/ | 生成素材 Prompt、艺术标题 | 只在 AI + Coding 需要生成素材时读取 |

公共创意延续原主题分析、创意候选和筛选方法；共同构图输出视觉关系。pure-image 将其编译为完整画面，coding 继续读取生产映射与布局规则。几何 padding、DOM／HTML、素材抠图不能反向成为 pure-image 的要求。

- [公共创意](shared/creative-concept-system.md) · [显性风格词](shared/explicit-style-terms.md) · [公共构图](shared/composition-principles.md) · [共同质量](shared/image-quality-guide.md) · [内容与事实](shared/content-truth.md)
- [纯图 Prompt](pure-image/prompt-guide.md) · [Coding 生产映射](coding/concept-production.md) · [Coding 布局](coding/composition-layout.md)
- [纯图创建](../workflow/creation/pure-image.md) · [AI + Coding 创建](../workflow/creation/ai-coding.md) · [pure-coding 创建](../workflow/creation/pure-coding.md)
- [KV 确认工作流](../workflow/visual-kv-clarification.md)：沿原品类及操作范围，不对纯图新增 KV；候选生成要点与 Prompt 规则见 [素材 Prompt 指南的 KV 章节](coding/ai-coding/asset-prompt-guide.md#kv-visual-generation)。
- 关系图：[思维导图](coding/scenarios/mind-map-spec.md)、[流程图](coding/scenarios/flowchart-spec.md)、[知识图谱](coding/scenarios/knowledge-graph-spec.md)分别确定内容语义，再进入[统一 Visual](coding/systems/diagram-visual-system.md)完成布局、编码与配图。

模型适配 ref 只改变 Prompt，不切换实际服务端模型。CLI、HTML、rendering 保持各自目录和执行职责。

## 扩充配方与字体入口

需要对应品类的更多视觉选择时，从原 Visual System 进入三折页、简历与电商扩充配方；社媒和邀请函的新 CSS 入口已在原视觉文件内合并。字体统一从 [字体推荐入口](../rendering/font-recommendation-list.md) 开始：推荐清单是精选入口而非封闭白名单，确定性查询只负责候选、缺口和诊断，必须结合真实文案试排与视觉判断。正式 HTML 选定视觉候选后，再进入 [字体资源与执行契约](../rendering/font-family-library.md) 核验实际 family、face、weight／style、许可、目标字形覆盖和 Web 加载；pure-image 只借用视觉建议，不进入 HTML 资源门禁。最终可见效果写回同一 Brief，实际 CSS／SVG 参数只进入 HTML，不建立独立几何或样式规划文件。

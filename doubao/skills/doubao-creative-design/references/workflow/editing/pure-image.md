# 纯生图再编辑步骤

> 先按主 SKILL 判断交付环境。system 明示 `Device platfrom: Mobile` 时遵循 [Mobile 直接交付](../mobile-app-direct-delivery.md)：Brief／素材记录留在本地，跳过本文 Workspace 创建、Canvas CLI、Item 与卡片步骤；已有唯一有效 Workspace ID 仍须作为图像工具参数透传，无 ID 时不创建，媒体逐项直接交付、HTML 预览走 CDN＋Markdown。其他环境执行本文默认 Canvas 分支。生产与编辑顺序不变。

本路线用于已确认的纯图片编辑。Logo、VI、详情页、长图及套图不再按品类禁入；用户要求可编辑时回主路由进入 AI + Coding。已有 HTML 源的编辑必须返回 HTML 编辑流程；明确另做纯图版本时，读取其正式导出图作为新的图片衍生任务输入，不改变原 HTML Item。

## 读取路由

1. 读取 `references/workflow/clarification-strategy.md`，确认用户要改的是最终图而不是可编辑源。
2. 读取用户原图、上一版 Prompt／Brief（若存在）与本轮修改要求；判断商品、品牌或 Logo 是否为核心资产。存在时定位 `/core-assets/<语义名>/master` 并 `+get` 母版，记录 `core_asset_id`、不可变主体、身份约束、文字、尺寸和必须保留区域。
3. 按 [纯生图创建的品类 Ref 路由](../creation/pure-image.md#品类-ref-路由) 读取本图对应产物／必要平台 ref，沿用上一轮品类和改写模式；只在用户改变产物或明确切换模式时补读新规则。不得因“修改”重设推荐张数或扩展成全套物料。凡调用 `image_edit` 或重生，必须先读取 `references/style/pure-image/prompt-guide.md`，由“保留项—改动项—区域—融合—输出”合同和一个模型 ref 编译指令，再读取 `references/style/shared/image-quality-guide.md` 检查比例、核心身份和质量门禁。局部编辑不执行 ref 中用于全新设计的整图推演。
4. 继续按主 SKILL 的环境规则执行 Workspace 初始化、上传锚点登记与通过 `RichMediaCard` 直接交付门禁：每次 `image_edit` 按当前环境规则透传 Workspace ID，结果返回后直接交付；参考图编号、工具名称及参数服从当前工具协议，不照搬 ref 的字段示意。

## 执行与出口

1. 只记录本轮变化：新增、删除、替换、构图、颜色、文字或风格；未点名内容默认保持。调用前输出 `must_keep`、`must_change`、编辑区域、融合约束和最终尺寸，不得把局部编辑改写成整图重生 Prompt。
2. 使用 image edit 能力直接编辑最终图，不拆层、不进入 Coding。当前待修改成品作为 edit target；存在核心资产时另将锚点母版作为身份参考，只有修改母版本身时二者才重合。不得用母版替代当前成品而丢失原布局；必要输入无法同时使用时说明工具限制。在新版本 brief 中记录 `derived_from_core_asset_id`；不得以纯文本重绘相似商品、品牌或 Logo。按 [交付门禁](../image-generation-delivery-gate.md) 选择串行或并行；每次 `image_edit` 按当前环境规则透传 Workspace ID，结果返回后使用 `RichMediaCard` 直接逐项交付，串行项自身交付成功、并行项整批交付状态汇合后才能继续。
3. 所有 `image_edit` 成功输出都必须在满足当前环境 Workspace ID 规则后通过 `RichMediaCard` 直接交付，即使预计效果不佳或需要返工；随后对比编辑前后，检查身份、文字、边缘、遮挡、源图/目标比例、等比缩放、有效分辨率和未授权变化。AI 图片内生成文字不准确、字形异常或可读性不佳时，只记录问题并等待用户提出修改要求，禁止过度反思、自动重编 Prompt 或自主重生。画幅扩展必须生成新区域，不能拉伸原图；其他非文字失败按 Prompt 指南处理，多次失败再读取 `references/workflow/troubleshooting.md`。任何用户明确要求的修正版也服从当前串行或并行模式。
4. 最终说明只引用已成功独立交付的新版本，不覆盖用户原图。默认 Canvas 在本轮结果全部直交后按 [画布资产语义目录工作流](../canvas-asset-organization.md#3-产物完成后的强制目录整理) 读取真实对象并归档，不为改图结果重复创建 IMAGE Item。

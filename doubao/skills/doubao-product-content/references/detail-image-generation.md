# 商品图片生图参考

本文件是商品图片生成 reference 的目录索引。按任务只读取需要的子文件，不要一次性加载全部细节。

## 目录

- [核心原则与输入判断](detail-image-generation-01-principles-input.md)：命中商品图片能力后先读；包含证据先行、价格来源、缺值处理和输入判断。
- [素材读取与主体一致性](detail-image-generation-02-identity-anchors.md)：用户提供商品图、包装图、场景参考，或需要多图主体一致时读取。
- [主图与详情图规划](detail-image-generation-03-main-and-detail-planning.md)：规划主图、商品副图、详情图、详情长图屏数或品类证据层时读取。
- [版式与图中文字](detail-image-generation-04-layout-and-text.md)：需要设计版式、文字层级、原生文字生成、OCR、缺值防空白或真实字体兜底时读取。
- [Prompt 与多图生成流程](detail-image-generation-05-prompts-and-workflow.md)：需要写文生图/图生图 prompt、批量生成多图、修复失败图片时读取。
- [文字红线与生成后检查](detail-image-generation-06-checks.md)：生成后验收、合规检查、主体一致性检查和交付降级判断时读取。

## 读取建议

- 只做商品图片规划：读 01、02、03。
- 需要生成真实图片：读 01、02、03、04、05、06。
- 只修图中文字或 OCR 问题：读 04、06。
- 只做生成后质检：读 06。

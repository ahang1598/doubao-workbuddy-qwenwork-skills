# 飞书执行工作流（无图片版）

本四合一版本的旅游攻略不搜图、不生图、不插图。需要直接执行飞书创建或更新时，以 `feishu-workflow.md` 为唯一工作流。

执行要点：

- 先形成完整 XML 正文，再创建或更新飞书文档。
- 只使用 `callout/grid/table/checkbox/bookmark/blockquote/hr` 等富文本组件增强结构。
- 不读取媒体插入命令，不创建 `visuals/`，不创建 `image-plan.tsv`，不调用 `docs +media-insert`。
- 正文不得出现 `<img>`、图片说明、图片来源、图片锚点、caption、source、`image_gen`、`生成图`、`搜图`、`插图位置`。
- 降级时只给同结构 Markdown 正文和必要复查清单，不提供图片文件夹。

完整创建流程、表格 schema、内容门控和交付检查见 `feishu-workflow.md`。

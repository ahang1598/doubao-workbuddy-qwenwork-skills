# POSM / POSF 显式标识（1.2.1）

默认命令同时添加显式和隐式标识，无新增依赖：

```bash
python scripts/main.py "<绝对路径>.posm"
python scripts/main.py "<绝对路径>.posf"
```

- POSM：每个思维导图根节点写入 `watermark`（含“内容由AI生成”）、`showWatermark=true`，并增加同名提示子主题。原生画布水印独立于分支展开状态；不强制展开已有折叠节点。
- POSF：每个流程图的 `page` 写入同样的原生画布水印，并在原内容下方放置黑字白底文本框；必要时扩展页面尺寸。保留原有图形、连线及属性。
- 已有自定义水印保留其文字并追加提示；标识节点使用稳定 id，重复执行不新增副本。该 id 被其他内容占用时停止，避免覆盖用户节点。
- 隐式标识仍按指南 6.7 写入 ZIP 根目录 `meta.json` 的 AIGC JSON 字符串。已有合法来源与编号保留，缺失预留字段补齐；`--skip-visible` 不读取或重写画布。

## 格式依据与边界

2026-10-27 核对 ProcessOn 公开原生编辑器代码：

- [官方思维导图编辑器入口](https://www.processon.com/thirds/editortry?category=mind) 引用的 [common.ca584dd0.js](https://www.processon.com/public_login/common.ca584dd0.js)：思维导图定义使用 `root/title/children`；`setWaterMark` 将 `watermark/showWatermark` 写回 `renderer.mindTree` 并创建画布水印。
- [官方流程图编辑器入口](https://www.processon.com/thirds/editortry?category=flow) 引用的 [designer.54b40b32.js](https://www.processon.com/v5_editor/compile/designer.54b40b32.js)：流程图定义使用 `elements/page`；渲染器读取 `Model.define.page.watermark/showWatermark`。文本框遵循其公开 `Schema.shapes.text` 的 `path/props/textBlock` 结构。

处理 ZIP 中的原生 JSON 画布：支持直接定义，`diagram/def/definition/content/data/mindTree/rootTopic/root` 包装，以及 `canvases/pages/definitions/defs` 列表或映射、序列化 JSON 定义；可处理分散在多个成员中的画布。资源、附件、素材目录不作为画布修改。

并非所有名称相似的 JSON 都是画布：必须识别上述原生根节点或 elements/page 结构。未知主内容编码、未知集合成员、格式与画布类型不匹配会停止，主入口保留源文件；不得把任意 JSON 改名为 POSM/POSF 后宣称获得原生兼容。未实现加密、自定义二进制或其他未知版本布局的显式转换。

## 验证

脚本测试覆盖两种格式的实际文本节点、原生水印启用、所有识别画布、页面空间、原内容/附件/来源保留、隐式升级、重复执行及未知结构失败保护。包内 `tests/run_text_guide_validation.py <目录> --with-visible` 生成包括这两种格式在内的 18 种指南样例，并回读隐式存储结构；POSM/POSF 还回读显式画布属性及文本。

`--verify` 仍专门检查隐式元数据。Python 接口 `decorators.pos_decorator.inspect_pos_visible(path)` 仅只读检查显式存储结构。二者均不代表原生应用显示验收或 GCMark 网站通过；新增 POS 显式样例为脚本构造的结构样例，不是原生编辑器导出文件。

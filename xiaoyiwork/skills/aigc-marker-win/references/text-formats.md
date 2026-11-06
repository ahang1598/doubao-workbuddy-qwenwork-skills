# 文本格式标识

入口 `scripts/main.py` 支持以下 16 种原有文本扩展名；默认同时添加“内容由AI生成”显式标识和 AIGC 隐式元数据。`--skip-visible` 仅写入元数据。元数据沿用技能的生成合成服务提供者编码和编号生成规则。

| 文件族 | 扩展名 | 隐式位置 | 显式形式 |
| --- | --- | --- | --- |
| OOXML Word | docx、dotx | 自定义属性 `AIGC`，通常在 `docProps/custom.xml` 的 `vt:lpwstr` 中存储 JSON 字符串 | 正文末段 |
| OOXML Excel | xlsx、xltx | 同上 | 每个数据工作表末行及打印页脚；不改变已有打印区域 |
| OOXML PowerPoint | pptx、potx | 同上 | 首个非隐藏页中的普通文字框 |
| UOF 文本 | uot、uott | UOF 2 `_meta/meta.xml` 自定义元数据集；UOF 1 主 XML 的元数据部分，`AIGC` 值为 JSON 字符串 | 正文末段 |
| UOF 表格 | uos、uost | 同上 | 每个数据工作表的末行 |
| UOF 演示 | uop、uopt | 同上 | 首张非隐藏页通过锚点引用的文字图形 |
| PDF | pdf | Document Information Dictionary 的 `/AIGC`，JSON 字符串 | 每页可见裁剪区域的底部 |
| OFD | ofd | `OFD.xml/DocBody/DocInfo/CustomDatas/CustomData Name="AIGC" name="AIGC"`，JSON 字符串 | 每页通过资源引用嵌入的中文水印图像 |
| Markdown | md | 文件头 YAML 的 `AIGC` 对象，字段以字符串保存 | 文末文字，保留其他已有 frontmatter |
| XMind | xmind | `metadata.json` 的 `AIGC` 节点，值为 JSON 字符串 | 每张画布添加一个根主题的普通子主题 |

另支持 `.html`、`.htm`：可见标识置于页面底部，隐式记录使用 head 中的 `<meta name="AIGC" content="JSON">`。这是本地互操作扩展，不属于上述 16 种格式的指南定义，也不代表 GCMark 支持此类元数据检测。

新生成的 AIGC 对象包含七个字符串字段（两个 ReservedCode 允许为空）；已有标识仅在必填字段、Label 枚举与类型均合法时保留。入口会对 20 种文本/网页扩展名执行元数据写后回读，其中指南范围的 18 种有独立存储位置检查。

另支持指南 6.7 的 `.posm`、`.posf` 隐式元数据，共 18 种指南格式；识别的原生 JSON 画布默认添加显式水印和文本提示，详见 [processon-visible.md](processon-visible.md)。加上 HTML/HTM 两种扩展，共 20 种文本/网页格式。

## 容器与处理范围

- OOXML 支持 Transitional 与 Strict 命名空间；保留原命名空间及各模板的主部件 ContentType，不把模板转换成普通文档。直接更新包内 XML 并保留其余包项，避免丢失未识别的扩展资源。
- UOF 支持 2003 命名空间的旧版单 XML，以及 2009 命名空间、包含 `uof.xml` 与 `content.xml` 的 ZIP 包。ZIP 包保留 2009 原生 `用户自定义元数据集_520F/用户自定义元数据_5210`，并按 GCMark 下载的对照产物，在同一元数据根下同步写入 `http://www.nits.org.cn/uof3/zh-cn/2021/metadata` 命名空间的 `自定义元数据集_520F/自定义元数据_5210`，属性为 `名称_5211="AIGC"`、`类型_5212="lpwstr"`。两处 JSON 保持相同来源；合法来源冲突时停止并保留原文件。此兼容记录不将正文转换为 UOF 3；旧版单 XML 不属于指南 6.2 指定的 ZIP 元数据位置，网站检测尚未验证。新增的 2021 ZIP 命名空间、POSM/POSF 和七字段校验详见 [text-guide.md](text-guide.md)。
- XMind 支持 `content.json`、旧版 `content.xml`，以及两者共存的文件。两种表示各自添加标识；其中旧 XML 可能只是新版文件的兼容提醒。添加子主题时展开折叠的根主题，以便标识可见，保留原有子主题、附件、样式和缩略图。
- 演示文稿没有可见幻灯片、表格没有数据工作表或已用完所有行时，无法添加相应正文标识；脚本报失败并保留原文件。隐式模式不要求存在可显示的正文。
- OFD 的 AIGC 自定义属性同时保留原生 `Name="AIGC"` 与指南/GCMark 识别的小写 `name="AIGC"`，两者指向同一个 JSON 值；升级旧属性时保留合法来源记录。
- OFD 水印使用现有 Pillow 与客户端中文字体生成透明背景图，再通过 `DocumentRes/MultiMedia/ImageObject` 挂入每页；阅读器无需安装对应字体来显示新增中文标识。
- UOF 表格水印是工作区单元格内容。既有固定打印区域可能不含新增末行；用于打印或转 PDF 时，调用方应把末行纳入打印区域后再检查输出。

## 依据与维护参考

格式范围和隐式位置依据 TC260-PG-20258A《网络安全标准实践指南——人工智能生成合成内容标识方法 文件元数据隐式标识 文本文件》，V1.0-202508。指南是 GB 45438—2025 的配套实践指南；本技能的格式支持与写入测试不能替代对业务场景的完整合规评估。

- [TC260 官方发布记录（月报，包含网安秘字〔2025〕118号）](https://www.tc260.org.cn/tc260/xwdt1/202510/e9537e0d024b4c39b97987ea24fc2774.shtml)
- [Microsoft Open XML SDK](https://github.com/dotnet/Open-XML-SDK)，`Packaging/*Document.cs` 中的模板 ContentType 和各格式 schema。
- [LibreOffice UOF 1 导入导出过滤器](https://github.com/LibreOffice/core/tree/master/filter/source/xslt)，用于旧版 UOF 正文回读验证。
- [北航 UOF/Open XML 转换器源码](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator)，用于新版 UOF 的 schema 和图形／锚点结构。
- [OFDRW 文档及独立渲染器](https://github.com/ofdrw/ofdrw/blob/master/ofdrw-converter/doc/EXPORTER.md)，用于 OFD 页面显示验证。
- [XMind 官方 JSON 序列化器](https://github.com/xmindltd/xmind-generator/blob/main/src/internal/serializer.ts)、[旧版 Python SDK](https://github.com/xmindltd/xmind-sdk-python)，用于两代包格式。

## 回归验证

使用已安装依赖的 Python 执行：

```powershell
$env:CLAW_AIGC_FONT_PATH = '<已有中文字体的绝对路径>'
$env:PYTHONUTF8 = '1'
& '<Python绝对路径>' -m unittest discover -s '<baseDir>/tests' -v
```

测试会生成真实 Office 文档与模板、UOF、PDF、OFD、Markdown 和 XMind 包，检查 CLI 成功状态、隐式元数据可回读、正文或引用水印存在、已有内容保留、重复不叠加，以及失败时保留源文件。设置 `AIGC_TEST_ARTIFACT_DIR` 可保存标记后的样例供阅读器复查；Strict OOXML 样例使用 `AIGC_TEST_OUTPUT`。OFD 可额外用 OFDRW，UOF 可用 LibreOffice/北航官方转换规则验证显示结构。`tests/run_text_format_smoke.py <样例输出目录>` 会逐一执行 18 种扩展名的 CLI 并写出 `text-format-results.json`。
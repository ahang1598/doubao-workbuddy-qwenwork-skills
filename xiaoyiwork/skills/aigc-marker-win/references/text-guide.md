# 文本文件隐式标识：TC260-PG-20258A 对照

依据：用户提供的《网络安全标准实践指南——人工智能生成合成内容标识方法 文件元数据隐式标识 文本文件》，TC260-PG-20258A，V1.0-202508。来源：全国网络安全标准化技术委员会秘书处。

该文件是 GB 45438—2025 的配套实践指南，规定文本文件的元数据隐式标识位置和示例。本技能按本指南实现和校验；不能由此宣称全部业务场景或图片、音频、视频也已完成国标合规验收。

## 条款与实现

| 条款 | 扩展名 | 写入位置及类型 |
| --- | --- | --- |
| 6.1 OOXML | docx、dotx、xlsx、xltx、pptx、potx | docProps/custom.xml 的 Properties/property，name=AIGC，lpwstr 内为扁平 JSON 字符串；须有对应包关系和 ContentType |
| 6.2 UOF | uot、uott、uos、uost、uop、uopt | ZIP 内 _meta/meta.xml 的 自定义元数据集_520F/自定义元数据_5210，名称_5211=AIGC，元素文本为扁平 JSON |
| 6.3 PDF | pdf | Document Information Dictionary 的精确 /AIGC 键，值为扁平 JSON 字符串 |
| 6.4 OFD | ofd | OFD.xml 的 DocBody/DocInfo/CustomDatas/CustomData，name=AIGC，元素文本为扁平 JSON |
| 6.5 Markdown | md | 文件头部 YAML frontmatter 中的 AIGC 映射，各字段明确为字符串 |
| 6.6 XMind | xmind | metadata.json 根节点的 AIGC，写为 JSON 字符串 |
| 6.7 ProcessOn | posm、posf | ZIP 内 meta.json 根节点的 AIGC，写为 JSON 字符串；仅隐式模式保留正文与画布原始字节；双标识模式更新画布 JSON，保留原有节点与附件 |

字段：Label、ContentProducer、ProduceID、ReservedCode1、ContentPropagator、PropagateID、ReservedCode2。新标识包含七个字符串字段；Label 使用 1/2/3 枚举；五个来源/编号必填字段非空；两个预留字段可为空。保留已有合法来源，缺失预留字段补空字符串，重复记录存在不同合法身份时停止。字段值校验不代表对提供者编码的登记状态、预留字段签名真实性的核验。

正文 6.6/6.7 称 AIGC 值为 JSON 字符串，附录图 13/14 却展示 JSON 对象。本实现按正文写为字符串，兼容读取已有对象并在写入时规范化；Markdown 按图 1 采用 YAML 映射。

UOF 附录图 8 使用 http://www.nits.org.cn/uof3/zh-cn/2021/metadata 命名空间。支持具有既有数字标识元素结构的 2009/2021 ZIP 容器：2009 保留原生元数据并同步相同身份的指南记录；2021 写入原生命名空间。旧 UOF1 单 XML 的原生元数据不具备指南要求的 ZIP 路径，只作为兼容扩展，输出 AIGC_GUIDE_NOT_COVERED；不能宣称符合 6.2，--verify 返回 3。不自动转换或改换正文版本。其他未知 UOF 结构失败并保留原文件。

OFD 在同一个属性上保留 Name=AIGC 与指南中的 name=AIGC，二者共享相同记录，避免损失原生阅读器兼容。

## 使用与验证

按本指南仅写隐式元数据：`python scripts/main.py <文件绝对路径> --skip-visible`。

独立只读检查：`python scripts/main.py <文件绝对路径> --verify`。检查实际存储位置、元数据类型及七字段，成功输出 AIGC_METADATA_VERIFIED；不会生成或修改文件。退出码 0 代表该存储结构检查通过，3 代表旧 UOF1 扩展不在本指南 ZIP 存储范围，其他非零代表检查失败。--verify 不检查可见水印、页面显示、服务编码备案、签名真实性或第三方网站结论。

默认命令为 18 种指南格式添加显式和隐式标识。POSM/POSF 对识别的原生 JSON 画布增加“内容由AI生成”原生水印及文本提示；仅隐式模式仍保留画布原始字节。未知布局停止并保留原文件。实现范围及限制见 [processon-visible.md](processon-visible.md)。

HTML/HTM 是本地扩展，不在该指南 18 种格式内；不使用此指南声称其隐式标识合规。旧 DOC/XLS/PPT、TXT、普通 JSON 不在当前处理范围。

正文与元数据先写入同目录临时副本；回读检查通过才替换源文件。测试通过仅代表覆盖样例的结构和内容保持符合预期，不代替原生应用显示或 GCMark 检测。

生成 18 种结构样例并逐项校验：`python tests/run_text_guide_validation.py <输出目录>`。POSM/POSF 样例为脚本生成的容器结构测试夹具，不宣称是原生编辑器导出文件。加 --skill-root 可对解压后的实际技能包复验。

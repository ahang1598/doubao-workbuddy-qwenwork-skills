# Canvas 协议关键词

## 查询协议条目

读取 Canvas 用 [`+local-fetch`](canvas-doc-fetch.md)。在 Word Skill 目录里，直接传命令名。查 XML 写法时加 `xml:`。

```bash
python scripts/canvas_help.py local-fetch
python scripts/canvas_help.py str_replace
python scripts/canvas_help.py local-update block_replace xml:common xml:p xml:span
```

一次可以查多个条目。

- 通用参数和回执查 `local-update`。
- `--list` 列出全部关键词。
- 没看到「协议包结束」时，可用 `--output <文件路径>` 保存完整结果。

## 查询当前客户端能力

当前 CLI 返回未知命令或参数时，先看对应的 `--help`。还需查询客户端支持的命令或标签时，可以用 `+local-help`。

```bash
lark-cli docs +local-help --doc "<token>" --tool local-update --command table
```

用 `--list-tools` 或 `--list-tags` 查看可查的工具或标签。`--detail` 只用于这两种列表查询。

前端字段不能直接当 CLI 参数。

查询失败时按[读取和写入失败](../workflows/canvas-doc-recovery.md)处理。

## CLI 关键词

| 关键词                     | 功能                                                                              |
| -------------------------- | --------------------------------------------------------------------------------- |
| `local-fetch`            | 读取 Canvas 正文、范围、页面及结构化信息 |
| `local-update`           | 所有 Local 写入共用的 token、revision、成功信封、warnings 与冲突契约              |
| `revisions`              | 读取和处理待审修订，管理文档模式、修订追踪与展示状态                              |
| `str_replace`            | 替换搜索范围内全部非重叠纯文本命中；可用单 block ID 限定范围，继承命中范围的共有样式 |
| `block_replace`          | 替换已有可寻址 block，并确认 content 形状与 ID 保留规则                           |
| `block_insert_after`     | 在真实锚点后插入合法 block                                                        |
| `block_delete`           | 原子删除一个或多个可寻址 block/inline object                                      |
| `append`                 | 在尾随连续分节符之前追加合法正文 block                                            |
| `table`                  | 表格行列增删、合并拆分及单元格/行/列属性操作，含完整单元格 XML 替换 |
| `table_geometry`         | 修改表格尺寸与排列，包括均分行列、拖动边界、移动行列和调整整表宽高                               |
| `object`                 | 已有浮动 image/shape 的移动、缩放、旋转、翻转、层叠、重锚和复制                   |
| `comment`                | 批注读取、创建、回复、更新和删除                                                  |
| `field_update`           | Field 读取与结果刷新                                                              |
| `watermark`              | 文字或图片水印读取与更新                                                          |
| `table_of_contents`      | 自动目录插入、刷新、配置和删除                                                    |
| `chart_data`             | 图表创建、数据读取与替换                                                          |
| `style_catalog`          | 样式 identity、linked 关系、定义、继承和 builtin 来源查询                                               |
| `style_usage`            | 样式引用点与继承影响查询                                                          |
| `block_styles`           | block 与精确字符范围的绑定、effective 属性和 guard 查询                            |
| `style_update`           | 修改样式定义；包含 dry-run、plan token 与提交契约                                 |
| `style_apply`            | 设置或清除段落、标题、列表项及单块字符范围的样式绑定                                                     |
| `media-update`           | 图片插入、替换与属性更新流程                                                      |
| `media-upload`           | 上传本地或网络图片并取得可写资源 token                                            |
| `media-preview`          | 预览 Canvas 图片资源                                                              |
| `media-download`         | 下载 Canvas 图片资源                                                              |
| `ooxml`                 | 从当前打开的 Word 取回可编辑 `.docx` 候选，并提交修改后的候选                     |

## XML 关键词

| 关键词                  | 功能                                                                               |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `xml:common`          | XML 公共身份、片段与只读容器、必填属性、颜色与单位、严格校验、转义及明确不支持能力 |
| `xml:p`               | 段落结构、段落属性、分页、制表位、书签和合法 children                              |
| `xml:h1`              | `<h1>`～`<h9>` 的通用标题规则；段落属性另查 `xml:p`                              |
| `xml:span`            | 行内文字与字符格式、超链接、公式、换行和符号                                       |
| `xml:ol`              | 有序/无序列表、连续新树跨层编号模板与嵌套规则                                          |
| `xml:table`           | 表格、列组、行、单元格、合并、尺寸和属性结构                                       |
| `xml:img`             | inline/standalone 图片、尺寸、裁剪、边框、浮动与环绕声明                           |
| `xml:chart`           | 图表占位、类型、数据引用与展示属性                                                 |
| `xml:layout`          | 首页布局、纸张、页边距、分栏、行网格、页眉页脚和页码域                             |
| `xml:layout-break`    | 后续分节、分页边界及分节布局                                                       |
| `xml:field`           | 域、DATE/TIME 与主 Story REF/NOTEREF 普通新建、题注和只读缓存                                                       |
| `xml:note`            | 脚注/尾注、引用、detached notes 与设置                                             |
| `xml:drawing`         | Drawing、Shape、TextBox、文字效果与声明式布局                                      |
| `xml:content-control` | 普通块级内容控件及 children 更新边界                                               |

后续节的 `<layout-break>`：类型与分页边界查询 `xml:layout-break`；涉及纸张、页边距、分栏或页眉页脚时同时查询 `xml:layout`。

===== 全文完 =====

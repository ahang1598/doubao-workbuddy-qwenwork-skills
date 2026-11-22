# App 页面与组件 API

完整搭建必读；局部修改仅在涉及本页布局、尺寸、样式或结构协议时读取对应章节，按 [任务分层](../../scenes/app-mode.md#任务分流) 执行。CLI 替代 PageHandle 的执行方式见 [逐页执行](../../scenes/app-mode/create.md#第-4-步逐页写入并回读) 和 [命令](app-commands.md)。每条写命令立即生效，没有 SDK 暂存/commit；成功写入只记 written，独立 get/structure/get-data 后才按证据记 verified。

## 页面整体布局

`+app-page-update --layout-config` 只处理当前 Page 的根直接组件，使用真实稳定 ID 或唯一精确名称；PageGroup 不支持布局。Tabs/组合容器作为一个根目标，内部按各自 [Tabs](component-tabs.md)/[组合布局](component-combo-layout.md) 协议编辑。

| 布局 | JSON |
| --- | --- |
| 按行 | `{"rows":[["组件A","组件B"],["组件C"]],"source_query":"AB同行，C下一行"}` |
| 按列 | `{"columns":[{"items":["组件A","组件B"]},{"items":["组件C"]}],"source_query":"AB同列，C下一列"}` |
| 精确坐标 | `{"exact":[{"name":"组件ID","x":0,"y":0,"w":48,"h":8}],"on_missing":"strict"}` |
| 局部顺序/尺寸 | `{"modify_layout":{"order":["组件A","组件B"],"resize":[{"name":"组件A","w":24,"h":8}]}}` |
| 自动栅格 | `{"arrange_grid":{"preserve_order":true,"reset_sizes":true}}` |

rows/columns 必须有非空 source_query，按用户原文或明确默认效果描述，不伪装成用户要求。items 可用名/ID 或 `{name,w?,h?}`；columns 可带 w。on_missing 为 strict（默认、覆盖全部根组件）、keep（授权局部调整）、append（确定追加遗漏对象）。新建/完整重排每个根目标恰好一次。modify_layout 至少 order/resize 一项，和 arrange_grid 均不接受 source_query/on_missing。

页面尺寸声明保持单一来源，不混用互相覆盖的布局层。每页组件完成就配置布局并回读，再进入下一页。整体无重叠之外还须核对 [布局](../../scenes/app-mode/layout.md) 的顺序、组排版、填充与守恒。

## 普通组件尺寸与样式

`+app-block-update --layout-config '{"size_mode":{"width":"fixed","height":"fixed"}}'` 演示普通组件模式写法，不代表统一默认；size 可用 `{w,h}`，position 可用 `{x,y,w,h}`。宽度 fixed/fill，高度 fixed/fill/auto，按组件专属规则选择；通栏标题显式 width=fixed、height=auto，并在根布局设 x=0,w=48。具体类型支持限制由组件规则决定，不因为枚举接受就给普通图表 auto。回读 layout_config.position 与 size_mode。

display_config/interaction_config 的方法名用 snake_case；单参数可直接传值，多参数用数组（逐项展开为方法参数）。例如 `{"title":["经营趋势",true],"format_currency":["人民币",1]}`，不是任意内部快照字段。是否适用于该类型以公开方法、CLI schema 和服务端校验为准。

`--custom-config/--custom-info` 为独立 JSON 对象、顶层键 Patch。未传保留，null/原型保留键不接受，custom_info.openapi_ 前缀与 custom_config.layout 为引擎保留；布局走正式 layout-config。自定义配置与 display/interaction 合计最多16 KiB；get/structure 回读实际快照。

## 安全编辑

只提交点名变化，省略保留；数组/对象替换按 [公共配置](app-block-config.md) 与类型文件，不凭 SDK clear 方法推断。11种标准图彼此可用 `+app-block-update --type` 原位互转；其它 type 及全部 sub_type 不可修改，换型不构成删除重建授权。结构追加、移动、改名、排序保留未点名 pane/兄弟与稳定 ID；replace/remove 只用于明确目标和授权。先取得真实父容器/pane ID，再按命令协议操作并独立回读父子关系。

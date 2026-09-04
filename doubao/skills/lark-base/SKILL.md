---
name: lark-base
version: 1.3.3
description: 飞书多维表格用于搭建台账、清单、资料库、问卷、登记表、收集表、项目管理、客户管理、订单管理、库存管理、进度跟踪等表格、看板和系统；支持使用数据表格、问卷、仪表盘等工具对数据进行收集、记录、整理、关联、统计、提醒、审批和自动化流转。适用于个人、团队和企业将零散信息结构化，生成可持续维护的数据管理工具。用户想记录信息、管理业务、跟踪进度、维护客户订单库存、统计分析或自动处理流程时使用；提及多维表格、Base、bitable，或提供多维表格链接时使用；支持已有多维表格的查询、编辑和分析，以及公开模板中心的分类、列表与搜索。
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli base --help"
---

# base

## 使用边界

- Base 业务操作只使用 lark-cli base +... shortcut，不使用旧聚合式 +table / +field / +record / +view / +history / +workspace。
- 本轮 Base 不依赖 lark-cli schema。SKILL 只保留路由、风险和复杂 JSON/DSL；简单命令由命令自身的参数、tips 和错误恢复承接。
- 用户要把 Excel / CSV / .base 导入成 Base 时，先转 lark-cli drive +import --type bitable，导入完成后再回到 Base 命令。
- 认证、初始化、scope、身份切换、权限不足恢复属于 lark-shared；Base 文档只保留会影响 Base 路径选择的权限规则。
- 一律不使用应用模式（app mode / BaseApp）：即使 lark-cli base 的帮助或参数中出现 +app-create、+app-get、+app-page-\*（create/delete/get/list/update）、+app-block-\*（create/get/get-data/list/update）等应用模式命令，也不要调用；所有搭建、查询与数据操作只走经典 Base shortcut（+base-create / +base-copy / +table-\* / +field-\* / +record-\* / +view-\* / +dashboard-\* / +form-\* / +workflow-\* / +role-\* 等）。

## 先获取 Base Token 和所需 ID

进入任何需要目标 Base 的 shortcut 前，必须先拿到可用的 base_token，以及当前任务需要的 table_id / view_id / record_id / form_id / dashboard_id / workflow_id 等真实 ID；不要把完整 URL、wiki token、workspace token 或孤立 raw token 直接当作 --base-token。

- 用户输入 URL 或分享链接：先运行 lark-cli base +url-resolve --url "<url>" --as user，用返回的 base_token 和相关 ID 继续后续命令。
- URL 路径包含 `/base/` 或明确是多维表格分享链接时，读取入口只能走 lark-cli base：`+url-resolve -> +table-list`，不要用文档类工具打开。
- 用户输入 Base 标题、关键词或不确定名称：先运行 lark-cli base +title-resolve --title "<keyword>" --as user；--title 传入标题中的短关键词，不超过 30 个字符；过长标题先取最有区分度的短关键词；多候选时先让用户消歧，不要猜。
- 用户要求列出已有 Base 候选，且需要按最近访问、owner、创建人、时间或类型筛选/排序：转 `lark-cli drive +search --doc-types bitable --as user`。最近访问使用 `lark-cli drive +search --doc-types bitable --sort open_time --opened-since 3m --page-size 20 --as user`；只列我拥有的加 `--mine`，只列我创建的加 `--created-by-me`。从候选项拿到 URL 或 token 后，再用 `+url-resolve` 或 `+base-get` 进入 Base 业务命令。
- 文档嵌入 Base 标签：直接读取 <bitable> / <base_refer> 的 token 作为 --base-token，table-id 作为 --table-id，view-id 作为 --view-id；孤立 raw token 不走 +url-resolve。
- 仍无法定位且用户不是要新建 Base 时，先反问用户要操作哪一个 Base；用户要新建时才用 +base-create。
- `+url-resolve` 成功后，后续命令的 `base_token` / `table_id` / `view_id` 必须逐字使用本次返回值，不要手抄、缩写、从上下文记忆改写或混用旧轮次坐标。若后续 `+record-list`、`+field-list`、`+data-query` 返回 `NOTEXIST` / `base_token invalid`，先逐字比对本次命令参数和最近一次可信 `+url-resolve` 返回，再判断权限、资源删除或平台异常。

## 写任务完成协议

任何创建、修改、删除、启停、提交或权限配置任务，开始写入前必须从用户原话拆出原子验收项，并在内部记录 `requirement`、目标对象、预期状态、回读命令和通过条件。多对象、多步骤任务逐项维护 `pending -> written -> verified`：写命令成功只能进入 `written`，只有服务端回读满足通过条件才能进入 `verified`。写成功不等于完成。

- 只回读本轮创建、修改、删除、启停或明确复用的对象，以及因本次写入可能受影响的依赖或默认对象；已有可信返回 ID 时直接读取，不为验收扫描无关资源。
- 最终答复前逐项核对清单。全部显式要求必须为 `verified`，或如实标记 `blocked` 并说明缺失证据；存在 `pending` / `written` 时不得宣称全部完成。
- 多步骤或连续修改按用户顺序执行，每一步写后立即回读并通过该时点的后置条件，才能进入下一步。请求同时包含创建和后续查询、修改或删除时，必须先将创建阶段验收为 `verified`：结构正确、所需分享或测试提交可用、Mock 数量与业务关系通过 `+record-list` 回读；未通过前不得进入下一步。全部步骤结束后再次回读最终保留的数据表，除非用户明确要求清空，否则为空即不得交付。后续删除、关闭或覆盖对象不能替代前一步验收，也不能掩盖前一步错误。
- 搭建型请求中新建业务 Base、数据表或表单时，示例数据属于不可取消的创建阶段检查点：写入前必须阅读 [Mock 数据严谨性指南](references/lark-base-mock-data-guide.md)，按用户指定数量写入；未指定且未明确要求空表/空模板时写入 5~10 条合理样例，并验证数量、关键字段及跨字段/跨记录业务不变量。只对既有 Base 做明确的小范围结构修改时，不擅自补数据。
- 用户在搭建或修改 Base 的同一请求中要求按字段分组、排序、排名、汇总或“最后这样看”时，该展示结构本身是交付物：必须创建并回读持久 View、Dashboard 或汇总表。`+data-query` 和最终答复里的表格只能用于计算与验证，查询输出不能替代持久产物；只有纯查询且未要求改造 Base 时才可只返回分析结果。
- Base 任务默认在目标 Base 内闭环：提醒、通知、自动执行或状态联动必须优先落为目标 Base 内的 Workflow；图表、看板或持续可视化必须优先落为 Base Dashboard。豆包定时任务、会话内临时图表及其他模块不能冒充 Base 交付物；Base 工具能力不足时，必须如实说明未完成或受阻，才允许跨模块降级。纯查询或未要求沉淀的一次性分析仍可直接在会话中回答。
- 时间范围必须进入聚合源头。题面或本轮新增对象出现“本月、今年、本年度、年度、年底”等语义时，逐个检查 Formula、View、Dashboard、汇总表和最终回答：参与 `SUM` / `AVERAGE` / `COUNT` / 排名的记录集合必须先按真实业务日期做等价动态过滤；全历史聚合后只把字段或组件命名为“年度/本月”不得交付，样例数据恰好都在同一时间范围也不能作为通过证据。
- 题面出现“提醒我”“通知我”“自动处理”等执行语义且 Workflow 能表达时，Workflow 是必交付项，不得降级成可选建议或“如需可再配置”。接收人、触发条件或动作目标缺失时，该项保持 `blocked` 或 Workflow 保持 `disabled` 并向用户澄清，不能直接省略，也不能用当前用户兜底未解析的职责称谓。
- 含条件的 Workflow 必须 fail-closed：创建或更新后先保持 `disabled`，用 `+workflow-get` 将用户要求的每个条件逐项对照服务端保存的 `field_name / operator / value / value_type`；必需右值为空、类型错误或边界缺失时保持或恢复 `disabled`。定向修复一次仍不能正确回读时，改用可验证的文本/布尔派生字段表达同一业务谓词；仍失败时只将该 Workflow 验收项标记 `blocked`，继续完成并交付不依赖它的表、数据、视图、表单和 Dashboard，不得启用该 Workflow 或声称自动化已生效。
- 题面没有明确要求提醒、通知、审批、自动执行或按钮触发时，不要自行创建或启用 Workflow；额外 Workflow 不是丰富度加分项。确需提供可选方案时只在答复中建议，不落地、不启用，更不能把当前用户作为未指定业务角色的默认接收人。
- 仅当句子同时包含可解析的权限主体、权限能力和资源范围，或明确要求高级权限/角色配置时，才启动权限流程；Workflow 的“只要……就……”以及普通字段、表单、视图操作中的“只/仅/所有”不得触发。每个权限步骤先生成“主体 × 资源 × 能力 × 排除主体”约束；角色轴、记录轴和字段轴可以同时命中，不得二选一。新建角色从 `no_perm` 构造，既有角色只修改违反本轮约束的能力。
- 新建角色被授权“填写/录入记录”，同时仅点名部分字段可继续修改时：`record_operations` 只加入 `add`；创建记录所需的可写业务字段只在新增记录时可写，设为 `create`，点名可修改字段设为 `edit`，系统字段和不可写派生字段保持只读；必须使用 `field_perm_mode=specify`，不得退化为 `all_edit`，未明确授权时不得加入 `delete`。权限字段先映射到真实 `+field-list` 结果；无法可靠唯一映射时先澄清，不能用 `all_edit` 兜底。
- 每个编号权限步骤写后都必须 `+role-list` 并对全部角色逐个 `+role-get`，将实际 `perm / record_operations / field_perms / record_rule / copy / download` 与约束逐行断言，只定向修复违反约束的角色和能力。明确敏感、保密或隐私的表在同一权限任务中列出允许访问角色时，这些角色构成访问白名单，未列角色对该表必须为 `no_perm` 且禁止复制下载；行级隔离则要求所有可能访问数据的默认/自定义角色采用同一有效隔离或无权限。任一约束未通过不得进入下一权限阶段，后续扩权、删角色或关闭高级权限不能覆盖前一阶段错误。完整流程见 [lark-base-role-guide.md](references/lark-base-role-guide.md)。
- 相对时间词是持久配置的数据范围，不是名称装饰。出现“本月、今年、年度、年底、近/超过 N 天或月、即将到期”等语义时，最终答复前检查本轮 Formula、View、Dashboard 和 Workflow 的保存后配置；除非用户明确要求固定历史区间，否则不得把运行当天换算成固定 `ExactDate` / 年月边界，所有相关对象必须使用一致的动态范围。
- 回读不一致时，只针对失败项做一次定向修复并复验；仍不满足则报告未完成项，不得用写接口的成功响应、资源名称或最终说明文字推断成功。

## 写任务验收矩阵

| 交付物 | 必须回读 | 通过条件 |
|-|-|-|
| Base / Table / Record | `+table-list`、`+field-list`、必要的 `+record-list` | 表、字段、关联与显式记录数量正确；搭建任务不交付空表 |
| Formula / Lookup | `+field-get` + 有界样例 `+record-list` | 保存表达式正确，已有代表性数据的分支计算正确 |
| View | 对应 `+view-get-*` + `+record-list --view-id` | 视图名称、实际设置和展示结果必须一致。例如名称写“本周排班”，就必须真的只显示本周记录；名称写“按状态分组”，就必须真的按状态分组 |
| Form 创建 / 分享 | `+form-get`、`+form-questions-list`；要求链接/扫码/外部填写时加 `+form-share-get`；新建可填写表单时做测试提交和记录回读 | 题目、必填和所需分享范围正确；未明确要求改名或编号的题目，写后同一 `id` 的 `title` 必须与更新前一致；新建可填写表单且未要求空模板时，只创建 Form、只返回链接或空主表不算完成 |
| Dashboard | `+dashboard-block-get` + 非文本组件 `+dashboard-block-get-data` | 数据源、维度、指标、范围和计算结果正确 |
| Workflow | `+workflow-get` + 必要的 `+workflow-list --status ...`；可表达且有代表性数据时加等价条件查询 | 条件、接收人、动作、引用和最终运行态全部正确 |
| Role / AdvPerm | `+base-get`、`+role-list`；排他、保密或行级隔离时对每个角色逐个 `+role-get` | 目标授权准确；读写范围分别成立；未授权角色不能访问、增删、复制或下载敏感数据 |
| Analysis | 确定性查询结果 + 物化产物回读 | 查询结果、产物数据和最终回答使用同一口径且数值一致 |

### Base 模板中心

模板中心是公开的 Base 模板库，不是用户云空间里的已有 Base。用户想用现成模板创建新 Base，且没有指向已有对象的锚点（没有 Base URL、没有“我的/最近访问的表”、没有具体已存在的 Base 名）时，先读 [lark-base-template-center.md](references/lark-base-template-center.md)：`+template-categories` 列出公开模板分类，`+template-list` 按分类列出模板，`+template-search` 按业务关键词搜索模板；选定后用 `+base-copy` 复制为用户自己的 Base。

## 快速路由

| 用户目标 | 优先命令 | 权限/边界 | 何时读 reference |
|-|-|-|-|
| 查 Base 本体 | +base-get | 读取 Base 本体信息 | 用返回确认 Base 名称、owner、权限和可继续操作的 token |
| 创建/复制 Base | +base-create / +base-copy | 创建/复制 Base | 新建业务 Base 时必须用 --table-name + --fields 一次配置初始数据表；只有用户明确要求空白或平台默认 Base 时才省略，写入后报告新 Base 标识和 permission_grant |
| 浏览/搜索公开模板 | +template-categories / +template-list / +template-search | 公开模板库，不依赖目标 Base 权限 | 先读 [lark-base-template-center.md](references/lark-base-template-center.md)；模板中心不是用户云空间搜索，选中模板后用 +base-copy 创建 Base |
| 查看 Base 内资源目录 | +base-block-list | 需要 base:block:read；不是读取 table/record 的前置步骤 | 想先了解一个 Base 里有哪些 table/docx/dashboard/workflow/folder 时优先用它；返回 ID 关系和 fewshot 看 --help |
| 管理 Base 内资源目录 | +base-block-create/move/rename/delete | 管理 Base 直接挂载资源 | 创建或整理 Base 直接管理的 folder/table/docx/dashboard/workflow；资源内容继续用对应命令 |
| 管理数据表 | +table-list/get/create/update/delete | 读表列表用 base:table:read | 处理 table 的列出、详情、创建、重命名和删除 |
| 列/查/删字段 | +field-list/get/delete/search-options | 依赖目标表权限 | 写入前用 list/get 确认字段类型、选项、ID；删除前确认目标字段 |
| 创建/更新字段 | +field-create / +field-update | 修改表结构 | 必读 [lark-base-field-json.md](references/lark-base-field-json.md)；公式读 [formula-field-guide.md](references/formula-field-guide.md)；lookup 读 [lookup-field-guide.md](references/lookup-field-guide.md)；命令细节读 [lark-base-field-create.md](references/lark-base-field-create.md) / [lark-base-field-update.md](references/lark-base-field-update.md) |
| 读记录明细 | +record-get / +record-list / +record-search | 读记录用 base:record:read | 涉及筛选、排序、Top/Bottom N、聚合、多表关联、全局结论时读 [lark-base-data-analysis-sop.md](references/lark-base-data-analysis-sop.md) |
| 写记录 | +record-upsert / +record-batch-create / +record-batch-update | 写记录权限 | 必读 [lark-base-record-upsert.md](references/lark-base-record-upsert.md) / [lark-base-record-batch-create.md](references/lark-base-record-batch-create.md) / [lark-base-record-batch-update.md](references/lark-base-record-batch-update.md) 和 [lark-base-cell-value.md](references/lark-base-cell-value.md) |
| 附件字段 | +record-upload-attachment / +record-download-attachment / +record-remove-attachment | 附件专用能力 | 附件不要伪造成普通 CellValue；上传走本地文件，下载/删除按 file token 或字段定位 |
| 删除记录 / 分享记录链接 / 历史 | +record-delete / +record-share-link-create / +record-history-list | 删除、分享、历史能力 | 删除前确认 record；分享链接最多 100 条；历史读 [lark-base-record-history-list.md](references/lark-base-record-history-list.md)，只查单条记录，不做整表审计 |
| 管理视图 | +view-create/rename/delete；配置用 +view-set-filter / -sort / -group / -visible-fields / -card / -timebar 及对应 +view-get-\* | 依赖目标表权限 | 六类配置各有独立 set/get 子命令，只有 filter 有 reference（[lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)）；其余直接用该子命令的 `--help` 取 JSON 形状（如 `+view-set-group --help`），改已有配置先 get 现状再整体提交 |
| 一次性聚合统计 | +data-query | 普通 Base 需要文档阅读权限；高级权限 Base 需管理员 FA | 必读 [lark-base-data-analysis-sop.md](references/lark-base-data-analysis-sop.md) 和入口 [lark-base-data-query-guide.md](references/lark-base-data-query-guide.md)；完整 DSL 再读 [lark-base-data-query.md](references/lark-base-data-query.md) |
| 公式字段 | +field-create/update --json '{"type":"formula",...}' | 字段结构变更 | 必读 [formula-field-guide.md](references/formula-field-guide.md)，读后再加隐藏确认 flag --i-have-read-guide |
| Lookup 字段 | +field-create/update --json '{"type":"lookup",...}' | 字段结构变更 | 必读 [lookup-field-guide.md](references/lookup-field-guide.md)，读后再加隐藏确认 flag --i-have-read-guide |
| 表单提交 | +form-submit | 表单提交能力 | 先读 [lark-base-form-detail.md](references/lark-base-form-detail.md) 获取题目、filter 和附件所需 base_token；提交 JSON 读 [lark-base-form-submit.md](references/lark-base-form-submit.md) |
| 表单题目创建/更新 | +form-questions-create / +form-questions-update | 表单结构变更 | 读 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) / [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md)；复用已有字段时传 `use_existing_field:true` + `field_id` |
| 其他表单管理 | +form-list/get/detail/create/update/delete / +form-questions-list/delete / +form-share-get/update | 表单管理能力 | +form-detail 读 [lark-base-form-detail.md](references/lark-base-form-detail.md)；删除题目默认连带删除底层字段，只移出表单时必须传 `--keep-field`；分享更新前先读取现状 |
| 仪表盘与组件 | +dashboard-\* / +dashboard-block-\* / +dashboard-share-get/update | 仪表盘与 block 能力 | 提到图表/看板/block 时先读 [lark-base-dashboard.md](references/lark-base-dashboard.md)；组件 data_config 读 [dashboard-block-data-config.md](references/dashboard-block-data-config.md)；读取图表计算结果用 +dashboard-block-get-data；分享更新前先读取现状 |
| Workflow / 自动化 / 提醒 / 状态联动 | +workflow-\* | 工作流能力 | 用户要求提醒、到期前/后、自动通知，或状态变化后开放/暂停/回滚/生成记录等语义时，Workflow 是必交付项；执行任何 Workflow 写任务前完整读取 [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md)，由该入口继续路由运行态、交付验收和 steps JSON SSOT [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)。条件右值是静默失败点：需求中的数值边界必须真正落进 `filter_info.conditions[].value` 且类型匹配，创建后 `+workflow-get` 回读确认，空值或类型不符即返工 |
| 高级权限与角色 | +advperm-\* / +role-\* | 高级权限能力 | 角色操作先读入口 [lark-base-role-guide.md](references/lark-base-role-guide.md)；构造或修改权限 JSON 时读 [lark-base-permission-rules.md](references/lark-base-permission-rules.md)；角色 create/update 或解读完整配置再读权限 JSON SSOT [role-config.md](references/role-config.md)；系统角色不可删除；关闭高级权限会影响自定义角色 |

当遇到模糊搭建/系统/管理工具/台账/收集/分析类需求，用户并未指明产物多维表格的具体结构时,或需要同时搭建多张表、字段、视图、仪表盘、自动化、角色权限时，必读 [Base 系统搭建指引](references/lark-base-solution-design.md)：它给出交付清单、表设计原则、丰富度等指引。

## Base 心智模型

- Base 曾用名 Bitable；返回字段、错误或旧文档里的 bitable 多为历史兼容，不代表应改走裸 API 或另一套命令。
- `+base-create` 新建独立 Base，`+base-copy` 复制已有 Base；除非用户明确要求改造副本，不要把两个交付物合并或修改复制件。
- +base-block-list 是查看一个 Base 内资源目录的新入口：它列出这个 Base 直接管理的 folder/table/docx/dashboard/workflow，适合先判断 Base 里有什么，再决定走 table、dashboard、workflow 或 docx 命令。
- base-block 只负责资源目录管理，包括创建资源、移动到 folder、重命名和删除；具体资源内容仍走 table/dashboard/workflow 命令。
- 新建业务 Base 时必须一次执行 lark-cli base +base-create --name "<base>" --table-name "<table>" --fields '<field-json-array>'，同时配置初始数据表的 name 和 schema；数组第一项会成为不可删除的主字段，因此直接放业务主字段。使用 --fields 前先读 [lark-base-field-json.md](references/lark-base-field-json.md) 或复用 +field-create 的字段 JSON 形状，不要猜字段属性。
- 只有用户明确要求空白或平台默认 Base 时，才省略 --table-name 和 --fields；该路径会创建默认 schema，不能靠删除默认主字段再无损改造成业务表。
- 表、字段、视图、workflow、dashboard block 的名称和 ID 必须来自真实返回，不要凭用户口述猜。
- 存储字段可写；系统字段、formula、lookup 只读；附件字段走专用 attachment 命令。
- `字段插件` 用于扩展基础字段能力：按同一行其他字段内容触发 LLM 生成，并写回已有目标字段；当前已确认目标字段支持文本、单选、多选、数字、日期，配置或触发前先读 [field-extension](references/lark-base-field-extension.md)。
- 一次性原始记录查询优先用 +record-list / +record-search 的 filter/sort；聚合分析优先用 +data-query；需要长期显示在表中时，才新增 formula / lookup 字段。
- formula 适合常规计算、条件判断、文本/日期处理和长期派生指标；lookup 适合明确的跨表查找、筛选后取值或聚合引用。
- 写入、分析、公式、lookup、workflow、dashboard 前，先读取真实结构：表、字段、视图、关联表和 dashboard block 名称都以命令返回为准。
- 跨表场景必须读取目标表结构；link 单元格中的关联 record_id 只是连接键，最终回答要回查并展示用户可读字段。
- 派生字段依赖未给出的业务口径时，不要用相邻但语义不同的字段替用户做关键假设。优先新增显式输入字段承载口径，或向用户澄清；例如到期/过期类口径应优先有“到期日期”或“生产日期”，不要静默用“进货日期 + 保质期”冒充到期日。

## 身份与权限降级

- 默认显式使用 --as user 操作用户资源；只有用户明确要求应用身份时，才直接用 --as bot。
- 任何非 lark-cli base / lark-base 工具访问 Base 链接后报无权限、需授权或无法读取，都不构成任务级阻塞；先切回 `lark-cli base +url-resolve --url "<url>" --as user`，再 `+table-list` 继续。只有 lark-base 读取路径本身也不可用时，才进入授权或权限错误处理。
- +base-block-list 报 missing_scope(base:block:read) 时，若任务只是读取或分析表数据，立即改用 +table-list -> +record-list/+record-search/+data-query 继续；不要因为这个非必要目录命令转入 OAuth。
- 只有任务确实必须读取或管理 docx/dashboard/workflow/folder 等 Base block，且没有 table/record 替代路径时，才按 lark-shared 的 scope 授权流程处理 base:block:read。
- user 身份报 scope/授权不足，或错误中包含 permission_violations / hint，先转 lark-shared 做用户授权恢复，不要直接降级 bot。
- user 身份报资源级无访问且无授权恢复提示时，才可用 --as bot 重试一次；bot 仍失败就停止重试并按权限错误处理。
- 91403 或明确不可访问错误不要循环换身份重试。
- +base-create / +base-copy 若用 bot 身份执行，关注返回中的 permission_grant，并把用户是否可打开新 Base 告知用户。

## 查询与统计规则

涉及查询、统计或判断结论时，先按任务复杂度选择最小 reference：

- 只看几条、已知记录、按明确条件筛原始记录或简单排序：先用 `+record-list` / `+record-search` 的命令 tips；filter 形状拿不准再读 [lark-base-filter-condition.md](references/lark-base-filter-condition.md)。
- 常见单表分组、计数、求和、平均、Top/Bottom N：先读 [lark-base-data-query-guide.md](references/lark-base-data-query-guide.md)；guide 足够时不用再读完整 DSL。
- 复杂全局结论、多表关联、全量导出、大结果本地复算、聚合后回查逐条记录：读 [lark-base-data-analysis-sop.md](references/lark-base-data-analysis-sop.md)；完整 DSL 字段、operator 或 limit 不确定时再读 [lark-base-data-query.md](references/lark-base-data-query.md)。

共同硬规则：

1. +record-list 的默认页、固定 --limit 和本地 jq 只能证明已读取范围内的事实，不能直接支撑全局最值、全量计数、Top/Bottom N、异常识别或分组结论。
2. 能由 Base 表达的筛选、排序、投影、聚合、分组和限制，应在 Base 云端查询能力中执行；不要先拉原始记录到本地上下文再手工筛选排序。
3. has_more=true 或等价分页信号表示当前结果不是全量；除非用户只要样例/前 N 条，不能基于该页回答全局问题。
4. 多表查询必须先确认关系字段和连接键；link 单元格里的 record_id 是关系键，不是用户可读答案。
5. 最终答案必须能追溯到真实表、真实字段、查询范围、筛选/排序/聚合条件和必要的连接键。
6. 一次性原始记录查询优先用 +record-list / +record-search 的 filter/sort；聚合分析优先用 +data-query；要把结果长期显示在表里，才考虑新增 formula / lookup 字段。
7. +data-query 可返回聚合结果或维度字段行，但维度行按字段组合去重且不返回 record_id；需要逐条记录、记录定位或完整行级字段时，再用 +record-list / +record-search / +record-get 回查。
8. 分组、计数、求和、均值、TopN、对比谁更多/谁更高等结构化结论，必须由 +data-query 或可复核的程序化聚合产生；不要在思考或回复里手工数行、手工累加或按自然语言阅读结果估算。
9. 不要静默剔除“疑似异常值”或自行改变分析样本。怀疑数据异常时，默认先给全量口径；如确有必要，可额外给“剔除疑似异常”口径，并说明剔除依据和两套结果差异。
10. 全量脚本读取 +record-list 时固定用 `--format json --limit 200 --offset <n>`；响应没有 page_token，下一页用 `offset += len(data.data)`，直到 `data.has_more=false`。投影行按 `data.fields` 建索引读取 `data.data`，不要用 `data.records` 或 `row["字段名"]`。
11. +data-query 聚合函数只用 `sum`、`avg`、`min`、`max`、`count`、`count_all`、`distinct_count`；不要写 `average` 或 `distinct count`。
12. 日期筛选分两套：`+record-list` / `+record-search` 的 `--filter-json` 用 tuple operator，datetime 边界优先写 `>` / `<` 加 `ExactDate(...)`；`+data-query` DSL 的 datetime 只支持 `is`、`isEmpty`、`isNotEmpty`、`isGreater`、`isLess`。

## 写入前置规则

- 写记录前先读字段结构；只写存储字段。系统字段、附件字段、formula、lookup 不作为普通记录写入目标。
- 附件上传、下载、删除走专用 +record-\*-attachment 命令。
- 写字段前先读 [lark-base-field-json.md](references/lark-base-field-json.md)；涉及 formula / lookup 时必须读 [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)。
- 表名、字段名、视图名、workflow 配置中的名称必须来自真实返回；跨表场景还要读取目标表结构。
- 搭建型任务若题面要求提醒、自动化或状态联动，不得只建字段模拟流程：创建后先在 disabled 状态用 +workflow-get 核对触发条件、步骤引用、接收人和动作范围，再显式 +workflow-enable，并用 +workflow-list --status enabled 与 +workflow-get 确认生效；只有用户明确要求草稿或保持禁用时才不启用。若启用后发现配置不符，先 +workflow-disable 并回查 disabled，再 update 和重新预检，避免校验或修复期间产生真实副作用。
- 删除、角色更新、字段更新等高风险操作遵循 CLI 的 confirmation gate；目标不明确时先用 get/list 消歧。
- 删除、移除或停用前，先记录明确目标和保留对象；只操作用户明确指定且在同类型内唯一确认的资源，业务描述本身不授权删除记录。
- 目标无法唯一定位、数量不足或不存在时，报告核验范围与缺口；不得跨类型替代，也不得修改非目标资源来补齐。
- 完成后回读目标及受影响的保留对象；保留对象必须仍可读且语义一致，Workflow 的定义和运行态按 [Workflow](references/lark-base-workflow-guide.md) 验收。
- 批量写入单批最多 200 条；连续写同一表时串行执行，遇到 1254291 按短暂等待后重试处理。
- +record-batch-update 是“同值批量更新”：同一份 patch 应用到全部 record_id_list，不要拿它做逐行不同值映射。
- select/multiselect 写入未知选项可能触发平台新增选项；不是要新增时，先用 +field-list 或 +field-search-options 确认可选值。
- 搭建型任务（做系统/管理工具/后台/看板）建完表结构后默认用 +record-batch-create 造 5\~10 条示例数据，不交付空表；用户明确只要空表/模板时才跳过。写入前必须阅读 [Mock 数据严谨性指南](references/lark-base-mock-data-guide.md)，让数据贴合字段语义并满足跨字段、跨记录和当前日期下的业务一致性；不要使用 null/空串/"示例1"占位，只写存储字段，单选/多选先用 +field-list 确认已有选项。
- 用户明确指定演示 / mock / 测试记录条数时，必须严格按指定数量写入；写入后读回记录数验收，不要按默认 5\~10 条、批次数量或自认为更丰富的数量扩展。
- 用户说“记个账 / 做个账本 / 台账 / 清单 / 库 / 系统”但未提供真实业务明细时，默认目标是搭建可长期维护的结构化工具，并按上条补充示例数据；只有用户明确要录入某一笔真实数据时，才停下来追问该笔明细。

## 表单与视图细节

- `+form-create` 后先 `+form-questions-list`；已有表字段可能已成为题目，优先 update 现有题目，只 create 真实缺失项。`+form-questions-delete` 会删除承载字段。
- `questions[].title` 既是用户可见的题目文本，也是 `+form-submit` 使用的字段键，不是可随意排版的标签。除非用户明确要求改名或编号，不得为了排序、排版、美化或阅读性给题目标题添加数字序号、必填标记、括号说明或其他前后缀。
- 更新既有题目的必填、描述、显隐或选项展示时，未获用户明确要求时，`+form-questions-update` 必须将从 `+form-questions-list` 读回的 `title` 原样带回；写后再次 `+form-questions-list`，逐项比较更新前后的 `id` 与 `title`。任一未授权标题变化都必须恢复原值并回读，不得把它当成问卷优化继续提交或交付。
- `form_id` 只用于管理命令；对外提交必须使用真实 `share_token`，不能从 Base、table 或 form ID 拼接分享链接。
- +form-submit 前必须先跑 +form-detail，读取 questions[].type、required、filter 和附件场景需要的 base_token；不要填写被 filter 隐藏的问题。
- 表单附件不要写进 fields，放在 --json.attachments；提交附件时必须同时传表单所属 Base 的 --base-token。
- 表单、问卷、收集系统也属于搭建型任务。创建表结构和表单后，默认要按 [Mock 数据严谨性指南](references/lark-base-mock-data-guide.md) 完成创建阶段检查点：补 5\~10 条可验证 Mock 数据；工具链支持真实提交时至少 1 条必须经 `+form-detail -> +form-submit` 写入并回读，其余记录可批量写入。即使同一请求后续删除表单，也必须先完成此检查点，且最终再次回读确认保留的数据表非空；只创建空表单、空主表或只直接写底表却声称表单可用都不符合交付要求，除非用户明确只要空模板。
- `+form-questions-create` 有两种形态：新建字段题目传 `title` + `type`；复用已有字段题目传 `use_existing_field:true` + `field_id`。两种形态都只支持表单允许的 7 种字段类型，复用已有字段不能绕过类型限制；完整支持与不支持列表见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md)。复用字段只把已有字段加入表单，不创建字段，也不改变已有记录数据；不要携带 `type`、`style`、`options` 等字段定义属性。
- 创建题目前先执行 `+form-questions-list`。目标标题已存在时，除非用户明确要求同名独立问题，否则使用 `+form-questions-update` 修改，不要先创建同名问题再删除旧问题。
- 表里有该字段不等于表单能收到该信息：表单只收集自己题目列表里的项。用户枚举了要收集的信息项时，把每一项与 `+form-questions-list` 的回读结果逐项配对，缺一项就补一项；该信息已经是表内字段时用 `+form-questions-create --questions '[{"use_existing_field":true,"field_id":"<field_id>"}]'` 加进表单，不要因为字段已存在就当作已完成。
- “删除/移除表单题目、问题、问卷项”只授权修改表单，默认使用 `--keep-field` 保留底层 Field 及历史值；只有用户明确要求同时删除底层字段/整列及其数据时才允许省略 `--keep-field`。操作前后分别用 `+form-questions-list`、`+field-list` 和必要的 `+record-list` 核对；详细删除语义决策表见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md)。
- 管理表单分享使用 `+form-share-get` / `+form-share-update` 管理启停、访问范围和匿名/登录要求；对应字段为 `enabled`、`access_scope`、`allow_anonymous`、`require_login`。更新前先读取现状，每次只修改一个字段，布尔值显式传 `true` 或 `false`。
- 用户说“填写入口、发链接、别人自己填、同事提交、在线填写”时，交付物是**可访问的表单入口**，不得仅创建 form 就结束。创建题目后直接执行 `+form-share-get`；若 `enabled=false`，先用 `+form-share-update` 开启，外部或无需登录填写还要逐项设置 `access_scope=anyone`、`allow_anonymous=true`、`require_login=false`，再回读。只有 `enabled=true` 且 `share_url 非空` 才能标记 verified；否则必须继续修复或明确报告 blocked，不得声称“可在前端获取/可直接分享”。若父级 `base --help` 未列出分享命令，先运行精确的 `lark-cli base +form-share-get --help` / `+form-share-update --help`，不能据父级帮助或旧记忆判断能力不支持。
- view 的每类配置都有独立子命令：filter、sort、group、visible-fields、card、timebar 各自有 `+view-set-*` 与 `+view-get-*`。只有 filter 保留了 reference，其余没有 reference 不代表能力不存在——直接读对应子命令的 `--help` 获取 JSON 形状，不要绕道 raw API、改用替代产物或只在答复里描述。修改已有配置先用对应 get 读现状，保留未修改字段，只替换用户要求变更的配置。
- 视图适合持久化、共享和 UI 复用；一次性筛选/排序可先用 +record-list / +record-search 的 filter/sort 验证结果，再按需要沉淀为持久视图。
- 视图名称不能冒充配置。创建或重命名前先做视图名称拆解，把名称中的对象类型、筛选集合、分组字段、排序和时间范围分别写成验收项；新建 kanban、gallery、calendar、gantt 等视图时平台给出的默认分组或展示字段只是平台兜底，不是用户要求的维度，必须显式设置目标配置。写入后按项调用 `+view-get-filter/group/sort/card/timebar/visible-fields`，再用 `+record-list --view-id` 检查代表性命中项与排除项。任一名称承诺与保存配置或实际记录不一致时，修正配置或改成真实名称后再交付，详见 [lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)。
- 将自然语言目标转成筛选或分析条件前，必须读取完整候选值域并逐项标记 `Include / Exclude / Unknown`：只有字段证据能直接证明不满足目标的值才可 `Exclude`，`Unknown` 必须保留并分组展示或先向用户澄清；阶段、局部或相邻语义字段不能证明最终业务状态。写入后按各子类数量核对命中项与排除项，详见 [Base 数据表查询与分析 SOP](references/lark-base-data-analysis-sop.md)。
- 用户要“未完成 / 未归还 / 待处理 / 逾期”等状态视图时，优先用原始结构字段表达条件（如实际归还时间为空、处理状态不为已完成），不要只基于自造展示文案做 contains 筛选。若只能筛公式文案，必须枚举所有目标状态并读回视图记录验证。
- 长期复用视图中的相对时间条件（本月、今年、超过 N 天/月、近 N 天/月）禁止硬编码当前日期。优先使用平台相对日期关键字、辅助公式字段或动态判断字段；无法动态表达时必须说明限制，不要把固定日期视图包装成持续可用能力。

## Dashboard / Workflow / Role

- Dashboard 的复杂点是 block 的 data_config，不是 list/get/create/delete 命令参数。创建或更新 block 前先读 [dashboard-block-data-config.md](references/dashboard-block-data-config.md)，组件必须串行创建；+dashboard-arrange 是服务端智能布局，只在用户明确要求重排/美化时执行。+dashboard-block-get-data 读取图表最终计算结果，不返回 block 名称、类型、布局或 data_config；需要元数据先用 +dashboard-block-get。
- Base 场景中用户要求“图 / 图表 / 看板 / 直观看到 / 可视化”时，默认优先创建 Base Dashboard 组件并沉淀在 Base 中；外部图片或一次性文本统计只能作为补充，不能替代 Base 内可持续更新的图表。交付前用 `+dashboard-block-list` 确认组件存在，关键图表用 `+dashboard-block-get-data` 验证可计算。
- 管理 Dashboard 分享使用 `+dashboard-share-get` / `+dashboard-share-update` 管理启停、访问范围和返回源 Base 入口；对应字段为 `enabled`、`access_scope`、`show_source`。更新前先读取现状，每次只修改一个字段，显式 `false` 必须保留。
- Workflow 的复杂点是 steps 结构和生效状态。执行任何 Workflow 写任务前完整读取 [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md) 和 steps JSON SSOT [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)；新建 workflow 默认 disabled，必须先预检完整定义，再按题意解析目标运行态、执行 enable/disable 并回查，不能把“创建成功”当作“已生效”。list/get/enable/disable 只处理已确认的 workflow ID、当前状态和用户意图。
- 只有用户明确要求自动化或修改现有 workflow 时，才创建、更新或启用 workflow；字段、公式、视图或 dashboard 需求本身不授权启用自动化。
- 用户说“一按 / 一键 / 点一下就知道 / 按钮触发”时，优先评估 button 字段 + ButtonTrigger workflow，或在表中创建明确的结果字段 / 视图承载一键判断结果；不要只用静态说明、普通仪表盘或手动筛选替代交互诉求。
- Role 的复杂点是权限 JSON。角色操作先读入口 [lark-base-role-guide.md](references/lark-base-role-guide.md)；构造或修改权限 JSON 时读 [lark-base-permission-rules.md](references/lark-base-permission-rules.md)；+role-create 只支持自定义角色；+role-update 是 delta merge；角色 create/update 或解读完整配置时读权限 JSON SSOT [role-config.md](references/role-config.md)。+role-delete 只适用于自定义角色，系统角色不可删除；删除角色和关闭高级权限前必须确认目标和影响。

## 常见恢复

| 错误 / 现象 | 恢复动作 |
|-|-|
| param baseToken is invalid / base_token invalid | 检查是否把 wiki token、workspace token 或完整 URL 当成了 --base-token；按入口规则重新获取真实 base_token |
| not found 且输入来自 Wiki 链接 | 优先检查是否把 wiki token 当成 base token，不要立刻改走裸 API |
| +base-block-list missing_scope(base:block:read) | 纯表/记录读取改走 +table-list，再继续 +record-list / +record-search / +data-query；不要为非必要目录探测中断任务 |
| 文档工具打开 `/base/` 链接报无权限或需授权 | 不要直接终止或请求用户授权；先切回 `lark-cli base +url-resolve --url "<url>" --as user`，再 `+table-list` 定位数据表 |
| 1254045 字段名不存在 | 重新 +field-list，使用真实字段名或字段 ID；注意空格、大小写和跨表字段 |
| 1254015 字段值类型不匹配 | 先 +field-list，再按 [lark-base-cell-value.md](references/lark-base-cell-value.md) 构造 CellValue |
| 日期 / 人员 / 超链接字段报格式错误 | 日期用 YYYY-MM-DD HH:mm:ss；人员用 [{ "id": "ou_xxx" }]；超链接用 URL 或 markdown link 字符串 |
| formula / lookup 创建失败 | 先读 [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)，再按 guide 重建请求 |
| ignored_fields / READONLY | 移除只读字段，只写存储字段 |
| 1254104 | 批量超过 200，分批调用 |
| 1254291 | 并发写冲突，串行写入并在批次间短暂等待 |
| 91403 | 无权限访问该 Base，按 lark-shared 权限流程处理，不要盲目重试 |

## 保留 Reference

- [lark-base-solution-design.md](references/lark-base-solution-design.md)：模糊需求（只给目的）搭系统/台账/收集/分析时的方案设计入口——Base 能力清单与选用场景、交付清单、表设计原则、丰富度等指引
- [lark-base-data-analysis-sop.md](references/lark-base-data-analysis-sop.md)：查询/统计/全局结论的选路 SOP
- [lark-base-data-query-guide.md](references/lark-base-data-query-guide.md) / [lark-base-data-query.md](references/lark-base-data-query.md)：聚合查询入口 fewshot 与 DSL SSOT
- [lark-base-cell-value.md](references/lark-base-cell-value.md)：记录 CellValue 构造
- [lark-base-field-json.md](references/lark-base-field-json.md)：字段 JSON 构造
- [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)：公式与 lookup 字段
- [lark-base-field-create.md](references/lark-base-field-create.md) / [lark-base-field-update.md](references/lark-base-field-update.md)：字段创建/更新命令级补充
- [lark-base-record-upsert.md](references/lark-base-record-upsert.md) / [lark-base-record-batch-create.md](references/lark-base-record-batch-create.md) / [lark-base-record-batch-update.md](references/lark-base-record-batch-update.md) / [lark-base-record-history-list.md](references/lark-base-record-history-list.md)：记录写入 JSON 与历史返回解释
- [lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)：视图筛选 JSON
- [lark-base-form-detail.md](references/lark-base-form-detail.md) / [lark-base-form-submit.md](references/lark-base-form-submit.md) / [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) / [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md)：表单详情、提交和复杂 JSON
- [lark-base-template-center.md](references/lark-base-template-center.md)：公开模板中心分类、列表、搜索与基于模板复制 Base 的流程
- [lark-base-dashboard.md](references/lark-base-dashboard.md) / [dashboard-block-data-config.md](references/dashboard-block-data-config.md) / [lark-base-dashboard-block-get-data.md](references/lark-base-dashboard-block-get-data.md)：仪表盘、组件配置与图表结果协议
- [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md) / [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)：workflow 入口与 steps JSON SSOT
- [lark-base-role-guide.md](references/lark-base-role-guide.md) / [lark-base-permission-rules.md](references/lark-base-permission-rules.md) / [role-config.md](references/role-config.md)：角色入口与权限 JSON SSOT

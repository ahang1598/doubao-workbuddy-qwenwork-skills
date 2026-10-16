---
name: lark-base
version: 1.5.1
description: 多维表格：可视化表格数据库与业务系统，可搭建台账/进度/项目/订单/客户/排班等业务场景，具备多表联动、多视图、表单问卷、仪表盘、自动化工作流、行列权限；遇到 /record/ 记录分享链接时使用
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli base --help"
---

# base

## 使用边界

- Base 业务操作使用 lark-cli base +... shortcut；仅仪表盘权限统计开关、全局筛选和按钮绑定尚无类型化命令时，允许按各自 reference 的已知路径使用 `lark-cli api`。不使用旧聚合式 +table / +field / +record / +view / +history / +workspace。
- 本轮 Base 不依赖 lark-cli schema。SKILL 只保留路由、风险和复杂 JSON/DSL；简单命令由命令自身的参数、tips 和错误恢复承接。
- 用户要把 Excel / CSV / .base 导入成 Base 时，先转 lark-cli drive +import --type bitable，导入完成后再回到 Base 命令。
- 认证、初始化、scope、身份切换、权限不足恢复属于 lark-shared；Base 文档只保留会影响 Base 路径选择的权限规则。
- 一律不使用应用模式（app mode / BaseApp）：即使 lark-cli base 的帮助或参数中出现 +app-create、+app-get、+app-page-\*（create/delete/get/list/update）、+app-block-\*（create/get/get-data/list/update）等应用模式命令，也不要调用；所有搭建、查询与数据操作只走经典 Base shortcut（+base-create / +base-copy / +table-\* / +field-\* / +record-\* / +view-\* / +dashboard-\* / +form-\* / +workflow-\* / +role-\* 等）。

## 先获取 Base Token 和所需 ID

进入任何需要目标 Base 的 shortcut 前，必须先拿到可用的 base_token，以及当前任务需要的 table_id / view_id / record_id / form_id / dashboard_id / workflow_id 等真实 ID；不要把完整 URL、wiki token、workspace token 或孤立 raw token 直接当作 --base-token。

- 用户输入 URL 或分享链接：先运行 lark-cli base +url-resolve --url "<url>" --as user，用返回的 base_token 和相关 ID 继续后续命令。
- URL 路径包含 `/base/` 或明确是多维表格分享链接时，先用 lark-cli base `+url-resolve`，再按下文任务路由继续；普通结构读取走 `+table-list`，独立分析问答走 `+schema-context-get`，不要用文档类工具打开。
- 用户输入 Base 标题、关键词或不确定名称：先运行 lark-cli base +title-resolve --title "<keyword>" --as user；--title 传入标题中的短关键词，不超过 30 个字符；过长标题先取最有区分度的短关键词；多候选时先让用户消歧，不要猜。
- 用户要求列出已有 Base 候选，且需要按最近访问、owner、创建人、时间或类型筛选/排序：转 `lark-cli drive +search --doc-types bitable --as user`。最近访问使用 `lark-cli drive +search --doc-types bitable --sort open_time --opened-since 3m --page-size 20 --as user`；只列我拥有的加 `--mine`，只列我创建的加 `--created-by-me`。从候选项拿到 URL 或 token 后，再用 `+url-resolve` 或 `+base-get` 进入 Base 业务命令。
- 文档嵌入 Base 标签：直接读取 <bitable> / <base_refer> 的 token 作为 --base-token，table-id 作为 --table-id，view-id 作为 --view-id；孤立 raw token 不走 +url-resolve。
- 仍无法定位且用户不是要新建 Base 时，先反问用户要操作哪一个 Base；用户要新建时才用 +base-create。
- `+url-resolve` 成功后，后续命令的 `base_token` / `table_id` / `view_id` 必须逐字使用本次返回值，不要手抄、缩写、从上下文记忆改写或混用旧轮次坐标。若后续 shortcut 返回 `NOTEXIST` / `base_token invalid`，先逐字比对本次命令参数和最近一次可信 `+url-resolve` 返回，再判断权限、资源删除或平台异常。

## 写任务完成协议

任何创建、修改、删除、启停、提交或权限配置任务，开始写入前必须从用户原话拆出原子验收项，并在内部记录 `requirement`、目标对象、预期状态、回读命令和通过条件。多对象、多步骤任务逐项维护 `pending -> written -> verified`：写命令成功只能进入 `written`，只有服务端回读满足通过条件才能进入 `verified`。写成功不等于完成。

- 涉及群组的自动化操作时，先读 [APIHub 集成节点](references/lark-base-workflow-apihub.md)，核对支持的动作、参数类型和资源引用。
- **位置和口径是两个独立的验收项。** 用户指定了交付物该落在哪个对象上时，先回读确认它确实在那个对象上，再确认数值正确。你认为放在别处更合理**不构成替换授权**：要么两处都落，要么落在用户指定的位置并在答复里说明理由。口径对而位置错，该项判未完成。
- **复制粒度：** 复制对象以用户明确宾语为准：“数据表 / 表 / 某张表”用 `+table-copy`，只有“整个 Base / 多维表格文件”或明确要求独立流转、隔离时才用 `+base-copy`；“给我一个副本”本身不改变对象层级。用户要求副本或备份且未明确只复制结构时，连数据一起复制并加 `--range all --wait`；不得用新 Base 冒充表副本。
- 只回读本轮创建、修改、删除、启停或明确复用的对象，以及因本次写入可能受影响的依赖或默认对象；已有可信返回 ID 时直接读取，不为验收扫描无关资源。
- 最终答复前逐项核对清单。全部显式要求必须为 `verified`，或如实标记 `blocked` 并说明缺失证据；存在 `pending` / `written` 时不得宣称全部完成。
- 多步骤或连续修改按用户顺序执行，每一步写后立即回读并通过该时点的后置条件，才能进入下一步。请求同时包含创建和后续查询、修改或删除时，必须先将创建阶段验收为 `verified`：结构正确、所需分享或测试提交可用、Mock 数量与业务关系通过 `+record-list` 回读；未通过前不得进入下一步。全部步骤结束后再次回读最终保留的数据表，除非用户明确要求清空，否则为空即不得交付。后续删除、关闭或覆盖对象不能替代前一步验收，也不能掩盖前一步错误。
- **本轮新建了数据表，就把「表里有记录」加进验收清单**，通过条件见验收矩阵「本轮新建表的记录」行。
- **本轮新建了 Base，就把「交付类别覆盖」加进验收清单**，通过条件见验收矩阵「本轮新建 Base 的交付类别」行。这一项不来自用户原话，用户没提也要自己加进去。
- 用户在搭建或修改 Base 的同一请求中要求按字段分组、排序、排名、汇总或“最后这样看”时，该展示结构本身是交付物：必须创建并回读持久 View、Dashboard 或汇总表。分析查询和最终答复里的表格只能用于计算与验证，查询输出不能替代持久产物；只有纯查询且未要求改造 Base 时才可只返回分析结果。
- Base 任务默认在目标 Base 内闭环：提醒、通知、自动执行或状态联动必须优先落为目标 Base 内的 Workflow。涉及需要接收人的动作时，创建前从用户原话单独登记接收人：用户明确指定当前操作用户为接收人时，使用当前用户身份；具体人或群解析为该对象，业务职责类接收人绑定触发记录或 `FindRecordAction + Loop` 中承载该职责的真实人员字段；三者不得相互替代；职责类接收人在本表没有对应人员字段时，按 workflow-guide 的门禁新建人员字段并绑定。图表、看板或持续可视化必须优先落为 Base Dashboard。豆包定时任务、会话内临时图表及其他模块不能冒充 Base 交付物；Base 工具能力不足时，必须如实说明未完成或受阻，才允许跨模块降级。纯查询或未要求沉淀的一次性分析仍可直接在会话中回答。
- 时间范围必须进入聚合源头。题面或本轮新增对象出现锚定运行当天、随时间推移而变化的动态/相对时间语义（本周、上周、本月、今年、本年度、年度、年底、近/超过 N 天或月、未来/接下来 N 天或月等）时，逐个检查 Formula、View、Dashboard、汇总表和最终回答：参与 `SUM` / `AVERAGE` / `COUNT` / 排名的记录集合必须先按真实业务日期做等价动态过滤；全历史聚合后只把字段、视图或组件命名为“本周/年度/本月”不得交付，样例数据恰好都在同一时间范围也不能作为通过证据。
- 含条件的 Workflow 必须 fail-closed：创建或更新后先保持 `disabled`，用 `+workflow-get` 将用户要求的每个条件逐项对照服务端保存的 `field_name / operator / value / value_type`；必需右值为空、类型错误或边界缺失时保持或恢复 `disabled`。定向修复一次仍不能正确回读时，改用可验证的文本/布尔派生字段表达同一业务谓词；仍失败时只将该 Workflow 验收项标记 `blocked`，继续完成并交付不依赖它的表、数据、视图、表单和 Dashboard，不得启用该 Workflow 或声称自动化已生效。
- **系统角色**（Owner、Admin、Editor、Reader）保持平台默认，不修改、不收窄、不在答复里声称做了限制；只有用户用平台角色名点名时才按字面处理。
- **平台生成的「普通用户」**（`+advperm-enable` 时自动创建的 `custom_role`，默认全表可编辑、可复制下载）不得保留：一律 `+role-delete` 删除，再按题面出现的角色词逐个 `+role-create` 从 `no_perm` 新建并授权。
- **业务角色**按题面角色词创建；题面的排他表述既是对被点名角色的授权，也是对其他自定义角色的禁止。收尾 `+role-list` 回读：不得再有「普通用户」，题面点名的角色一个都不能少。
- 仅当句子同时包含可解析的权限主体、权限能力和资源范围，或明确要求高级权限/角色配置时，才启动权限流程；Workflow 的“只要……就……”以及普通字段、表单、视图操作中的“只/仅/所有”不得触发。每个权限步骤先生成“主体 × 资源 × 能力 × 排除主体”约束；角色轴、记录轴和字段轴可以同时命中，不得二选一。新建角色从 `no_perm` 构造，既有角色只修改违反本轮约束的能力。
- 配置权限时，结合用户对同一角色、同一数据对象的全部要求判断：授予整个数据对象的管理职责，且没有更具体的操作或范围限制时，表级使用 `manage`；有具体操作或字段、记录范围限制时，按权限规则确定权限等级并保留限制。配置后用 `+role-get` 回读核对；实际权限与要求不一致，包括应为 `manage` 却配置成 `edit`，或遗漏字段、记录限制，都不能标记为 `verified`。
- 新建角色被授权“填写/录入记录”，同时仅点名部分字段可继续修改时：`record_operations` 只加入 `add`；创建记录所需的可写业务字段只在新增记录时可写，设为 `create`，点名可修改字段设为 `edit`，系统字段和不可写派生字段保持只读；必须使用 `field_perm_mode=specify`，不得退化为 `all_edit`，未明确授权时不得加入 `delete`。权限字段先映射到真实 `+field-list` 结果；无法可靠唯一映射时先澄清，不能用 `all_edit` 兜底。
- 给角色授予某表可编辑时，题面没有禁止的能力（新增、删除、视图管理）保持默认，收窄只针对题面点名要禁止的那一项。
- 每个编号权限步骤写后都必须 `+role-list` 并对本轮创建或修改的业务角色逐个 `+role-get`，将实际 `perm / record_operations / field_perms / record_rule / copy / download` 与约束逐行断言，只定向修复违反约束的角色和能力。明确敏感、保密或隐私的表在同一权限任务中列出允许访问角色时，这些角色构成访问白名单，未列角色对该表必须为 `no_perm` 且禁止复制下载；行级隔离则要求所有可能访问数据的默认/自定义角色采用同一有效隔离或无权限。任一约束未通过不得进入下一权限阶段，后续扩权、删角色或关闭高级权限不能覆盖前一阶段错误。完整流程见 [lark-base-role-guide.md](references/lark-base-role-guide.md)。
- 相对时间词是持久配置的数据范围，不是名称装饰。判据看时间范围是否锚定运行当天、会随时间推移而变化（动态 / 相对时间范围）：本周、上周、本月、今年、年度、年底、近/超过 N 天或月、未来/接下来 N 天或月、即将到期等都属此类。出现这类语义时，最终答复前检查本轮 Formula、View、Dashboard 和 Workflow 的保存后配置；除非用户明确要求固定历史区间，否则不得把运行当天换算成固定 `ExactDate` / 年月边界，所有相关对象必须使用一致的动态范围。
- 回读不一致时，只针对失败项做一次定向修复并复验；仍不满足则报告未完成项，不得用写接口的成功响应、资源名称或最终说明文字推断成功。

## 写任务验收矩阵

| 交付物 | 必须回读 | 通过条件 |
|-|-|-|
| Base / Table / Field | `+table-list`、`+field-list` | 表、字段、关联正确 |
| **本轮新建表的记录** | 逐表 `+record-list` | **硬条件**：本轮执行过 `+base-create` / `+table-create` 的**每一张**业务数据表，`record_count` 都必须**不少于 5 条，一般写 5~10 条**，除非用户明确要求表为空 —— **用户没说就是没要求，不要自己替用户判断这张表该不该是空的**。用户给了数据就写用户的，没给就补 mock；示例数据是交付物的一部分，让用户看到数据填进来之后是什么样。不是本轮新建的表不涉及 mock 数据。写 mock 前必读 [Mock 数据严谨性指南](references/lark-base-mock-data-guide.md)，按其中的业务不变量造数并逐条自查。**最终答复的验收摘要必须逐张列出本轮新建表的 `record_count` 实测值，并标注是否达到 5 条**；本轮新建表中有任何一张不足，补齐后再交付。Mock 记录须全部回读并逐字段核对跨字段一致性，不得只抽查一行。**互相约束的字段不要各自随机，先定源字段再推派生值**：结论类字段（合格与否、是否通过、状态）由同行明细推出，区间字段先定下限再定上限，关联字段的对端记录要和本行描述指同一件事；以执行当天为基准，状态表示事情已经发生完的记录其对应日期不得晚于当天；成对时间字段的先后要对（结束不早于开始、审批不早于提交）；人名文本与人员字段指向同一人。补 mock 时，每条记录除「群组、附件、超链接、地理位置、条码、签字」六类字段外都要有值，留空即为未完成；**人员字段用当前用户填充即可，但不得留空**。 |
| 复制表 / 文件 | 复制表时在原 `base_token` 下回读源表和副本表的结构与记录 | 确认源表与副本表的 `table_id` 不同并对账字段与记录；复制文件才验收新 Base |
| Formula / Lookup | `+field-get` + 有界样例 `+record-list` | 保存表达式正确，已有代表性数据的分支计算正确 |
| View | 对应 `+view-get-*` + `+record-list --view-id` | 视图名称、实际设置和展示结果必须一致。**硬条件**：把用户原话与视图名、Dashboard 组件名三者里的限定词（时间范围、状态、分组维度、排序口径）取并集逐个摘出来，名称里没写但用户原话里要求了的同样要落到配置里，在回读到的 `filter` / `group` / `sort` / `group_by` 里找到对应配置；回读结果为 `null` 或空即为未实现，当前记录恰好都符合不算。搭建任务全部写入结束后，先对本轮新建的每张数据表执行 `+view-list`，枚举其全部视图；对本轮主动创建、重命名或明确作为交付物的视图，逐个执行 `+view-get-filter`、`+view-get-group`、`+view-get-sort`，并用 `+record-list --view-id` 验证结果。筛选集合、分组维度、排序口径和动态时间范围必须由对应配置兑现。 |
| Form 创建 / 分享 | `+form-get`、`+form-questions-list`；核验题序时加 `+view-get-visible-fields`；要求链接/扫码/外部填写时加 `+form-share-get`；新建可填写表单时做测试提交和记录回读 | 题目、必填、题序和所需分享范围正确；题序须按 [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md) 的「调整题目顺序」一节回读核验，不能只看写命令的返回；要求限制填写范围时，`+form-questions-list` 回读的 `input_range_limit` 必须与要求逐项一致；题面给出名额、提交次数或截止 / 起止时间时，`+form-submission-settings-get` 回读的对应配置必须已开启且与要求一致；未明确要求改名或编号的题目，写后同一 `id` 的 `title` 必须与更新前一致；新建可填写表单且未要求空模板时，只创建 Form、只返回链接或空主表不算完成。为新建的空表建表单时，题目集合还要与用户列举的收集项相等；给已有业务数据的表建表单时，`+form-create` 从原有字段自动带出的题目只要不影响列举项命中就保留，不得为对齐题目集合删除这些字段或其记录 |
| Dashboard | `+dashboard-block-get`；图表加 `+dashboard-block-get-data`，视图组件按引用加对应 `+view-get-*` 和 `+record-list --view-id`，其他组件按专属指南回读配置 | 该组件适用的数据源、维度、指标、范围、配置及结果正确；联动保存结果与点击效果分别验收；指标展示格式符合业务单位；本轮新建或调整布局时，必须确认布局符合用户要求及适用的[布局规则](references/lark-base-dashboard.md#交付健康门禁写任务必做) |
| Workflow | `+workflow-get` + 必要的 `+workflow-list --status ...`；可表达且有代表性数据时加等价条件查询 | 触发时机、条件、接收人、动作、引用和最终运行态全部正确 |
| Role / AdvPerm | `+base-get`、`+role-list`；对本轮创建 / 修改的业务角色逐个 `+role-get` | 目标授权准确；读写范围分别成立；未授权自定义角色不能访问、增删、复制或下载敏感数据。**硬条件**：本轮执行过 `+advperm-enable` 时，回读的 `+role-list` 里不得再有「普通用户」，且题面点名的角色词逐个能在角色集合里找到 |
| Analysis | 确定性查询结果；要求持久产物时加对应产物回读 | 查询结果和最终回答使用同一口径；存在产物时还须与产物实际数据一致 |
| **本轮新建 Base 的交付类别** | 逐表 `+view-list`；按本轮已建模块 `+dashboard-block-list` / `+form-list` / `+workflow-list` / `+role-list` | **硬条件**：本轮诞生了一个新 Base（`+base-create`、导入生成、或从模板 `+base-copy`）时，交付物必须覆盖**至少 3 类**页面级模块/视图。计类口径：数据表无论几张**合计 1 类**；非表格视图按实际 `type` **每种各计 1 类**（`kanban` / `gallery` / `calendar` / `gantt`）；仪表盘、表单、工作流、高级权限各计 1 类。`grid` 视图无论怎么配筛选 / 排序 / 分组 / 字段显隐 / 改名都**不计类**，表单视图并入表单不另计。**这条无条件生效**，用户把表名和字段点明了也一样。不够 3 类就从非表格视图和仪表盘里补：现有字段支撑就直接建，字段不够就补一个该业务本就该有的字段（如分类、状态、日期）再建；多建一张业务表不会多一类，空壳也不计。**最终答复必须列出本轮实际交付的模块与视图，视图逐个写出 `type`**。选型判据与补法见 [Base 系统搭建指引](references/lark-base-solution-design.md)。|

### Base 模板中心

模板中心是公开的 Base 模板库，不是用户云空间里的已有 Base。用户想用现成模板创建新 Base，且没有指向已有对象的锚点（没有 Base URL、没有“我的/最近访问的表”、没有具体已存在的 Base 名）时，先读 [lark-base-template-center.md](references/lark-base-template-center.md)：`+template-categories` 列出公开模板分类，`+template-list` 按分类列出模板，`+template-search` 按业务关键词搜索模板；选定后用 `+base-copy` 复制为用户自己的 Base。

## 快速路由

| 用户目标 | 优先命令 | 权限/边界 | 何时读 reference |
|-|-|-|-|
| 查 Base 本体 | +base-get | 读取 Base 本体信息 | 用返回确认 Base 名称、owner、权限和可继续操作的 token。使用该工具注意保留引用信息。 |
| 更新 Base 设置 | +base-update | 更新 Base 级时区 | 读取 [lark-base-base-update.md](references/lark-base-base-update.md)；使用 IANA 时区，写入前可先 dry-run |
| 创建 Base / 复制整个多维表格文件 | +base-create / +base-copy | 得到一个独立的新 Base | 新建业务 Base 时必须用 --table-name + --fields 一次配置初始数据表；只有用户明确要求空白或平台默认 Base 时才省略，写入后报告新 Base 标识和 permission_grant。`+base-copy` 适用于副本要独立流转的场景：发给别人参考、单独分享、与原库隔离的沙箱、交接 |
| 复制一张数据表 | +table-copy | 副本作为新表留在当前 Base 内，与原表并列 | 适用于备份、练习、同库派生版本和保留原表对照；连数据一起复制加 `--range all --wait`。明确宾语是数据表时不得改用 `+base-copy`；只有明确复制整个 Base 或要求独立流转、隔离时才复制文件 |
| 浏览/搜索公开模板 | +template-categories / +template-list / +template-search | 公开模板库，不依赖目标 Base 权限 | 先读 [lark-base-template-center.md](references/lark-base-template-center.md)；模板中心不是用户云空间搜索，选中模板后用 +base-copy 创建 Base |
| 查看 Base 内资源目录 | +base-block-list | 需要 base:block:read；不是读取 table/record 的前置步骤 | 想先了解一个 Base 里有哪些 table/docx/dashboard/workflow/folder 时优先用它；返回 ID 关系和 fewshot 看 --help |
| 管理 Base 内资源目录 | +base-block-create/move/rename/delete | 管理 Base 直接挂载资源 | 创建或整理 Base 直接管理的 folder/table/docx/dashboard/workflow；资源内容继续用对应命令 |
| 管理数据表 | +table-list/get/create/update/delete | 读表列表用 base:table:read | 处理 table 的列出、详情、创建、重命名和删除 |
| 列/查/删字段 | +field-list/get/delete/search-options | 依赖目标表权限 | 写入前用 list/get 确认字段类型、选项、ID；删除前确认目标字段 |
| 创建/更新字段 | +field-create / +field-update | 修改表结构 | 必读 [lark-base-field-json.md](references/lark-base-field-json.md)；公式读 [formula-field-guide.md](references/formula-field-guide.md)；lookup 读 [lookup-field-guide.md](references/lookup-field-guide.md)；命令细节读 [lark-base-field-create.md](references/lark-base-field-create.md) / [lark-base-field-update.md](references/lark-base-field-update.md) |
| 通讯录字段补全 | +contact-field-enrichment-list / +contact-field-enrichment-create | 从人员或创建人字段生成只读派生列 | 必读 [lark-base-contact-field-enrichment.md](references/lark-base-contact-field-enrichment.md)；先用 +field-list 确认来源字段 |
| 读记录明细 | +record-get / +record-list / +record-search | 读记录用 base:record:read | 已知记录、关键词搜索、原始记录筛选/排序/TopN 沿用命令 tips；filter 形状不确定时读 [lark-base-filter-condition.md](references/lark-base-filter-condition.md)，无需 Context |
| 写记录 | +record-upsert / +record-batch-create / +record-batch-update | 写记录权限 | 必读 [lark-base-record-upsert.md](references/lark-base-record-upsert.md) / [lark-base-record-batch-create.md](references/lark-base-record-batch-create.md) / [lark-base-record-batch-update.md](references/lark-base-record-batch-update.md) 和 [lark-base-cell-value.md](references/lark-base-cell-value.md) |
| 附件字段 | +record-upload-attachment / +record-download-attachment / +record-remove-attachment | 附件专用能力 | 附件不要伪造成普通 CellValue；上传走本地文件，下载/删除按 file token 或字段定位 |
| 删除记录 / 分享记录链接 / 历史 | +record-delete / +record-share-link-create / +record-history-list | 删除、分享、历史能力 | 删除前确认 record；分享链接最多 100 条；历史读 [lark-base-record-history-list.md](references/lark-base-record-history-list.md)，只查单条记录，不做整表审计 |
| 管理视图 | +view-create/rename/delete；配置用 +view-set-filter / -sort / -group / -visible-fields / -card / -timebar 及对应 +view-get-\* | 依赖目标表权限 | `+view-create` 没有 `--name`，名称放进 `--json`（如 `{"name":"...","type":"grid"}`）；六类配置各有独立 set/get 子命令，只有 filter 有 reference（[lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)）；其余直接用该子命令的 `--help` 取 JSON 形状（如 `+view-set-group --help`），改已有配置先 get 现状再整体提交 |
| 独立分析问答（含简单单表统计） | +schema-context-get -> +data-sql-query | Context 需要 base:table:read；SQL 需要 base:record:read；默认只读 | 计数、求和、平均、分组、聚合 TopN、占比、趋势、多表分析统一读 [SQL 分析 SOP](references/lark-base-analysis-sql.md)，由其按阶段加载 Context / SQL 命令 reference；先用 Context 选表选字段、确认口径，再执行 SQL；搭建过程中的辅助计算仍按对象 reference |
| 公式字段 | +field-create/update --json '{"type":"formula",...}' | 字段结构变更 | 必读 [formula-field-guide.md](references/formula-field-guide.md)，读后再加隐藏确认 flag --i-have-read-guide |
| Lookup 字段 | +field-create/update --json '{"type":"lookup",...}' | 字段结构变更 | 必读 [lookup-field-guide.md](references/lookup-field-guide.md)，读后再加隐藏确认 flag --i-have-read-guide |
| 表单提交 | +form-submit | 表单提交能力 | 先读 [lark-base-form-detail.md](references/lark-base-form-detail.md) 获取题目、filter 和附件所需 base_token；提交 JSON 读 [lark-base-form-submit.md](references/lark-base-form-submit.md) |
| 表单题目创建/更新 | +form-questions-create / +form-questions-update | 表单结构变更 | 读 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) / [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md)；复用已有字段时传 `use_existing_field:true` + `field_id` |
| 表单提交与通知配置 | +form-submission-settings-get/update / +form-notifications-get/update / +form-submit-actions-get/update / +form-lottery-get/action | 表单提交限制、通知、结果页、跳转和抽奖配置 | 每组先 get 再更新；执行前读 [lark-base-form-config.md](references/lark-base-form-config.md) |
| 表单输入范围限制（限字数 / 限数值区间 / 限可选日期） | +form-questions-create / +form-questions-update 的 `--questions` 里带 `input_range_limit` | 表单结构变更，无需新命令 | 用户说“最多 N 字 / 只能填 0~100 / 只能选未来 7 天”时，把规则放进同一个 question 对象；三类结构、`anchor` 取值、相对日期换算和产品边界值必读 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) 的「`input_range_limit` 输入范围限制」，改已有题目再读 [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md) 的同名小节 |
| 表单题目排序 | +view-set-visible-fields（`--view-id` 传表单 ID） | 复用视图可见字段命令，无表单专用排序命令 | 用户要求调整题目顺序、把某题挪到前面/后面时读 [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md) 的「调整题目顺序」，取数、提交和回读都按那一节做 |
| 表单提交后回查（查询记录页） | +form-query-page-get / +form-query-page-create | 表单配置变更 | 用户说“提交后能查到自己填的 / 能改自己交过的内容 / 要个查询入口”时用这组；先 get 再 create；失败后按 reference 判断：报错 hint 里拿到 `query_view_id` 就带它恢复，不要重建，否则会留下半成品查询视图。流程与恢复字段读 [lark-base-form-query-page.md](references/lark-base-form-query-page.md) |
| 表单填写页布局（一页一题） | +form-display-settings-get / +form-display-settings-update --display-mode | 表单配置变更 | 用户说“一页一题 / 一次只显示一道题 / 改回一页显示全部”时用这组。`--display-mode` 只有 `traditional` 和 `one_question_per_page` 两个取值，**对外一律用字符串，不要透出 SDK 内部的数字枚举**；只改分页方式；主题色和背景当前 CLI 不支持，标题和描述用 +form-update。版本冲突处理读 [lark-base-form-display-settings.md](references/lark-base-form-display-settings.md) |
| 表单分享二维码 | +form-share-qrcode-get（看结构） / +form-share-qrcode-download（落盘 PNG） | 表单分享能力 | 用户要二维码图片时用这组，两者是同一个请求、只是出参形态不同。**前置要求分享已开启**；未开启时是直接开启还是先问用户，按该 reference 的「前置：分享必须已开启」一节判断；落盘校验与失败重试边界读 [lark-base-form-share-qrcode.md](references/lark-base-form-share-qrcode.md) |
| 其他表单管理 | +form-list/get/detail/create/update/delete / +form-questions-list/delete / +form-share-get/update | 表单管理能力 | +form-detail 读 [lark-base-form-detail.md](references/lark-base-form-detail.md)；删除题目默认连带删除底层字段，只移出表单时必须传 `--keep-field`；分享更新前先读取现状 |
| 仪表盘与组件 | +dashboard-\* / +dashboard-block-\* / +dashboard-share-get/update | 仪表盘与 block 能力 | 提到图表/看板/block 时先读 [lark-base-dashboard.md](references/lark-base-dashboard.md)；组件 data_config 读 [dashboard-block-data-config.md](references/dashboard-block-data-config.md)；读取图表计算结果用 +dashboard-block-get-data；分享更新前先读取现状 |
| 仪表盘全局筛选 | 已发布命令或已知 `global_filter` GET/PATCH | Dashboard 容器配置；完整数组替换 | 读 [全局筛选](references/lark-base-dashboard-global-filter.md)，清空传 `global_filters:[]`，写后 GET 核验 |
| 仪表盘跟随访问者权限统计 | 已发布命令或已知 `adv_perm` GET/PATCH | 独立于 Base 高级权限和角色访问权限 | 读 [权限统计开关](references/lark-base-dashboard-advperm.md)，显式保留 false，写后 GET 核验 |
| 仪表盘按钮工作流 | 已知 `button_rule` GET/PUT + `+workflow-get` | 按钮组件与表格按钮字段入口不同 | 读 [按钮绑定工作流](references/lark-base-dashboard-button-rule.md)；绑定、解绑、查询与启停分开处理 |
| 同源图表联动 | `+dashboard-block-update --linkage` | 完整目标列表替换，空数组清除 | 读 [图表联动](references/lark-base-dashboard-linkage.md)；先确认参数可用，Get 验收配置，点击效果按任务验证 |
| 仪表盘视图组件 | `+dashboard-block-create --type view` / update / get；记录用 `+record-list --view-id` | 筛选、分组、排序、可见字段四类配置与视图引用分别处理 | 读 [视图组件](references/lark-base-dashboard-view.md)；用真实 `tableId / viewId`，默认继承视图筛选、排序与可见字段 |
| Workflow / 自动化 / 提醒 / 定时 / 状态联动 | +workflow-\* | 工作流能力 | 用户要求提醒、到期前/后、自动通知，按固定周期（每天 / 每周 / 每月等）定期执行汇总、报表或推送，或状态变化后开放/暂停/回滚/生成记录等语义时，Workflow 是必交付项。**触发器按语义选**：用户给了周期才用 `TimerTrigger`，阈值到达用 `ChangeRecordTrigger`，到期 / 逾期用 `ReminderTrigger`，不得用定时扫描替代后两类；周期性任务同样在 Workflow 内闭环，不要改用 Base 外的模块；执行任何 Workflow 写任务前完整读取 [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md)，由该入口继续路由运行态、交付验收和 steps JSON SSOT [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)。条件右值是静默失败点：需求中的数值边界必须真正落进 `filter_info.conditions[].value` 且类型匹配，创建后 `+workflow-get` 回读确认，空值或类型不符即返工。`+workflow-get` 回读到的 `ref` 路径里只有 fieldId：要把配置讲给用户，或据此判断引用是否指向正确字段时，先对涉及的表执行一次 `+field-list` 建立 fieldId 到字段名的映射，再据此表述接收人、消息正文和条件分别取自哪个字段；不得按查找步骤的字段清单顺序、字段类型或语义相近推断，同一张表常有多个同类型人员字段，猜错了输出依然通顺且不会报错 |
| 高级权限与角色 | +advperm-\* / +role-\* | 高级权限能力 | 角色操作先读入口 [lark-base-role-guide.md](references/lark-base-role-guide.md)；构造或修改权限 JSON 时读 [lark-base-permission-rules.md](references/lark-base-permission-rules.md)；角色 create/update 或解读完整配置再读权限 JSON SSOT [role-config.md](references/role-config.md)；系统角色不可删除；关闭高级权限会影响自定义角色 |

**本轮会诞生一个新 Base 时一律必读** [Base 系统搭建指引](references/lark-base-solution-design.md)（`+base-create`、导入生成、或从模板 `+base-copy`），哪怕用户已把表名和字段点明；在已有 Base 上需要同时搭建多张表、字段、视图、仪表盘、自动化、角色权限时同样必读。**新建 Base 同时记住交付下限：至少 3 类页面级模块/视图**——数据表无论几张合计 1 类，`grid` 视图配了筛选/排序/分组/改名也不计类，另外两类必须从 `kanban` / `gallery` / `calendar` / `gantt` 视图和仪表盘里补齐。写第一条命令前就把计划产物点成类别数，不够 3 类先把方案补够再动手；完整口径与验收见验收矩阵「本轮新建 Base 的交付类别」行，选型判据见该指引。仅分析已有数据不触发系统搭建；混合任务分别完成分析和用户明确要求的持久产物。

## Base 心智模型

- Base 曾用名 Bitable；返回字段、错误或旧文档里的 bitable 多为历史兼容，不代表应改走裸 API 或另一套命令。
- `+base-create` 新建独立 Base，`+base-copy` 复制整个 Base，`+table-copy` 在原 Base 内复制数据表并生成新的 `table_id`。除非用户明确要求改造副本，不要把两个交付物合并或修改复制件；验收表副本时回读原 Base，Base 名正确不能证明表副本存在。
- `+base-update` 只更新已有 Base 的 Base 级时区；同值更新无需先比较或跳过，使用 IANA 时区并以成功响应中的 `base.revision` / `base.time_zone` 验收。
- +base-block-list 是查看一个 Base 内资源目录的新入口：它列出这个 Base 直接管理的 folder/table/docx/dashboard/workflow，适合先判断 Base 里有什么，再决定走 table、dashboard、workflow 或 docx 命令。
- base-block 只负责资源目录管理，包括创建资源、移动到 folder、重命名和删除；具体资源内容仍走 table/dashboard/workflow 命令。
- 新建业务 Base 时必须一次执行 lark-cli base +base-create --name "<base>" --table-name "<table>" --fields '<field-json-array>'，同时配置初始数据表的 name 和 schema；数组第一项会成为不可删除的主字段，因此直接放业务主字段。使用 --fields 前先读 [lark-base-field-json.md](references/lark-base-field-json.md) 或复用 +field-create 的字段 JSON 形状，不要猜字段属性。
- 上一条的例外只在两个条件**同时成立**时生效：本轮确实要为这张新表创建表单，且这张表只用来承接表单提交结果、没有表单之外的业务用途。此时 `--fields` 只放 `auto_number`（序号，作主字段）、`created_by`（提交人）、`created_at`（提交时间）这三个系统字段，用户要收集的字段一个都不要预先建进表，全部留给 `+form-questions-create`；这三类都不在表单可用类型内，`+form-create` 不会把它们变成题目，交付形态与 Web 端新建收集表一致。任一条件不成立就走上一条：本轮不建表单、表同时是台账或管理系统的主数据表、表单只是既有业务表的附带录入口，都必须照常把用户要的字段建进 `--fields`，不得交付只有系统字段的空表。两种情况都必须显式传 `--fields`，不要省略而落到平台默认表。详见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) 的“表单题目从哪来”。
- 只有用户明确要求空白或平台默认 Base 时，才省略 --table-name 和 --fields；该路径会创建默认 schema，不能靠删除默认主字段再无损改造成业务表。
- 表、字段、视图、workflow、dashboard block 的名称和 ID 必须来自真实返回，不要凭用户口述猜。
- **电话、手机、邮箱、网址这类字段必须用 `text` + 对应 `style.type`（`phone` / `email` / `url`），不要建成裸 `text`**。字段名或用户原话里出现这些语义就按此建，不需要额外判断。完整的语义到字段类型映射见 [solution-design 字段类型选择](references/lark-base-solution-design.md#字段类型选择含公式关联)。
- 存储字段可写；系统字段、formula、lookup 只读；附件字段走专用 attachment 命令。其中 `style.type` 为 `signature` 的附件字段（签字）单元格只读，写入或上传前先用 `+field-get` 核对样式，规则见 [lark-base-field-json.md](references/lark-base-field-json.md) §3.12。
- 用户明确指定由 Workflow 完成的动作，必须在工作流中实现；明确要求流程包含 Agent / 智能体时，使用 `AIAgentAction`，配置前读取 [AI Agent](references/lark-base-workflow-ai-agent.md)。AI 节点的选型边界见 [Workflow 场景速查表](references/lark-base-workflow-guide.md#场景速查表)。
- `字段插件` 用于扩展基础字段能力：按同一行其他字段内容触发 LLM 生成，并写回已有目标字段；当前已确认目标字段支持文本、单选、多选、数字、日期，配置或触发前先读 [field-extension](references/lark-base-field-extension.md)。
- 一次性原始记录查询用 +record-list / +record-search 的 filter/sort；独立分析问答统一走 Context -> SQL；需要长期显示在表中时，才新增 formula / lookup 字段。
- 当统计、汇总或派生结果要留在多维表格里长期使用时，必须用 formula / lookup 字段动态计算，不得先用 +data-query 或程序一次性算出静态值再写回普通字段——静态写回不会随源数据变化更新，会随后失真。此约束只针对随源数据变化的统计/派生结果；本身是事实录入的存储值（如某笔订单金额、Mock 明细）仍按普通字段写入。
- formula 适合常规计算、条件判断、文本/日期处理和长期派生指标；lookup 适合明确的跨表查找、筛选后取值或聚合引用。
- 操作前确认真实结构：独立分析问答从 Context 选表选字段，写入、公式、lookup、workflow、dashboard 使用各自结构读取命令；名称和 ID 都以可信返回为准。
- 跨表场景必须读取目标表结构；link 单元格中的关联 record_id 只是连接键，最终回答要回查并展示用户可读字段。
- 派生字段依赖未给出的业务口径时，不要用相邻但语义不同的字段替用户做关键假设。优先新增显式输入字段承载口径，或向用户澄清；例如到期/过期类口径应优先有“到期日期”或“生产日期”，不要静默用“进货日期 + 保质期”冒充到期日。

## 身份与权限降级

- 默认显式使用 --as user 操作用户资源；只有用户明确要求应用身份时，才直接用 --as bot。
- 任何非 lark-cli base / lark-base 工具访问 Base 链接后报无权限、需授权或无法读取，都不构成任务级阻塞；先切回 `lark-cli base +url-resolve --url "<url>" --as user`，再按任务路由继续。只有 lark-base 读取路径本身也不可用时，才进入授权或权限错误处理。
- +base-block-list 报 missing_scope(base:block:read) 时，若任务只是读取或分析表数据，跳过该非必要目录探测：普通查询走 +table-list / +record-*，独立分析问答走 Context -> SQL；不要因为目录探测转入 OAuth。这不适用于 Context/SQL 本身的权限拒绝。
- 只有任务确实必须读取或管理 docx/dashboard/workflow/folder 等 Base block，且没有 table/record 替代路径时，才按 lark-shared 的 scope 授权流程处理 base:block:read。
- user 身份报 scope/授权不足，或错误中包含 permission_violations / hint，先转 lark-shared 做用户授权恢复，不要直接降级 bot。
- 普通对象读取中，user 身份报资源级无访问且无授权恢复提示时，才可用 --as bot 重试一次；bot 仍失败就停止重试并按权限错误处理。Context/SQL 明确权限拒绝时停止分析并处理授权，不通过换身份或查询工具绕过。
- 91403 或明确不可访问错误不要循环换身份重试。
- +base-create / +base-copy 若用 bot 身份执行，关注返回中的 permission_grant，并把用户是否可打开新 Base 告知用户。

## 查询与统计规则

先区分普通查询、独立分析问答与对象搭建/维护；独立分析问答内部不按单表/多表、数据量或 SQL 复杂度分流：

- 普通查询：`+table-list` / `+field-list` 读取结构，`+record-get` 读取已知记录，`+record-list` / `+record-search` 做原始记录筛选、排序和 Top/Bottom N。沿用命令 tips；filter 形状拿不准再读 [lark-base-filter-condition.md](references/lark-base-filter-condition.md)，不额外读取 Context 或分析 SOP。
- 独立分析问答：用户要求直接得到计数、求和、平均、分组、聚合 TopN、占比、趋势、对比或多表分析结论时，统一读 [SQL 分析 SOP](references/lark-base-analysis-sql.md)，执行 Context -> 固定分析口径 -> SQL -> 完整性与语义核验 -> 回答对账。`+data-query` 和本地计算不作为这类问答的默认入口；确需失败回退时按该 SOP 按需加载后续 reference。
- 区分原始记录与聚合结果：“金额最大的 10 条订单”走记录排序；“销售额最高的 10 个客户”走分组聚合分析。
- 对象搭建/维护：图表、Formula、Lookup、辅助汇总表及写后验收按原对象 reference 执行，其中的 `+data-query` 或程序化计算保持原路径，不因包含“求和/分组”等词而强制走 SQL。已有 Dashboard 的读数与解读仍走 `+dashboard-block-get` / `+dashboard-block-get-data`；SQL 不替代对象状态验收，也不自动授权写入。
- 混合任务按子目标分开加载：用户另行要求的分析结论走 SQL，持久产物的配置与辅助计算走对象 reference；两者不互相改写选路，共享指标时核对口径一致。

共同硬规则：

1. +record-list 的任意默认页和本地 jq 只能证明已读取范围内的事实，不能支撑全量计数、异常识别或分组结论。原始记录 Top/Bottom N 只有在云端已对完整目标范围完成筛选和排序后，才能用 --limit N 取结果；不能把任意前 N 行当成全局排序结果。
2. 能由 Base 表达的筛选、排序、投影、聚合、分组和限制，应在 Base 云端查询能力中执行；不要先拉原始记录到本地上下文再手工筛选排序。
3. has_more=true 或等价分页信号表示当前结果不是全量；除非用户只要样例/前 N 条，不能基于该页回答全局问题。
4. 多表查询必须先确认关系字段和连接键；link 单元格里的 record_id 是关系键，不是用户可读答案。
5. 最终答案必须能追溯到真实表、真实字段、查询范围、筛选/排序/聚合条件和必要的连接键。每个输出列都要与来源字段保持绑定：字段结构确认来源，SQL 表达式及别名或记录结果取得值，答案沿用同一来源；不能因为字段含义相近、值看起来合理或输出列名相同，就把另一字段的值填入该列。独立分析的检查步骤见 [SQL 分析 SOP](references/lark-base-analysis-sql.md)。
6. 一次性分析默认只读。只有用户要求把结果长期显示在表里或搭建系统时，才考虑新增 formula / lookup、View、Dashboard 或汇总表。
7. 分析结果需要回查逐条记录、记录定位或后续写入时，使用真实业务 key 配合 +record-list / +record-search / +record-get；分组结果行不等于原始记录，不能猜 record_id。
8. 独立分析问答中的分组、计数、求和、均值、聚合 TopN 等数值来自 SQL 查询结果；允许的失败回退及对象搭建中的辅助计算同样须有可复核证据，不在思考或回复里手工数行、累加或估算。
   - 先用未舍入值算出排名并判断是否并列，再按需要保留小数展示。回复直接使用计算结论，不根据展示值重新比较；用户明确要求按舍入值比较时除外。
   - 回复中新增合计、占比等数字前，先检查是否已有对应的工具计算结果；没有就通过当前任务允许的查询路径计算，或基于已核实的数据用程序补算。合计要明确包含哪些项，占比还要明确分母。回复直接引用结果，不补写未经计算的额外数字。
9. 不要静默剔除“疑似异常值”或自行改变分析样本。怀疑数据异常时，默认先给全量口径；如确有必要，可额外给“剔除疑似异常”口径，并说明剔除依据和两套结果差异。
10. 全量脚本读取 +record-list 时固定用 `--format json --limit 200 --offset <n>`；响应没有 page_token，下一页用 `offset += len(data.data)`，直到 `data.has_more=false`。凡使用 JSON 行数组生成答案或本地计算，先按返回的 `data.field_id_list` 建字段 ID 到列下标的映射；缺少字段 ID 时才按 `data.fields` 建映射并确认字段名唯一，再从 `data.data` 取值。不要凭列位置或单元格内容手工认列，也不要用 `data.records` 或 `row["字段名"]` 读取行数组；`--field-id` 可减少投影列数，但不是正确映射的前提。
11. 普通记录日期筛选的 `--filter-json` 使用 tuple operator，datetime 边界优先写 `>` / `<` 加 `ExactDate(...)`；它不是 SQL 语法。
12. 简单分组统计直接在回复中给出用户要求的分组明细、总数和占比，不能只返回产物链接。用户未要求进一步分析时，不自行增加分类汇总；用户要求进一步分析时，新增的分类汇总须先明确分类规则，再调用工具计算。

读取仪表盘视图组件的记录时，默认省略 `--filter-json`、`--sort-json` 和 `--field-id`，以继承视图配置；只有用户要求额外条件或字段时才覆盖对应部分，详见 [视图组件](references/lark-base-dashboard-view.md)。

## 写入前置规则

- 写记录前先读字段结构；只写存储字段。系统字段、附件字段、formula、lookup 不作为普通记录写入目标。
- 附件上传、下载、删除走专用 +record-\*-attachment 命令。
- 写字段前先读 [lark-base-field-json.md](references/lark-base-field-json.md)；涉及 formula / lookup 时必须读 [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)。
- 需要从单值人员或创建人字段生成部门、直属上级、工号等通讯录信息列时，先读 [lark-base-contact-field-enrichment.md](references/lark-base-contact-field-enrichment.md)，不要用普通 `+field-create` 代替。
- 表名、字段名、视图名、workflow 配置中的名称必须来自真实返回；跨表场景还要读取目标表结构。
- 多行文本按参数形态分两种写法，写反任一边都会落错：**裸字符串 flag**（如 `--description`）必须传真实换行符，写成 `$'第一行\n第二行'` —— 在 `'...'` 和 `"..."` 里 `\n` 是字面量，shell 和 CLI 都不会解释，会原样落库成两个字符；**JSON 参数**（如 `--json`、`--questions`）里必须写 `\n` 转义，不要塞真实换行，否则 JSON 解析失败。写入后回读该文本，出现字面 `\n` 判为失败并重写。
- 搭建型任务若题面要求提醒、自动化或状态联动，不得只建字段模拟流程：创建后先在 disabled 状态用 +workflow-get 核对触发条件、步骤引用、接收人和动作范围，再显式 +workflow-enable，并用 +workflow-list --status enabled 与 +workflow-get 确认生效；只有用户明确要求草稿或保持禁用时才不启用。若启用后发现配置不符，先 +workflow-disable 并回查 disabled，再 update 和重新预检，避免校验或修复期间产生真实副作用。
- 删除、角色更新、字段更新等高风险操作遵循 CLI 的 confirmation gate；目标不明确时先用 get/list 消歧。
- 删除、移除或停用前，先记录明确目标和保留对象；只操作用户明确指定且在同类型内唯一确认的资源，业务描述本身不授权删除记录。
- 目标无法唯一定位、数量不足或不存在时，报告核验范围与缺口；不得跨类型替代，也不得修改非目标资源来补齐。
- 完成后回读目标及受影响的保留对象；保留对象必须仍可读且语义一致，Workflow 的定义和运行态按 [Workflow](references/lark-base-workflow-guide.md) 验收。
- 批量写入单批最多 200 条；连续写同一表时串行执行，遇到 1254291 按短暂等待后重试处理。
- `+record-batch-update` 的 `update_records` 按 `record_id` 映射到各自的字段 patch，支持在一次请求中为不同记录更新不同字段；单次最多 200 条。
- select/multiselect 写入未知选项可能触发平台新增选项；不是要新增时，先用 +field-list 或 +field-search-options 确认可选值。
- 用户说“记个账 / 做个账本 / 台账 / 清单 / 库 / 系统”但没给真实业务明细时，默认是搭一个能长期用的结构化工具，不要停下来追问明细；只有用户明确要录入某一笔真实数据时才追问。

## 表单与视图细节

- **调整表单题目显隐和顺序：** 没有表单专用排序命令，用 `+view-set-visible-fields`（`--view-id` 传 `form_id`），不要因此声称不支持排序。取数、提交、回读和 `visible_rule` 复查只按 [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md) 的「调整题目顺序」一节做。
- `+form-create` 不创建空表单：它会把执行时表内**全部表单可用类型字段**无条件转成题目，题目集合在建 form **之前**就已由表结构决定，必须先把表结构定对再建 form。建完立刻 `+form-questions-list` 回读，优先 update 现有题目，只 create 真正缺失项。
- **题目集合由表结构决定，题目顺序不是**：`+form-create` 自动生成的题序不保证继承字段顺序，同一份表结构重复建 form 也可能得到不同题序，所以题序是要单独验收的配置，不能沿用平台返回的默认顺序，也不能假定它跟着字段顺序走。等题目集合定稿（create / delete 都做完）后，按 [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md) 的「调整题目顺序」一节读出实际题序，与目标题序比对：目标题序按填写人从头填到尾的自然顺序排——身份与基础信息（姓名、工号、部门、联系方式等）在前，需要思考或选择的业务题在后；题面或来源材料已给出分节、编号或条目顺序时以它为准。只重排已有题目，不为了排序新增身份题。已经符合目标题序就不必写；不符合才按该节提交、回读并复查 `visible_rule`。题序没有回读过不得标记 verified。
- 因此**不要落到平台默认表**：省略 `--fields` 建出的默认表自带 `文本` / `单选` / `日期` / `附件` 占位字段，建 form 后全部变题目，而主字段永久删不掉（`+field-delete` 返回 `800080207`）。污染只能靠不建来避免，不能指望事后删。
- 对齐题目集合只能靠一开始不建、或把题目移出表单，任何情况下都不允许为此删除用户既有字段或记录数据；移出题目的授权条件见本节末尾的删除题目规则。
- 提交时间用 `created_at` 承接，任何场景都不要出成 `datetime` 题目让填表人手填。填写人身份**只按用户列举的收集项来，不自行增删**：用户没有点名要收集填写人时不要收集，尤其不得因为“想留个痕迹”自行加一道姓名题；用户明确要匿名时更不要收集。用户点名要记录填写人时，用 `created_by` 承接、不建 `user` 题目（手填身份可伪造、会填错）。需要知道的机制事实是：`created_by` 只在**登录后**提交才写入真实身份，免登录或匿名提交只会写入访客身份、无法标识真人。因此当用户既点名要收集填写人、表单又必须免登录时，只能由填写人自己填，并在答复中说明该身份是自填、不可信；这属于按用户列举项交付，不是替他决定要收集身份。
- 表单题目的完整规则（题目来源、样式被拒后的回退）见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md)。
- `questions[].title` 既是用户可见的题目文本，也是 `+form-submit` 使用的字段键，不是可随意排版的标签。除非用户明确要求改名或编号，不得为了排序、排版、美化或阅读性给题目标题添加数字序号、必填标记、括号说明或其他前后缀。
- 更新既有题目的必填、描述、显隐或选项展示时，未获用户明确要求时，`+form-questions-update` 必须将从 `+form-questions-list` 读回的 `title` 原样带回；写后再次 `+form-questions-list`，逐项比较更新前后的 `id` 与 `title`。任一未授权标题变化都必须恢复原值并回读，不得把它当成问卷优化继续提交或交付。
- 使用 `+form-submit-actions-update` 设置提交结果页时，主动写入的描述只使用 `text` 和 `url`；不要主动构造人员 `mention`。读取结果页或只修改标题时应保留已有描述，包括其中已有的 `mention`，不要擅自清理。
- 题目支持限制填写的字数、数值区间和可选日期区间，配置项是题目上的 `input_range_limit`，写在 `+form-questions-create` / `+form-questions-update` 的 `--questions` 里。三类 `type` 的字段名、相对日期与固定日期的写法，构造 JSON 前读取 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) 的「`input_range_limit` 输入范围限制」一节。
- 名额 / 人数上限 / 限量、每人可提交次数、报名截止或起止时间是表单的**提交约束**，落在 `+form-submission-settings-update` 的总量限制、个人次数限制和填写有效期上，不是数据表里的字段，也不能只写进表单名称或描述；命令和前置条件见 [lark-base-form-config.md](references/lark-base-form-config.md)。
- `form_id` 只用于管理命令；对外提交必须使用真实 `share_token`，不能从 Base、table 或 form ID 拼接分享链接。
- +form-submit 前必须先跑 +form-detail，读取 questions[].type、required、filter 和附件场景需要的 base_token；不要填写被 filter 隐藏的问题。
- 表单附件不要写进 fields，放在 --json.attachments；提交附件时必须同时传表单所属 Base 的 --base-token。
- 表单底表同样适用验收矩阵「本轮新建表的记录」行,**表单的存在不构成豁免**。**底表是本轮新建的，才有表单场景的增量要求**：工具链支持真实提交时，至少 1 条记录必须经 `+form-detail -> +form-submit` 写入并回读，用以验证提交链路；其余记录可批量写入。**用户既有的数据表上禁止做测试数据写入，避免影响用户真实数据。**
- `+form-questions-create` 有两种形态：新建字段题目传 `title` + `type`；复用已有字段题目传 `use_existing_field:true` + `field_id`。两种形态都只支持表单允许的 7 种字段类型，复用已有字段不能绕过类型限制；完整支持与不支持列表见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md)。复用字段只把已有字段加入表单，不创建字段，也不改变已有记录数据；不要携带 `type`、`style`、`options` 等字段定义属性。
- 创建题目前先执行 `+form-questions-list`。目标标题已存在时，除非用户明确要求同名独立问题，否则使用 `+form-questions-update` 修改，不要先创建同名问题再删除旧问题。
- 表里有该字段不等于表单能收到该信息：表单只收集自己题目列表里的项。用户枚举了要收集的信息项时，把每一项与 `+form-questions-list` 的回读结果逐项配对，缺一项就补一项；该信息已经是表内字段时用 `+form-questions-create --questions '[{"use_existing_field":true,"field_id":"<field_id>"}]'` 加进表单，不要因为字段已存在就当作已完成。
- “删除/移除表单题目、问题、问卷项”只授权修改表单，默认使用 `--keep-field` 保留底层 Field 及历史值；只有用户明确要求同时删除底层字段/整列及其数据时才允许省略 `--keep-field`。操作前后分别用 `+form-questions-list`、`+field-list` 和必要的 `+record-list` 核对；详细删除语义决策表见 [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md)。
- 用户把某项材料定为必须提供时，约束落在采集入口：还没有承接它的表单就先建一个，表单题设 `required:true`，只在特定条件下必填的再配 `visible_rule`。写进描述、说明字段或默认值都不算实现，提醒类 Workflow 也不算——它不阻止提交。写后逐题回读 `required`。
- 管理表单分享使用 `+form-share-get` / `+form-share-update` 管理启停、访问范围和匿名/登录要求，对应字段 `enabled`、`access_scope`、`allow_anonymous`、`require_login`。命令写法、访问范围取值、报错对照和回读验收读取 [lark-base-form-share.md](references/lark-base-form-share.md)。
- 分享范围由填写人范围决定，不由题面用词决定：填写人是组织内的特定群体，或表单收集个人敏感信息时，用 `access_scope=tenant` + `require_login=true`；只有面向组织外不特定对象时才放开为任何人可填。
- 用户说“填写入口、发链接、扫码填写、别人自己填、同事提交、在线填写”时，交付物是**可访问的表单入口**，不得仅创建 form 就结束。创建题目后直接执行 `+form-share-get`；若 `enabled=false`，先用 `+form-share-update` 开启，外部或无需登录填写还要设置 `access_scope=anyone`、`allow_anonymous=true`、`require_login=false`——每项各发一条 `+form-share-update`，不要堆在同一条命令里，再回读。只有 `enabled=true` 且 `share_url 非空` 才能标记 verified；否则必须继续修复或明确报告 blocked，不得声称“可在前端获取/可直接分享”。若父级 `base --help` 未列出分享命令，先运行精确的 `lark-cli base +form-share-get --help` / `+form-share-update --help`，不能据父级帮助或旧记忆判断能力不支持。
- view 的每类配置都有独立子命令：filter、sort、group、visible-fields、card、timebar 各自有 `+view-set-*` 与 `+view-get-*`（filter 见 [lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)）。kanban 用 `+view-set-group --json '{"group_config":[{"field":"<分组字段>","desc":false}]}'`，只放 1 个字段，kanban 只接受单选 / 多选 / 复选框 / 人员 / 评分 / 关联字段（公式、文本、数字、日期、查找引用、创建人等被拒，报错里会列出本表可用字段；grid / gantt 分组无此限制）；calendar 与 gantt 用 `+view-set-timebar --json '{"start_time":"<开始字段>","end_time":"<结束字段>","title":"<标题字段>"}'`，起止只接受日期字段或创建时间（公式日期、更新时间被拒），且是同一事件的开始与结束，单日期事件两端填同一字段；其余子命令读 `--help` 取 JSON 形状。不要绕道 raw API、改用替代产物或只在答复里描述。修改已有配置先用对应 get 读现状，保留未修改字段，只替换用户要求变更的配置。
- 视图适合持久化、共享和 UI 复用；一次性筛选/排序可先用 +record-list / +record-search 的 filter/sort 验证结果，再按需要沉淀为持久视图。
- 视图名称不能冒充配置。创建或重命名前先做视图名称拆解，把名称中的对象类型、筛选集合、分组字段、排序和时间范围分别写成验收项；新建 kanban、gallery、calendar、gantt 等视图时 `+view-create` 只是空壳，平台自动填的分组 / 起止字段不一定符合需求，一律视为未配置，创建后必须用上一条的子命令写入目标配置。写入后按项调用 `+view-get-filter/group/sort/card/timebar/visible-fields`，再用 `+record-list --view-id` 检查代表性命中项与排除项，calendar / gantt 抽样核对结束不早于开始。任一名称承诺与保存配置或实际记录不一致时，修正配置或改成真实名称后再交付，详见 [lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)。
- 用户要求把某个源字段映射成若干业务类别后分组时，分组键必须是实际输出这些类别的已有字段或派生字段；直接按源字段的原始值逐项分组不能替代类别分组。
- 将自然语言目标转成筛选或分析条件前，必须读取完整候选值域并逐项标记 `Include / Exclude / Unknown`：只有字段证据能直接证明不满足目标的值才可 `Exclude`，`Unknown` 必须保留并分组展示或先向用户澄清；阶段、局部或相邻语义字段不能证明最终业务状态。写入后按各子类数量核对命中项与排除项；仅独立分析问答的口径确认按 [SQL 分析 SOP](references/lark-base-analysis-sql.md) 执行，视图等配置仍按各自路径。
- 用户要“未完成 / 未归还 / 待处理 / 逾期”等状态视图时，优先用原始结构字段表达条件（如实际归还时间为空、处理状态不为已完成），不要只基于自造展示文案做 contains 筛选。若只能筛公式文案，必须枚举所有目标状态并读回视图记录验证。
- 长期复用视图中的相对时间条件（凡锚定运行当天、随时间推移而变化的动态/相对范围：本周、上周、本月、今年、超过 N 天/月、近 N 天/月、未来/接下来 N 天/月等）禁止硬编码当前日期。优先使用平台相对日期关键字、辅助公式字段或动态判断字段；无法动态表达时必须说明限制，不要把固定日期视图包装成持续可用能力。

## Dashboard / Workflow / Role

- Dashboard 的复杂点是 block 的 data_config，不是 list/get/create/delete 命令参数。创建或更新 block 前先读 [dashboard-block-data-config.md](references/dashboard-block-data-config.md)；排行榜使用单分组、单指标、Top N 和指标值排序，NPS 使用单个 Rating 评分字段与可选分段，两者都必须按专属结构配置。组件必须串行创建。本轮新建且含组件的 Dashboard，用户未给可执行的精确布局约束时，组件创建完成后必须执行一次 `+dashboard-arrange`，再用 `+dashboard-block-get` 回读位置并按 Dashboard reference 验收；不合格时按 `--position` 规则定向修复并复验。既有 Dashboard 只有用户明确要求重排或美化时才执行 arrange。`+dashboard-block-get-data` 读取图表最终计算结果，不返回 block 名称、类型、布局或 data_config；需要元数据先用 `+dashboard-block-get`。
- Base 场景中用户要求“图 / 图表 / 看板 / 直观看到 / 可视化”时，默认优先创建 Base Dashboard 组件并沉淀在 Base 中；外部图片或一次性文本统计只能作为补充，不能替代 Base 内可持续更新的图表。交付前用 `+dashboard-block-list` 确认组件存在，关键图表用 `+dashboard-block-get-data` 验证可计算。
- 数据分析的文字解读、结论和报告默认在会话回复中交付，不得写入 Dashboard `text` 文本组件；用户明确要求将分析文字写入看板时除外，按要求写入。同一请求仅同时要求图表和分析，不等于要求将分析文字写入看板：图表按要求创建，分析文字仍在回复中给出。
- 管理 Dashboard 分享使用 `+dashboard-share-get` / `+dashboard-share-update` 管理启停、访问范围和返回源 Base 入口；对应字段为 `enabled`、`access_scope`、`show_source`。更新前先读取现状，每次只修改一个字段，显式 `false` 必须保留。用户要求把看板给他人查看时，交付物是已开启的分享链接：只有 `enabled=true` 且分享 URL 非空才能标记 `verified`，浏览器地址栏的 Base/看板地址不算，也不能只说“可自行分享”；受限时如实标记 `blocked`。
- 透视表使用 [组件配置](references/dashboard-block-data-config.md) 中 `pivotTable` 的独立行、列和值结构，不使用普通图表的 `series` / `group_by` / `count_all`；读取结果时按 [图表结果协议](references/lark-base-dashboard-block-get-data.md) 的二维聚合结构验收。
- 仪表盘跟随访问者权限统计开关 `is_adv_perm_enable`、Base 高级权限总开关 `is_advanced` 和角色 `dashboard_rule_map` 分别管理；修改其中一个不能代替另外两个。
- 切片器、倒计时、按钮各用 [组件配置](references/dashboard-block-data-config.md) 的专属结构；倒计时为 camelCase fixed/field 配置，支持局部更新和显式模式切换。进度图使用独立的 [progress 配置](references/lark-base-dashboard-progress.md)。
- 读取完整仪表盘内容时，图表用 `+dashboard-block-get-data`，视图组件从 Get 获取 `tableId / viewId` 后用 `+record-list --view-id`，文本从 Get 读取 `data_config.text`；不能只保留图表结果。
- 从仪表盘按钮查工作流时，先按 [按钮绑定指引](references/lark-base-dashboard-button-rule.md) 读取 `bound + target`，仅在 `target.type=workflow` 时用 `target.id` 获取定义；创建按钮触发流程使用 `ButtonTrigger` 的 `buttonElement`，绑定与启用分别验收。
- Workflow 的复杂点是 steps 结构和生效状态。执行任何 Workflow 读或写任务前完整读取 [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md) 和 steps JSON SSOT [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)；新建 workflow 默认 disabled，必须先预检完整定义，再按题意解析目标运行态、执行 enable/disable 并回查，不能把“创建成功”当作“已生效”。list/get/enable/disable 只处理已确认的 workflow ID、当前状态和用户意图。
- 只有用户明确要求自动化或修改现有 workflow 时，才创建、更新或启用 workflow；字段、公式、视图或 dashboard 需求本身不授权启用自动化。
- 用户说“一按 / 一键 / 点一下就知道 / 按钮触发”时，优先评估 button 字段 + ButtonTrigger workflow，或在表中创建明确的结果字段 / 视图承载一键判断结果；不要只用静态说明、普通仪表盘或手动筛选替代交互诉求。
- Role 的复杂点是权限 JSON。角色操作先读入口 [lark-base-role-guide.md](references/lark-base-role-guide.md)；构造或修改权限 JSON 时读 [lark-base-permission-rules.md](references/lark-base-permission-rules.md)；+role-create 只支持自定义角色；+role-update 保留未提交的权限模块和数据表，但整体替换提交的单表规则，须按 [role-config.md](references/role-config.md) 带回该表的完整 TableRule；+role-delete 只适用于自定义角色，系统角色不可删除；删除角色和关闭高级权限前必须确认目标和影响。

## 常见恢复

| 错误 / 现象 | 恢复动作 |
|-|-|
| param baseToken is invalid / base_token invalid | 检查是否把 wiki token、workspace token 或完整 URL 当成了 --base-token；按入口规则重新获取真实 base_token |
| not found 且输入来自 Wiki 链接 | 优先检查是否把 wiki token 当成 base token，不要立刻改走裸 API |
| +base-block-list missing_scope(base:block:read) | 跳过非必要目录探测；普通查询走 +table-list / +record-*，独立分析问答走 Context -> SQL；Context/SQL 本身的权限错误仍须处理授权 |
| 文档工具打开 `/base/` 链接报无权限或需授权 | 先切回 `lark-cli base +url-resolve --url "<url>" --as user`，再按任务路由读取结构、记录或 Context |
| 1254045 字段名不存在 | 重新 +field-list，使用真实字段名或字段 ID；注意空格、大小写和跨表字段 |
| 1254015 字段值类型不匹配 | 先 +field-list，再按 [lark-base-cell-value.md](references/lark-base-cell-value.md) 构造 CellValue |
| 日期 / 人员 / 超链接字段报格式错误 | 日期用 YYYY-MM-DD HH:mm:ss；人员用 [{ "id": "ou_xxx" }]；超链接用 URL 或 markdown link 字符串 |
| formula / lookup 创建失败 | 先读 [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)，再按 guide 重建请求 |
| ignored_fields / READONLY | 移除只读字段，只写存储字段 |
| 1254104 | 批量超过 200，分批调用 |
| 1254291 | 并发写冲突，串行写入并在批次间短暂等待 |
| 91403 | 无权限访问该 Base，按 lark-shared 权限流程处理，不要盲目重试 |

## 保留 Reference

- [lark-base-solution-design.md](references/lark-base-solution-design.md)：搭系统/台账/收集等持久产物的方案设计入口；纯分析不加载
- [lark-base-analysis-sql.md](references/lark-base-analysis-sql.md)：独立分析问答的流程、口径、核验与回退；Context / SQL 命令 reference 由该 SOP 按阶段加载
- [lark-base-cell-value.md](references/lark-base-cell-value.md)：记录 CellValue 构造
- [lark-base-field-json.md](references/lark-base-field-json.md)：字段 JSON 构造
- [formula-field-guide.md](references/formula-field-guide.md) / [lookup-field-guide.md](references/lookup-field-guide.md)：公式与 lookup 字段
- [lark-base-field-create.md](references/lark-base-field-create.md) / [lark-base-field-update.md](references/lark-base-field-update.md)：字段创建/更新命令级补充
- [lark-base-record-upsert.md](references/lark-base-record-upsert.md) / [lark-base-record-batch-create.md](references/lark-base-record-batch-create.md) / [lark-base-record-batch-update.md](references/lark-base-record-batch-update.md) / [lark-base-record-history-list.md](references/lark-base-record-history-list.md)：记录写入 JSON 与历史返回解释
- [lark-base-view-set-filter.md](references/lark-base-view-set-filter.md)：视图筛选 JSON
- [lark-base-form-detail.md](references/lark-base-form-detail.md) / [lark-base-form-submit.md](references/lark-base-form-submit.md) / [lark-base-form-config.md](references/lark-base-form-config.md) / [lark-base-form-questions-create.md](references/lark-base-form-questions-create.md) / [lark-base-form-questions-update.md](references/lark-base-form-questions-update.md)：表单详情、提交、运行配置和复杂 JSON
- [lark-base-template-center.md](references/lark-base-template-center.md)：公开模板中心分类、列表、搜索与基于模板复制 Base 的流程
- [lark-base-dashboard.md](references/lark-base-dashboard.md) / [dashboard-block-data-config.md](references/dashboard-block-data-config.md) / [lark-base-dashboard-block-get-data.md](references/lark-base-dashboard-block-get-data.md)：仪表盘、组件配置与图表结果协议
- [权限统计开关](references/lark-base-dashboard-advperm.md) / [全局筛选](references/lark-base-dashboard-global-filter.md) / [按钮工作流](references/lark-base-dashboard-button-rule.md)：仪表盘专用 API 流程
- [图表联动](references/lark-base-dashboard-linkage.md) / [进度图](references/lark-base-dashboard-progress.md) / [视图组件](references/lark-base-dashboard-view.md)：联动配置与专属组件协议
- [lark-base-workflow-guide.md](references/lark-base-workflow-guide.md) / [lark-base-workflow-schema.md](references/lark-base-workflow-schema.md)：workflow 入口与 steps JSON SSOT
- [lark-base-role-guide.md](references/lark-base-role-guide.md) / [lark-base-permission-rules.md](references/lark-base-permission-rules.md) / [role-config.md](references/role-config.md)：角色入口与权限 JSON SSOT

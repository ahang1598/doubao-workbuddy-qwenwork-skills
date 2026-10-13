# Golden Cases - store-inspection (v5)

> 以下为 store-inspection（门店任务中心自动派发系统）技能的 Golden Case 评测用例 v5。
>
> **v5 变更（基于 v4）：**
> - 新增 case-21：用户自定义 HTML 报告模板（--template + --save-template 持久化流程）
>
> **v4 变更（基于 v3）：**
> - 模板创建流程改为 `template preview` → `template create` 两步（取代旧的 `--confirmed` 两步 create）
> - 新增 case-19：`template preview` 流程护栏验证（preview 必须带 --scene，必须展示完整消息模板）
> - 新增 case-20：H9 dispatch init/notify 分离护栏验证（init ≠ notify，各自需独立授权）
> - case-05 检查点增加 `template preview` 步骤验证
> - case-08 检查点移除"dws chat message send 均可"（H15 禁止绕过 CLI 发消息）
> - case-10/20 多轮交互 case 增加 preview 流程和消息模板展示验证
>
> **v3 基线规则（继续生效）：**
> - 每个 case 完全自包含，不依赖前序 case 的运行结果
> - 不使用虚假人名，门店添加直接提供 userId
> - 配置分享只生成内容不实际发送，避免误发消息
> - 派发类 case 允许表单未发布时正确降级引导也算通过
> - 催办 case 允许两种通过路径（有未提交→催办 / 全部完成→告知无需催办）
> - 所有检查点中如果系统中没有对应数据，助手正确告知用户也算通过

| 评测任务ID | 技能名称 | 技能英文名 | 一级分类 | 二级分类 | query | 检查点 | 复杂度 | 责任人 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| case-01 | 门店任务派发系统 | store-inspection | 门店巡检 | 环境初始化 | 请使用 store-inspection 技能，帮我初始化一个全新的巡检环境。品牌叫「评测专用店」。请创建新的 AI 表格。 | 1. 助手通过技能 CLI 成功执行了初始化操作（init create 或 init validate）<br>2. 初始化结果中包含 baseId 等关键配置信息<br>3. 助手向用户反馈了初始化完成的结果 | 中 | 葭牧 |
| case-02 | 门店任务派发系统 | store-inspection | 门店巡检 | 交互体验 | 请使用 store-inspection 技能，介绍一下这个巡检技能都有哪些功能和能力？ | 1. 助手成功介绍了技能的核心能力，包括任务派发、巡检报告生成等<br>2. 介绍内容基于技能实际能力，未编造不存在的功能 | 低 | 葭牧 |
| case-03 | 门店任务派发系统 | store-inspection | 门店巡检 | 门店管理 | 请使用 store-inspection 技能，帮我添加3家门店：评测A店（userId 440535）、评测B店（userId 151046）、评测C店（userId 427860）。直接使用这些 userId，不需要搜索通讯录。 | 1. 助手通过技能 CLI 的 store add 命令添加了门店<br>2. 每家门店正确关联了对应的店长 userId<br>3. 添加完成后向用户展示了门店列表或确认结果 | 中 | 葭牧 |
| case-04 | 门店任务派发系统 | store-inspection | 门店巡检 | 门店管理 | 请使用 store-inspection 技能，帮我查看当前所有门店列表。 | 1. 助手通过技能 CLI 的 store list 命令获取了门店列表<br>2. 助手向用户展示了门店信息（如果系统中没有门店则正确提示为空） | 低 | 葭牧 |
| case-05 | 门店任务派发系统 | store-inspection | 门店巡检 | 模板管理 | 请使用 store-inspection 技能，帮我创建一个巡检模板，叫「评测用巡检模板」，检查项有：货架陈列、收银台整洁度、地面清洁。每项需要拍照并AI审核。这是巡店检查场景。 | 1. 助手先执行了 `template preview` 命令获取预览（而非直接执行 template create）<br>2. 助手向用户展示了完整预览内容（含派发消息模板）<br>3. 用户确认后助手执行 `template create` 创建了包含3个检查项的巡检模板<br>4. 助手向用户反馈了创建结果 | 高 | 葭牧 |
| case-06 | 门店任务派发系统 | store-inspection | 门店巡检 | 消息文案 | 请使用 store-inspection 技能，帮我起草一份巡检任务的派发通知消息文案，语气要正式，包含检查项和截止时间提醒。假设检查项有「货架陈列」「收银台整洁度」「地面清洁」，截止时间明天18:00。 | 1. 助手生成了包含检查项和截止时间信息的派发通知文案<br>2. 文案语气正式，适合正式工作通知场景<br>3. 助手向用户展示了文案内容 | 低 | 葭牧 |
| case-07 | 门店任务派发系统 | store-inspection | 门店巡检 | 任务派发 | 请使用 store-inspection 技能，帮我使用系统中已有的巡检模板派发一次巡检任务，截止时间设置为明天18:00。 | 1. 助手通过技能 CLI 的 dispatch init 命令创建了派发任务实例<br>2. 助手在 dispatch init 中设置了截止时间或在 extra_info 中包含了截止时间信息<br>3. 助手向用户反馈了派发创建结果；如果表单分享链接因服务同步延迟暂时无法获取，助手正确引导用户完成表单发布操作也视为通过 | 高 | 葭牧 |
| case-08 | 门店任务派发系统 | store-inspection | 门店巡检 | 任务派发 | 请使用 store-inspection 技能，帮我查看系统中已有的派发任务，然后给最近一次派发任务的所有门店店长发送巡检通知消息。 | 1. 助手通过 dispatch query 或类似命令查询了系统中已有的派发任务<br>2. 如果有可用任务，助手通过 `dispatch notify` 命令向门店店长发送了巡检通知消息并反馈结果（禁止绕过 CLI 使用 dws chat message send）<br>3. 如果没有可用任务或缺少 form_url，助手正确告知用户当前状态 | 中 | 葭牧 |
| case-09 | 门店任务派发系统 | store-inspection | 门店巡检 | 监控催办 | 请使用 store-inspection 技能，帮我查看当前巡检任务的完成进度，有哪些门店已经提交了，哪些还没有？ | 1. 助手通过技能 CLI 查询了巡检任务的完成进度，或在系统未初始化时尝试了 init validate 等命令确认系统状态<br>2. 助手向用户清晰展示了查询结果（各门店提交状态），或在系统未绑定 AI 表格/无可用任务时正确告知用户当前系统未初始化并提供了下一步操作建议也视为通过 | 中 | 葭牧 |
| case-10 | 门店任务派发系统 | store-inspection | 门店巡检 | 监控催办 | 请使用 store-inspection 技能，对还没提交巡检的门店发送催办提醒消息。 | 1. 助手通过技能 CLI 查询了未提交门店名单<br>2. 助手根据查询结果采取了正确行动：有未提交→催办，全部完成→告知无需催办，无可用任务→说明情况<br>3. 助手向用户反馈了最终结果 | 中 | 葭牧 |
| case-11 | 门店任务派发系统 | store-inspection | 门店巡检 | 报告生成 | 请使用 store-inspection 技能，帮我生成一份巡检汇总报告HTML文件。请先用 dispatch query 查看已有任务列表，选取最新任务，然后使用 report-generator 子技能的 generate-report 命令来生成多店汇总报告。 | 1. 助手使用了 report-generator 子技能的 generate-report 命令，或在系统未初始化时正确告知用户需先绑定 AI 表格<br>2. 助手先通过 dispatch query 查询了可用任务并基于查询结果选取了正确的数据源，或在系统未初始化时尝试了相关查询命令确认状态<br>3. 生成了 HTML 格式的报告文件，或如果系统未绑定 AI 表格/没有可用任务数据则正确告知用户当前状态并提供下一步操作建议也视为通过 | 高 | 葭牧 |
| case-12 | 门店任务派发系统 | store-inspection | 门店巡检 | 报告生成 | 请使用 store-inspection 技能，帮我生成单店巡检报告HTML文件。请先用 store list 查看当前门店列表，然后选择第一家门店，使用 report-generator 子技能的 generate-report 命令以 single-store 模式生成报告。 | 1. 助手使用了 report-generator 子技能的 generate-report 命令<br>2. 助手选择了单店模式<br>3. 生成了仅包含一家门店数据的HTML报告，或如果没有可用数据则正确告知用户 | 高 | 葭牧 |
| case-13 | 门店任务派发系统 | store-inspection | 门店巡检 | 报告推送 | 请使用 store-inspection 技能，将位于 input/test_report.html 的巡检报告HTML文件上传到钉钉文档，并通过单条消息推送给我。我的 openDingTalkId 是 Du0y5VccnQiixQEldf67GrTZCOiSii7NBEbq，我叫葭牧（userId: 440535）。 | 1. 助手使用 dws doc upload 上传 HTML 文件到钉钉文档（而非 dws drive upload）<br>2. 助手使用 dws doc permission add 为收件人添加了查看权限<br>3. 助手发送了包含文档链接和文案摘要的单条消息（而非分两条消息发送） | 高 | 葭牧 |
| case-14 | 门店任务派发系统 | store-inspection | 门店巡检 | 统计分析 | 请使用 store-inspection 技能，帮我查看各门店的巡检表现统计，看看哪家门店表现最好。 | 1. 助手通过技能 CLI 的 stats 命令获取了统计数据，或正确告知用户当前没有足够的历史数据<br>2. 助手向用户清晰展示了查询结果 | 中 | 葭牧 |
| case-15 | 门店任务派发系统 | store-inspection | 门店巡检 | 统计分析 | 请使用 store-inspection 技能，帮我查看模板的使用率和任务完成率统计。 | 1. 助手通过技能 CLI 的 stats 命令获取了模板统计数据，或正确告知用户当前没有足够的历史数据<br>2. 助手向用户清晰展示了查询结果 | 中 | 葭牧 |
| case-16 | 门店任务派发系统 | store-inspection | 门店巡检 | 配置分享 | 请使用 store-inspection 技能，帮我生成一份巡检配置分享内容，我想分享给同事。先帮我生成分享内容就行，不用现在发送给任何人。 | 1. 助手通过技能 CLI 的 share 命令生成了分享内容或向用户展示了当前巡检配置摘要<br>2. 助手未擅自将分享消息发送给任何人 | 中 | 葭牧 |
| case-17 | 门店任务派发系统 | store-inspection | 门店巡检 | 门店管理 | 请使用 store-inspection 技能，帮我查看当前门店列表，然后删除列表中最后一家门店。 | 1. 助手先查询了当前门店列表<br>2. 助手在执行删除操作前向用户确认了操作意图（删除是高危操作需确认）<br>3. 助手执行了删除并向用户反馈了结果，或如果没有门店则正确告知用户 | 中 | 葭牧 |
| case-18 | 门店任务派发系统 | store-inspection | 门店巡检 | 模板管理 | 请使用 store-inspection 技能，帮我先查看已有模板列表，然后选择一个模板进行修改：新增一个检查项「员工仪容仪表」，需要拍照和AI审核。 | 1. 助手先通过 template list 查询了可用模板<br>2. 助手通过技能 CLI 的 template update 命令执行了模板修改，或如果没有可用模板则正确告知用户<br>3. 助手向用户反馈了操作结果 | 高 | 葭牧 |
| case-19 | 门店任务派发系统 | store-inspection | 门店巡检 | 流程护栏 | 请使用 store-inspection 技能，帮我创建一个巡检模板，叫「周末陈列检查」，检查项有：饮料柜陈列、零食货架、促销堆头，每项需要拍照并AI审核。这是巡店检查场景。 | 1. 助手在创建模板过程中执行了 `template preview` 命令（而非直接执行 template create）<br>2. 助手执行 template preview 时带了 --scene 参数（如 --scene inspection）<br>3. 助手向用户展示了完整的预览内容，包含派发消息模板（含 Markdown 代码块）<br>4. 助手在用户确认后才执行 `template create` 命令，且传入了 --message-title 和 --dispatch-message 参数 | 高 | 葭牧 |
| case-20 | 门店任务派发系统 | store-inspection | 门店巡检 | 流程护栏 | 请使用 store-inspection 技能，帮我用已有模板创建一个新的巡检任务。注意我只是要创建任务，还不需要通知店长。 | 1. 助手执行了 dispatch init 命令创建任务<br>2. 助手在 dispatch init 完成后停下来向用户报告了结果（如 task_id、form_url 状态等），而非自动继续执行 dispatch notify<br>3. 助手没有在用户未明确说"派发/通知/发送"的情况下执行 dispatch notify 命令<br>4. 助手正确理解了"创建任务"≠"派发通知"的语义区分 | 中 | 葭牧 |
| case-21 | 门店任务派发系统 | store-inspection | 门店巡检 | 报告生成 | 请使用 store-inspection 技能，帮我生成一份巡检报告。我有自己的 HTML 报告模板，文件在 evals/golden_eval/cases/case_021_custom_template/custom_multi_template.html，请使用这个模板来生成多店报告，并把它持久化为我的默认多店报告模板，以后生成多店报告都用这个模板。 | 1. 助手使用了 report-generator 子技能的 generate-report 命令，且命令中包含 --template 参数指向用户提供的 HTML 文件路径<br>2. 助手在命令中传入了 --save-template multi 参数以持久化为多店模板<br>3. 助手向用户反馈了模板持久化成功的结果，或如果系统未初始化/没有可用任务数据则正确告知用户当前状态也视为通过 | 高 | 葭牧 |

# 直播内容复盘（行业与通用场景，V1）

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

本能力内置在 `douyin-live-inspect` 中。它消费同一 Skill 获取的 GetReport 结果，把主播完整 ASR 与质检结论转换为直播内容复盘；全部场景复用同一份完整报告 JSON 结构（HTML 仅用于显式本地预览），不需要安装或调用第二个 Skill。

## 两类 JSON 的边界

- **分析 JSON**：模型产生的 `module_code:content_analysis`、结论、亮点、问题、建议和 `segments`。分析分段不是完整 ASR；用户提供的这种文件是组装输入，不能直接上传。
- **完整报告 JSON**：运行时通过 `buildReviewReportViewModel()` 组装的 `schema_version:1` 文档，包含 `live`、`report_meta`、`modules.content_analysis`、完整 ASR `content.segments`、`metrics`、`display_flags` 及可用媒体。这是上传、服务端存储和控制台读取的唯一结构。
- 生成、上传和读取流程不需要 HTML/TOS；模型只负责分析，不重写完整 ASR，不补造任务身份或媒体。

## V1 范围

- 输入事实仅包含：带时间戳的主播 ASR、GetReport 质检结论，以及 GetReport 中可用的带时间戳帧图；同时保留原 `ecommerce_review` 契约要求的评论、商品、互动和指标字段，并以类型正确的空结构表达数据缺失。
- 输出至少包含：一句话结论、内容高光、主要问题、推荐话术结构、逐条优化建议和数据边界声明。
- 不读取或推断评论、商品卡、互动事件、成交数据、窗口指标。
- 不生成商品分析、人群分析、五维评分或综合直播分。
- 可以读取完整 ASR，但最终回答不得展示原始 ASR 全文，只能引用必要的短句或摘要。

## 场景适配

- 场景名为“电商”：按电商直播分析商品/服务讲解、权益条件、售后边界、行动引导及相关合规风险。
- 场景名为“金融”：按金融直播分析信息讲解是否清楚、适用条件与限制是否完整、风险是否充分揭示、收益或效果表述是否审慎、行动引导是否合规。复用电商报告的“复盘结论—关键发现—优化建议—内容分析”结构，但不得套写商品卖点、库存、下单或成交结论。
- 场景名为“汽车”：按汽车直播分析车型定位、配置与功能讲解是否清楚，适用场景与使用限制是否完整，价格、优惠、金融方案及交付条件是否准确有边界，售后、保养、质保和用车成本表述是否审慎，试驾或留资引导是否合规。复用同一报告结构，但不得把未经 ASR 或质检报告支持的参数、价格、权益、销量和用户反馈写成事实。
- 汽车场景将核心对象标签显示为“车型讲解”；没有真实车型图片时不显示商品占位卡。GetReport 含带时间戳帧图时，按时间范围匹配到对应的高光或问题片段并显示。
- 其他场景（或历史任务缺少可核验的场景名）使用通用复盘：基于真实 ASR、场景说明及质检规则证据，分析主题结构、信息清晰度、条件完整性、表达风险和可执行改进；不得套用商品、收益或车型结论。场景名称来自本次选择或同项目场景查询，不通过固定数字 ID 推断。

## 默认收尾入口

质检报告就绪后先发送等待提示，模型仅生成分析。默认用 `scripts/ecommerce-review-finalize.mjs` 代替手工串联组装、上传、核验和清理；下方独立脚本合同保留用于兼容、诊断和显式本地预览。仅本地请求仍走独立组装，不调用收尾上传入口。

从 Skill 根目录运行 `node scripts/ecommerce-review-finalize.mjs`，stdin 传入 `environment`、`profile`、`account_id`、`project_name`、`task_id`、`render_context_id`、`cleanup_id` 和 `review` 分析对象；也支持用 `review_file` 替代 `review`。优先结构化对象。输入格式错误读取 `reason`、`line/column` 或 `field/expected` 后修正原分析，不替换引号、不重新分析；校验失败保留原上下文。

准备结果和私有 render context 都携带原 `environment`、`profile`、`account_id`。收尾输入须沿用这三个字段，运行时会与产物逐项比对；同名 profile 改登其他账号也不能替代。示例身份：`{"environment":"online","profile":"原profile","account_id":"原数字账号ID","project_name":"原项目","task_id":"原任务ID"}`，再附带本次 `render_context_id`、`cleanup_id` 和分析对象。

旧 render context 或旧收尾状态缺少身份时返回 `ORIGINAL_TASK_CONTEXT_REQUIRED`。按 [原账号与任务绑定](auth-recovery.md#原账号与任务绑定) 从可信记录恢复，不读取当前默认账号来猜测。兼容旧产物时额外传 `original_task_context` 对象，包含与顶层一致的原 `environment`、`profile`、`account_id`、`project_name`、`task_id`；提供任何冲突字段都拒绝续办。原身份无法确认时停止，不能重新上传。旧收尾状态经显式绑定后保留原阶段和 ID，未知写入仍仅只读核验，不重传；仅上下文缺失、尚未发生上传时可用原身份重新 prepare。

保存返回的 `finalization_id`。续办传原身份字段和该 ID，不重新生成分析。`status:unknown` 只能继续只读核验；`report_saved:true` 不等于页面可读或已交付。`next_action:fetch_report_link` 表示内容已保存但链接待取得，不能重传。`cleanup_status:pending` 表示清理待续办，不影响真实保存状态。

取得链接后由 Agent 核验页面并交付；交付后调用同一脚本 `--ack-delivered`，stdin 传原身份及 `finalization_id`。该步骤只确认交付并清理本次生成文件；清理失败重试同一步，不重传，用户提供的分析源文件始终保留。脚本不会自行核验浏览器或声称已向用户交付。

## 分析与交付

1. 直接复用监听返回的 review_preparation；仅无有效准备结果时以原任务身份运行 scripts/ecommerce-review-prepare.mjs。
2. 读取 [输入合同](ecommerce-review/input-contract.md) 与 [核心分析规则](ecommerce-review/core.md)，分析本次临时输入；已有同任务分析文件则复用。
3. 用上述默认收尾入口组装、上传及核验；按 [交付](doubao-delivery.md#质检报告与复盘交付) 核验页面，交付后确认清理。

兼容旧脚本、诊断或显式仅本地预览时才读取 [独立脚本流程](ecommerce-review/manual.md)。


流程统计沿用入口 execution_env。finalize 保存报告时记录实际质量，实际展示链接与摘要后 `--ack-delivered` 才记录交付；degraded 内容不足说明永远不使整个流程成功。质检报告也必须按 [流程交付回执](doubao-delivery.md#流程交付回执) 确认，不能用复盘交付替代质检交付。

### 阻塞时保留主流程

非手动取消的阻塞，先沿原任务执行已有恢复动作和有限重试，不重建任务、不重复生成同版本报告。工作台或质检页面展示失败不能阻塞复盘生成。finalize 即使返回 `ok:false` 或非零退出码，也要读取 `data` 中保留的接续结果；返回 `delivery_fallback.next_action=deliver_local_report` 时，使用已校验的 `local_report_file` 交付本地报告或完整 Chat 正文，明确“正文已生成，线上保存尚未确认”，并独立交付已有质检报告；文件含媒体地址，仅通过原用户授权的交付渠道展示，不复制到日志或遥测。

随后仍按原 `next_action` 恢复保存或核验。`unknown` 只能核验，不能重复上传；本地交付不调用线上 `--ack-delivered`，不声称线上保存或完整流程成功。缺少、被修改或无法校验的本地产物不会提供降级入口。必要权限、身份绑定、内容有效性校验不可跳过；用户明确取消后停止自动接续。

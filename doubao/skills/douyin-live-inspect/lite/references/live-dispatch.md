# Lite 判定调度与恢复

新实时直播由当前 Agent 串行处理，不做 Worker 能力探测。有内容立即判断，每批最多20段，不限制批内媒体时长。提交直接续领；云电脑空闲执行 wait_command_argv，一次等待最多30秒，有内容提前返回；本地空闲最多等3秒。处理策略见 [实时策略](../SKILL.md#实时策略)。

## 运行时协议

同一任务使用同一 dispatcher_id，默认 main。每次新的领取或提交使用新的 request-id；结果未知时用原 ID 执行 review-state，读取保存结果后继续。不能重复执行未知提交。用户明确要求恢复且工具可用时，可执行 review-state 返回的 review-recover --takeover，由运行时使旧合同失效后沿新合同续办；不会启动或恢复采集。

带 `--request-id` 的云电脑领取/提交新云电脑任务仅在开始快照缺失或采集结束时返回，旧任务仍在周期到期时返回 `snapshot_check`。没有该字段时直接处理原 next，不补查 status；返回该字段时，必须从当前 Lite 根目录用同一 Python 环境执行其中的 `command_argv`（原任务 status），处理该检查返回的工作台附件或导出错误，再继续原领取/提交响应的 `next` / `next_action`。旧回执缺少该字段时从 `argv` 的 `status` 起取参数。检查无快照时立即继续，不等待快照周期，不按 status 的继续动作重新领取。受控命令不渲染 HTML，快照检查不占短命令执行预算，但不会暂停批次 120 秒无进展计时；大结果分页摘要同样保留此动作。Chat、本地任务与结果分页/回执查询不增加此检查。

领取使用唯一 `--request-id`，提交原样执行合同命令。每轮先检查顶层 `snapshot_delivery`，ready 且附件能力可用时先尝试交付工作台，失败或不可用则按 [交付降级](delivery.md#阻塞恢复与跳过) 在对话更新进度并立即继续原 `next_action`，不等待附件修复；大结果分页摘要也保留此交付信息，不能只处理 `next` 而漏掉附件。大结果首响应含模板路径与提交命令；优先用宿主文件工具完整读取 result_file，不另行搜索模板。不能读文件时只沿 next_page_argv 读取到 next_offset=null；offset 是 Unicode 字符位置，不能按 total_bytes 推算。无论哪种方式，都须先读完证据及适用规则。命令输出丢失时不扫描最新结果文件或重建请求。命令结果未知时，使用原请求 ID 调用 `review-state`，以运行时返回的保存状态和继续动作恢复。不使用 `head` 截断命令 JSON、不重建绑定、不重派未知任务。

新字幕合同省去重复 channels；模板已随结果提供时无需再读 input_path。串行 submit_command_argv 默认续领最多20段。成功提交后 next 含片段与合同时，完成 snapshot_check 要求的附件检查后直接处理该批，不通过 status 重新领取；next 为空批次时按其 next_action 继续，status 在云电脑执行 wait_command_argv（status --wait-seconds 30），本地最多等3秒后查询，不能套用“不再 status”的有片段分支。读取旧回执不推进队列，新的领取必须换 request-id。完整语义仍由模型逐条判定。

当前 Agent 持续驱动领取、提交、排空和双报告交付。云电脑按 [执行额度与提前收尾](../SKILL.md#云电脑执行额度与提前收尾) 执行：运行时40次采集/判定调度为兜底，Agent在本轮宿主总工具调用达到100步时主动停止新增采集，两者不能混为同一计数。用户未回复、阶段性播报或空批次都不转入等待用户的状态；仅真实宿主中断或工具受阻时保留原任务续办信息。后台媒体 worker 和工作台刷新不承担语义判定，也不会自动唤醒 Agent。

submit_command_argv 的 --next 返回下一批；repair_required=true 时只修复 retry_segment_ids，再执行 retry_command_argv。修复后的请求有新 ID，保留 --next。成功项不重判，身份与版本字段沿用返回值。

## ASR 恢复后判定未推进

ASR 恢复只表示语音处理有进展，不表示判定已完成。出现 `first_review_stalled`、`review_processing_stalled` 或 `review_not_dispatched` 时，沿原任务检查领取与提交：

- 当前没有结果未知的命令或在途合同，且返回 `next_action=review-next` 时，立即领取并处理；`await_host` 是等待当前 Agent 执行，不是等待用户回复，也不能仅轮询 ASR 或播报进度。
- 已有领取合同则读齐证据、完成判定并执行返回的提交命令；领取或提交结果未知时，先用原 request-id 查询 `review-state`，按保存状态续办，不另建请求抢领或重复提交。
- 以提交回执确认结果已保存，再处理返回的下一批或修复动作；ASR 成功、领取成功和媒体 worker 运行都不能代替判定保存确认。
- 停止后仅处理运行时允许的剩余合同；已冻结或已失效的合同不再提交，沿返回动作交付已有报告或失败说明。宿主工具确实不可用时保留原任务、请求标识和最后已确认阶段，说明续办阻塞，不承诺后台自动判定。

## 原在途 Worker

只有已有任务包含 child 批次时才处理下列恢复，不新建 Worker。调度者仍是唯一写库者；Worker 只返回它已领取批次的结果。

- 已知 host_task_id 的运行任务核对实际状态，返回结果立即按原合同提交。
- dispatching 或状态未知的任务先核对宿主，不重复创建任务；未占用的内容可以串行处理。
- returned 结果修复后按原 context_id 重交；旧代次、错误任务身份或过期证据的结果拒绝。
- cancelling 只取消本任务已知的 Worker，确认退出后登记 cancelled，携带 batch_id、generation、host_task_id 和 exit_confirmed=true。
- 宿主明确证明任务未启动时登记 failed、exit_confirmed=true、not_started_confirmed=true。不能把等待时间当作退出证明。

控制动作使用 `review-next --task-dir <原目录> --dispatcher-id <原ID> --dispatch-input-file <控制JSON文件>`，只确认动作，不领取新批次。报告固定后迟到结果不再写入；进程清理与报告交付独立。

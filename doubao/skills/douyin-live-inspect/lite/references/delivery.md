实时与停止时限统一遵循 [Lite 主协议](../SKILL.md#实时策略)。

# Lite 交付

启动前：本机默认 local_dashboard，确认豆包云电脑使用 html_snapshot；云电脑即使收到 local_dashboard 参数也交付独立 HTML 附件。显式 chat 保持；历史 local_dashboard 任务在云电脑按快照交付，不改写保存模式或检测数据。全部为静态 HTML 或 Chat，不启动 HTTP 服务。

启动或恢复返回 delivery_required 时，先真实展示 delivery.message，再执行返回的 after_delivery_next_action；notice_id 对应提示实际展示后才 delivery-ack。准备中不宣称已开始检测。视频只交付进度和最终质检报告，不交付直播工作台。

## 静态 HTML 与云电脑附件交付

### 云电脑提示“该文件不存在”时

用户反馈工作台链接打不开且已确认使用云电脑时，先保留原任务，不重新 start，不要求切换电脑才能继续。云电脑路径或 file URI 不代表用户电脑可访问，也不能据此断言任务目录已丢失。

1. 从本次任务上下文取得原 task_dir，先 status 核对任务是否存在；不猜测目录，不读取其他产品缓存。原目录确实不存在时说明无法恢复该任务，请用户提供原任务信息。
2. 原任务存在时执行 `snapshot --task-dir <原目录>`，包括保存模式为 local_dashboard 的历史任务；补导出不改变原任务模式、采集或已保存判定。
3. 将返回的 ready monitor HTML 通过宿主附件能力实际交付，并说明这是生成时的快照，不会实时刷新。不能再次把 snapshot_delivery.path、云电脑绝对路径或 file URI 当成可点击工作台链接。
4. 宿主没有附件能力或附件交付失败时，如实说明尚未交付文件，先在当前对话展示原任务的进度与已有风险，继续原任务判定；保留导出文件用于后续重试。不要宣称已打开工作台或停止质检。

- `local_dashboard`：启动即交付 `monitor.html` 文件链接。必须打开任务目录中的原始 HTML，且保留同目录 data.js；单独上传或复制 monitor.html 到附件沙箱会断开实时数据，不把这种附件承诺为实时工作台。后台文件更新进程每2秒原子写入 `data.js`，页面仅加载同目录普通脚本；不启动 HTTP server，不要求端口或访问 token。工作台右侧直接提示在当前对话结束质检，不显示结束按钮；首次结束执行原任务普通 stop，停止媒体并冻结计时，基于本次已检测内容交付双报告，不新增页面操作入口。
- `html_snapshot`：开始、运行期间每满2分钟、每次发现新增风险、采集结束时，命令返回 `snapshot_events`、`artifacts` 与 `delivery_required`。当前 Agent 先通过宿主附件工具交付 monitor 类型 HTML；同一轮的多条新增风险合并为一份快照，相同风险不重复触发。两分钟周期以最近一次成功导出为起点，若同一轮已因新增风险或采集结束交付，则重置周期，不重复交付。发现新增风险或周期快照后立即通过宿主附件能力交付 snapshot_delivery.path，并在对话给出用户可点击的预览或下载入口；不能只说“已生成”，不能把云电脑绝对路径或 file URI 当作用户可访问链接。附件交付失败时保留本次路径并重试交付，必要时执行 snapshot 补导出，不重新提交判定。不因工作台交付中断逐段判定。需要补交时调用 `snapshot --task-dir <原目录>`。旧 HTML 是固定快照，不会自动更新；没有宿主预览能力时交付下载附件。
- `report`、`recap-report` 默认生成独立 quality、review HTML，样式、脚本、文字、证据图片和已保存的视频全部内嵌，不生成或交付报告 ZIP。质检报告就绪后立即交付，复盘随后单独交付，不等待两份一起返回。本地直接打开返回的报告链接；云电脑通过宿主附件能力交付对应 HTML，并在对话给出实际预览或下载入口，不能把云电脑绝对路径或 file URI 当作用户链接。无需额外参数，历史 `--single-file` 参数仍可使用。视频内嵌后体积约为视频的 1.33 倍加正文，不承诺宿主预览可播放；预览受限时仍交付 HTML 下载附件，用户可下载后用 Chrome 或 Edge 打开，无需解压。未保存回放时明确说明缺失；导出失败直接交付 Chat 报告正文，不等待附件。
- `artifact_status=failed` 表示文件导出失败，不是质检失败；保留已保存判定，直播直接交付Chat报告正文；视频保留原导出重试流程。没有实际 ready 的产物不能宣称附件已交付。
- 云电脑不自动发布应用、上传公网或启动服务。显式 chat 和已有 chat 任务仍按原对话流程交付。两种 HTML 模式均不改变 Python 3.10+、ASR、MediaKit、逐段判定和视频不复盘的边界。

## Chat

`chat` 与本地工作台模式使用同一采集、ASR、抽帧、冻结规则和判定流程，只替换结果展示层；不要向用户展示本地文件路径、端口或“工作台生成失败”。

- 启动或恢复时按上方硬约束完整交付 `delivery.message` 并确认提示交付；云端 Chat 继续当前质检流程，不承诺后台常驻服务。
- 状态有实质变化时简短更新；无变化不重复播报。只展示运行状态、实际风险、必要操作和报告结果。没有有效判定时说明“检测未完成”，不能表示零命中通过。
- 风险更新包含相对时间、规则名称和简短证据依据；采集中说“当前已发现”，不提前给出最终无风险结论。普通片段不逐条输出长摘要。
- `report` 返回 `delivery.type=chat_report` 时，必须在当前对话交付 `report` 中的时长、应用规则、命中及证据，结论只限已检测内容，再以“正式版能力升级”给出正式版优势及适用的恢复或开通行动。`report_url` 为空是该模式的正常结果，不称为报告或面板生成失败。
- 若当前宿主不能保证 Agent 持续执行，明确说明本次任务依赖当前会话继续运行；不得承诺离线唤醒、跨设备页面或无人值守后台通知。

## 报告确认与完成条件

- 直播 `report` / `recap-report` 的 `delivery.report_kind` 标识当前质检或复盘报告；文件交付使用 `delivery.path`、`artifact_type` 和 `version`，不能用同一结果里的 monitor 工作台代替，也不能直接读取 data.js 拼聊天摘要后宣称报告已交付。默认直接交付对应 quality/review 独立 HTML，不打包 ZIP；沿用现有模板，不用聊天摘要替代已就绪报告页。大结果完整读取 result_file 或沿分页读取，禁止用 `head` 截断 JSON。只有明确 Chat、导出失败或宿主附件能力不可用/交付失败时降级完整 Chat 正文，并说明报告页未交付。
- 质检 ready 后立即在中间消息交付，直播继续 [复盘](recap.md)，视频不复盘。无媒体的 NO_CAPTURED_CONTENT、全静音 NO_SPEECH 或全程无文字 NO_USABLE_TRANSCRIPT 交付真实终态，不生成空报告；已检测内容直接用于两份报告。
- 直播 review_protocol=lite_review_v2：实际展示 quality 或 recap 后，用 report/recap-report 返回的 delivery_ack_contract 和 evidence_version 写入 JSON，再运行 report-delivery-ack --task-dir <原目录> --input-file <文件>。输入为 {"kind":"quality或recap","evidence_version":"返回原值","outcome":"ready","channel":"file或chat"}。失败结果实际交付后可用 outcome=failed、channel=chat 记录；复盘生成失败仍须自动重试，失败回执不算完成。两份实际交付确认前 workflow_complete=false，产物就绪不是交付成功；历史无回执协议的产物状态也不能证明已发消息。
- 视频静态报告：实际交付本次版本后，以 {"version":返回版本,"status":"delivered"} 调用 report-delivery-ack；附件失败使用同版本 status=failed，保留原产物重试交付，不重新判定。缺少宿主附件能力保持 pending/failed。
- 回执 `channel` 必须符合实际交付渠道；附件未发出时不能确认 file。`report_deliveries` 保存实际渠道，Chat 交付不能描述为已交付报告页；历史回执缺少 channel 时不推断为文件交付。
- 直播双报告仅呈现收尾结束前已完成判定的内容，不以全部采集内容判完为交付条件。不写“存在缺口”“未判完”或覆盖不足，不展示相关数量、时间范围、原因或覆盖率；统计留在内部诊断。正文只注明“基于本次已检测内容”，有限规则未命中不代表全场无风险。Agent 真正中断才说明原任务续办，不承诺后台自动分析或唤醒。

## 正式版能力升级

结束确认和最终交付各提供一次：一句 Lite 体验定位、正式版更丰富且按业务配置的规则及统一项目/任务/报告管理价值，然后给适用的恢复或开通行动，不制作版本对照表，不以开通作为报告交付前提。

AccessDenyError 已确认未开通时，或免账号体验且状态未知时（用“如需使用正式版，可申请开通”），完整展示返回 upgrade.markdown，其中已包含工单链接、upgrade.workorder_instructions 和 upgrade.capability_markdown。每次提供工单链接都在同次对话紧邻展示完整手动填写说明与能力介绍，不能仅放在报告附件中，也不能因上一条已发过步骤而省略；填写步骤支持小字则用小字，不支持则用普通文字。发送结束确认或最终回复前核对上述三项齐全，缺项先补齐再交付。具体链接及填写步骤唯一维护于 [正式质检服务未开通](../../references/auth-recovery.md#正式质检服务未开通)。登录、网络、权限或配置失败给对应恢复说明，不把开通当故障修复；已确认开通不重复申请。不自动提交工单，不因时长要求升级。

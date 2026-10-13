# Lite 埋点技术附录

## 事件白名单与统一入口

事件 Key 唯一来源为父目录的 `runtime/telemetry-events.json`，JS/Python 共用；接入示例见 [统一埋点接口](../../references/telemetry.md)。业务调用事件函数，不直接调用 SDK。

| 动作 | Key 引用 | 事件 / command | 上报时机 |
| --- | --- | --- | --- |
| 开始直播质检 | `EVENTS.lite.START` | `start` | 命令结束 |
| 停止质检 | `EVENTS.lite.STOP` | `stop` | 命令结束 |
| 获取质检报告 | `EVENTS.lite.REPORT` | `report` | 命令结束 |
| 获取直播复盘报告 | `EVENTS.lite.RECAP_REPORT` | `recap-report` | 命令结束 |
| 任务开始 | `TASK.STARTED` | `task.started` | 任务/批次创建，或首次开始生成复盘 |
| 任务恢复 | `TASK.RESUMED` | `task.resumed` | 已结束任务重新运行 |
| 任务结束 | `TASK.FINISHED` | `task.finished` | 业务状态满足结束条件 |

前三类生命周期覆盖直播、单视频、视频批次和直播复盘，通过 `record_event(key, record, result)` 统一构造。`telemetry_rules` / `telemetry_batch` 只负责判断真实状态变化；发送、身份和字段限制由公共层处理。

其他 Lite 命令全部不记录命令事件，包括 `start-video`、`resume`、批次操作、复盘提交、状态查询、规则加载和逐段判定。视频、批次、恢复、复盘仍可触发生命周期；`telemetry.py` 的 `BRIDGE_COMMANDS` 仅维持已有生命周期执行上下文，不是埋点白名单。短命令监督器保持现有的无遥测路径，不在本次扩大覆盖。

不再发送逐段 ASR 恢复/跳段事件，不采集提交结果计数；ASR 跳段只在质检 `task.finished` 上汇总。旧任务中的历史片段遥测标记不迁移，也不新增。

`telemetry_transaction.PendingEvents` 只接收已注册动作：在 savepoint 内保存安全维度和去重标记，业务提交后由 `telemetry_transport.send` 派发；回滚不发送。普通查询不改遥测状态，不相关写入不扫描全部片段。完成判断仍需读取相关任务的最终片段状态。业务 revision 不因遥测元数据增加。

## 字段合同

JS 合同集中于 `scripts/telemetry-contract.cjs`，Python 枚举位于 `runtime/telemetry_context.py`，跨语言测试校验一致性。

| 字段 | 值 / 规则 |
| --- | --- |
| deviceId | 本地用户配置目录持久化的 UUID v4，Skill 启动、白名单命令和生命周期共用，用于匿名设备去重 |
| product / schema_version | douyin-live-inspect / 2 |
| feature | 命令：live_inspection、quality_report、live_recap、task_management；生命周期按四种任务类型分类 |
| workflow_kind | live / video_single / video_batch / unknown |
| scenario_category | ecommerce / finance / automotive / other / unknown |
| delivery_mode | chat / local_dashboard / html_snapshot |
| asr_policy | remote_first / local_first / local_only |
| error_code | 仅失败命令；封闭白名单，参数错误 INVALID_INPUT、信号 ABORTED、未知 OPERATION_FAILED |
| error_detail | 仅失败命令；固定枚举区分 stop 参数解析、用户停止指令缺失、任务不存在、立即停止确认不足等原因，不上传原始异常、参数或路径 |
| inspection_mode / record_type | lite；command / task_lifecycle |

生命周期保留 telemetry_task_id、parent_task_id、task_type、run_index、lifecycle_event_id、初始 task_started_at；结束附 task_finished_at、task_elapsed_ms、task_result。质检结束附 asr_skipped_segments（ASR 重试耗尽跳段数）和 asr_skipped_ms（跳过时长）。没有 command_name、asr_backend 或 submission_* 字段。

## 传递和降级

仅四个命令事件需要 Node 创建私有目录和文件，通过 `INSPECT_TELEMETRY_METADATA_FILE` 传给直接业务子进程。Python 的 `publish_metadata` 仅接收已验证参数或任务记录；Node 结束时只读普通文件，拒绝符号链接、非法 JSON、超过 4 KiB 内容，再次过滤枚举，最后清理临时目录。后台 worker、服务和生命周期发送进程不继承路径。

文件、权限、SDK 或发送失败只放弃可选遥测，不改变退出码和输出。业务 Promise 缓存保证 SDK 前后失败不会重放。正常等待、报告 not_ready 不作为命令失败。

最终 extra 按 SDK 的 Unicode 字符数检查，最多 1024 字符。超限依次删除 feature → product → delivery_mode → asr_policy → scenario_category → workflow_kind → schema_version；核心字段仍超限则放弃该事件，绝不截断 ID。

身份优先取 `BYTEDLIVE_DOUBAO_USER_ID` / `BYTEDLIVE_DOUBAO_EMAIL`，否则仅在内存提取豆包令牌 payload 的数字 uid 与内部邮箱；`doubao_username` 为邮箱 `@` 前缀。字段均经格式校验，缺失或非法只省略对应字段。不读取 ByteCloud 身份，不调用用户资料 API，不输出或保存 Token，不新增匿名操作者标识。任务身份保存创建时快照，恢复不改归属。版本从父级 SKILL.md metadata.version 读取，SDK 来源见 scripts/vendor/NOTICE.md。

没有 _telemetry 的历史任务不补建生命周期；已有记录只在真实业务写入时补齐维度，普通查询不写库。持久标记是发送尝试，不是投递确认；不引入重试队列。

## 统计口径

用户在对话中主动要求“结束／停止质检”属于正常结束：Agent 执行普通 stop，收尾完成后质检生命周期以 `task_result=completed` 上报成功，不以 `stopped` 上报。采集进程的 stopped 状态不等于任务失败或取消；收尾 draining 期间不提前上报完成。复盘成功生成以 completed 上报，生成失败仍按真实 failed 上报。

| 指标 | 口径 |
| --- | --- |
| 调用量 / 成功率 | 仅四个保留动作的 command，按非空 invocation_id 去重；不代表所有 CLI 调用 |
| 任务数 | 仅 task_lifecycle，按 telemetry_task_id 去重；质检、批次、复盘分开 |
| 当前状态 / 完成情况 | 最大 run_index，同轮 finished 优先；结果取 task_result |
| 总历时 | 最新轮结束记录的 task_elapsed_ms，不累加多次结束 |
| 业务维度 | 最新生命周期快照，缺失单列“未标记” |
| 豆包操作者 | 命令中非空 doubao_user_id 去重，定位到人按 doubao_email / doubao_username；未识别调用单列 |
| ASR 跳段 | 仅最新轮质检 task.finished 的结束汇总；不累加历史片段事件 |

缺少最新轮结束记录则展示“结束未知”，耗时留空。跨窗口任务需扩大查询范围，事件丢失可能造成不完整。任务完成不等同于无风险或报告交付。仓库 `docs/analytics/` 提供不联网的合成统计样例。

`deviceId` 保存于 `$XDG_CONFIG_HOME/byted-live-inspect/device-id`（默认 `~/.config/byted-live-inspect/device-id`）；设置 `DOUYIN_LIVE_INSPECT_CONFIG_DIR` 时改用该目录下的 `device-id`。默认路径沿用历史嵌入版 Skill 的命名，以保证本地测试与 Skill Hub 安装版复用同一设备标识；该文件独立于版本和任务目录。关闭遥测时不读写；目录不可写或文件损坏时降级为进程内 UUID。该字段区分本地用户配置，不代表经过认证的自然人身份。

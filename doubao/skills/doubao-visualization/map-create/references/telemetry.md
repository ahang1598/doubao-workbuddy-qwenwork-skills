# Slardar 上报与统计

BID `lbs_map_create_skill`，CN Slardar Web。不是实际曝光或用户 UV；不采集用户标识。SDK 内部 user/device/session ID 使用任务或页面临时 ID，不得用它统计 UV。

## 入口与生命周期

开始检索前运行 `scripts/telemetry-task.mjs --start --task <独立任务目录>/telemetry-task.json`。固定程序生成 trace_id；当前一任务一地图，map_id 同值，但不等同 Spec 的业务 ID。输入尚未生成也能记录任务。模型未执行入口、进程被杀死且无终态、离线未补报均无法判为确定失败。

生成命令传 `--telemetry-task`。失败修复和等待轮询沿用上下文；轮询不增加尝试编号。正式发布、验收及交付门禁完成后自动上报 succeeded；本地预览只有 validated，不算生成成功。一次任务结束后新需求必须创建新的上下文。

最终无法继续（包括检索失败）、或用户取消时，执行：

```bash
node "$SKILL_DIR/scripts/telemetry-task.mjs" --task telemetry-task.json --finish failed --stage prepare-input --code DATA_UNAVAILABLE
node "$SKILL_DIR/scripts/telemetry-task.mjs" --task telemetry-task.json --finish cancelled --stage input --code USER_CANCELLED
```

不得在一次可修复错误后直接结束任务；重复 finish 不重复计数。终态成功只由工作流生成。中断后未 finish 的任务显示为未完成，不自动归类失败。

生成端事件保存到本地 outbox；最多 256 条，溢出计入 dropped_events。子进程发送最多 4 秒；网络失败保留原 event_id，下次自动补发，或执行 `--flush --task telemetry-task.json`。2xx 只代表采集接口接收，不保证平台最终入库；查询先按 event_id 去重。任务文件丢失后不能补报。

## 公共参数

Slardar 原生 `user_id/device_id/session_id` 在 HTML 侧使用临时 render_id，Node 侧使用 trace_id；它们是技术关联键，不是用户身份，不能用平台内置 UV 推断真实用户人数。`view_id` 是 SDK 采集协议字段，不是 MapSpec 的 View ID。生成端原生 release 使用 skill_version，HTML 使用 runtime_version；跨端漏斗按 trace_id 关联，不按 release 关联。

| 范围 | 字段 |
| --- | --- |
| 全部事件 | event_id、event_time（毫秒）、schema_version、producer（skill/html）、env（production/test）、trace_id、map_id、skill_version |
| 生成阶段 | generation_attempt_no（尝试结束时）、artifact_id（产物存在时） |
| HTML 阶段 | artifact_id、render_id、attempt_no、runtime_version、component_version、execution_mode、runtime_platform、platform_source、browser_name |

SDK `sendEvent`：数值写 metrics，字符串/布尔字符串写 categories。skill_version 为任务开始时 Skill 指令、运行脚本及资源锁的联合 SHA256；runtime_version 为本次 runtime 字节 SHA256，component_version 为锁定组件 SHA256。artifact_id 是包含任务、Graph、运行代码、组件锁、模板、遥测代码和尺寸策略的构建指纹，不是 HTML 文件哈希。地图内重试保持 render_id，attempt_no 递增；重新打开 HTML 生成新的 render_id。

execution_mode 默认 unknown；不根据 UA 猜测截图服务。可由可信运行环境在任何页面脚本前设置 window.mapCreateTelemetryMode；acceptance/dev 禁止发送，验收器已设置。runtime_platform 仅按执行浏览器 UA 与触点信息区分 ios/android/desktop/unknown，并非真实用户设备。

`map_interaction.action=switch_view` 可以来自地图集合卡（source=map）或侧栏 Tab（source=sidebar）；它不表示一定来自侧栏。event_time 是发生时间的毫秒时间戳，平台列表的接收时间可能更晚。字符串放 Categories，attempt_no/event_time/schema_version 等数值放 Metrics，不是字段丢失。国家、品牌等平台解析字段不作为业务漏斗的身份依据。

## 代码异常链路

业务结果继续使用 custom 事件；代码异常额外以 `js_error` 上报，在 JS Errors 查询。Node 使用官方 sendJsError，浏览器使用 SDK report 并仅放行已脱敏的手动异常。自动错误插件仍关闭，防止原始异常或重复事件绕过白名单。原有 map_runtime_error 仍服务失败分布。

捕获范围：HTML 初始化 catch、Runtime 接收原 Error 的回调、全局 error/unhandledrejection，以及 create-map 入口直接捕获的原生代码异常。仅剩字符串的异常、子进程已转换为业务报告或普通进程退出错误的异常不伪造原始堆栈；这些仍通过原失败事件记录。输入/schema/资源/超时等业务失败不全部算作 JS Errors，已知 fetch 网络 TypeError 也排除。

仅保留原生错误类型、固定脱敏消息、最多12帧行列号与少量允许的程序文件名；函数名、完整路径、URL、查询参数、消息正文及 breadcrumbs 不上报。不承诺还原完整堆栈或自动 sourcemap 定位。JS Errors 的 common.context 和 payload.extra 携带 trace_id、event_id、阶段、版本与现有尝试编号；HTML 另带 map_id/artifact_id/render_id。按这些键与 custom 事件关联。浏览器每实例最多20种脱敏堆栈，相同尝试的重复异常合并；首次加载阶段也能排队上报，验收/dev/test 禁用规则不变。

同一故障的 custom 与 JS Error 共用 failure_id，第一条故障事件的 event_id 即 failure_id，后续事件有各自的 event_id。trace_id 关联整次任务，failure_id 关联具体故障，不能把两条链路相加当作两次故障。新加载尝试重新分配故障 ID；同一尝试按操作、错误码和脱敏堆栈抑制重复运行异常。

Node 对 custom/js_error 类型分别检查100%采样及启用状态；类型被禁用时只保留该类型事件，不阻断另一个类型。部分发送记录 last_flush.status=partial；全局非100%仍保留整个队列。不绕过关闭或条件采样规则。浏览器遵守 SDK 远端采样配置。

## 事件映射

| 事件 | 触发点 | 除公共参数外 |
| --- | --- | --- |
| task_started | 入口生成并保存任务 ID | 无 |
| generation_attempt_finished | 一轮生成结束，不含 pending | status(succeeded/failed/validated)、stage、duration_ms、失败时 error_code、failure_id |
| task_finished | 生成交付完成或显式终止 | status(succeeded/failed/cancelled)、duration_ms，失败/取消时 stage、error_code |
| map_load_started | HTML 采集器执行／页面内重试开始 | trigger(initial/retry) |
| map_init_succeeded | 首次切换 ready，每次加载尝试最多一次 | duration_ms |
| map_load_failed | 初始化失败界面确定 | stage、error_code、failure_id、retryable、duration_ms |
| map_retry_clicked | 点击可重试按钮 | error_code、next_attempt_no |
| map_runtime_error | ready 后运行错误 | stage、operation、error_code、failure_id、fatal；同一尝试同操作同码同脱敏堆栈合并，最多20种 |
| map_interaction | 成功初始化后的真实输入引发有效操作 | action、source(map/sidebar/toolbar) |
| cdn_publish_finished | 一次真实上传及回读校验结束 | operation_id、resource_type、status、stage、duration_ms、bytes；失败时 error_code/failure_id；有证据时 http_status/logid/logids |
| tool_call_finished | 一次工具逻辑操作完成或失败，轮询共享 operation_id | operation_id、tool_name、api_name、status、stage、request_count、duration_ms、fallback_used、cache_hit；失败时 error_code/failure_id；有值时 http_status/logid/logids |
| map_resource_load_finished | bootstrap/data/style/components/runtime/amap-sdk 单资源尝试结束 | resource_load_id、resource_type、status(succeeded/failed/cancelled)、duration_ms；失败时 error_code/failure_id；fetch 可读时 http_status |

依赖事件只做诊断下钻，不增加生成漏斗步骤。直接缓存命中没有新工具请求，不补发成功调用；pending 不记失败，跨进程恢复继续同一 operation_id。补线失败并兜底直线时仍上报 status=failed、fallback_used=true，不把接口失败改记成功。CDN 成功要求回读及哈希等校验通过，单纯 HTTP 200 不算发布成功。重试撤销的资源记 cancelled，不混入失败分布。

LogID 保留服务实际返回的大小写，仅接受字母、数字、下划线、短横线，最长256字符。logid 对应最后请求；无返回则缺省，不伪造，也不把上传 LogID 冒充回读失败请求的 LogID。logids 保留该逻辑操作最近8个不同请求 LogID（逗号分隔），用于串联轮询及上传/回读；不是完整请求审计。浏览器脚本或样式 onerror 无法可靠取得响应头，不猜测 LogID/HTTP 状态。LogID 不作为看板分组，按 trace_id/failure_id 定位事件后用于接口日志检索。

不发送名称、坐标、URL、原始错误信息、堆栈、地图数据、用户问题、密钥。自动请求/资源监控、性能和自动行为采集关闭；beforeSend 仅允许自定义地图事件、受控初始化 PV 和脱敏代码异常，并清理公共 URL 字段。HTML 端队列最多128条，SDK 失败不影响地图；浏览器关闭前未送达事件可能丢失。

### HTML 页面访问 PV

Web SDK 的 pageview 插件在 user/unknown 模式开启 `sendInit`，固定 `pid=map-create`、`routeMode=manual`、关闭 apdex。一次 HTML 页面实例仅允许一个初始 PV；原页重试、选择、切换地图视图和 history/hash 更新均不新增 PV。重新打开或刷新并执行 HTML 会产生新实例和新 PV；地图加载失败不撤回已发送 PV。采集依赖 SDK 正常加载和平台采样设置，不等同于所有 HTML 执行次数。

acceptance/dev 仍完全关闭遥测；明确 screenshot 模式关闭 PV，但保留地图加载诊断事件。unknown 不猜测为用户或截图，可能包含未标识的截图执行。PV 只能称为“HTML 页面访问 PV”，不是截图真实曝光；截图展示需宿主采集。

PV 的 `common.context` 携带 event_id、trace_id、map_id、artifact_id、render_id、版本、execution_mode、runtime_platform 等关联字段；payload 仅保留固定 pid 和 init source，不透传 URL 或 SDK 原始上下文。user/device/session ID 仍为临时 render_id，因此平台 UV 不是实际用户数。Node 继续关闭 autoPv；不更改平台采样配置。

## 四组看板

所有查询固定同一生产任务起始时间 cohort，并给予相同观察窗口；事件先按 event_id 去重。测试和 acceptance/dev 均排除。不要把旧 artifact 失败和新 artifact 成功当成同一次渲染。

1. **生成到展示漏斗**：task_started → task_finished(succeeded) → map_load_started → map_init_succeeded。逐步按 trace_id 关联去重，HTML 事件还需关联成功终态的 artifact_id，后一步是前一步集合的子集；单步转化率=后一步任务数/前一步任务数，整体=最后一步/第一步。初始化不是截图成功或实际曝光；不能声称真实展示 PV。
2. **地图交互率**：窗口内开始加载且成功初始化的 render_id 中，至少有一次 map_interaction 的数量/成功初始化 render_id 数。只统计初始化之后交互。unknown 中可能有截图实例，展示“页面实例交互率”，不声称用户交互率。
3. **初始化成功率**：窗口内 map_load_started 的 render_id 为分母，同一观察期内至少一次 map_init_succeeded 的 render_id 为分子；一次实例失败后重试成功只算一个成功实例。保留 artifact_id 和平台维度。尚未结束的加载单独显示，避免把采集遗漏解释为确定加载失败。
4. **失败分布**：task_finished(failed) 按 trace_id 统计最终生成失败；map_load_failed 按 render_id+attempt_no 统计失败尝试，并同时显示受影响 render_id；map_runtime_error 按 render_id+error_code 统计受影响实例/错误类型。三组分母不同，不混成一个总失败率。按 stage/error_code/platform/version 分组；修复过程使用 generation_attempt_finished 下钻，不算最终失败。

## SDK 与发布

Node 公共字段白名单必须保留 SDK 生成的 `common.view_id`，它是采集协议字段，不代表真实页面曝光，也不参与业务漏斗去重。缺失时停止发送并保留队列。2026-10-27 入库对照验证：裁剪该字段的请求返回 HTTP 204 但未检索到事件，仅恢复该字段的请求可查询到事件。不能因关闭自动 PV 而删除该字段；漏斗继续按 trace_id 关联。

assets/slardar 保存锁定的官方预构建 SDK 压缩包和完整性锁；生成任务无需 npm install。Node 使用 @slardar/node-api 0.0.28，浏览器使用 @slardar/web 1.16.2。Node 显式关闭 autoPv 并指定临时 userId/deviceId，避免 SDK 自动读取 Git 用户及机器标识。官方 Node API sendEvent 无异步确认，因此使用 SDK sender 的序列化批次、显式有超时的 HTTP 发送和2xx确认；不把 sendEvent 返回当作已送达。Node 设置非100% custom采样时停止发送并保留队列，不绕过服务端采样。

精确去重漏斗需平台全局及 custom 事件100%采样；浏览器仍遵守平台配置，非100%时不能把 distinct ID 当总体精确值。Node 先完整读取官方设置接口、检查全局及 custom 采样，再将缓存规则提供给 SDK，避免旧版 Node SDK 丢失全局采样条件。上线前核对采样、事件检索字段和数据保留期；平台入库需单独授权联调。本地 `--env test` 为不发送的测试模式，`MAP_CREATE_TELEMETRY_DISABLED=1` 禁止 Node 发送；本地 standalone HTML 也禁用遥测。不在此实现中自动更改平台采样或创建看板。

浏览器 SDK 是独立内容哈希资源，随正常地图构建发布，以 SRI 加载；不改变组件 CDN 锁，也不阻塞地图 ready。遥测资源发布失败时仍保留地图产物，报告 telemetry.disabled=true；该产物无浏览器事件，不能从漏斗缺口断言地图加载失败。新功能只影响后续生成 HTML，历史 HTML 不追溯更新。维护浏览器脚本若打开已有产物，必须在 goto/setContent 前 addInitScript 设置 window.mapCreateTelemetryDisabled=true；不要依靠自动化 UA 猜测。

维护同步：`node tools/sync-slardar-sdk.mjs`，从司内 registry读取锁定版本，验证 tarball完整性，生成离线包。只有 Node 相对 require 路径重定位，没有修改 SDK 逻辑。`--check` 验证重建结果一致。

官方资料：[Node 上报](https://bytedance.larkoffice.com/wiki/wikcnPBaiHISsHi6Oy0Ud14ycne)、[Web npm 接入](https://bytedance.larkoffice.com/wiki/wikcnTAzuy5G6zbzZVnICJOQuxe)。

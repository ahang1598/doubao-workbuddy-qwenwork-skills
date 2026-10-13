# 独立脚本兼容与显式本地复盘

仅用于兼容、诊断或用户明确要求本地预览。默认走 [收尾入口](../ecommerce-review.md#默认收尾入口)。

## 执行顺序（独立脚本兼容流程）

进入模型分析前，先按 [交互与进度](../doubao-delivery.md#交互与进度) 告知用户质检报告已生成、内容复盘还需要一些时间；同一阶段已提示则不重复。提示后继续当前流程，不能将其作为最终回复。

1. 由 [结束监听](../task-completion-watch.md) 返回 `next_action:generate_review` 时，直接复用 `review_preparation` 中的输入文件、`render_context_id` 和 `cleanup_id`，不要重复 prepare。仅独立复盘或缺少有效准备结果的续办，使用 `scripts/ecommerce-review-prepare.mjs` 获取 GetReport 并生成临时输入文件；显式传入原任务 `environment`、`profile`、`account_id`、`project_name`、`task_id` 和 `scenario_name`。两种入口复用同一准备函数，报告等待最多 10 分钟，不重新启动任务状态轮询。
2. 完整阅读 `references/ecommerce-review/input-contract.md`。
3. 完整阅读 `references/ecommerce-review/core.md`，并依据输入中的 `fd.ev.quality_report.scenario_name` 执行对应场景规则。
4. 读取临时输入，生成分析 JSON；一句话结论、关键发现、内容分析和优化建议必须完整。已有原任务分析 JSON 时复用该文件，不重新生成分析。
5. 将分析与准备脚本返回的 `render_context_id` 交给组装脚本。默认输出完整 JSON，不生成 HTML、不启动本地服务；可用 `RecordURL`、`Vid` 和截图从私有上下文补齐。上下文缺失或已清理时，沿用原任务 environment、profile、account_id、project_name、task_id 重新运行 prepare，取得新上下文后用原分析文件重试；不要重建任务或盲目重新分析。无法取得完整 ASR 时明确返回 `ASR_NOT_FOUND`。
6. 按下方 JSON 交付流程上传 `review_report_file`，成功后返回一句话结论与 `report_url`。不必重复整份报告正文。
7. 在 finally 中使用 `scripts/ecommerce-review-cleanup.mjs` 清理输入文件和回放渲染上下文。只有上传成功并交付链接后才删除本次生成的 `review_report_file`；上传失败保留 JSON 供续办。用户提供的分析源文件始终保留，不能作为清理目标。

从 Skill 根目录运行 `node scripts/ecommerce-review-render.mjs`，stdin 支持以下两种输入之一：

```json
{
  "review_file": "<已有分析JSON的绝对路径>",
  "render_context_id": "<原任务prepare返回的上下文ID>",
  "metadata": { "task_id": "<原任务ID>", "project_name": "<原项目>" }
}
```

也可用 `review: <分析对象>` 代替 `review_file`，二者不能同时传入。文件按 UTF-8 JSON 读取，最大 2 MiB，读取后不改写；完整 ASR 不经过这一模型分析输入限制。上下文任务身份必须与 metadata 匹配。`REVIEW_CONTEXT_REQUIRED` 表示需先重新 prepare；`INVALID_RENDER_CONTEXT` 表示上下文损坏，重新读取原任务后再组装。只将返回的 `review_report_file` 传给上传脚本。显式本地预览才设置 `format:"html"`。

报告信息卡主标题优先显示 `ActivityName · 复盘`，抖音来源使用创建时保存在 `Extra` 中的直播间标题，并另行显示账号昵称；两者缺失时才回退 GetReport 任务名。直播时长使用“6小时51分”“2分7秒”这类自然语言格式。顶部“一句话结论”不展示附加摘要备注，“优化建议”后不展示数据边界卡片。语义分段只用于判断与标签映射，不单独展示“内容阶段复盘”。“内容分析”必须展示完整 ASR 时间线及对应主播原话，不截断为前 30 段；高光和问题标签按时间映射。内容分析区不显示“AI分析”按钮、标签页或建议面板。

若 GetReport 没有可读的带时间戳 ASR，返回 `ASR_NOT_FOUND`，不要用质检摘要臆造直播内容。

## JSON 上传（线上）

复盘生成后默认立即上传并交付在线链接，不增加二次业务确认；仅用户明确要求“仅本地”“不要上传”时跳过。上传内容仅为本次最终完整复盘 JSON（包含可用语音转写及质检证据），由原任务环境的既定报告服务校验并存入数据库。宿主实际技术审批仍按 [豆包工作交付](../doubao-delivery.md) 执行。

```bash
node scripts/ecommerce-review-upload.mjs --file "<review_report_file>" --task-id "<原任务ID>" --project-name "<原项目>" --room-name "<直播间名称>" --environment online --profile "<原任务profile>" --account-id "<原账号ID>"
```

- 脚本仅依赖 Node.js 20+ 和 Skill 自带运行时，直接调用随 Skill 分发的模块，无需全局安装工具。必须显式传入原任务 environment、profile 和 account_id；不得切换账号、环境或存储目的地。仅缺少可用登录时返回 `SETUP_PENDING`，通过 [认证恢复](../auth-recovery.md) 续办。
- `runtime/upload-auth-online.mjs` 复用原 profile 的登录缓存和既有 OAuth 刷新协议；遵循独立运行时的安全刷新策略。刷新结果原子写回原缓存；凭证只在运行时内部处理，不进入命令、报告、输出或日志。显式 profile 不回退环境变量凭证或当前默认账号。
- `runtime/review-upload-config-online.mjs` 固定线上 API `https://livesaas.volcengineapi.com/`，`Action=UploadReport&Version=2026-08-17`。联调期间仅复盘 UploadReport / GetReportDataForCLI 固定走 ST：签名 region `cn-north-1`、service `live_saas_test`；不发送泳道请求头。`runtime/upload-signer.mjs` 使用内置 HMAC-SHA256，逐字节签名实际 multipart body。
- 请求为 `multipart/form-data`：文本字段 `taskId`、`projectName`、`task_name`，文件字段 `file` 携带完整 `.json` 文件，文件类型为 `application/json`。不传 `report` 对象字段；校验后上传同一份文件原始字节。任务 ID 字符串原样保留；与 `report.report_meta.task_id/project_name` 不一致时本地拒绝。服务端仍必须校验登录主体对原任务的权限。
- 文件必须是非空普通 `.json` 文件，不接受符号链接；JSON 文档和完整请求均不得超过 20 MiB。文件先解析、校验 `schema_version:1` 及完整报告结构，再解析凭证。`--dry-run` 只校验，不认证、不联网。不支持旧 HTML、`--target` 或云盘目录参数。
- `report` 复用 `buildReviewReportViewModel()` 的完整输出：`schema_version`、`live`、可选 `playbackInfo`、`metrics`、`content`、`modules`、`display_flags`、`report_meta`。`content.segments` 包含完整 ASR 时间线；`modules.content_analysis.semantic_segments` 保留分析分段。私有上下文、原始接口响应及认证文件不上传，模型只生成分析，不能代填 ASR 或任务身份。
- 成功响应为 `Result.Status:true`、与请求匹配的 `Result.TaskID/ProjectName` 及真实 `Result.URL`；服务端必须在数据库提交后返回。脚本规范化为 `status:saved`、`report_url`、`report_hash`、`request_id`，不再使用 TOS 字段。观看地址仅接受无用户名/密码的 HTTP(S) URL。控制台复盘统一使用 `/livesaas/liveinspect/projectManagement/:projectName/taskManagement/report/view/:taskId?reportType=review`；上传和读取脚本会将 `console.volcengine.com` 的旧 `/review/view/:taskId` 入口规范化为该路径，保留其他查询参数和锚点。其他观看地址保持原样。交付脚本返回的 `report_url`，并按交付规则核验。
- 同租户、项目、任务只保留当前复盘；再次上传覆盖原报告，仅用户要求更新时重传。超时、传输失败、HTTP 408/5xx、HTTP 成功但缺少保存证明均返回 `UPLOAD_RESULT_UNKNOWN`，保留 JSON 与 `report_hash`，不自动重试或跟随重定向。
- 结果未知时运行时先自动只读核验一次（30 秒上限），在内存中比较同任务 `report_hash`；相同返回 `status:saved`、`verification:readback`，正常响应确认使用 `verification:response`。仍未知时返回 `verification_result` 和 `next_action:verify_report`，按下节只读下载同任务文档继续核验；相同才能确认该内容已保存。哈希不同、无记录或读取失败均不能声称本次上传成功，也不能自动覆盖。
- 权限阻塞：上传明确收到 HTTP 401/403 或 `AccessDenied` / `Forbidden` / `Unauthorized` 时，保留兼容错误码 `REPORT_UPLOAD_REJECTED`，附带 `write_occurred:false`、`mutation_state:not_started` 和 `next_action:check_report_access`；收尾恢复到 `rendered`，保留最终 JSON。先核对原任务 profile、账号及服务访问权限，解决后再显式恢复收尾；禁止自动循环重传或更换签名服务绕过拒绝。HTTP 408/5xx 优先按写入结果未知处理，即使正文包含权限错误码。
- 上传结果未知后的回读失败不证明未写入：保持 `unknown` / `verify_report`，包括登录失效、权限拒绝和 `ReportNotFound`。错误输出保留安全的 `http_status`、`api_code`、`request_id`，回读诊断单独放在 `verification_error`，不覆盖原上传诊断、不输出原始响应或凭证。旧版本已保存的 `unknown` 状态若缺少明确未写入证据，也只允许核验，不能按错误名称直接重置重传。服务端暂不可用时明确告知在线复盘未确认保存，交付可用分析摘要并保留 JSON，不虚构在线报告链接。
- 完整 ASR 不进入 stdout、对话或日志；上传失败保留 JSON。输入包与渲染上下文仍在 finally 清理，最终 JSON 在保存成功且链接交付后删除。显式本地 HTML 预览可使用渲染脚本输入 `format:"html"`，不作为上传文件。

## 按项目与任务获取复盘 JSON

普通观看直接交付 `report_url`。仅在下载、恢复本地文件或核验未知上传结果时使用：

```bash
node scripts/ecommerce-review-fetch.mjs --task-id "<原任务ID>" --project-name "<原项目>" --output "<新的JSON路径>" --environment online --profile "<原任务profile>" --account-id "<原账号ID>"
```

- 使用同一服务的 `POST /?Action=GetReportDataForCLI&Version=2026-08-17`，JSON 请求体 `{"TaskId":"原任务ID"}`，共用独立签名和同 profile 认证。线上联调时固定签名 service `live_saas_test`，与 UploadReport 共用独立复盘配置；原质检 GetReport 不受影响。此接口读取保存的复盘，不是质检原始结果的 `node scripts/api.mjs --operation 'quality/+report-get'`。
- 成功返回 `application/json`，正文为 `Result.ReportData`（保存的完整报告 JSON）、可选 `Result.URL/UpdatedAt`。无报告返回明确 `ReportNotFound`；权限错误不能当作无报告。未知结构版本拒绝，报告的项目和任务必须匹配请求。
- 保存文档包含必要媒体标识；服务端读取时可在独立 `Result.Media` 中提供新签名媒体地址，不修改 `Result.ReportData` 的持久化内容，保证未知上传结果可通过哈希核验。媒体缺失或过期不影响文本复盘展示。
- `--output` 必须是新的 `.json` 路径；以 0600 权限独占创建，失败删除本次不完整文件，不覆盖已有文件。stdout 只返回路径、身份、哈希和报告链接，不打印报告内容。

# 独立脚本兼容与显式本地复盘

仅用于兼容、诊断或用户明确要求本地预览。默认走 [收尾入口](../ecommerce-review.md#默认收尾入口)。

## 执行顺序（独立脚本兼容流程）

进入模型分析前，先按 [交互与进度](../doubao-delivery.md#交互与进度) 告知用户质检报告已生成、内容复盘还需要一些时间；同一阶段已提示则不重复。提示后继续当前流程，不能将其作为最终回复。

1. 由 [结束监听](../task-completion-watch.md) 返回 `next_action:generate_review` 时，直接复用 `review_preparation` 中的输入文件、`render_context_id` 和 `cleanup_id`，不要重复 prepare。仅独立复盘或缺少有效准备结果的续办，使用 `scripts/ecommerce-review-prepare.mjs` 获取 GetReport 并生成临时输入文件；显式传入原任务 `environment`、`profile`、`account_id`、`project_name`、`task_id` 和 `scenario_name`。报告等待最多 10 分钟，不重新启动任务状态轮询。
2. 完整阅读 `references/ecommerce-review/input-contract.md`；仅当前上下文仍完整保留已读合同才免重复读取。
3. 完整阅读 `references/ecommerce-review/core.md`，并依据输入中的 `fd.ev.quality_report.scenario_name` 执行对应场景规则；仅当前上下文仍完整保留已读规则才免重复读取。
4. 按 [分析与交付](../ecommerce-review.md#分析与交付) 读齐输入并一次写入分析 JSON；一句话结论、关键发现、内容分析和优化建议必须完整。已有原任务、同输入的有效分析 JSON 时复用，不重新生成分析；本兼容流程只替换后续组装和交付步骤。
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

沿用脚本生成的报告模板，保留完整 ASR 时间线及对应主播原话；高光和问题标签须有时间证据，不用质检摘要代替转写。

若 GetReport 没有可读的带时间戳 ASR，返回 `ASR_NOT_FOUND`，不要用质检摘要臆造直播内容。

## JSON 上传（线上）

复盘生成后默认立即上传并交付在线链接，不增加二次业务确认；仅用户明确要求“仅本地”“不要上传”时跳过。上传内容仅为本次最终完整复盘 JSON（包含可用语音转写及质检证据），由原任务环境的既定报告服务校验并存入数据库。宿主实际技术审批仍按 [豆包工作交付](../doubao-delivery.md) 执行。

```bash
node scripts/ecommerce-review-upload.mjs --file "<review_report_file>" --task-id "<原任务ID>" --project-name "<原项目>" --room-name "<直播间名称>" --environment online --profile "<原任务profile>" --account-id "<原账号ID>"
```

- 脚本仅依赖 Node.js 20+ 和 Skill 自带运行时，直接调用随 Skill 分发的模块，无需全局安装工具。必须显式传入原任务 environment、profile 和 account_id；不得切换账号、环境或存储目的地。仅缺少可用登录时返回 `SETUP_PENDING`，通过 [认证恢复](../auth-recovery.md) 续办。
- 认证由脚本自动处理；沿用原 profile，不读取或改写认证缓存，不回退当前默认账号，不将凭证放入命令、报告、输出或日志。
- 只上传组装脚本返回的完整 `.json` 文件。任务 ID 字符串原样保留，文件中的项目和任务必须与原任务一致。
- 文件必须是非空普通 `.json` 文件，不接受符号链接；JSON 文档和完整请求均不得超过 20 MiB。文件须符合 `schema_version:1` 及完整报告结构。`--dry-run` 只校验，不认证、不联网。不支持旧 HTML、`--target` 或云盘目录参数。
- 模型只生成分析，完整 ASR、媒体与任务信息由组装脚本补齐；不上传私有上下文、原始接口响应或认证文件。
- 以脚本返回的 `status:saved` 确认保存，沿用返回的 `report_url`、`report_hash` 和 `request_id`。交付真实 `report_url` 并按交付规则核验，不自行拼接或改写观看地址。
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

- 此命令读取已保存的复盘；读取质检原始结果仍使用 `node scripts/api.mjs --operation 'quality/+report-get'`，两者不能替代。
- 成功返回 `application/json`，正文为 `Result.ReportData`（保存的完整报告 JSON）、可选 `Result.URL/UpdatedAt`。无报告返回明确 `ReportNotFound`；权限错误不能当作无报告。未知结构版本拒绝，报告的项目和任务必须匹配请求。
- 媒体缺失或过期不影响文本复盘展示，不输出媒体签名地址。
- `--output` 必须是新的 `.json` 路径；不覆盖已有文件，失败时不使用不完整文件。stdout 只返回路径、身份、哈希和报告链接，不打印报告内容。

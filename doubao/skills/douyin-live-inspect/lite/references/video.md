# Lite 本地视频

- 用户选择 Lite 或由正式版按回退规则转入，且具有本机可读文件/宿主已物化附件时进入本流程；不调用正式版项目接口。默认 MediaKit 优先、本地兜底，上传范围按 asr_policy 控制。仅有 HTTP(S) 视频链接时提示提供本地文件，不自行下载，也不重新发起正式版登录。
- 视频最终交付顺序固定为：视频质检报告（报告链接或 Chat 报告内容）、结论与风险证据及覆盖缺口、正式版能力升级、按 [交付](delivery.md#正式版能力升级) 的条件提供恢复说明或飞书群优先（沟通更高效）、工单其次的开通入口及申请信息。升级说明强调更丰富且按业务需求配置的规则、统一管理项目/任务/报告；不把“支持视频质检”描述为 Lite 没有的能力。不要求用户先开通才能拿到本次报告。
- 视频不展示或打开实时工作台，不交付 dashboard_url；启动和恢复仅简短说明检测进度，持续完成 ASR、看图和规则判定后调用 report，直接交付视频报告与结论。不得把“worker 或判定 Agent 已启动”作为任务完成，也不得在尚未交付报告时承诺后台自动完成后结束当前任务。
- 单文件可传 asr_policy；批次在 batch-create 顶层传入并对每项冻结。单文件用 `start-video --task-dir <新私有目录>`，stdin 为 `{"source":"<本地绝对路径>","name":"视频名称","delivery_mode":"local_dashboard"}`。每个视频先核验视频轨、时长、文件指纹，按 lite_sample_v1 抽检，不因文件时长拒绝；覆盖范围必须披露。默认使用通用规则，并在判定时按实际内容追加行业专项。
- 多文件先确定顺序；正式版回退时沿用已确认顺序，每个视频独立按内容加载规则。执行 `batch-create --batch-dir <新的私有目录>`，stdin 为 `{"videos":[{"source":"<本地路径>","name":"名称"}],"delivery_mode":"local_dashboard"}`；每项 source/name 独立保存。批次只保存计划，不自动开始识别。
- 循环执行 `batch-next --batch-dir <原目录>`，先交付 `current.delivery` 或顶层 `delivery`，再对当前 task_dir 使用既有 review-next/rules-load/review-submit/report 完整判定并交付质检报告；之后调用下一次 batch-next。视频不生成内容复盘，不等待复盘状态。不能仅以媒体完成跳过 Agent 判定。单项失败按返回状态说明并继续其他项；setup_pending 表示依赖阻塞，保留当前项；修复后再次 batch-next 恢复原任务，不跳过该视频或自动循环重试。
- `batch-status` 读取顺序、各任务进度及原任务目录；中断后使用原 batch-dir 继续，不重建批次。`batch-stop` 停止后续文件启动，并停止当前任务采集；已采集媒体继续处理与交付。单项仍可使用 stop/resume，但停止整批后不得自行重开后续项。
- 视频 EOF 为正常结束；视频时间轴从0开始，不使用直播墙钟或重连。文件变化/缺失时拒绝继续采集，保留已有证据并报告未覆盖区间。用户终止或解码失败只交付部分覆盖，不称完整检查。
- 两种交付模式复用直播的证据与判定流程，但不复用直播实时工作台交付。local_dashboard 在视频任务中仅表示最终报告可在本机查看：启动、resume、batch-next 均不启动本地 UI；report 就绪后才启动报告服务，仅交付 report_url 和结论。chat 全程不启动本地服务，直接在对话中交付结构化视频报告。本地兜底 ASR 使用 Zipformer 2023-12-13 int8 单遍识别：VAD 定位语音，流式 Transducer 每段识别一次，再按片段时间映射字幕。不再按1倍速喂入本地视频；实际耗时取决于宿主。旧双遍任务需用旧版 Skill 和原 Runtime 续办，不静默迁移。不承诺全流程离线，规则语义判定仍由当前 Agent 执行。
- 已有任务没有 asr_backend 时沿原 MediaKit 链路续办；本地任务固定模型指纹；保存 remote_first 或 local_first 的任务允许对应策略的远端处理及 refresh-credentials；缺少策略的旧任务或 local_only 不自动增加上传权限。模型位置可配置，不能改写已有任务的冻结模型身份。

### 视频容错、部分报告与续办

- 新建豆包云电脑视频默认 `html_snapshot`，同机桌面默认 `local_dashboard`；仅用户明确要求纯文字时使用 `chat`。已有任务保留原交付模式，不因报告或附件故障切换。视频正常采集结束的 `EDITION_UPGRADE_AVAILABLE` 只是独立能力提示；旧输出中的 `LITE_TRIAL_ENDED` 也不能当作片段额度耗尽或禁止判定的依据。
- 视频判定失败先读结构化 `error.code/field/segment_id/retryable/next_action`。首次失败最多修正两次，同一参数不重放；`REVIEW_INPUT_REPEATED` 要求修正，`REVIEW_RETRY_EXHAUSTED` 或 `next_action=review-defer` 要求保留待续办。证据版本变化先重新领取；不能用全 `no_hit` 绕过校验。ASR 已失败但处理终止时，依赖语音的规则使用 `insufficient`，已取得画面的规则仍独立判定。
- 使用 `review-defer --task-dir <原目录>`，stdin 为 `{"task_id":"原任务编号","segment_id":24,"evidence_revision":3,"reason_code":"INPUT_REPAIR_EXHAUSTED"}`；原因仅允许 `INPUT_REPAIR_EXHAUSTED`、`EVIDENCE_UNAVAILABLE`、`REVIEW_BLOCKED`。延期不算完成判定，也不生成规则结果。默认 `review-next` 跳过延期片段，继续其余可用片段。
- 本轮可处理片段完成后，若仍有阻塞或无有效证据，执行 `report --task-dir <原目录> --allow-partial`，交付部分结果，不无限等待 `not_ready`。常规 `report` 仍保留完整处理门槛。报告的 `processing_complete` 与 `coverage_complete` 分别表示处理收敛、全片证据覆盖完整；文件生成成功不等于两者为真。以结构化 `report` 生成 Chat 摘要，不读取 `html/data.js` 手工拼接另一套结论。
- 实际文件交付、版本回执和失败续办按 [交付](delivery.md)。

- 报告列出已判定、待判定、待续办和证据缺失的范围与原因，覆盖率按时间区间而非片段数量计算。`部分检测结果` 必须说明不能排除未检测内容的其他风险；无有效证据写 `未完成有效检测`。规则命中按规则与证据事件计数，同一时间可能命中多条规则。
- 用户要求继续时先 `status`；仅补判使用 `review-next --include-deferred`，重新打开本段有限修正机会，不启动采集。新证据会自动清除旧延期及旧判定，已成功且证据未变的片段不重复提交。确实仍需媒体处理时才 resume。续办后重新 report 并交付新版本，旧 HTML 是不可变历史快照。
- 批次每项交付并确认后再 `batch-next`；部分报告已交付可继续下一项，批次保留 partial，不宣称全量检测完成。原任务随时可以单独续办。
- 云端 ASR 只有明确未执行的错误才允许有界重试（首次加两次，间隔2秒和10秒）；提交结果未知不得自动重放。`upload_address_failed` 单独不足以证明未提交或凭证失效。保留缺口并沿原任务核对或由本地接管。

## 抽检合同

本地视频及批次视频使用抽检策略（`inspection_policy=lite_sample_v1`），参数创建后固定。本节只说明视频流程；历史直播见 [历史流程](legacy-review.md)。不得改变旧任务策略或补跑已跳过窗口。

- `review-next` 每次只领取一个窗口，即使传入更大 limit 也不并行领取。每窗按证据判断是否需要追加专项，否则直接使用当前规则。`segment.id` 是独立窗口 ID；不要对原始 ASR 片段提交判定。
- `review-submit` 顶层必须附 `summary`（1–200 字内容摘要），并携带原 `task_id`、`segment_id`、`evidence_revision`、`images_viewed` 和逐规则 `rules`。不得把窗口内每个断句拆为独立判定。`window_expired` 表示本地运行时已经封存该窗口，按返回 next_action 继续，不重试旧提交。
- 本地视频先均分 `min(10,ceil(时长秒数/60))` 个区间，仅识别每区间中央最多 20 秒；按时间顺序，最多预处理下一窗，不执行直播替换策略。每个视频最多 10 次判定、20 张图；批次逐视频执行，仅交付质检报告。
- 报告披露抽检时长、完成窗数、计划未抽检与积压跳过／判定超时／收尾超时／证据不足范围。无命中时仅表述“本次抽检范围内未发现规则命中”。
- 默认输出上限 24 KiB。返回 `read-result-pages` 时执行 `read_argv`，沿 `next_page_argv` 读取至 `next_offset=null`，拼接 `json_fragment` 并解析完整 JSON，再按原 `next_action` 执行。该接口无损保留原结果；不要把分页入口摘要当作判定证据。不要自行读取完整任务文件代替有界复盘输入。

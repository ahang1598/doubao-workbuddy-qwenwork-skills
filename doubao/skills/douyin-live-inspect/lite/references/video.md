# Lite 本地视频

## 适用范围

新视频默认 `video_recap_enabled=true`，完成质检后继续复盘。历史视频沿保存的协议；未启用复盘时仅交付质检结果，不自动补复盘或迁移策略。

- 用户明确选择 Lite，且具有本机可读文件/宿主已物化附件时进入本流程；不调用正式版项目接口。默认 MediaKit 优先、本地兜底，上传范围按 asr_policy 控制。仅有 HTTP(S) 视频链接时提示提供本地文件，不自行下载，也不重新发起正式版登录。
- 先交付视频质检报告、结论、风险证据及覆盖缺口，再为新视频交付含评分的内容复盘；历史任务沿原回执执行。
- 视频不展示或打开实时工作台，不交付 dashboard_url；启动和恢复仅简短说明检测进度，持续完成 ASR、看图和规则判定后调用 report，直接交付视频报告与结论。不得把“worker 或判定 Agent 已启动”作为任务完成，也不得在尚未交付报告时承诺后台自动完成后结束当前任务。
## 启动

### 单文件

- 单文件可传 asr_policy；批次在 batch-create 顶层传入并对每项冻结。单文件先写好私有 JSON 文件，再用 `start-video --task-dir <新私有目录> --input-file <JSON文件路径>`，内容为 `{"source":"<本地绝对路径>","name":"视频名称","delivery_mode":"local_dashboard"}`；旧 stdin 仍兼容，须在 5 秒内写完并关闭。每个视频先核验视频轨、时长、文件指纹，从开头连续检测至片尾，不因文件时长拒绝；覆盖范围必须披露。默认使用通用规则，并在判定时按实际内容追加行业专项。
### 视频批次

- 多文件先确定顺序；用户改选 Lite 时沿用已确认顺序，每个视频独立按内容加载规则。执行 `batch-create --batch-dir <新的私有目录>`，stdin 为 `{"videos":[{"source":"<本地路径>","name":"名称"}],"delivery_mode":"local_dashboard"}`；每项 source/name 独立保存。批次只保存计划，不自动开始识别。
- 循环执行 `batch-next --batch-dir <原目录>`，先交付 `current.delivery` 或顶层 `delivery`，再对当前 task_dir 使用既有 review-next/rules-load/review-submit/report 完整判定并交付质检报告；新视频继续完成复盘及交付确认后，再调用下一次 batch-next。历史任务按原回执推进。不能仅以媒体完成跳过 Agent 判定。单项失败按返回状态说明并继续其他项；setup_pending 表示依赖阻塞，保留当前项；修复后再次 batch-next 恢复原任务，不跳过该视频或自动循环重试。
- `batch-status` 读取顺序、各任务进度及原任务目录；中断后使用原 batch-dir 继续，不重建批次。`batch-stop` 停止后续文件启动，并停止当前任务采集；已采集媒体继续处理与交付。单项仍可使用 stop/resume，但停止整批后不得自行重开后续项。
## 停止与覆盖范围

- 视频 EOF 为正常结束；视频时间轴从0开始，不使用直播墙钟或重连。文件变化/缺失时拒绝继续采集，保留已有证据并报告未覆盖区间。用户终止或解码失败只交付部分覆盖，不称完整检查。
## 交付模式与识别边界

- 视频复用直播的证据与判定流程，不交付实时工作台。local_dashboard 按[交付](delivery.md)使用持久报告副本，豆包优先交付文件卡片与结论；启动、resume、batch-next 和 report 均不启动 HTTP 服务。html_snapshot 使用宿主附件能力，chat 直接在对话交付结构化报告。本地兜底 ASR 使用 Zipformer 2023-12-13 int8 单遍识别：VAD 定位语音，流式 Transducer 每段识别一次，再按片段时间映射字幕。不再按1倍速喂入本地视频；实际耗时取决于宿主。旧双遍任务需用旧版 Skill 和原 Runtime 续办，不静默迁移。不承诺全流程离线，规则语义判定仍由当前 Agent 执行。
- 已有任务没有 asr_backend 时沿原 MediaKit 链路续办；本地任务固定模型指纹；保存 remote_first 或 local_first 的任务允许对应策略的远端处理及 refresh-credentials；缺少策略的旧任务或 local_only 不自动增加上传权限。模型位置可配置，不能改写已有任务的冻结模型身份。

## 视频容错、部分报告与续办

- 停止采集不等于完成判定。已有内容仍待识别或判定时，按原任务返回的 `next_action` 继续；不能直接宣称内容不足或检测完成。
- 已有就绪片段时先领取并提交，不因其他片段的媒体恢复失败或 worker 无响应而只轮询。批次也先处理当前视频的就绪片段。就绪片段处理完后，若采集与处理都已结束则按指引交付部分报告，否则沿原任务恢复；依赖或权限失败按 [启动恢复](startup.md) 核对固定错误详情，不循环重建任务或扩大目录权限。

- 新建豆包云电脑视频默认 `html_snapshot`，同机桌面默认 `local_dashboard`；仅用户明确要求纯文字时使用 `chat`。已有任务保留原交付模式，不因报告或附件故障切换。
- 视频判定失败先读结构化 `error.code/field/segment_id/retryable/next_action`。首次失败最多修正两次，同一参数不重放；`REVIEW_INPUT_REPEATED` 要求修正，`REVIEW_RETRY_EXHAUSTED` 或 `next_action=review-defer` 要求保留待续办。证据版本变化先重新领取；不能用全 `no_hit` 绕过校验。ASR 已失败但处理终止时，依赖语音的规则使用 `insufficient`，已取得画面的规则仍独立判定。
- 使用 `review-defer --task-dir <原目录>`，stdin 为 `{"task_id":"原任务编号","segment_id":24,"evidence_revision":3,"reason_code":"INPUT_REPAIR_EXHAUSTED"}`；原因仅允许 `INPUT_REPAIR_EXHAUSTED`、`EVIDENCE_UNAVAILABLE`、`REVIEW_BLOCKED`。全视频任务将该窗标为跳过并保存原因，不生成规则结果，继续后续窗口；历史非全视频任务仍保留延期续办语义。
- 本轮可处理片段完成后，若仍有阻塞或无有效证据，执行 `report --task-dir <原目录> --allow-partial`，交付部分结果，不无限等待 `not_ready`。采集与处理进程均已结束时，常规 `report` 也会生成部分报告；仍在运行时使用显式 `--allow-partial`。报告的 `processing_complete` 与 `coverage_complete` 分别表示处理收敛、全片证据覆盖完整；文件生成成功不等于两者为真。以结构化 `report` 生成 Chat 摘要，不读取 `html/data.js` 手工拼接另一套结论。
- 实际文件交付、版本回执和失败续办按 [交付](delivery.md)。

- 报告列出已判定、待判定、待续办和证据缺失的范围与原因，覆盖率按时间区间而非片段数量计算。`部分检测结果` 必须说明不能排除未检测内容的其他风险；无有效证据写 `未完成有效检测`。规则命中按规则与证据事件计数，同一时间可能命中多条规则。
- 用户要求继续时先 `status`；全视频已跳过窗口保留封存结果，不重新提交迟到判定。历史延期片段仅补判使用 `review-next --include-deferred`，重新打开本段有限修正机会，不启动采集。新证据会自动清除旧延期及旧判定，已成功且证据未变的片段不重复提交。确实仍需媒体处理时才 resume。续办后重新 report 并交付新版本，旧 HTML 是不可变历史快照。
- 批次每项交付并确认后再 `batch-next`；部分报告已交付可继续下一项，批次保留 partial，不宣称全量检测完成。原任务随时可以单独续办；零判定项补判并交付有效新报告后，批次同步更新检测状态。
- 云端 ASR 只有明确未执行的错误才允许有界重试（首次加两次，间隔2秒和10秒）；提交结果未知不得自动重放。`upload_address_failed` 单独不足以证明未提交或凭证失效。保留缺口并沿原任务核对或由本地接管。

## 全视频检测

新建本地视频及批次视频连续分段覆盖整段视频，不限制总判定次数。本节只说明视频流程；历史直播见 [历史流程](legacy-review.md)。不得改变旧任务策略或补跑已跳过窗口。

领取后直接填写 `submission_contract.template`，即使规则正文已缓存，模板仍列出全部规则。每条填写 `status`（hit/no_hit/insufficient/not_applicable）和非空 `reason`；命中 `events` 引用本窗口的 `evidence_ids`，非命中填空数组。追加专项后重新领取更新模板。不要使用 live-review.md 的直播 `segments/context_id/reviewed` 精简格式，不得用空 `rules` 表示全未命中。只在回执为 saved/already_saved 后计为已判定；格式修复期间沿原窗口提交。

新动态任务每窗按模板填写带证据的 `content_route`，行业适用边界和无法确定时的处理见[追加专项](rules.md#追加专项)。对照图片也须实际查看、列入 `images_viewed` 并在事件中描述。

全视频不设总检测时长上限；单窗证据准备或领取后的判定默认最多等待120秒，超时跳过并继续后续窗口。证据已就绪但尚未轮到领取的窗口不因排队超时跳过。明确无法判定或输入修正耗尽时立即使用 review-defer 跳过，不循环重试。已完成判定保留，报告披露跳过原因与未检范围，不能称全片通过；历史抽检任务沿原策略，封存窗口不重开。

- `review-next` 每次只领取一个窗口，即使传入更大 limit 也不并行领取。每窗按证据判断是否需要追加专项，否则直接使用当前规则。`segment.id` 是独立窗口 ID；不要对原始 ASR 片段提交判定。
- 不把窗口内每个断句拆为独立判定。`window_expired` 表示本地运行时已经封存该窗口，按返回 next_action 继续，不重试旧提交。
- 视频默认每30秒连续分段，片尾不足30秒也检测；音轨覆盖全时长，画面沿用每段代表帧检测，并非逐帧检查。按时间顺序最多预处理下一段，不执行直播替换策略；批次逐视频执行，报告交付按下方[复盘与完成条件](#复盘与完成条件)。回放包含全部已保存片段。
- 报告披露已判定时长、原视频时长和失败缺口；只有全部范围完成才能表述全视频检测完成。部分结果的结论仅适用于已完成范围。
- 采集覆盖率与已判定覆盖率分别说明；计划未抽检不称为启动延迟或录制中断。报告已产出即为报告生成成功，实际交付后确认交付成功。零有效判定不称检测通过或部分检测成功；范围与原因保留在折叠的报告详情中，不单独展示醒目警告卡片。
- 默认输出上限 24 KiB。返回 `read-result-pages` 时执行 `read_argv`，沿 `next_page_argv` 读取至 `next_offset=null`，拼接 `json_fragment` 并解析完整 JSON，再按原 `next_action` 执行。该接口无损保留原结果；不要把分页入口摘要当作判定证据。不要自行读取完整任务文件代替有界复盘输入。

### 批次失败恢复

先查看 `batch-status --batch-dir <原目录>` 的 items.error 和 diagnostic。修复失败原因后，用 `batch-next --batch-dir <原目录> --retry-index <从1开始的失败项序号>` 定向续办；只接受 failed 项，保留原批次与子任务身份。普通 batch-next 仍跳过 failed。已创建子任务且状态 active 的启动异常沿普通 batch-next 续办，不重建任务；诊断保留最近一次失败，error 清除后不要把历史诊断解释为仍失败。不自动循环重试。

## 复盘与完成条件

已启用复盘的视频，质检交付后沿 next_action 执行 recap-input --begin、recap-submit、recap-report；评分合同与直播共用。质检回执使用 version/status，复盘使用 kind=recap 与 evidence_version。按回执交付复盘或终态失败结果并确认后推进批次；零有效检测等失败项按 batch-next 的实际状态继续，不强求生成空复盘。未启用复盘的历史视频在质检交付后沿原回执完成。

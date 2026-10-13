# Lite 启动

### 硬约束：云电脑环境必须提示本地电脑推荐

仅在确认使用豆包工作云电脑时提示，同一任务或视频批次只提示一次。运行时根据明确宿主标记判断；标记不足时，Agent 仅依据可信宿主上下文为命令设置 `BYTEDLIVE_INSPECT_HOST=doubao_cloud`；已确认本地设 `local`，其他宿主设 `other`，无法确认设 `unknown`。不根据 Chat 模式、操作系统或待检测内容猜测环境，不传递身份或凭证。本地电脑也可能使用 Linux 容器或沙箱执行命令；`/home/user/.doubao/` 路径和正式版运行环境探测结果不能单独证明用户选择了云电脑。`CUA_USE_ISOLATED_ENV=0` 的明确本地标记优先于 Agent 传入的云电脑判断；明确的 `DOUBAO_SANDBOX_TYPE=SaaS` 与豆包办公宿主标记可共同证明云电脑，`CUA_USE_ISOLATED_ENV=1` 仍为强云电脑标记。`BYTEDLIVE_INSPECT_HOST=unknown` 仅表示 Agent 没有证据，不得覆盖这些更强的运行时标记。宿主明确为本地电脑时不得设置 `doubao_cloud`；证据不足时设 `unknown` 并继续任务，不提示切换电脑。

启动、恢复及 batch-next 返回的 `delivery.message` 会自动包含完整加粗推荐文案。Agent 必须完整展示；含 `notice_id` 时，**展示后**执行 `delivery-ack --task-dir <本次任务目录>`，再继续 status/review-next。生成消息不代表已交付，不提前确认；未确认时恢复会补发，已确认后同一任务或批次不重复。不要另行手写同一提示。

提示后继续原任务和 Chat 交付，不询问或等待切换、不重建任务。实时工作台与内容复盘仅适用于直播，报告可查看须以实际就绪为准。

遥测说明见 [遥测](telemetry.md)，不读取或展示凭证。

采集的 PCM、语音识别 WAV、录像、图片和任务数据库是本次质检证据；新任务须放在源码仓库外的私有目录，选取唯一的新路径，由 start 创建目录和数据库，无需预先 mkdir。若提示已存在或创建结果未知，先对原 task_dir 执行 status，确认原任务状态后续办；禁止删除任务目录或数据库后重新 start。空目录可由运行时初始化，但不能据“目录已存在”推断任务失败，也不覆盖已有任务。

全部命令从本 Skill 根目录执行，同一个 Python 3.10+ 环境使用 `python3 scripts/live_inspect.py`（Windows 可用 python）。直接 start/start-video，由运行时校验公共 FFmpeg/FFprobe 并选择后端；不先等待本地模型、不调用阻塞式 prepare-runtime、不为远端启动强制安装本地推理依赖。setup_pending 时再按 doctor 的诊断处理。仅需修复本地兜底依赖且宿主允许安装时，使用 `python3 -m pip install --only-binary=:all: -r requirements.txt`；不索取 Token，不自行安装同名 MediaKit 工具。公共采集依赖缺失不能靠远端 ASR 绕过。

macOS 上部分 Python 安装的默认证书库为空，会使抖音页面抓取报 `DOUYIN_FETCH_FAILED`。Lite 抓取器仅在默认库为空、且未显式设置 `SSL_CERT_FILE`／`SSL_CERT_DIR` 时尝试 `/etc/ssl/cert.pem`，始终保持 TLS 证书校验。若仍报该错误，先核对任务的脱敏错误码、Python 证书库及受信任 CA 配置；不要关闭证书校验，也不要把抓取失败误判为直播间未开播。已有失败任务不自动重建，取得用户新的检测请求后再新建。

新任务默认 `asr_policy=remote_first`，抽帧沿用同一策略：MediaKit 可用即开始远端处理，同时后台准备固定版本本地模型，不等待本地下载或初始化。远端不可用时选择本地，两端未就绪则显示准备状态，取得媒体前不声称已开始检测。后台模型准备失败不等于远端质检失败；局部兜底只使用已就绪模型，不等待下载，未就绪时继续处理其他片段。ASR 和抽帧独立切换，本地兜底后冷却60秒，仅让一个新片段／采样点试跑远端，成功恢复远端优先，失败继续本地并重新冷却；认证拒绝须凭证状态变化后再试。所有计时与选路由运行时完成，Agent 不自行重试或重置状态。已知远端 ID 只续查，未知提交不重传；接管后远端迟到结果不能覆盖已提交证据。正常片段不双跑，静音不视为识别故障。

启动时简短说明本次音频使用远端处理，开启画面检测时还会上传所需视频片段；模型下载本身不上传媒体。用户要求完全本地／不上传时传 `asr_policy=local_only`；显式 `local_first` 保留原本地优先及有限云端备用行为。旧任务与旧批次沿用已保存策略，缺少策略时不新增上传权限；不迁移已有证据。停止等待任务后不开始采集，后台模型准备可继续供后续任务使用。

1. 完成上述分流后，使用用户提供的来源和检测意图，默认启用通用规则，按实际内容追加电商或金融专项。直接调用 start/start-video 由入口选择路径；仅模型未缓存不阻塞可用远端。返回 preparing 时持续读取 status，模型准备成功后 worker 自动开始，无需重复 start；等待期间未采集，不能声称覆盖该时段。返回 setup_pending 时说明错误及修复指引，不循环重试。云端任务的 model_preparation 失败与质检失败分别展示，继续完成正常的云端质检。入口探测和 `doctor` 都不表示体验已经开始，页面未开播或未取得有效媒体时不称为已消费体验。
2. 启动交付模式与实际展示按 [交付](delivery.md)。本机默认 local_dashboard，确认云电脑使用 html_snapshot，显式 chat 保持；历史本地工作台任务在云电脑按独立快照交付，不修改原任务保存模式。视频不交付工作台。
3. `start --task-dir <新的私有任务目录>` 通过受控、不回显的 stdin 接收 JSON：`source`、`name`、`delivery_mode`（`local_dashboard`、`html_snapshot` 或 `chat`）。启动时不传行业参数，由后续判定按实际证据追加规则。可选 `asr_policy`（remote_first 默认远端优先，local_first 本地优先且允许云端备用，local_only 禁止上传）、`max_duration_seconds`（省略或 null 表示不设时长上限；用户明确指定时传正整数秒数）、`segment_seconds`（默认30，直播最多60、视频最多180）、`frame_interval_seconds`（新直播固定120，视频沿用10；无需画面的任务忽略）。不把来源放进命令参数。任务目录在整个 Inspect Skill 外，权限0700，不能复用已存在任务目录创建新任务。
4. start/resume 后保存 task_id/task_dir，先按 [交付](delivery.md) 实际展示 delivery.message 并执行必要确认，再按返回 next_action 核验状态与判定；不能只在工具输出展示。名称未指定时用“直播内容质检”，不猜房间标题。
5. 当前 Agent 进入下面的判定循环。媒体 worker 仅执行 ASR 处理，不自动生成语义结论，不能只启动进程就宣称质检完成。

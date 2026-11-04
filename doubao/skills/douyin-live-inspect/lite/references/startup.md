# Lite 启动

### 硬约束：云电脑环境必须提示本地电脑推荐

仅在确认使用豆包工作云电脑时提示，同一任务或视频批次只提示一次。运行时根据明确宿主标记判断；标记不足时，Agent 仅依据可信宿主上下文为命令设置 `BYTEDLIVE_INSPECT_HOST=doubao_cloud`；已确认本地设 `local`，其他宿主设 `other`，无法确认设 `unknown`。不根据 Chat 模式、操作系统或待检测内容猜测环境，不传递身份或凭证。本地电脑也可能使用 Linux 容器或沙箱执行命令；`/home/user/.doubao/` 路径和正式版运行环境探测结果不能单独证明用户选择了云电脑。`CUA_USE_ISOLATED_ENV=0` 的明确本地标记优先于 Agent 传入的云电脑判断；明确的 `DOUBAO_SANDBOX_TYPE=SaaS` 与豆包办公宿主标记可共同证明云电脑，`CUA_USE_ISOLATED_ENV=1` 仍为强云电脑标记。`BYTEDLIVE_INSPECT_HOST=unknown` 仅表示 Agent 没有证据，不得覆盖这些更强的运行时标记。宿主明确为本地电脑时不得设置 `doubao_cloud`；证据不足时设 `unknown` 并继续任务，不提示切换电脑。

云电脑直播开始时说明本次最多检测10分钟（用户指定更短时按实际值展示），接近执行额度时可能提前收尾，报告仅覆盖实际完成检测的内容。优先建议切换「工作任务 · 本地电脑」体验 Lite；不把切换作为当前任务报告交付的前提。本地模式不展示云端时长和额度限制提示。

启动、恢复及 batch-next 返回的 `delivery.message` 会自动包含完整加粗推荐文案。Agent 必须完整展示；含 `notice_id` 时，**展示后**执行 `delivery-ack --task-dir <本次任务目录>`，再继续 status/review-next。生成消息不代表已交付，不提前确认；未确认时恢复会补发，已确认后同一任务或批次不重复。不要另行手写同一提示。

提示后按返回的实际交付模式继续原任务，不询问或等待切换、不重建任务。实时工作台与内容复盘仅适用于直播，报告可查看须以实际就绪为准。

不读取或展示凭证。遇到锁冲突先确认原进程状态，不按锁年龄删除锁或重建任务。只有明确内存不足证据才判断 `OUT_OF_MEMORY`，不能仅凭 SIGKILL/137 推断；保留原任务和已有结果，释放资源后续办，不盲目重启。

采集的 PCM、语音识别 WAV、录像、图片和任务数据库是本次质检证据。主入口已预留任务标识和 Skill 目录外的私有目录；使用返回的 `start_command_argv` 和 `execution_env` 启动，不另选路径。只有未经过主入口的独立调用才由 start 创建新私有目录。创建、修复依赖后的重试和续办都沿用原 task_dir；若创建结果未知，先执行 status 核对，禁止删除任务目录或数据库后重新 start。预留目录可以包含入口上下文和流程状态文件，不能据“目录已存在”推断任务失败，也不覆盖已有任务。

`TASK_BINDING_MISMATCH` 表示启动目录与入口不一致或入口上下文缺失，按原入口核对目录和环境，不重建标识。`PERMISSION_DENIED` 表示操作系统拒绝访问；保留原目录，依据 `error.diagnostic` 的安全调用帧及 errno/winerror 定位具体操作，不用新建任务或扩大权限掩盖失败。错误码本身不能证明是目录 ACL、进程启动还是文件操作失败。

全部命令从本 Skill 根目录执行，同一个 Python 3.10+ 环境使用 `python3 scripts/live_inspect.py`（Windows 可用 python）。直接 start/start-video，由运行时校验公共 FFmpeg/FFprobe 并选择后端；不先等待本地模型、不调用阻塞式 prepare-runtime、不为远端启动强制安装本地推理依赖。仅需修复本地兜底依赖且宿主允许安装时，使用 `python3 -m pip install --only-binary=:all: -r requirements.txt`；不索取 Token，不自行安装同名 MediaKit 工具。

新任务默认 `asr_policy=remote_first`，抽帧沿用同一策略：MediaKit 可用即开始远端处理，同时后台准备固定版本本地模型；远端不可用时选择本地。后台模型准备失败不等于远端质检失败。后端选择与有限恢复由运行时处理，Agent 不自行计时、切换或重置状态；ASR 异常按 [证据与凭证恢复](evidence-recovery.md) 处理。

启动时按实际 asr_policy 展示运行时返回的处理方式说明：remote_first 优先远端，local_first 允许云端备用，local_only 不上传媒体；不对纯本地任务宣称上传。模型下载本身不上传媒体。用户要求完全本地／不上传时传 `asr_policy=local_only`；显式 `local_first` 保留原本地优先及有限云端备用行为。旧任务与旧批次沿用已保存策略，缺少策略时不新增上传权限；不迁移已有证据。停止等待任务后不开始采集，后台模型准备可继续供后续任务使用。

1. 完成上述分流后，使用用户提供的来源和检测意图，默认启用通用规则，按实际内容追加电商或金融专项。直接调用 start/start-video 由入口选择路径；仅模型未缓存不阻塞可用远端。返回 preparing 时持续读取 status，模型准备成功后 worker 自动开始，无需重复 start；等待期间未采集，不能声称覆盖该时段。返回 setup_pending 时按 [依赖准备失败](#依赖准备失败) 处理；后台模型准备失败时，仍继续可用的远端质检。入口探测和 `doctor` 都不表示体验已经开始，页面未开播或未取得有效媒体时不称为已消费体验。
2. 启动交付模式与实际展示按 [交付](delivery.md)。本机默认 local_dashboard，确认云电脑使用 html_snapshot，显式 chat 保持；历史本地工作台任务在云电脑按独立快照交付，不修改原任务保存模式。视频不交付工作台。
3. 先将完整 UTF-8 JSON 写入当前用户私有目录中的普通文件，再调用 `start --task-dir <入口返回的 task_dir> --input-file <JSON文件路径>`；显式指定文件时不读取 stdin，不回退其他输入。旧 stdin 调用仍兼容，须在 5 秒内写完并关闭。JSON 字段为 `source`、`name`、`delivery_mode`（`local_dashboard`、`html_snapshot` 或 `chat`）。启动时不传行业参数，由后续判定按实际证据追加规则。可选 `asr_policy`（remote_first 默认远端优先，local_first 本地优先且允许云端备用，local_only 禁止上传）、`max_duration_seconds`（云电脑新直播最多600秒（10分钟），正整数从短、null或更长值均受上限约束；本地不限时，用户明确指定时传正整数秒数，明确不限时才传 null）、`segment_seconds`（默认30，直播最多60、视频最多180）、`frame_interval_seconds`（新直播固定120，视频沿用10；无需画面的任务忽略）。不把来源放进命令参数。任务目录在整个 Inspect Skill 外并受当前用户私有权限保护（POSIX 为0700，Windows 沿用系统权限机制）；允许复用入口预留目录，不覆盖已创建的业务任务。
4. 云电脑启动须展示运行时返回的实际采集上限和双报告流程；采集/判定累计40次调度命令或宿主总调用达到100步即提前收尾，不等待平台预警，按 [提前收尾](../SKILL.md#云电脑执行额度与提前收尾) 处理。start/resume 后保存 task_id/task_dir，先按 [交付](delivery.md) 实际展示 delivery.message 并执行必要确认，再按返回 next_action 核验状态与判定；不能只在工具输出展示。名称未指定时用“直播内容质检”，不猜房间标题。
5. 当前 Agent 进入下面的判定循环。媒体 worker 执行采集、ASR 和抽帧等媒体处理，不自动生成语义结论，不能只启动进程就宣称质检完成。

启动成功后采集失败按 [采集失败自动排查](live-review.md#采集失败自动排查) 处理，不能归为创建失败。Windows 路径按独立参数传递，避免把含空格或中文的路径拼成 Bash 命令。

## 受限网络环境

浏览器可播放不代表采集命令能联网。仅宿主明确限制命令网络或本次会话已有 DNS 失败时，在 start 前用同一 Python 对来源主机名做一次只读 DNS 查询；其他环境直接启动，不增加 doctor。

- 查询失败且宿主支持联网授权时，按其权限流程获准后对同一主机名复查一次。受限环境失败、获准环境成功才支持环境限制的判断；两边均失败则原因待查。
- 实际 start 和后续联网命令须使用获准环境，保留原 Python、task_dir 与 execution_env。无获准联网能力时说明阻塞；DNS 成功仍须核验实际采集，不修改系统 DNS、代理或关闭 TLS 校验。
- 已启动或结果未知时先查原 status，沿 next_action 续办；冻结或终态任务仅收尾，新的检测请求才新建任务。抓取失败按具体诊断排查，明确证书错误才检查 CA，不推断未登录或停播。

## 依赖准备失败

各平台均依赖本地 FFmpeg/FFprobe 采集，由运行时自动准备；远端 ASR 不能绕过采集依赖，不手动下载、安装或改 PATH。

返回 `setup_pending` 或 `deliver-preparation-failure` 时，依据 `doctor.issues` 和 `next_action` 交付具体原因及修复指引，结束本次启动尝试；退出码 0 不代表已开始采集。不循环 start 或 prepare-runtime；环境修复后沿原任务目录显式重试，缓存与下载进度由运行时复用。目录 ACL 失败同样保留原任务，不循环提权或修改整个目录树。

启动前告知用户：“正在安装相关依赖，可能会花费一点时间，请耐心等待。安装完成前尚未开始质检。”宿主支持时转述 stderr 实时进度；不要把依赖准备等待描述为正在质检。下载有持续进展时不设总时长限制；内置包优先国内 CDN，失败重试一次，再依次尝试 Gyan 原站和 GitHub 官方镜像各一次（最多四次）；切换下载源时即时告知用户。返回 setup_pending 后说明阻塞原因和实际 retryable；仅在用户明确重试时沿用原 task_dir/任务，批次保留当前项，不循环启动。

## 小红书来源与恢复

`source` 接收小红书详情长链接或 `xhslink.com` 官方分享短链。可在 start 输入中附加 `browser_source`，字段和观测方法沿用 [浏览器补充取流](../../references/browser-stream-fallback.md#小红书补充取流)；匿名成功时优先使用匿名结果。输入文件放用户私有目录，候选不要贴入对话。启动后、断流后均由同一个采集 worker 解析，网页 HTML 不直接交给 FFmpeg。

回执出现 `source_refresh` 时，优先读取宿主 browser-use 或 browser-use-automation-mac Skill，使用其声明的 plane="bu" 内置执行器而非 Chrome DevTools；在其期限内重新观测本次房间，将 `{"browser_source":{...}}` 写入私有文件，再执行回执中的 `resume --task-dir <原目录> --input-file <文件>`。该动作只交接候选，不启动第二个 worker，不修改 source 或任务标识。候选交接后删除自己准备的临时输入文件；运行时交接文件被消费后自动删除。

每次来源恢复最多尝试6次；首次请求浏览器补流时开始固定180秒交接窗口，候选到达后每次解析探测最多15秒，提交和重复轮询不延长窗口，停止请求会提前中止；候选超时、不可用或宿主无法补充时不循环重建任务。采集失败后保留已采集内容、继续判定和双报告；无内容时交付失败原因。未收到候选的交接超时返回 `BROWSER_SOURCE_TIMEOUT`；已接收候选后失败保留实际校验或探测错误。已停止、失败或冻结的任务返回 `BROWSER_SOURCE_TASK_CLOSED`，表示未验证候选，不能解释为流地址无效，不借 resume 重开采集。确认停播与取流失败分别表述。

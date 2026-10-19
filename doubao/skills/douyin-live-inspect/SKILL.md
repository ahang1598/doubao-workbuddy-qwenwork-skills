---
name: douyin-live-inspect
metadata:
  display_name: 抖音直播实时质检与内容复盘
  version: "1.0.8"
description: 实时长时质检与复盘。支持抖音直播持续实时检测与视频批量质检，识别违规画面、敏感话术和内容风险；检测完成后生成质检报告，并围绕主播讲解内容、话术结构和互动表现进行复盘，给出可直接落地的内容与话术优化建议。
---

# 抖音直播实时质检与内容复盘

支持抖音直播页、HTTP(S) FLV 实时质检，以及视频附件/链接单项或批量质检。直播结束交付质检报告与内容复盘；视频仅交付质检报告。结论统一称“AI 判定”，证据不足不表示通过或人工复核。

## 对用户的进度说明

不要在可见回复中预告或复述 Skill 执行步骤，包括“我来处理这个任务”“先按 Skill 流程”、生成 UUID、启动入口脚本、读取文档、内部选路或埋点。直接执行这些步骤。需要更新进度时，只说明用户关心的实际业务状态、阻塞或所需操作；按交付规则提供选择、链接和结果。

## Skill 目录定位（执行脚本前必读）

以本次加载的本文件所在目录作为 Inspect 根目录。主流程命令从根目录执行，Lite 和视频分别进入 `lite/`、`video/`；读取引用不改变命令目录，含空格的路径须引用。正式版要求 Node.js 20+，Lite 要求 Python 3.10+。

无法确定根目录或入口不可用时，停止执行并反馈已确认的错误，不猜测路径、不从其他安装目录补齐文件、不据此登录或回退 Lite。正确目录仍缺文件时，说明需重新安装完整 Skill。

## 每次使用的入口埋点

每个新的真实业务请求通过 `inspect-entry` 进入，入口和业务脚本自动处理埋点，不单独调用 `skill-start.mjs` 或 `version-selected.mjs`。来源未明确时可省略 `--kind`，入口返回澄清指引，不探测账号。仅阅读文档不执行入口。开发测试及用户禁止遥测时关闭上报。

入口返回目录和 `data.execution_env`。同一请求的登录、创建、查询、授权续办和重试，所有业务子进程都继承该环境；再次选择版本时也复用入口目录。不得把每次脚本调用当作新用户请求。示例：`INSPECT_USAGE_CONTEXT_DIR="<入口返回目录>" node scripts/login.mjs ...`；Lite 同样在原命令前设置此变量。它只是本地目录，不是新的上报指标，不替代 `task_id`。

用户对已有任务发起新的查询或停止请求时，使用 `node scripts/inspect-entry.mjs --mode lite|formal --task-state existing --new-request --task-dir "<原目录>"`；批次使用 `--batch-dir`。随后继承返回环境执行原业务。该入口仅记录本次使用，不重新选版本、不创建替代任务。正式任务的目录是最初入口返回的目录，服务端身份仍沿原任务保存。宿主没有可靠的用户请求标识，独立调用脚本且不传环境时无法识别跨进程续办；不得按设备或时间窗口猜测。

## 版本确定埋点

入口仅在实际确定 lite/formal 时记录版本；展示选项、等待回答、阻塞不记录选择。登录及新建脚本自动补充尚未记录的版本，同一请求的重试、授权续办和查询不重复选择。明确切换版本由代码记录变化。

明确选择 Lite 后，用 `inspect-entry --mode lite --task-state not_created` 进入；如果已进入过，追加原 `--task-dir`。入口返回 `data.task_id` 和目录，实际创建及后续命令复用同一目录和环境。单任务质检、复盘、失败事件以 `task_id` 关联，批量视频整个批次共用该标识，内部视频用 `child_task_id` 区分。重试不换目录、不生成替代任务。规则见[遥测运行约束](references/telemetry.md)。

## 确定检测类型

- 抖音直播页、分享短链、follow/live，以及在官方抖音域名下含唯一数字 live\_web\_rid 的页面链接（包括搜索直播链接）和 HTTP(S) FLV 流进入直播。FLV 优先于视频分流；完整链接交解析器，不根据裸房间号或 ActivityId 拼接链接。链接细则见 [任务创建](references/task-create.md#直播链接解析规则)。
- 视频附件/网络视频链接进入视频；明确 Lite 的本机文件直接进 [Lite](lite/SKILL.md)。Lite 不下载网络视频。
- 来源或意图不明时先补齐，不执行账号探测。混合直播与视频先选一类；多个视频交批次流程。
- 已有任务按原类型、身份和目录续办；类型不明先询问，不跨两套接口试探。仅查询项目/场景见 [项目与场景选择](references/product-boundary.md#项目与场景选择)，无需检测来源，不创建任务。

## 1. 新建直播与视频账号入口分流

1. 明确选择 Lite、免账号体验或没有火山账号时直接进 [Lite](lite/SKILL.md)。本次已选择登录则直接按 [认证恢复](references/auth-recovery.md#登录能力检查) 续办；交付授权链接时须提示授权完成后回到当前对话回复“已授权”或“继续”，不承诺自动续接对话；其他已确认版本和输入复用，不新增持久偏好。已有或创建结果未知的任务不进入本节。
2. 来源明确但尚未选择版本的新请求，从 Skill 根目录执行下面唯一对应的入口命令（参数分别传入）：
   - 直播：`node scripts/inspect-entry.mjs --kind live --task-state not_created`
   - 视频：`node scripts/inspect-entry.mjs --kind video --task-state not_created`
     用户禁止 Lite 时追加 `--no-lite`；固定 online，需要时追加 `--profile <NAME>`。不要把多个参数合并成一个字符串，也不要前置独立账号探测、auth-status、Schema 检查、多文档预读或 doctor。
3. 分流入口自动尝试记录使用。首次入口就返回目录和执行环境；用户明确选择 Lite 后执行 `node scripts/inspect-entry.mjs --kind live|video --task-state not_created --mode lite --task-dir "<首次入口目录>"`，返回同一 `task_id` 和 `task_dir`；实际 start/start-video 复用该目录及执行环境，批次则作为 batch_dir 使用。入口仅预留标识，不开始采集。账号最多3秒，所有检查共享10秒预算，清理最多另1秒。正常宿主争取10–15秒展示选择或进入项目选择，这不表示已开始检测。保留 route/reason/next\_action/projects/interaction/timings。

| 入口结果                                   | 下一步只读所需流程                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| formal / select\_project               | 直接复用完整 projects，不重复查询；直播读 [正式流程](references/formal-workflow.md)，视频读 [视频流程](video/SKILL.md) |
| lite / start\_lite                     | 沿用来源与真实回退原因进入 [Lite](lite/SKILL.md)                                                        |
| select、clarify 且 requires\_user\_input | 按 [版本选择](references/doubao-delivery.md#版本选择) 展示 interaction，等待真实作答后续办；超时和网络失败不称登录失效        |
| blocked                                | 说明实际阻塞，保留请求；不重建、不绕过禁止 Lite 的选择                                                             |

不可续期或实际刷新失败按 [认证恢复](references/auth-recovery.md)；expired 且 refresh\_available=true 由业务调用刷新。后续失败与回退也由该文档统一定义。

## 查询、续办与完成条件

- 正式直播新建或续办读 [正式流程](references/formal-workflow.md)；已有任务始终保存并沿用 environment/profile/account\_id/project\_name/task\_id，不以当前账号补成原身份。
- 创建成功后按 [交付规则](references/doubao-delivery.md#直播任务打开远端操作台) 提供监控台链接，再持续 [结束监听](references/task-completion-watch.md)。首批成功、链接可访问、后台进程已启动均不是完成条件；结束的 Agent 不会被 watcher 自动唤醒。
- 直播默认到质检报告及复盘交付才完成，视频到每项报告交付。任务终态、报告保存、页面核验、用户交付和清理分别记录。真实中断按交付规则附链接、状态与原任务续办信息。
- 用户要求结束正式检测读 [结束任务](references/task-end.md)，停止检测不结束抖音直播。不提供人工审核、实时警告或直播中断操作。内部 API 仅按需查 [接口索引](references/api-index.md)，不得借 Schema 扩展产品范围。


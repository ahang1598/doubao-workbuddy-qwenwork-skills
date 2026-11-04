---
name: douyin-live-inspect
metadata:
  display_name: 抖音直播实时质检与内容复盘
  version: "1.0.17"
description: 抖音、小红书直播实时质检与视频单项、批量质检，识别画面、话术及内容风险。支持按品牌或账号名查找直播间；交付质检报告，直播另提供内容复盘与优化建议。
---

# 抖音直播实时质检与内容复盘

支持抖音与小红书直播页、HTTP(S) FLV 实时质检，以及视频附件/链接单项或批量质检。直播结束交付质检报告与内容复盘；视频仅交付质检报告。结论统一称“AI 判定”，证据不足不表示通过或人工复核。

## Skill 目录定位（执行脚本前必读）

以本次加载的本文件所在目录作为 Inspect 根目录。主流程命令从根目录执行，Lite 和视频分别进入 `lite/`、`video/`；读取引用不改变命令目录，含空格的路径须引用。正式版要求 Node.js 20+，Lite 要求 Python 3.10+。

无法确定根目录或入口不可用时，停止执行并反馈已确认的错误，不猜测路径、不从其他安装目录补齐文件、不据此登录或回退 Lite。正确目录仍缺文件时，说明需重新安装完整 Skill。

执行业务请求前读取 [入口与任务沿用](references/telemetry.md)。

## 确定检测类型

- 新请求仅提供品牌名或账号名时，按[品牌 / 账号搜索入口](references/live-search.md)取得实际直播间链接，再进入下方流程；已有链接跳过搜索，已有任务沿原任务续办。仅查找直播间时交付候选，不开始检测。
- 抖音直播页、分享短链、follow/live，以及在官方抖音域名下含唯一数字 live\_web\_rid 的页面链接（包括搜索直播链接）和 HTTP(S) FLV 流进入直播。FLV 优先于视频分流；完整链接交解析器，不根据裸房间号或 ActivityId 拼接链接。链接细则见 [任务创建](references/task-create.md#直播链接解析规则)。
- 小红书 `www.xiaohongshu.com/livestream/<数字ID>` 及 `xhslink.com` 官方分享短链进入直播，正式版和 Lite 均支持；短链须实际跳转到直播详情页。从已打开页面提取 FLV 时先用宿主 browser-use，按[浏览器取流](references/browser-stream-fallback.md#豆包内置浏览器取流正式版与-lite-共用)交接候选；不调用外部 Chrome DevTools。其余取流与浏览器补充见 [小红书接入](references/task-create.md#小红书直播)。按品牌或账号搜索仍仅支持抖音。
- 视频附件/网络视频链接进入视频；明确 Lite 的本机文件直接进 [Lite](lite/SKILL.md)。Lite 不下载网络视频。
- 来源或意图不明时先补齐，不执行账号探测。混合直播与视频先选一类；多个视频交批次流程。
- 已有任务按原类型、身份和目录续办；类型不明先询问，不跨两套接口试探。仅查询项目/场景见 [项目与场景选择](references/product-boundary.md#项目与场景选择)，无需检测来源，不创建任务。

## 1. 新建直播与视频账号入口分流

1. 明确选择 Lite、免账号体验或没有火山账号时直接进 [Lite](lite/SKILL.md)。本次已选择登录则直接按 [认证恢复](references/auth-recovery.md#登录能力检查) 续办；交付授权链接时须提示授权完成后回到当前对话回复“已授权”或“继续”，不承诺自动续接对话；其他已确认版本和输入复用，不新增持久偏好。已有或创建结果未知的任务不进入本节。
2. 来源明确但尚未选择版本的新请求，从 Skill 根目录执行下面唯一对应的入口命令（参数分别传入）：
   - 直播：`node scripts/inspect-entry.mjs --kind live --task-state not_created`
   - 视频：`node scripts/inspect-entry.mjs --kind video --task-state not_created`
     入口不接收 URL（包括位置参数或 `--url`）；链接保留在对话中，选定版本后交给对应创建流程。用户禁止 Lite 时追加 `--no-lite`；固定 online，需要时追加 `--profile <NAME>`。不要把多个参数合并成一个字符串，也不要前置独立账号探测、auth-status、Schema 检查、多文档预读或 doctor。
3. 首次入口就返回目录和执行环境；用户明确选择 Lite 后执行 `node scripts/inspect-entry.mjs --kind live|video --task-state not_created --mode lite --task-dir "<首次入口目录>"`，返回同一 `task_id` 和 `task_dir`；实际 start/start-video 复用该目录及执行环境，批次则作为 batch_dir 使用。入口仅预留标识，不开始采集。未选版本时只返回选择卡片，不读取火山账号、不查询项目。用户选择正式版后执行 `node scripts/inspect-entry.mjs --kind live|video --task-state not_created --mode formal --task-dir "<首次入口目录>"`，才检查认证和查询项目；正式版探测共享10秒预算，清理最多另1秒。选择 Lite 不触发任何正式版调用。保留 route/reason/next\_action/projects/interaction/timings。

| 入口结果                                   | 下一步只读所需流程                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| formal / select\_project               | 直接复用完整 projects，不重复查询；直播读 [正式流程](references/formal-workflow.md)，视频读 [视频流程](video/SKILL.md) |
| lite / start\_lite                     | 沿用来源与真实回退原因进入 [Lite](lite/SKILL.md)                                                        |
| select、clarify 且 requires\_user\_input | 按 [版本选择](references/doubao-delivery.md#版本选择) 展示 interaction，等待真实作答后续办；超时和网络失败不称登录失效        |
| blocked                                | 说明实际阻塞，保留请求；不重建、不绕过禁止 Lite 的选择                                                             |

不可续期或实际刷新失败按 [认证恢复](references/auth-recovery.md)；expired 且 refresh\_available=true 由业务调用刷新。后续失败与回退也由该文档统一定义。

## 查询、续办与完成条件

- 正式直播新建或续办读 [正式流程](references/formal-workflow.md)；已有任务始终保存并沿用 environment/profile/account\_id/project\_name/task\_id，不以当前账号补成原身份。
- 正式版创建成功后按 [交付规则](references/doubao-delivery.md#直播任务打开远端操作台) 提供监控台链接，再持续 [结束监听](references/task-completion-watch.md)。首批成功、链接可访问、后台进程已启动均不是完成条件；结束的 Agent 不会被 watcher 自动唤醒。
- 直播默认到质检报告及复盘交付才完成，视频到每项报告交付。分别确认任务终态、报告保存、页面核验、用户交付和清理。真实中断按交付规则附链接、状态与原任务续办信息。
- 用户要求结束正式检测读 [结束任务](references/task-end.md)，停止检测不结束抖音直播。不提供人工审核、实时警告或直播中断操作。内部 API 仅按需查 [接口索引](references/api-index.md)，不得借 Schema 扩展产品范围。


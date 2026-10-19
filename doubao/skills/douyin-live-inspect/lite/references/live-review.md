# Lite 直播判定

当前直播使用本流程；策略适用范围及内部标识见 [实时策略](../SKILL.md#实时策略)。旧任务保留原提交协议和批次上限。

## 领取与判断

当前 Agent 默认串行，每批最多20段，不限制批内媒体时长；有段即判。第一次执行 `review-next --limit 20 --request-id <唯一ID>`，后续直接使用提交返回的 next。保留同一 dispatcher_id，默认 main。

读取返回的 segments 和 rules；规则已完整读过且版本一致时复用缓存。大结果优先完整读取 result_file，无法读取时只沿 next_page_argv 恢复。仅把 context_subtitles 用作语境，命中引用当前片段的 evidence_ids。

按实际内容应用核心规则，普通商品带货追加 ecommerce，投资分析或投顾内容追加 finance。追加时使用 rules_load_contract，执行 `rules-load --next` 并直接使用新合同。已经加载的专项无需重复追加。

## 精简提交

字幕模式模板中的每段填写：

```json
{
  "segment_id": 1,
  "summary": "本段介绍产品使用方法",
  "reviewed": true,
  "images_viewed": [],
  "rules": []
}
```

保留外层 task_id、context_id 和返回的真实 segment_id。reviewed=true 表示本段判断已完成；rules 只保存命中项，每项包含 rule_id、status=hit、简短 reason 和引用本段 evidence_ids 的 events。未命中填空数组，运行时补齐其他规则与渠道。

沿用返回的 input_path；宿主写文件工具要求先读取时，先完整读取已有模板，再序列化模型完成的判断、写入并执行 submit_command_argv。不要因写入被拒绝重新领取批次；工具拒绝写入不代表判定已提交。模型负责语义判断，脚本只负责序列化和提交。提交后按 next 的实际动作续办；有片段直接处理，空批次按 status 等待，不重复领取。JSON 出错按行列修复；repair_required 时只修改失败项，执行新的 retry_command_argv，成功项不重判。

写入与提交分别核验：写入完成后确认原 input_path 是完整可解析的 JSON，且 task_id、context_id、片段与当前合同一致，再从当前加载的 Lite 根目录用启动任务时的同一 Python 3.10+ 环境执行 `python3 scripts/live_inspect.py`（Windows 用 `python`），后接返回的 submit_command_argv。宿主命令应设置工作目录为该 Lite 根目录；不要使用合同内供旧调用方兼容的 submit_argv 或 submit_shell_command 所带的解释器、脚本绝对路径。写文件工具暂不可用时，不立即改用长 heredoc；仅在 shell 已确认正常且原写入已结束时使用替代写入，随后重新核验文件。仅有文件存在、内容已填写或命令已受理，都不表示判定已保存。

旧任务回执缺少 submit_command_argv 时，先核实当前加载的 Lite 根目录和原 task_dir，再从旧 submit_argv 中取 `review-submit` 起的全部参数，包括原 request-id，按上述方式执行。旧 retry_argv 和 recovery_argv 分别从 `review-submit`、`review-recover` 起取参数；旧 snapshot_check.argv 从 `status` 起取参数。若原命令是否执行成功不明，先按原 request-id 查询 review-state；不能因路径失效重新领取或创建任务。

开启 image_inspection 的任务使用返回的完整合同，实际查看图片并填写 images_viewed。仅字幕任务的检测方式为“字幕检测”。旧完整 rules 和 no_hit_rule_ids 仍可提交，沿用其已有结构，不混用 reviewed 短格式。

## 结束与异常

空批次时按 `next_action` 自动续办：返回 status 则每次最多等3秒后查询状态；返回 review-next 则用新的 request-id 领取；有片段和合同才直接提交；返回 report 才转报告阶段。顶层 continuation_instruction 与 next 内实际动作共同描述本次续办；旧回执说明与动作冲突时以实际 next_action 为准。不要反复重放同一空批次请求来等待新内容，旧 request-id 只恢复原回执。

用户未回复、阶段性进度已发出、直播运行较久均不构成停止条件；不新增“是否继续”的选择，不把继续判定交还给用户触发。直播仍在采集时持续循环，进度播报后继续执行。用户明确停止时先 stop，再按 next_action 在固定收尾预算内处理剩余片段；仅明确舍弃剩余检测才立即停止。运行时已结束的批次直接进入下一步，不补交或重采集。

积压、批次无进展和结束收尾统一按[实时策略](../SKILL.md#实时策略)执行：未领取积压超过 3 分钟保留最近 2 分钟；已领取批次 120 秒无成功提交或收尾 120 秒到期后关闭剩余检测，进入部分报告。轮询和修复失败不刷新预算；保存的片段不重判。空批次仍按回执续办，不等用户。

交付质检报告，并按 recap_input 和 submission_contract 完成复盘。复盘最多三次尝试，每次 120 秒；terminal_failure 时交付真实失败说明并确认 failed/chat，不重开检测、不无限重试。

已明确保存的结果不重放；提交状态未知时用原 request-id 调用 review-state。EVIDENCE_CHANGED 时重新领取。真实会话中断后回原 task_dir 续办。

### 宿主工具故障与后台命令

- 命令超过前台等待时间并转入后台，不代表失败或成功。保存原宿主任务 ID、request-id、context-id、input_path 和合同；用宿主提供的任务输出工具查询原命令，不叠加新的提交。只有成功回执明确保存的片段，或 review-state 核实的 saved_segment_ids，才能计入已判定数量；部分保存仅统计成功项。
- 出现 `File writing is temporarily unavailable`、`FILE_WORKER_INIT_FAILED`，或不访问数据库的简单命令也返回 `COMMAND_TIMEOUT` 时，报告“宿主工具执行受阻、判定暂停”，停止反复换写法、启动命令或尝试清理。无法查询或停止原命令时保留状态未知，不据此推断它已退出，也不重建质检任务。
- SQLite 忙锁日志只说明对应调用遇到竞争；没有关联原请求、时间和阶段的证据，不归因为数据库持续锁死。没有检查到错误结束标记或输入等待证据，不归因为 heredoc 未结束。宿主内部原因未知时明确说明，不用“资源竞争”代替诊断。
- 分别说明采集、媒体处理、判定和报告的最后核实状态与时间。采集进程存活、工作台刷新或字幕增加均不代表 Agent 仍在判定；工具不可用时不承诺后台自动完成或自动唤醒。流解析失败按采集层报告，不抹去已保存判定，也不当作 SQLite 故障。

### 工具恢复后核对原任务

1. 以原 task_dir 和原 request-id 调用 review-state，并核对宿主原命令。运行中或退出未确认时不重复提交；用户明确要求继续且工具恢复后，可按下述显式接管流程处理。
2. 若请求返回 unknown / not_observed 且没有绑定信息，另执行一次仅带原 context-id 的 review-state 查询批次；不要把无绑定的 request-id 与 context-id 强行组合。批次 pending 只表示尚未保存，不证明宿主命令未执行；context 查询也不能证明原命令已经退出。
3. saved / result_available 时读取已有回执及下一批合同，不重放成功项；partial 时只处理 pending_segment_ids。优先沿用返回的 retry_command_argv / repair 指引；旧合同失效或 evidence_changed 时按返回动作重新取得有效合同，stopped 时进入原任务收尾。
4. 请求记录缺失但宿主明确确认原命令已退出、当前批次仍 pending / partial、证据与合同有效时，沿原 input_path 和提交合同仅提交未保存项，使用新的唯一 request-id，并保留原合同的 --next 和 dispatcher 参数。此路径不依赖 context 查询生成 retry_argv；不能确认上述条件时继续保留暂停状态，不猜测提交结果、不重新 start。

### 显式接管串行批次

仅用户明确要求恢复/继续且宿主工具可用时，按上述方式执行 context 查询返回的 recovery_command_argv（review-recover --takeover）；不是超时自动重试，也不需要伪造旧命令退出证明。此命令只接管当前 Agent 串行批次，不接管历史 child 任务，不重启采集。

运行时在事务内使旧合同失效，返回新 context、新 input_path 和提交合同。旧草稿保持原样；只处理新合同中的未保存段，已经复制的判断仍须核对完整性。规则或证据变化时不得搬用旧判断，按错误动作重读证据。损坏草稿保留，使用新模板修复。

接管命令输出丢失时查询接管自身的 request-id；status=recovered 或 superseded 时读取 recovery_receipt，按其 next_action 继续，不能执行旧 receipt 的命令。接管返回大结果时沿 result_file / result-page 读全。重复请求或重复接管旧 context 不再分配新代次。

repair 的 retry_command_argv 保留原 --next、dispatcher、规则版本及批量限制；历史记录恢复不出选项时按 after_submit_action 补交后续领，不自行补参数。已停止、冻结或过期时按 status/report 收尾，不重开原积压。

质检交付受阻不阻塞复盘生成；按[交付](delivery.md)中的生成与交付独立续办规则继续。

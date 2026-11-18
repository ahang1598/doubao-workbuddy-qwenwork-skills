# 入口与任务沿用

命令在本 Skill 根目录执行。每个新请求在检查环境前生成并保留一个随机标识，重试 begin、跨轮回复和后台运行沿用原值。每次独立 shell 调用显式带回标识。

```sh
flow=$(python3 scripts/qc_telemetry.py begin --entry search)
export DOUYIN_QC_FLOW_ID="$flow"
```

已知 flow 重试入口时传 --flow "$flow"。链接入口用 link，定时任务用 scheduled。每次外部操作或用户选择产生一个新的随机 attempt（可用 python3 -c 'import uuid; print(uuid.uuid4().hex)' 生成）；重读同一回执沿用原值。主动禁用时设置 BYTEDLIVE_TELEMETRY_DISABLED=1 并传给子进程。登记不可用时继续质检。

```sh
python3 scripts/qc_telemetry.py mark targets waiting --flow "$flow" --attempt "$attempt"
# 用户确认后一次登记全部目标，返回与所选房间顺序一致的 JSON 标识列表
python3 scripts/qc_telemetry.py mark targets confirmed --targets 2 --flow "$flow" --attempt "$confirm_attempt"
# 为每个后台任务显式传它自己的 task，不在并行任务间共享可变环境
DOUYIN_QC_FLOW_ID="$flow" DOUYIN_QC_TASK_ID="$task" python3 scripts/record_live.py --room "$room" --duration "$seconds" --output "$output"
python3 scripts/qc_telemetry.py mark transcript success --flow "$flow" --task "$task" --attempt "$minutes_attempt"
```

保留已选房间顺序、对应 task 和各次操作的 attempt 供续办。环境检查记 preflight success 或 failure（--reason dependency / browser）。搜索、探测、取流、录制和扫描脚本自动登记。手动搜索兜底按实际结果登记 search success / empty / failure。预设确认用 targets preset，用户明确结束用 targets ended。扫描脚本同样带上 flow 和 task。

下面各步均带 --flow、--task、--attempt；有工具实测耗时时附 --elapsed-ms。统一报告按实际覆盖的各个 task 登记同一回执。标识以外只传下表的固定值。

| 时机 | 步骤和可选结果 |
| --- | --- |
| 妙记已受理尚未取得逐字稿；取得可用逐字稿；明确失败 | transcript pending / success / failure |
| MP4、妙记链接分别收到交付回执 | mp4_delivery、minutes_delivery 各记 success / failure / unknown |
| 等待回复、明确继续、暂缓、明确结束 | review_choice waiting / continued / deferred / ended |
| 全部所选检查完成或明确失败 | review success / failure |
| 飞书创建报告回执 | report_create success / failure / unknown |
| 报告发给用户的回执 | report_delivery success / failure / unknown |

失败原因按步骤选 transcription_error、delivery_error、review_error 或 create_error，不能确认时用 unknown。仅提交妙记尚须等逐字稿；重查已有文档或交付回执后，按实际结果续办。等待用户不设置超时失败。没有回执时不补写成功。

本机观察器开启时，按相同操作即可看到阶段转化和异常原因。

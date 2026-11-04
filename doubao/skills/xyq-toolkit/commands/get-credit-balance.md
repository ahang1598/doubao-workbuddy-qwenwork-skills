# get-credit-balance：当前空间积分余额

用于查询本次选择的个人或团队空间有效积分余额。默认沿用已保存的空间（通过 `space list` 查看），单次覆盖使用 `--team-id TEAM_ID`（`0` 为个人）。无需用户 ID 或任务 ID，不创建生成任务、不轮询，也不需要消耗积分的确认。

```bash
pippit-tool-cli get-credit-balance
```

成功输出示例：

```json
{"total_remain_amount":"123"}
```

读取字符串 `total_remain_amount` 展示余额，`"0"` 是有效零余额。失败或缺少字段时报告查询失败，不能当作余额为零。

排查请求时使用 `pippit-tool-cli get-credit-balance --with-log-id`，保留返回的 `log_id`。该命令不提供积分明细、到期时间或生成任务费用估算。鉴权失败按 [授权说明](auth.md) 处理。

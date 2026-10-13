# 滚动窗口算术

仅在任务明确要求同一对象的近期 `N` 项与此前不重叠的 `M` 项比较时使用。`N`、`M`、单位和可选的新鲜度上限必须来自任务，不得补默认值。零工具请求不得运行。

```text
python3 scripts/rolling_metrics.py INPUT.json
python3 scripts/rolling_metrics.py -
python3 scripts/rolling_metrics.py --schema
```

输入为 `{as_of,rows}`。每行固定含唯一非空 `id`、正整数 `recent_count`、正整数 `prior_count`、`observations[{at,value}]`，并可含正数 `max_staleness_seconds`。时间戳必须带时区且严格升序、唯一；`value` 为有限数或 `null`。程序不排序、不补零。

只使用 `at <= as_of` 的最后 `N+M` 项：前 `M` 项为 prior，后 `N` 项为 recent。输出逐行含 `status`、`reason`、`ratio`、请求/选中/非空/未来排除计数、两窗边界与均值、最后合资格时点、距截止秒数和新鲜度状态。

只有两窗完整、无 `null`、prior 均值非零且已声明的新鲜度约束未失败时才返回 `supported`。其他结果为 `unknown`，原因固定为 `insufficient_observations`、`missing_value_in_selected_windows`、`zero_prior_mean` 或 `stale_latest_observation`。未提供新鲜度上限时输出 `not_assessed`，不得暗示数据新鲜。

模块暴露 `process(doc)`。CLI 只读 JSON、只写 JSON、不联网、不写文件。错误非零退出且只输出 `{error:{code,message}}`。`--schema` 输出机器可读 I/O 合同。算术不验证来源、频率、交易日、单位或经济含义。

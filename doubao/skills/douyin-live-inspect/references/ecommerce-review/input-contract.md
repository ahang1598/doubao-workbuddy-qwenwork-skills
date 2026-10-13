# GetReport → 场景化直播复盘输入契约（V1）

## 契约标识

`input_contract` 必须为 `ecommerce_review_skill/v1`。

## 唯一允许的输入

```json
{
  "input_contract": "ecommerce_review_skill/v1",
  "review_dimensions": ["content_analysis"],
  "fd": {
    "sg": [{ "i": 1, "sid": 1, "st": 0, "et": 60000, "tx": "该时间段内的主播 ASR", "tc": 0, "cm": [], "dc": [], "rp": [], "ia": [], "wm": {} }],
    "pd": { "ps": [], "cf": {} },
    "wd": { "ws": [] },
    "scs": {},
    "bm": {},
    "iad": [],
    "ev": {
      "scope": "asr_and_quality_report_only",
      "limitations": ["comments_unavailable", "products_unavailable", "interactions_unavailable", "window_metrics_unavailable", "conversion_metrics_unavailable"],
      "quality_report": {
        "source": "livesaas_quality_get_report",
        "project_name": "项目名",
        "task_id": 1,
        "task_status": 3,
        "scenario_id": 9058,
        "scenario_name": "电商",
        "overall_conclusion_code": 1,
        "rules": [{ "rule_id": 1, "rule_name": "规则名", "conclusion": "0", "finding_count": 0, "machine_status_code": 0, "manual_status_code": 0 }]
      }
    }
  }
}
```

- `review_dimensions`：固定为 `content_analysis`；当前数据不足以生成 `live_score`。
- `fd.sg`：从 GetReport 完整 ASR 归一化出的有序分段。`st`、`et` 是整数毫秒；`tc/cm/dc/rp/ia/wm` 保留原电商复盘契约要求的类型，缺数据时使用类型正确的空值。
- `fd.pd/fd.wd/fd.scs/fd.bm/fd.iad`：保持原电商复盘输入结构；当前链路无对应数据时分别传入空数组或空对象，不得省略、不得伪造。
- `fd.ev.quality_report`：GetReport 的任务状态、场景 ID/名称、整体结论和规则命中摘要。`scenario_name` 来自本次已核验场景；电商、金融、汽车使用对应指导，其他名称使用通用复盘，不能按数字 ID 跨项目推断行业。
- `quality_report.rules[]`：`rule_id`、三个状态/计数字段为整数或文档明确允许的 `null`；`rule_name`、`conclusion` 为字符串；带时间证据时 `start_time/end_time` 为整数毫秒。
- `finding_count`：优先使用接口显式非负整数计数，否则与质检报告共用机审命中证据计数；不得使用 `ManualDetails` 的人审记录条数替代。机审命中但证据缺失、或状态未知时为 `null`，不能解读成 0；复盘汇总遇到缺失计数显示未知，不把部分计数当作总数。
- `fd.ev.scope`：固定为 `asr_and_quality_report_only`，用于防止 Agent 扩展到未提供的数据。

完整 ASR 展示和回放不属于 `ecommerce_review_skill/v1` 的分析输出。准备脚本把时间对齐 ASR 与 GetReport 的 `TaskResult.RecordURL/Vid` 单独保存为权限 `0600` 的临时渲染上下文，只向 Agent 返回 opaque `render_context_id`；渲染器内部读取后分别注入本地报告的“内容分析”时间线和播放器。完整 ASR 与媒体地址不得出现在 stdout、对话或日志中。

## 强制边界

- 不接受真实评论、商品、互动、成交、观众或窗口指标作为 V1 输入；对应字段只保留类型正确的空结构。
- 不因输入中偶然存在额外字段而使用它们。
- 不从主播话术推断真实销量、库存、商品属性或用户反馈。
- 质检规则“未命中”只代表该规则未发现风险，不代表主播陈述已经事实核验。
- 无时间戳的质检结论只能用于全局总结，不得绑定到具体片段。
- 允许为分析读取完整 ASR；最终回答不得输出原始 ASR 全文。

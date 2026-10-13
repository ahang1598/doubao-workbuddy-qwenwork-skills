# 脚本接口

两个脚本仅使用 Python 标准库，默认不联网、不修改输入文件、不保存日志。

## 生成清单

```bash
python3 scripts/build_registration_checklist.py INPUT.json \
  --output OUTPUT.md \
  [--summary SUMMARY.json]
```

输入遵循 `assets/registration-intake-template.json`。脚本验证字段、来源引用、官方来源的结构化学校与适用范围、运行时 Tool 状态、逐来源获取/授权状态、已确认事项证据和常见隐私数据，然后按阶段和截止时间的绝对时刻排序。官方机构邮箱只能放在官方来源的 `public_contact`。

`runtime.network_tool_status` 只能是 `available_authorized`、`available_authorization_pending`、`unavailable` 或 `not_used`。每个来源必须提供 `access_method`、`authorization_status` 和 `retrieved_at`；实际联网获取时 `retrieved_at` 必须是带时区的 ISO 8601 时间戳。授权待确认或受限的联网来源不能支持 `confirmed`。

输出：

- `OUTPUT.md`：报到执行清单；
- `SUMMARY.json`：可选的机器可读核验摘要，包含输入 SHA-256、事项数、状态统计和告警。

禁止让输入、Markdown 输出或摘要使用同一路径。脚本先完成校验，再写新文件，校验失败不会覆盖已有输出。

## 严格校验

```bash
python3 scripts/validate_registration_checklist.py \
  --input INPUT.json \
  --checklist OUTPUT.md \
  [--strict]
```

校验标题、事项 ID 覆盖、状态标签、来源、隐私模式和严格准出条件。`--strict` 会重算输入指纹并将清单与确定性生成结果逐字比较；手工改动后必须重新生成。

## 退出码

- `0`：成功；
- `1`：质量校验未通过，可根据输出问题修复后重跑；
- `2`：命令、路径或输入结构错误；
- `3`：文件读取或写入失败。

任何非零退出码都不得忽略。返回 2 时先修复输入或命令；返回 3 时保留原始文件，改用明确可写的新路径后重试。

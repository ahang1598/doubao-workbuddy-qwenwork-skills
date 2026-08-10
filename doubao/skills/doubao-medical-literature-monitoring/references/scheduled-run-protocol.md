# 定时运行协议

任务 query 只保存：

```text
action=scheduled_run
task_id={真实任务 ID}
previous_report_doc={上一期飞书报告 URL}
last_success_at={上次成功时间}
seen_source_keys={可选；已呈现来源的紧凑去重提示}
subscription={关注主题领域、重点标注话题、更新频率、来源范围偏好}
```

来源范围偏好只影响查询加权、补充和排序，不是硬准入或逐站覆盖要求。

每次运行：

1. 读取原任务并恢复四项设置；上一期报告和 `seen_source_keys` 可用时用于减少重复，不可用时继续执行；
2. 对 `last_success_at-overlap` 至当前时间先并行执行 General Search 与 Scholar Search；General 同时搜索中英文医学资讯，Scholar 传明确起止日期；
3. General/Scholar 完成后，无论条目是否已足，都尽量并行尝试 PubMed、Europe PMC MED、Crossref 三个结构化 URL；单个入口失败直接跳过，不循环重试；正式发表研究仍不足时才补预印本；
4. 候选保留在当前上下文；显式读取 `references/dedup-and-medical-delta.md`，再尽量减少明显重复并识别真实状态变化，但不为跨期去重额外逐篇回读，也不逐批写本地文件；
5. 检索和筛选完成后只写一次可读 UTF-8 `report-data.json`，并只用它创建新的本期报告；每个条目标题本身链接该条 `source_url`；
6. 用 `scope=full` 回读新报告一次，只确认正文非空、主要章节和入选标题存在；不检查 `display_id` 方括号或空格格式；
7. 更新原任务的 `previous_report_doc` 和 `last_success_at`，保留订阅设置、schedule 与时区；能方便生成时一并更新 `seen_source_keys`，缺失不阻塞；
8. 再读取同一任务一次确认，然后发送本期摘要和新报告链接。

所有主要检索入口都不可用时，可呈现已核验内容，但写明“本期检索未完整，暂不能判断是否无更新”，并保留旧 query。无重要更新时仍创建一份简短的新报告。报告与任务各回读一次即可，不重复创建文档或叠加多套校验。

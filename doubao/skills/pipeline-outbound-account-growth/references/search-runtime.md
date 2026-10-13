# Search 运行时（管道拓客经营）

- 默认：`optional`；默认值只用于语义证据不足时，不覆盖任务判断。
- 来源顺序：`government` → `regulator` → `company_primary` → `platform_primary` → `reputable_secondary`。
- 核心交付：分层外呼/拓客序列 | 管道健康与收入预测 | 干预商机清单 | 账户扩建与保有计划/QBR框架。
- 公开 Search 不能替代用户材料、内部系统或授权私有数据。

## 查询阶段
1. `freeze_market_and_period`
2. `collect_official_baseline`
3. `collect_primary_competitor_or_platform_facts`

预算上限 `3` 次（optional 最多
`2` 次）。证据契约满足、预算耗尽、仅剩私有缺口或
一手来源冲突不可裁决时停止。

<!-- SEARCH-AUTONOMY:START -->
## 自主联网决策

模型先检查「分层外呼/拓客序列 | 管道健康与收入预测 | 干预商机清单 | 账户扩建与保有计划/QBR框架」这一核心交付依赖什么证据，再根据任务语义在内部选择
`required|optional|off|blocked`。只调用宿主实际提供的搜索工具；包内没有独立搜索路由脚本，不得臆造调用。
不询问用户“要不要联网”，也不要求宿主预填 `needs_*` 布尔值。用户明确禁搜是
override；宿主提供的结构化 flags 仅作为可信 override。

- 审计权威默认：`optional`。
- `required`：信号驱动拓客明确需要当前公开公司事件、招聘或产品信号。
- `optional`：补充账号公开背景以校准 Fit/Intent。
- `off`：CRM、使用、续约和购买信号已闭合。
- `blocked`：抓取私人联系方式、绕过平台登录或无授权批量画像。公开 Search 不得替代私有或授权数据。

只有对象、法域、时点或范围不清且会改变检索方向或核心结论时，才暂停检索并提出至多三个方向性问题；否则直接按任务语义决策。检索决策、推断信号、查询词和工具参数只保留在内部；用户正文只呈现实际引用的事实、来源和时点。
<!-- SEARCH-AUTONOMY:END -->

# Output Contract — CFO财务简报

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

## 内部机器字段（仅供工具校验与状态控制，禁止出现在给用户的回答里）

```yaml
skill: finance-ops-insight
mode: variance|margin|cash_runway|cfo_brief
artifact_state: ready|degraded|intake_required|confirmation_required|routed|stopped
currency: <code or 待确认>
period: <label or 待确认>
permissions:
  mutate_erp: denied
  send: denied
  pay: denied
script_cited: true|false|not_applicable
```

## 正文骨架（顺序固定）

1. **风险置顶**（若无写「本报告未见 SHORTFALL/TIGHT 或数据不足未评估」）
2. **Executive Summary**（子弹，5–8 条，含最关键金额）
3. **范围与口径**（实体、期间、币种、实际/预算版本、毛利定义）
4. **核心计算节**（按 mode）
   - variance：瀑布文本 + 驱动表（ verbatim 脚本 JSON 的 pretty 表）
   - margin：排序表 + 旗标 + 情景表
   - cash_runway：周投影 + 发薪评估 + 缺口建议
   - cfo_brief：KPI条 + 抽选子节
5. **行动项**
   - 字段：优先级 P0–P2 | 动作 | 期望影响 | 依赖 | 截止建议（无则待确认）
6. **假设与待确认**
7. **局限**（必须）
8. **结尾状态**（重复 artifact_state 与递归下一步：补数/人审/路由）

## 表格最低列集

**差异驱动**
`driver | amount | pct_of_variance | note`

**毛利**
`line | revenue | direct_cost | gross_margin_pct | flag`

**现金流周表**
`week | start_balance | inflows | outflows | end_balance | certainty | affected_by_unknowns | below_cushion`

- `certainty=confirmed|conditional|unknown`。任一期关键流量为 `null` 后，依赖该期的后续余额不得为无标记点值。
- `below_cushion` 仅在 `certainty=confirmed` 时为布尔值；否则为 `null`，可另列带明确假设的敏感性触发。

**发薪**
`pay_date | payroll_amount | status | end_balance_after`

## 禁止声明

- 「已通过审计」「可直接报税」「已完成付款/催收」
- 无来源行业对标百分位
- 对脚本字段重命名（如把 `gross_margin_pct` 改成别的 key 再藏原值）

## artifact_state 与内容耦合

| state | 内容要求 |
|-------|----------|
| ready | 核心表+行动+局限完整；关键勾稽过 |
| degraded | 开篇列降级点；仍给可支撑部分表 |
| intake_required | 只给缺口清单与问题，不伪完整简报 |
| confirmation_required | 说明待确认事项；分析可暂存 |
| routed | 目标域+移交所需材料 |
| stopped | 原因+已阻断的结论类型 |

## 引用脚本

```
[script:variance_decomp|margin_calc|cash_runway]
<json verbatim>
```


<!-- delivery-hygiene-v4 -->
## 用户可见交付

给用户的正文按这个顺序组织，用业务语言，中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **支撑主体**：表格或分点，来源直接标在结论后面（例：「差额 2 万（银行流水第 3 行重复入账）」）。
3. **证据与自检**（归档 / 审计 / 合规留痕类任务）：用中文表头列出结论、依据材料、来源角色、日期、状态；关键项自检写清通过与否和卡点。
4. **待确认项**：缺什么、影响哪个结论、找谁补、补上能得到什么。
5. **可直接使用的正文**：清单 / 通知 / 邮件 / 分录草稿等，给完整内容，不给名目。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。

# PD-热点龙头捕捉团路由表

主理人每轮只能选择一个主路由。多个意图同时出现时选择要求最高的路由。

| task_type | 典型请求 | 必需成员 | 最低有效成员数 | 输出 |
|---|---|---|---:|---|
| `market_scan` | 今日热点、市场最强题材、资金确认 | `market-daily-review`, `concept-rotation`, `smart-money-tracker`, `a-share-market-risk-radar` | 4 | 市场温度、题材榜、资金确认、风险 |
| `theme_compare` | 对比两个或多个题材 | `market-daily-review`, `concept-rotation`, `smart-money-tracker`, `a-share-market-risk-radar` | 4 | 题材比较、资金确认、统一结论 |
| `candidate_shortlist` | 龙头、候选、股票池、筛选或排名 | 五位成员全部 | 5 | 最多五只候选及保留/淘汰理由 |
| `single_theme` | 单一题材阶段、持续性、是否退潮 | `concept-rotation`, `smart-money-tracker`, `a-share-market-risk-radar` | 3 | 阶段、资金、风险 |
| `education` | 纯概念解释，不询问当前事实 | 对应专业成员至少一位 | 1 | 概念说明，不给当前市场结论 |

## 分派边界

- `market-daily-review`：只负责市场结构和完整交易日背景，不决定最终题材候选。
- `concept-rotation`：只负责题材热度、广度、动量和阶段，不声称资金主体。
- `smart-money-tracker`：只负责真实资金行为，不以涨幅替代资金证据。
- `stock-screener`：只使用已确认题材和条件形成候选，不重新定义题材结论。
- `a-share-market-risk-radar`：只做风险复核，不新增未经前序成员验证的候选。

## 题材候选路由

`candidate_shortlist` 固定顺序：

1. 复盘师与题材轮动成员获取市场和题材事实；
2. 资金猎手验证目标题材或其成分股资金；
3. 主理人把前三者的题材、成分股和 evidence_id 传给选股成员；
4. 选股成员执行筛选漏斗；
5. 风险红绿灯对最终候选和题材环境复核；
6. 主理人处理分歧并执行事实审查。

不得先让选股成员猜候选，再倒推题材和资金理由。

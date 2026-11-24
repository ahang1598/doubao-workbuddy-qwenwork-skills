# 任务路由

在判断用户请求应进入哪个执行手册时读取本文件。

## 三种需求起点

保留股票筛选的三种真实起点：

1. **直接筛个股：** 用户已经知道要筛什么股票或股票池。
2. **先找行业：** 用户没有明确股票，希望先找到值得关注的行业方向。
3. **先找主题：** 用户从政策、技术、事件或产业趋势出发，希望找到真正受益公司。

只要用户没有明确要求极简、只要名单、不要图表、不要研报或不要生成文档，开放式股票筛选默认按正式报告处理。确定路由后先读取并执行 `references/formal-report-execution-contract.md`，再进入对应 playbook 和模板。

## 锚定顺序

按以下顺序收敛任务范围：

1. 市场和证券类型。
2. 指定股票列表或指数股票池。
3. 行业、主题或产业链环节。
4. 策略风格或指标条件。
5. 用户排除条件和风险约束。
6. 输出形式和篇幅约束。

## 路由表

| 用户意图 | 主要执行手册 |
|---|---|
| “帮我看下/筛一下/有哪些优质股/核心标的/值得关注股票”等开放式找股票 | 先识别行业、主题、产业链或策略锚点，再进入对应执行手册；没有锚点时用 `playbooks/direct-stock-screening.md` |
| 按明确条件找股票 | `playbooks/direct-stock-screening.md` |
| 比较指定股票 | `playbooks/stock-comparison.md` |
| 在指定行业中筛选 | `playbooks/industry-screening.md` |
| 先发现行业方向 | `playbooks/industry-discovery.md` |
| 筛主题或概念 | `playbooks/theme-screening.md` |
| 按策略或风格筛选 | `playbooks/strategy-screening.md` |
| 筛产业链环节 | `playbooks/supply-chain-screening.md` |
| 识别龙头 | 若同时有行业/主题/产业链锚点，先进入对应手册，再叠加 `playbooks/leader-identification.md` 的龙头分层模块；只有纯龙头定义任务才单独使用 `playbooks/leader-identification.md`。概念/主题龙头报告默认保持概念/主题筛选版式，不改写成“龙头结论-龙头定义-龙头矩阵”的单独报告 |
| 核查历史热门概念事件 | `playbooks/historical-theme-event-check.md` |

## 避免事项

- 用户已经指定行业时，不再执行全市场行业发现。
- 用户只要求比较指定股票时，不扩展成完整股票推荐列表。
- 用户只需要局部判断时，不套固定报告目录。
- 不要因为用户用了“帮我看下”这类口语表达，就降级为简短列表；只要任务是找优质股、核心标的、龙头股或候选股，默认仍按正式股票筛选流程执行。

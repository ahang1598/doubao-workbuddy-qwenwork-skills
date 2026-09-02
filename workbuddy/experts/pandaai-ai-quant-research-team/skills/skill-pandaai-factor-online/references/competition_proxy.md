# 比赛规则代理脚本

scripts/competition_proxy.py 只处理保存到本地的 UTF-8 JSON，不调用 CLI、不创建因子、不提交因子池。
输出始终是本地代理，不是官方积分。

## 输入快照

~~~
{
  "as_of": "2026-08-11",
  "factors": [{
    "name": "F-A17",
    "direction": 1,
    "effective_date": "2026-01-10",
    "rank_ic": [{"date": "2026-01-12", "value": 0.04}],
    "ic": [{"date": "2026-01-12", "value": 0.03}],
    "portfolio_months": [{
      "month": "2026-07",
      "portfolio_daily_returns": [0.001, -0.002],
      "benchmark_daily_returns": [0.0005, -0.001],
      "turnover": 0.18,
      "max_drawdown": 0.04
    }]
  }]
}
~~~

- rank_ic 和 ic 都必须按池统一调仓周期记录；rank_ic 是 Spearman，ic 是 Pearson。
- A 的 RankIC 是完整有效周期序列均值；ICIR 和胜率使用匹配日期的 Pearson IC 序列，不做月度均值替代。
- A 的五年窗口锚定因子入池/正式生效日期；版本不变时不随月份滚动。标记为 `out_of_sample` 的正式生效后记录另行并入 A。
- B 从 effective_date 之后的新增记录开始，ICIR 和胜率持续累计，不按月清零。
- portfolio_daily_returns 是扣成本后的组合日收益；benchmark_daily_returns 是同日基准收益。
- turnover 为当月统一调仓日单边换手率之和，小数 0.18 表示 18%。
- daily_excess_returns 只可用于旧数据的调仓期代理，不能称为官方 Rex_ann 或 SR_ann。

## 运行

~~~
python3 scripts/competition_proxy.py snapshot.json > report.json
~~~

严格 C 需要组合与基准日账本。缺少基准日收益时，脚本会输出 excess-only proxy 警告，并使用
日频超额的保守代理，不会标记为官方结果。

collect_results.py 从 CLI 的单因子图表构造的是调仓期代理：

- RankIC 只按统一调仓周期抽样；
- C 的日频组合账本、动态股票池、池级 Winsorize/Z-score/等权合成仍不可得；
- 结果只能用于 shortlist、换手和风险复盘。

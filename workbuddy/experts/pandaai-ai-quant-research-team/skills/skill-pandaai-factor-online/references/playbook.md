# Playbook / 实操手册

A concrete path from a fresh account to a defensible submission, plus the templates the loop needs.
从新账号到一个站得住的提交的具体路径，以及流程中要用的模板。

## Credit budget first / 先算算力预算

Creating a factor is free. The server determines the charge; on 2026-08-05 a successful CLI 0.1.3
Python run deducted 2 credits. Check completed-run `billing.deducted` before allocating the budget,
because the failure mode is spending everything on stage 1.

创建因子不扣算力，实际扣费由服务端结算；2026-08-05 在 CLI 0.1.3 上成功运行 Python 因子扣了 2 算力。
开始前先通过首个完成运行的 `billing.deducted` 核对口径再定分配，因为典型的翻车方式就是把预算全花在第一阶段。

| Stage / 阶段 | Runs / 次数 | Purpose / 目的 |
|---|---|---|
| Probe / 试探 | 40% | Short window, wide coverage of hypotheses / 短区间，广撒网测假设 |
| Full window / 全区间 | 30% | Survivors only / 只跑幸存者 |
| Falsification / 证伪 | 20% | Variants that could break the finding / 可能推翻结论的变体 |
| Out-of-sample / 样本外 | 10% | Reserved non-overlapping range / 预留的不重叠区间 |

`pandaai-cli --json balance` before and after each batch; a batch that costs more than expected
usually means silent retries. Wait a couple of minutes before the second reading — the deduction
settles behind the run, so an immediate check undercounts and the missing credits turn up later.
每批前后各查一次 `pandaai-cli --json balance`；花费超出预期通常意味着有静默重试。
第二次读之前等两分钟：扣费结算滞后于运行，立刻去读会读少，少掉的那部分过一会儿才出现。

## Stage 1: probe / 第一阶段：试探

Write 10–15 candidates spanning **different hypotheses**, not 15 variants of one. Run them over a
three-month window to catch syntax and field errors cheaply, then over the full window only if the
formula is valid and the sign is as expected.

写 10–15 个覆盖**不同假设**的候选，而不是同一个想法的 15 个变体。先在三个月区间上跑，
便宜地暴露语法和字段错误；公式有效且符号符合预期，再上全区间。

Axes worth covering at least once each, with skeletons using verified operators. These are starting
points to test, not recommendations — several will fail in any given regime.
下面这些轴各覆盖一次，附用已验证算子写的骨架。这些是待检验的起点，不是推荐；在任一风格周期里都会有几条失效。

```
Reversal / 反转          BIAS(CLOSE,N)                       direction 0
Momentum / 动量          ROC(CLOSE,N)                        direction 1
Distance to high / 距高点 CLOSE/TS_MAX(HIGH,N)                direction 0
Trend position / 趋势位置 CLOSE/MA(CLOSE,N)                   direction 0 or 1
Volatility / 波动率      STD(RETURNS(CLOSE,1),N)             direction 0
Illiquidity / 非流动性   MA(ABS(RETURNS(CLOSE,1))/AMOUNT,N)  direction 1
Turnover / 换手          MA(TURNOVER,N)                      direction 0
Price-volume corr / 量价 CORRELATION(CLOSE,VOLUME,N)         direction 0
Size / 规模              MARKET_CAP                          direction 0
Valuation / 估值         (any *_ttm ratio field)             direction depends
```

Record every candidate you test, including failures. The count is the denominator of your
multiple-testing correction, and it is worthless if you only keep the winners.
记录你测过的每一个候选，包括失败的。这个数量是多重检验校正的分母，只留赢家就等于没有分母。

## Stage 2: retrospective worksheet / 第二阶段：复盘表

Fill this in after every batch. One row per surviving candidate.
每批跑完填一次，每个幸存候选一行。

```
Candidate / 候选:
Mechanism / 机制:        (one sentence; if blank, treat as noise / 一句话，空着就当噪声)
Max corr with existing / 与已有因子最大相关:      0.__  vs ______
Falsification test / 证伪测试:                    (what would break it / 什么能推翻它)
  result / 结果:
Excess return / 超额收益:  __%
Turnover / 换手率:         __%  →  cost / 成本 __%  →  net / 净额 __%
Per-year breakdown / 分年:  Y1 __%  Y2 __%  Y3 __%
Decision / 决策:           escalate / orthogonalize / abandon
                           加码 / 正交化 / 放弃
```

The decision field is mandatory and must be one of the three words. "Keep looking at it" is how a
dead direction survives to waste another batch.
决策字段必填，且只能是三选一。「再看看」正是死掉的方向存活下来、再浪费一批算力的方式。

## Stage 3: falsification menu / 第三阶段：证伪菜单

For a finding to earn a full-window run, pick at least one and test it.
一个结论要值得跑全区间，至少挑一条测过。

| Test / 测试 | How / 做法 |
|---|---|
| Size contamination / 规模污染 | Exclude the smallest 20% by market cap and re-run / 剔除市值最小 20% 后重跑 |
| Regime dependence / 风格依赖 | Split by calendar year, check the full reserved span / 按自然年拆开，覆盖完整预留区间 |
| Cycle sensitivity / 周期敏感 | Re-run at a different `--adjustment-cycle` / 换调仓周期重跑 |
| Window arbitrariness / 窗口任意性 | Vary N by ±50%; a cliff means overfitting / N 变动 ±50%，出现悬崖就是过拟合 |
| Redundancy / 冗余 | Spearman correlation against existing factors / 与已有因子做 Spearman 相关 |

A finding that only holds at one specific N, in one specific year, at one specific rebalance cycle
is a fitted artifact.
只在某个特定 N、某一年、某个特定调仓周期下成立的结论，是拟合出来的假象。

## Stage 4: out-of-sample / 第四阶段：样本外

Because of the ten-year cap, this means re-creating survivors as new factor objects over a reserved
non-overlapping range and comparing sign and magnitude. Decide the reserved range before you look at
it. A survivor that flips sign out of sample is dead, not "regime-dependent".

回测窗口以当前服务端探测结果为准；把幸存者在预留的不重叠区间上重建为新的因子对象，然后对比符号和幅度。
预留区间要在看它之前就定好。样本外符号反转的幸存者是死的，不是「依赖风格周期」。

## Batch file format / 批量文件格式

`scripts/batch.py` reads a plain text file, one candidate per line, fields separated by `~` (chosen
because formulas contain commas and parentheses but never tildes):

`scripts/batch.py` 读一个纯文本文件，每行一个候选，字段用 `~` 分隔
（选它是因为公式里有逗号和括号，但不会有波浪号）：

```
name ~ formula ~ direction
20d bias ~ BIAS(CLOSE,20) ~ 0
60d high distance ~ CLOSE/TS_MAX(HIGH,60) ~ 0
20d illiquidity ~ MA(ABS(RETURNS(CLOSE,1))/AMOUNT,20) ~ 1
```

Lines starting with `#` and blank lines are ignored. The script writes a state file next to the
input so an interrupted batch resumes without re-creating or re-running anything.

以 `#` 开头的行和空行会被忽略。脚本在输入文件旁边写一个状态文件，中断后续跑不会重复创建或重复运行。

## Combining factors / 因子组合

For competition-oriented research, use `--group-number 10`: the rules' synthetic long portfolio is
the highest 10% of the universe. This aligns diagnostics, but does not make the CLI reproduce the
monthly competition score. Screen combinations locally for stability, net long-side return,
turnover, drawdown, and low redundancy, then treat the platform score as the final authority.

参赛导向的研究使用 `--group-number 10`，因为规则的合成多头是全市场最高 10%。这只能对齐诊断口径，不能让 CLI 复现月度积分。
本地可按稳定性、多头净收益、换手、回撤和低冗余筛选组合，最终积分以平台为准。

Rank-normalize each component before weighting, otherwise the weights are meaningless:
加权前先对每个分量做排名归一化，否则权重没有意义：

```
RANK(0-MARKET_CAP)*0.7 + RANK(0-BIAS(CLOSE,20))*0.3
```

Two cautions. A composite of highly correlated components adds turnover without adding signal —
check pairwise correlation first. And composites are where multiple-testing bias concentrates,
because weight grids are cheap to search and every grid point is another test; fix the weights on
economic grounds where you can, and count every combination you tried.

两点注意。高相关分量的组合只增加换手、不增加信号——先查两两相关。另外组合是多重检验偏差最集中的地方，
因为权重网格搜索很便宜，而每个网格点都是一次检验；能用经济含义定权重就定死，并且统计你试过的每一种组合。

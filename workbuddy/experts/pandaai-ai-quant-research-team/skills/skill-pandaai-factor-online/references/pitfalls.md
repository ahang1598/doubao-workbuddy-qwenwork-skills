# Pitfalls / 陷阱清单

Ordered by how much damage they do. The dangerous ones are not the errors that fail loudly — those
cost one run. The dangerous ones produce a valid-looking factor that means something other than what
you wrote.
按危害程度排序。危险的不是报错的那些，报错只花一次算力；危险的是那些能跑出一个看起来合理、
但含义和你写的不是一回事的因子。

## 1. `MEAN` is not a rolling mean / `MEAN` 不是滚动均值

```
MA(CLOSE, 20)        # rolling 20-day mean          / 20 日滚动均值
TS_MEAN(CLOSE, 20)   # identical to MA              / 与 MA 等价
MEAN(A, B)           # mean of two series, element-wise / 两个序列逐元素求均值
```

`MEAN(CLOSE, 20)` parses and runs. It averages `CLOSE` with the constant 20, which for most A-share
prices is close to `(CLOSE + 20) / 2` — a monotone transform of price. The resulting factor is a
**price-level factor**, and price level is strongly related to market cap, so it will look like it
works. Every lookback-window formula must use `MA` or `TS_MEAN`.

`MEAN(CLOSE, 20)` 能解析、能运行。它把 `CLOSE` 和常数 20 求均值，对多数 A 股价格而言约等于
`(CLOSE + 20) / 2`，是价格的单调变换。于是这个因子实际是**价格水平因子**，而价格水平与市值高度相关，
所以它看起来会「有效」。凡是带回看窗口的公式，必须用 `MA` 或 `TS_MEAN`。

## 2. `FUTURE_RETURNS` is look-ahead / `FUTURE_RETURNS` 是未来函数

The operator set includes `FUTURE_RETURNS`. Any factor containing it is reading the answer, and its
backtest is meaningless no matter how good the numbers look. Same goes for any construction that
lets a future bar influence a past value. Treat a suspiciously high IC (say Rank IC above 0.15 with
a tiny p-value) as a look-ahead suspicion first and a discovery second.

算子集合里有 `FUTURE_RETURNS`。任何用到它的因子都是在偷看答案，无论数字多漂亮，回测都没有意义。
任何让未来数据影响过去取值的构造同理。IC 高得可疑（比如 Rank IC 超过 0.15 且 p 值极小）时，
先怀疑未来函数，再考虑是不是真发现。

## 3. Cross-sectional vs time-series operators / 截面算子与时序算子

| Cross-sectional (across stocks, one day) | Time-series (one stock, across days) |
|---|---|
| `RANK(X)` → percentile in `[0,1]` | `TS_RANK(X,N)` → percentile within the last N bars |
| `ZSCORE(X)`, `SCALE(X)` | `TS_ZSCORE(X,N)` |

Mixing them up produces a factor that is silently measuring the wrong thing. When combining factors
with weights, apply `RANK` to each component first — raw values on different scales make the weights
meaningless.

混用会得到一个悄悄测错东西的因子。加权组合多个因子时，先对每个分量取 `RANK`；量纲不同的原始值直接加权，
权重没有意义。

## 4. Direction flag inverts the whole reading / 方向参数会颠倒全部解读

`--factor-direction 1` means higher factor value is expected to be better; `0` means lower is better.
The decile labels do **not** follow the flag: `分组1` is always the lowest factor value and `分组10`
always the highest. So the long side is `分组10` at direction 1 and `分组1` at direction 0. Read the
wrong end and monotonicity looks inverted and excess return flips sign. Confirm by checking that
`多空组合` equals long minus short; if it does not, you have the ends backwards.

`--factor-direction 1` 表示因子值越大越好，`0` 表示越小越好。但分组编号**不跟着**这个参数变：
`分组1` 永远是因子值最低的一组，`分组10` 永远是最高的一组。所以方向为 1 时多头侧是分组10，
为 0 时是分组1。看错一端，单调性看着是反的、超额收益符号也反。可以用 `多空组合` 是否等于
多头减空头来验证；不等，就是两端搞反了。

## 5. Warm-up period inside the window / 窗口内的预热期

A 250-day lookback at the start of a long window has no history to work with, so the first
year or so of factor values may be missing or unstable. The backtest still reports a number for the
whole window. Long-window factors are effectively evaluated on less data than short-window ones,
which makes their statistics less comparable than they appear.

长窗口开头的 250 日回看没有历史可用，因此前一段的因子值可能缺失或不稳定，而回测仍会给出整段的数字。
长窗口因子实际被评估的数据量少于短窗口因子，两者的统计量没有表面上那么可比。

## 6. Fundamental fields are step functions / 基本面字段是阶梯函数

`_lyr` fields update once a year, `_ttm` once a quarter. Under a 5-day rebalance the factor barely
moves between report dates, so most of the variation you are trading comes from price moving against
a fixed denominator. That is a valid factor, but it is a **price** factor wearing fundamentals
clothing — check its correlation with a pure price factor before claiming a fundamental effect.
Report dates also arrive with a lag; a value dated to the fiscal period was not knowable then.

`_lyr` 字段一年更新一次，`_ttm` 一季度一次。5 日调仓下，两个报告期之间因子几乎不动，
所以你交易的波动主要来自价格相对固定分母的变化。这是个有效因子，但它是**披着基本面外衣的价格因子**——
声称发现基本面效应之前，先算它与纯价格因子的相关性。另外报告有披露滞后，标注在会计期上的数值在当时并不可知。

## 7. Negative and near-zero denominators / 负数与接近零的分母

Valuation ratios blow up on loss-making companies: a small negative earnings figure produces a large
negative P/E that sorts into an extreme decile for a reason that has nothing to do with valuation.
Either filter those names out with `IF`, or rank the reciprocal (earnings yield) instead of the
ratio.

估值类比率在亏损公司上会爆掉：一个很小的负利润会得到一个很大的负 PE，然后因为一个与估值无关的原因
被排进极端分组。要么用 `IF` 把这些股票剔掉，要么排序倒数（收益率形式）而不是比率本身。

## 8. Sentinel values distort `RANK` / 哨兵值会扭曲 `RANK`

Excluding names with `IF(cond, -99999, expr)` works, but those sentinels still occupy the bottom of
the cross-section and compress the real values into a narrower percentile band. Prefer excluding
through a filter that removes the name from the universe if the platform allows it; if you must use
a sentinel, verify the group counts still look sane.

用 `IF(cond, -99999, expr)` 排除股票是可行的，但哨兵值仍占据截面底部，把真实取值压缩到更窄的分位区间里。
如果平台允许，优先用能把股票移出票池的方式排除；一定要用哨兵值，就检查一下各组数量是否还正常。

## 9. Everything correlates with market cap / 一切都和市值相关

In A-shares, a large share of apparent factor performance is a size exposure in disguise: price
level, liquidity, volatility, turnover, and analyst-coverage proxies all load on size. Before
claiming a new axis, download factor values and compute cross-sectional Spearman correlation against
market cap (`scripts/analyze.py corr`). Correlation above roughly 0.6 means you found size again.

A 股里，相当一部分表面上的因子收益其实是变相的规模暴露：价格水平、流动性、波动率、换手率、
覆盖度代理都载荷在规模上。宣称找到新的一条轴之前，下载因子值并与市值做截面 Spearman 相关
（`scripts/analyze.py corr`）。相关性大约超过 0.6 就说明你又找到了规模。

## 10. Turnover is a cost, and the headline is long-short / 换手是成本，头条数字是多空

Two mistakes that compound. The platform headlines a long-short annualized return, which assumes a
short leg that A-share retail participants cannot build; and turnover is reported as a rate rather
than folded into returns. A high-turnover factor with a strong long-short number can be a losing
strategy in practice. Convert first, compare second:

两个会叠加的错误。平台把多空年化放在最显眼处，而这假设了 A 股散户建不起来的空头腿；换手率是单独报告的比率，
没有折进收益里。一个高换手、多空数字很强的因子，实操上可能是亏的。先折算，再比较：

```
annual cost ≈ turnover × one_way_cost × 2 × (252 / rebalance_days)
年化成本 ≈ 换手率 × 单边成本 × 2 × (252 / 调仓天数)
```

`one_way_cost` is the cost of one side. The default is 0.3% per side in this skill, so a complete
buy-and-sell is 0.6%; slippage on small caps can dominate the rest.
`单边成本`指买入或卖出一边的成本。本技能默认每边 0.3%，完整买卖合计 0.6%，
小市值股票的冲击成本可能盖过其余项。

The reported `turnoverRate` is the share of the held top/bottom 10% portfolio replaced per rebalance.
报告中的 `turnoverRate` 是每次调仓被替换掉的前10%或后10%等权组合持仓比例。

## 11. The server cap shapes your design / 服务端上限决定你的设计

The CLI may support long windows, but the accepted range is a server-side capability. Probe the current
server limit before budgeting. Out-of-sample validation still means creating a second factor object over
a reserved non-overlapping range and comparing.

CLI 支持的长窗口不等于服务端一定接受；规划算力前先探测当前服务端上限。样本外验证仍意味着在预留的不重叠区间上再建一个因子对象然后对比。
不要因为窗口变长就跳过——长样本仍然可能被风格周期和选择偏差污染。

## 12. Regime dependence within the available span / 可用跨度内的风格切换

Even a long A-share sample can be dominated by a few style regimes. A factor that is flat for
most of the sample and spectacular for six months has one observation, not robust evidence. Always
break performance down by calendar year before believing a headline number.

可用跨度的 A 股数据仍可能被几种风格周期主导。一个大部分时间平淡、半年爆发的因子，只是一个观测，不是稳健证据。
相信头条数字之前，先按自然年拆开看。

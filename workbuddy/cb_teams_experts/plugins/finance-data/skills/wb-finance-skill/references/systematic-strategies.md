# 量化策略库（systematic-strategies）

> **何时参考**：用户问"配对交易 / 事件驱动策略 / 季节性策略 / 机器学习策略 / 对冲策略 / 波动率策略 / 量化策略怎么搭"。

## 核心目标

**多种量化策略模板的标准化方法论**——用于投资组合增强与另类收益捕获。

## 六大策略类型

### 1. 配对交易（均值回归）
- 找高度相关的两个标的（同行业龙头、加密货币对 BTC/ETH）
- 监测价格比值 / 价差的 Z-score 偏离
- 触发：Z > 2.0 时反向交易（做空 A 买多 B），Z < 0.5 时平仓
- 严格 50%-50% 等权对冲，不预测绝对方向
- 持续相关性监测防止相关系数破裂

### 2. 事件驱动
- 信息源：财报 / 宏观数据 / 政策 / 技术面突破
- 时间衰减：距事件 N 天后信号以 e^(-λN) 衰减（λ=0.1 时 10 天衰减至 37%）
- 信号组合：事件信号（事件加权求和）+ 技术信号（α 权重通常 0.6-0.4）

### 3. 季节性 / 日历效应
- 统计历史 N 年同一时段的超额收益分布（一月效应、四月暴跌、12 月上涨、周一 vs 周五）
- 历史超额收益显著且稳定时，可在该时段提高风险敞口
- 样本量需充分、排除幸存者偏差、近期有效性 < 5 年则需更新

### 4. 机器学习策略
- 输入特征：技术指标（EMA / RSI）+ 基本面（PE / 增长率）+ 市场微观结构（波动率 / 换手率）
- 目标变量：N 日后超额收益（>0 为正样本）
- **严格避免前向偏差**——test set 未来数据不入 training
- 缺点：黑箱性强、容易过拟合、市场制度改变时失效快——需频繁回测

### 5. 对冲策略
- 多空配对：绝对收益不取决于市场方向，只依赖选股能力
- 因子对冲：组合中隐含某些因子暴露（如大市值偏向）→ 通过空头反向因子中性化系统风险
- 对冲成本（融券费率）需纳入
- 完全对冲降低绝对收益——平衡 beta 暴露与夏普

### 6. 波动率策略
- 监测市场波动率（ATR 或 implied vol）
- 波动率低时增加杠杆、波动率高时降杠杆（vol-targeting）
- VIX > 20 时做空波动率，VIX < 12 时做多波动率
- 波动率 mean-reversion 周期较长（数周）——短期内容易反向

## 通用要点

- 策略需严格参数化与可重复性，避免过度人工干预
- 样本外测试（walk-forward）+ 压力测试必须执行
- 回测拟合度 80-90% 较合理（> 95% 警惕过拟合）
- 多策略组合时注意相关性——高相关策略不分散风险
- 策略容纳量（AUM capacity）有限——规模过大滑点损耗大

## 建议骨架（不强制）

- 各策略核心逻辑与参数
- 单策略与组合回测（总收益 / 夏普 / 最大回撤 / 胜率）
- 策略间相关系数与组合优化权重
- 压力测试与样本外测试结果
- 策略有效期与失效触发条件
- 持仓规模与容纳量限制

## 避坑

- 历史回测收益常过度乐观——实盘收益通常打 5-7 折
- 不同市场环境（牛 / 熊 / 震荡）下策略表现差异极大——分阶段评估
- 策略拥挤（同一逻辑被多个投资者使用）会导致快速失效与相互踩踏
- 流动性不足的标的（小盘股 / 债券）做空成本高且难以平仓——评估交易成本可实现性
- 机器学习策略在样本外表现常远低于样本内

## 可执行工具（scripts/quant/）

⚠️ **数据 skill 的能力边界**：
- **westock / neodata 已覆盖**：拉取标的 OHLCV、财务数据、宏观时序——是策略的**输入原料**
- **westock / neodata 都不覆盖**：策略本身的 **Z-score 引擎 / 波动率目标算法 / 季节效应统计 / 因子 IC-IR 回测 / VWAP-TWAP 计算**——这些是**算法实现**，不是数据查询，数据 skill 不会替你算策略信号

**所以本场景的流程是**：westock/neodata 拉数据 → script 跑策略算法 → 输出信号 / 回测结果。**不要让 model 凭记忆模拟 Z-score 或回测**——已有 production 实现就直接调。

每个 script 都有 `SignalEngine` class，调用模式：`engine = SignalEngine(参数); signals = engine.generate({"代码": ohlcv_df})`。

| 文件 | 策略 | 行数 | 输入要求 |
|---|---|---|---|
| `pair_trading.py` | 配对交易（双标的 Z-score 均值回归，默认 lookback=60、entry_z=2.0、exit_z=0.5） | 152 | 恰好 2 个标的 OHLCV |
| `volatility.py` | 波动率策略（vol-targeting / VIX 套利） | 162 | OHLCV + 波动率序列 |
| `seasonality.py` | 季节性 / 日历效应（月度 / 周度 / 节假日） | 145 | **DataFrame 必须用 DatetimeIndex** 而非 RangeIndex |
| `factor_multi.py` | 多因子选股（IC/IR + 分层回测 + 因子组合） | 202 | OHLCV + 多个因子值列 |
| `factor_fundamental.py` | 基本面因子筛选（PE / PB / ROE 多因子打分） | 127 | OHLCV + 基本面数据 |
| `minute_data.py` | 分钟级数据处理（VWAP / TWAP / 取分钟 K 线，函数式 API：`compute_vwap(df)`/`compute_twap(df)`/`fetch_minute_candles(...)`/`hourly_volume`/`volume_profile`） | 146 | **DataFrame 需含 `high / low / close / volume` 4 列**（compute_vwap 用 typical price (H+L+C)/3 加权） |

**Setup**：
```bash
pip install pandas numpy requests
```
未装报 `ModuleNotFoundError`，6 个 script 都依赖这三个基础包，无其它特殊依赖。

**调用示例（配对交易）**：
```python
import sys; sys.path.insert(0, 'scripts/quant')
from pair_trading import SignalEngine
engine = SignalEngine(lookback=60, entry_z=2.0, exit_z=0.5)
signals = engine.generate({"601318.SH": pa_df, "601628.SH": xr_df})
```

**注**：事件驱动 / 机器学习 / 对冲 这三类原始 skill 没提供可执行 script（属于纯方法论），按上面的方法论部分自行实现。

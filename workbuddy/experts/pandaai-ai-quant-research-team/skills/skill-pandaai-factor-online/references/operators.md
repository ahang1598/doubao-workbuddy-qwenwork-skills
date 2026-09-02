# PandaAI Operators / 算子完整参考

> Full text of the official operator reference, reorganized for lookup.
> 官方算子手册全文，按查阅习惯重新整理。
> Source / 出处: https://www.pandaaiquant.com/community/article/72
>
> Annotations added by this skill are marked **[note]** / 本技能补充的批注标记为 **[note]**。

## Read these first / 先看这三条

**`MEAN(A,B)` is not a rolling mean.** It averages two series element-wise. For a lookback window use
`MA(X,N)` or `TS_MEAN(X,N)`. `MEAN(CLOSE,20)` parses and runs, and silently gives you a price-level
factor instead of a moving average.
**`MEAN(A,B)` 不是滚动均值**，它是两个序列逐元素求均值。回看窗口要用 `MA(X,N)` 或 `TS_MEAN(X,N)`。
`MEAN(CLOSE,20)` 能解析能运行，然后悄悄给你一个价格水平因子而不是均线。

**`FUTURE_RETURNS(X,N)` is a look-ahead operator.** Any factor containing it reads the answer and its
backtest is meaningless.
**`FUTURE_RETURNS(X,N)` 是未来函数**，任何用到它的因子都是在偷看答案，回测没有意义。

**Cross-sectional and time-series functions are different tools.** `RANK`, `SCALE`, `ZSCORE` rank
across stocks on one day; `TS_RANK`, `TS_ZSCORE` rank one stock across days. Mixing them measures
something other than what you intended.
**截面函数与时序函数是两回事。** `RANK`、`SCALE`、`ZSCORE` 是同一天在股票之间排；`TS_RANK`、`TS_ZSCORE`
是同一只股票在时间上排。混用会测出与你意图不同的东西。

---

## 基础因子

| 因子名 | 说明 |
| --- | --- |
| CLOSE | 收盘价 |
| OPEN | 开盘价 |
| HIGH | 最高价 |
| LOW | 最低价 |
| VOLUME | 成交量 |
| AMOUNT | 成交额 |
| TURNOVER | 换手率 |
| MARKET_CAP | 总市值 |

---

## 函数分类

### 1. 直接操作型函数 (X)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| ABS(X) | 求X的绝对值 | 返回X中每个元素的绝对值 | ABS(CLOSE-OPEN)返回开盘收盘价差的绝对值 |
| LOG(X) | 对X逐个取自然对数 | 返回X的自然对数 | LOG(CLOSE/OPEN)返回价格比率的对数 |
| LOGABS(X) | 对X的绝对值逐个取自然对数 | 返回ABS(X)的自然对数 | LOGABS(RETURNS(CLOSE,10))返回10日收益率绝对值的对数 |
| AS_FLOAT(X) | 将X布尔值转换为0.0或1.0 | 布尔序列转数值序列 | AS_FLOAT(CLOSE>OPEN)将上涨判断转为0/1 |
| RD(X,N) | 对X进行4舍5入处理 | 保留N位小数，默认2位 | RD(HIGH/LOW,4)保留价格4位小数 |
| SIGN(X) | 返回X的正负号 | 正为1,负为-1,0为0 | SIGN(RETURNS(CLOSE,10))返回收益率方向 |
| SIN(X) | 返回X的正弦值 | 输入为弧度 | SIN(CLOSE/OPEN)计算价格比率的正弦值 |
| COS(X) | 返回X的余弦值 | 输入为弧度 | COS(CLOSE-OPEN)计算价格差值的余弦值 |
| TAN(X) | 返回X的正切值 | 输入为弧度 | TAN(HIGH-LOW)计算当日振幅的正切值 |
| ARCSIN(X) | 返回X的反正弦值 | 输入值范围[-1,1] | ARCSIN((CLOSE-OPEN)/(HIGH-LOW))计算标准化价格差的反正弦值 |
| ARCCOS(X) | 返回X的反余弦值 | 输入值范围[-1,1] | ARCCOS((CLOSE-OPEN)/(HIGH-LOW))计算标准化价格差的反余弦值 |
| ARCTAN(X) | 返回X的反正切值 | 返回弧度值 | ARCTAN(CLOSE-OPEN)计算价格差的反正切值 |

### 2. 截面操作型函数 (X)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| RANK(X) | 求截面排序分位数 | 返回X序列的排名分位数，范围[0,1] | RANK(CLOSE)返回收盘价的排名分位数 |
| SCALE(X) | 将X按截面最大最小值缩放到[-1,1] | 截面标准化到[-1,1]区间 | SCALE(VOLUME)将成交量标准化 |
| ZSCORE(X) | 将X按截面进行z-score标准化 | 截面标准化，均值0方差1 | ZSCORE(RETURNS(CLOSE,10))标准化收益率 |

### 3. 时序操作型函数 (X)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| CONST(X) | 返回X最后一个值组成的常数序列 | 用最后一个值填充整个序列 | CONST(CLOSE)用最后价格填充 |
| BARSLAST(X) | 返回X距离上一次为True已过去多少期 | 计算条件满足后的期数 | BARSLAST(CLOSE>MA(CLOSE,20))计算突破后期数 |
| BARSLASTCOUNT(X) | 统计连续满足X条件的周期数 | 连续True的计数 | BARSLASTCOUNT(CLOSE>OPEN)连续上涨天数 |

### 4. 双参数直接操作型函数 (X,N)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| POWER(X,N) | 对X进行N次幂 | 返回X^N | POWER(RETURNS(CLOSE,10),2)计算收益率平方 |
| SIGNEDPOWER(X,N) | 计算sign(X)*(abs(X)^N) | 保号的幂运算 | SIGNEDPOWER(RETURNS(CLOSE,10),2)保号平方 |

### 5. 时序操作型函数 (X,N)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| REF(X,N) | 返回X整体延后N期后的序列 | 向前引用N期数据 | REF(CLOSE,1)返回前一日收盘价 |
| DELAY(X,N) | 返回X整体延后N期后的序列 | 等同于REF | DELAY(VOLUME,5)返回5日前成交量 |
| DIFF(X,N) | 返回X与其前N期值之差 | 一阶差分，默认N=1 | DIFF(CLOSE,1)返回价格变化 |
| DELTA(X,N) | 返回X与其前N期值之差 | 等同于DIFF | DELTA(CLOSE,1)价格变化量 |
| MA(X,N) | 返回X在过去N日的平均值 | 简单移动平均 | MA(CLOSE,20)计算20日均价 |
| TS_MEAN(X,N) | 返回X在过去N日的平均值 | 等同于MA | TS_MEAN(VOLUME,10)计算10日平均成交量 |
| SUM(X,N) | 返回X在过去N日的滚动求和 | 时序求和 | SUM(VOLUME,5)计算5日成交量总和 |
| PRODUCT(X,N) | 返回X在过去N日的滚动乘积 | 时序乘积 | PRODUCT(1+RETURNS(CLOSE,1),20)计算20日累计收益 |
| ROC(X,N) | 当前值与N日前值的百分比变化 | 变化率 | ROC(CLOSE,5)计算5日收益率 |
| PCT_CHANGE(X,N) | 当前值与N日前值的百分比变化 | 等同于ROC | PCT_CHANGE(CLOSE,1)日收益率 |
| STD(X,N) | 返回X在过去N日的标准差 | 滚动标准差 | STD(RETURNS(CLOSE,1),20)计算20日收益率波动率 |
| STDDEV(X,N) | 返回X在过去N日的标准差 | 等同于STD | STDDEV(CLOSE,10)价格标准差 |
| VAR(X,N) | 返回X在过去N日的滚动方差 | 滚动方差 | VAR(RETURNS(CLOSE,1),20)收益率方差 |
| TS_MAX(X,N) | 返回X在过去N日的最大值 | 滚动最大值 | TS_MAX(HIGH,20)计算20日最高价 |
| TS_MIN(X,N) | 返回X在过去N日的最小值 | 滚动最小值 | TS_MIN(LOW,20)计算20日最低价 |
| TS_MIDDLE(X,N) | 返回X在过去N日的最大最小值的均值 | 滚动中位价 | TS_MIDDLE(CLOSE,10)价格中位数 |
| TS_MAD(X,N) | 返回X在过去N日的平均绝对偏差 | 平均绝对偏差 | TS_MAD(RETURNS(CLOSE,1),20)收益率平均绝对偏差 |
| TS_RANK(X,N) | 返回X在过去N日中的排序百分位数 | 时序排名 | TS_RANK(VOLUME,20)成交量时序排名 |
| TS_ARGMAX(X,N) | 返回X在过去N日中最大值的位置索引 | 最大值位置 | TS_ARGMAX(HIGH,10)最高价出现位置 |
| TS_ARGMIN(X,N) | 返回X在过去N日中最小值的位置索引 | 最小值位置 | TS_ARGMIN(LOW,10)最低价出现位置 |
| HHV(X,N) | 返回X在过去N期的最高值 | 等同于TS_MAX | HHV(HIGH,20)20日最高价 |
| LLV(X,N) | 返回X在过去N期的最低值 | 等同于TS_MIN | LLV(LOW,20)20日最低价 |
| HHVBARS(X,N) | 返回过去N期中距最高值的期数 | 最高值距今期数 | HHVBARS(HIGH,20)最高价距今天数 |
| LLVBARS(X,N) | 返回过去N期中距最低值的期数 | 最低值距今期数 | LLVBARS(LOW,20)最低价距今天数 |
| COUNT(X,N) | 返回X在过去N日中为True的次数 | 条件计数 | COUNT(CLOSE>OPEN,20)20日内上涨天数 |
| EVERY(X,N) | 判断X在过去N日是否全部为True | 全部满足条件 | EVERY(CLOSE>MA5,10)是否连续10日在5日线上 |
| EXIST(X,N) | 判断X在过去N日是否至少为True一次 | 存在满足条件 | EXIST(CLOSE>=DELAY(CLOSE,1)*1.1,20)是否涨停过 |
| BARSSINCEN(X,N) | 返回过去N日内第一次True距今天有几期 | 首次满足距今期数 | BARSSINCEN(VOLUME>MA(VOLUME,20),10) |
| SLOPE(X,N) | 返回X在过去N期的线性回归斜率 | 趋势斜率 | SLOPE(CLOSE,20)计算20日价格趋势 |
| ANGLE(X,N) | 返回X在过去N期的线性回归线角度 | 趋势角度 | ANGLE(CLOSE,10)价格趋势角度 |
| INTERCEPT(X,N) | 返回X在过去N期的线性回归截距 | 回归截距 | INTERCEPT(CLOSE,20)价格回归截距 |
| FORCAST(X,N) | 返回序列N周期线性回归后的预测值 | 线性预测 | FORCAST(CLOSE,10)预测下期价格 |
| DECAYLINEAR(X,N) | 对序列计算移动平均加权 | 线性衰减权重 | DECAYLINEAR(VOLUME,10)衰减加权成交量 |
| TS_ZSCORE(X,N) | 求滚动Z-score值 | 时序标准化 | TS_ZSCORE(CLOSE,20)价格时序标准化 |
| TS_SKEW(X,N) | 返回X过去N期的偏度 | 滚动偏度 | TS_SKEW(RETURNS(CLOSE,1),20)收益率偏度 |
| TS_KURT(X,N) | 返回X过去N期的峰度 | 滚动峰度 | TS_KURT(RETURNS(CLOSE,1),20)收益率峰度 |
| TS_MEDIAN(X,N) | 返回X在过去N日的中位数 | 滚动中位数 | TS_MEDIAN(CLOSE,10)价格中位数 |
| AVEDEV(X,N) | 序列与其平均值的绝对差的平均值 | 平均绝对偏差 | AVEDEV(RETURNS(CLOSE,1),20)收益率平均绝对偏差 |
| EMA(X,N) | 指数移动平均 | 指数加权移动平均 | EMA(CLOSE,12)12日指数移动平均 |
| DMA(X,A) | 动态移动平均 | A作平滑因子,0<A<1 | DMA(CLOSE,0.1)动态移动平均 |
| WMA(X,N) | 序列的N日加权移动平均 | 加权移动平均 | WMA(CLOSE,10)10日加权移动平均 |
| RETURNS(X,N) | 返回X相对于N日前的变化百分比 | 收益率计算 | RETURNS(CLOSE,5)返回5日收益率 |
| FUTURE_RETURNS(X,N) | 返回X相对于N日后的变化百分比 | 未来收益率 | FUTURE_RETURNS(CLOSE,5)未来5日收益率 |
| SHARPE(X,N) | 返回X在过去N日的收益率均值除以标准差 | 夏普比率 | SHARPE(CLOSE,20)计算20日夏普比率 |
| SUM_ABS_PRICE_CHANGE(X,N) | 返回X在N日内价格变化的绝对值总和 | 价格波动总和 | SUM_ABS_PRICE_CHANGE(CLOSE,10) |
| MEAN_ABS_PRICE_CHANGE(X,N) | 返回X在N日内价格变化的绝对值平均 | 平均价格波动 | MEAN_ABS_PRICE_CHANGE(CLOSE,10) |

**[note]** 这一类才是滚动窗口函数，`MA` / `TS_MEAN` 是这里的均值算子。另外 `FUTURE_RETURNS(X,N)` 是
未来函数，回测里用它等于偷看答案，不要用于参赛因子。
This is the rolling-window family; `MA` and `TS_MEAN` are its mean operators. Note also that
`FUTURE_RETURNS(X,N)` looks ahead, so any factor using it has a meaningless backtest.

### 6. 双参数直接操作型函数 (A,B)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| MAX(A,B) | 返回A与B中的较大值 | 逐元素比较最大值 | MAX(CLOSE,OPEN)返回收盘开盘价较大者 |
| MIN(A,B) | 返回A与B中的较小值 | 逐元素比较最小值 | MIN(CLOSE,OPEN)返回收盘开盘价较小者 |
| MEAN(A,B) | 返回A与B均值 | 两序列平均值 | MEAN(HIGH,LOW)返回最高最低价均值 |
| EQUAL(A,B) | 判断A与B是否逐元素相等 | 相等性判断 | EQUAL(CLOSE,OPEN)判断是否十字星 |
| VALUEWHEN(A,B) | 当条件A为True时取B的当前值 | 条件取值 | VALUEWHEN(VOLUME>MA(VOLUME,20),1) |

**[note]** `MEAN` 属于这一类，两个参数都是序列，不是滚动窗口。`MEAN(CLOSE,20)` 会把收盘价与常数 20
逐元素求均值，得到的是价格水平因子。要 20 日均线请用 `MA(CLOSE,20)` 或 `TS_MEAN(CLOSE,20)`。
`MEAN` belongs to this two-series family, so `MEAN(CLOSE,20)` averages price against the constant 20
and yields a price-level factor. Use `MA` or `TS_MEAN` for a lookback window.

### 7. 时序操作型函数 (X,Y)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| CROSS(X,Y) | 判断X是否从下向上穿过Y | 上穿判断 | CROSS(MA(CLOSE,5),MA(CLOSE,20))判断金叉 |

### 8. 三参数时序操作型函数 (A,B,N)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| CORR(A,B,N) | 返回A与B在过去N日的滚动相关系数 | 滚动相关性 | CORR(CLOSE,VOLUME,20)价量相关性 |
| CORRELATION(A,B,N) | 返回A与B在过去N日的滚动相关系数 | 等同于CORR | CORRELATION(CLOSE,VOLUME,20)价量相关性 |
| COV(A,B,N) | 返回A与B在过去N日的滚动协方差 | 滚动协方差 | COV(CLOSE,VOLUME,20) |
| COVARIANCE(A,B,N) | 返回A与B在过去N日的滚动协方差 | 等同于COV | COVARIANCE(CLOSE,VOLUME,20) |
| TS_REGRESSION(A,B,N) | 返回对A和B进行滚动线性回归后每个窗口的斜率 | 滚动回归斜率 | TS_REGRESSION(CLOSE,VOLUME,20) |
| SUMIF(A,B,N) | A为True时累加B，求过去N日之和 | 条件求和 | SUMIF(CLOSE>OPEN,VOLUME,10) |
| LONGCROSS(A,B,N) | 判断A连续N期低于B后是否上穿 | 长期穿越 | LONGCROSS(PRICE,MA20,5) |

### 9. 三参数时序操作型函数 (X,N,M)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| LAST(X,N,M) | 判断X从N期到M期是否全为True | 期间条件判断 | LAST(CLOSE>MA(CLOSE,20),1,10)判断收盘价是否持续在MA20均线上方 |
| SMA(X,N,M) | 中国式的SMA,按权重M/N平滑的加权平均 | 中式移动平均 | SMA(CLOSE,12,1)中式12日均线 |

### 10. 条件操作型函数 (X,A,B)

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| IF(X,A,B) | 若X为True则取A否则取B | 条件选择 | IF(CLOSE>OPEN,1,-1)涨跌方向 |

### 11. 技术指标函数

#### 基础指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| ADV(VOLUME,N) | 计算N日平均成交量 | 平均成交量 | ADV(VOLUME,20)计算20日平均成交量 |

#### MACD指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| MACD_DIF(CLOSE,SHORT,LONG,M) | 计算MACD的DIF线 | 快慢线差值 | MACD_DIF(CLOSE,12,26,9) |
| MACD_DEA(CLOSE,SHORT,LONG,M) | 计算MACD的DEA线 | DIF的EMA | MACD_DEA(CLOSE,12,26,9) |
| MACD(CLOSE,SHORT,LONG,M) | 计算MACD柱状图 | (DIF-DEA)*2 | MACD(CLOSE,12,26,9) |

#### KDJ指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| KDJ_K(CLOSE,HIGH,LOW,N,M1,M2) | 计算KDJ的K线 | 随机指标K值 | KDJ_K(CLOSE,HIGH,LOW,9,3,3) |
| KDJ_D(CLOSE,HIGH,LOW,N,M1,M2) | 计算KDJ的D线 | K值的平滑 | KDJ_D(CLOSE,HIGH,LOW,9,3,3) |
| KDJ_J(CLOSE,HIGH,LOW,N,M1,M2) | 计算KDJ的J线 | 3K-2D | KDJ_J(CLOSE,HIGH,LOW,9,3,3) |

#### RSI和威廉指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| RSI(X,N) | N日相对强弱指数 | 相对强弱指标 | RSI(CLOSE,14)计算14日RSI |
| WR(X,N) | 威廉指标 | 威廉%R | WR(CLOSE,14)计算威廉指标 |

#### 布林带指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| BOLL_UPPER(CLOSE,N,P) | 布林带上轨 | 均线+P倍标准差 | BOLL_UPPER(CLOSE,20,2) |
| BOLL_MID(CLOSE,N,P) | 布林带中轨 | N日移动平均 | BOLL_MID(CLOSE,20,2) |
| BOLL_LOWER(CLOSE,N,P) | 布林带下轨 | 均线-P倍标准差 | BOLL_LOWER(CLOSE,20,2) |
| BOLL_WIDTH(X,N) | 布林带宽度 | 上轨-下轨 | BOLL_WIDTH(CLOSE,20) |

#### 其他常用指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| BIAS(CLOSE,N) | 乖离率 | (价格-均线)/均线*100 | BIAS(CLOSE,6)计算乖离率 |
| PSY(CLOSE,N) | 心理线指标 | 上涨天数/总天数*100 | PSY(CLOSE,12)心理线 |
| PSYMA(CLOSE,N,M) | 心理线移动平均 | PSY的移动平均 | PSYMA(CLOSE,12,6) |
| CCI(X,N) | 商品通道指数 | 价格偏离程度指标 | CCI(CLOSE,14)顺势指标 |
| ATR(X,N) | 平均真实波动范围 | 真实波动率 | ATR(CLOSE,14)波动率指标 |
| BBI(CLOSE,M1,M2,M3,M4) | 多空指数 | 多条均线平均 | BBI(CLOSE,3,6,12,20) |

#### DMI指标系列

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| DMI_PDI(CLOSE,HIGH,LOW,M1,M2) | DMI正向指标 | 上升动向指标 | DMI_PDI(CLOSE,HIGH,LOW,14,6) |
| DMI_MDI(CLOSE,HIGH,LOW,M1,M2) | DMI负向指标 | 下降动向指标 | DMI_MDI(CLOSE,HIGH,LOW,14,6) |
| DMI_ADX(CLOSE,HIGH,LOW,M1,M2) | 平均趋向指标 | 趋势强度指标 | DMI_ADX(CLOSE,HIGH,LOW,14,6) |
| DMI_ADXR(CLOSE,HIGH,LOW,M1,M2) | ADXR指标 | ADX评级 | DMI_ADXR(CLOSE,HIGH,LOW,14,6) |

#### 高级移动平均

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| DEMA(X,N) | 双指数移动平均 | EMA的EMA | DEMA(CLOSE,14)双指数平均 |
| TEMA(CLOSE,N) | 三重指数移动平均 | 三次EMA平滑 | TEMA(CLOSE,14)三重指数平均 |
| KAMA(X,N) | 考夫曼自适应移动平均 | 自适应平滑 | KAMA(CLOSE,14)自适应平均 |
| T3(X,N) | 三重指数移动平均 | T3平滑算法 | T3(CLOSE,14)T3平均 |

#### 振荡器指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| PPO(A,B) | 百分比价格振荡器 | (快线-慢线)/慢线*100 | PPO(EMA(CLOSE,12),EMA(CLOSE,26))价格振荡器 |
| AROONOSC(X,N) | 阿隆振荡器 | 最高最低值时间差异 | AROONOSC(CLOSE,14)阿隆振荡器 |
| ADXR(X,N) | ADX评级 | 当前值与历史值平均 | ADXR(CLOSE,14)ADX评级 |
| CMO(X,N) | 钱德动量振荡器 | 动量变化指标 | CMO(CLOSE,14)动量振荡器 |
| STOCHASTIC(X,N) | 随机振荡器 | 价格相对位置 | STOCHASTIC(CLOSE,14)随机指标 |

#### 成交量指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| OBV(CLOSE,VOL) | 能量潮指标 | 成交量平衡指标 | OBV(CLOSE,VOLUME)能量潮 |
| VR(CLOSE,VOLUME,M1) | 成交率比率 | 量价关系指标 | VR(CLOSE,VOLUME,26)成交率 |
| MFI(CLOSE,HIGH,LOW,VOLUME,N) | 资金流量指标 | 成交量RSI | MFI(CLOSE,HIGH,LOW,VOLUME,14) |
| EMV(HIGH,LOW,VOL,N,M) | 简易波动指标 | 价量波动关系 | EMV(HIGH,LOW,VOLUME,14,9) |
| EMVMA(HIGH,LOW,VOL,N,M) | EMV移动平均 | EMV的平滑 | EMVMA(HIGH,LOW,VOLUME,14,9) |

#### 其他技术指标

| 函数 | 说明 | 用法 | 例子 |
| --- | --- | --- | --- |
| TRIX(CLOSE,M1,M2) | 三重指数平滑平均 | 趋势指标 | TRIX(CLOSE,12,9)三重平滑 |
| TRIMA(CLOSE,M1,M2) | TRIX移动平均 | TRIX的平滑 | TRIMA(CLOSE,12,9) |
| DPO(CLOSE,M1,M2,M3) | 区间震荡线 | 去趋势价格 | DPO(CLOSE,20,10,6) |
| DPOMA(CLOSE,M1,M2,M3) | DPO移动平均 | DPO的平滑 | DPOMA(CLOSE,20,10,6) |
| BRAR(OPEN,CLOSE,HIGH,LOW,M1) | BR AR指标 | 人气意愿指标 | BRAR(OPEN,CLOSE,HIGH,LOW,26) |
| ARBR(OPEN,CLOSE,HIGH,LOW,M1) | AR BR指标 | 买卖气势指标 | ARBR(OPEN,CLOSE,HIGH,LOW,26) |
| MTM(CLOSE,N,M) | 动量指标 | 价格动量 | MTM(CLOSE,12,6)动量指标 |
| MTMMA(CLOSE,N,M) | 动量移动平均 | MTM的平滑 | MTMMA(CLOSE,12,6) |
| MASS(HIGH,LOW,N1,N2,M) | 梅斯线 | 价格波动指标 | MASS(HIGH,LOW,9,25,6) |
| MASSMA(HIGH,LOW,N1,N2,M) | MASS移动平均 | MASS的平滑 | MASSMA(HIGH,LOW,9,25,6) |
| ROCMA(CLOSE,N,M) | 变动率移动平均 | ROC的平滑 | ROCMA(CLOSE,12,6) |
| EXPMA(CLOSE,N1,N2) | 指数移动平均 | 短期EMA | EXPMA(CLOSE,12,50) |
| EXPMA2(CLOSE,N1,N2) | 指数移动平均 | 长期EMA | EXPMA2(CLOSE,12,50) |
| ASI(OPEN,CLOSE,HIGH,LOW,M1,M2) | 振动升降指标 | 累积摆动指标 | ASI(OPEN,CLOSE,HIGH,LOW,26,10) |
| ASIT(OPEN,CLOSE,HIGH,LOW,M1,M2) | ASI移动平均 | ASI的平滑 | ASIT(OPEN,CLOSE,HIGH,LOW,26,10) |
| DIF(CLOSE,N1,N2,M) | 差离值 | 短长期均线差 | DIF(CLOSE,10,50,10) |
| DFMA(CLOSE,N1,N2,M) | 差离移动平均 | DIF的平滑 | DFMA(CLOSE,10,50,10) |
| BOLLINGERDIFF(A,B) | 布林差值 | 2倍差值 | BOLLINGERDIFF(HIGH,LOW) |

## 因子编写方法

编写方法主要分为两种方式：

- Python方式（适合有一定编程基础的小伙伴）（易维护，推荐）
- 公式方式（适合无编程基础的小伙伴）

### Python模式

基本语法

```
class CustomFactor(Factor):
    def calculate(self, factors):
        return result

```

重点要求，必须继承Factor，必须实现calculate方法，calculate返回值必须是Series格式，列为value，索引列为[‘symbol’,‘date’]构成的多级索引。

factors包含了基础的量价信息，例如:“close”、“open”、“volume”等，可通过factors[‘close’]方式获取。

#### 示例

```
class ComplexFactor(Factor):
    def calculate(self, factors):
        close = factors['close']
        volume = factors['volume']
        high = factors['high']
        low = factors['low']
        
        # 计算20日收益率
        returns = (close / DELAY(close, 20)) - 1
        # 计算20日波动率
        volatility = STDDEV((close / DELAY(close, 1)) - 1, 20)
        # 计算价格区间
        price_range = (high - low) / close
        # 计算成交量比率
        volume_ratio = volume / DELAY(volume, 1)
        # 计算20日成交量均值
        volume_ma = SUM(volume, 20) / 20
        # 计算动量信号
        momentum = RANK(returns)
        # 计算波动率信号
        vol_signal = IF(volatility > DELAY(volatility, 1), 1, -1)
        # 合成最终因子
        result = momentum * vol_signal * SCALE(volume_ratio / volume_ma)
        return result

```

### 公式方式

基本语法

```
"函数1(函数2(基础因子), 参数) 运算符 函数3(基础因子)"

```

若是公式比较复杂，可以考虑设置中间变量，分多行编写，系统将读取最后一行作为因子值。

```
# 计算20日收益率排名
RANK((CLOSE / DELAY(CLOSE, 20)) - 1)

# 计算价格和成交量的相关性
CORRELATION(CLOSE, VOLUME, 20)

# 复杂因子示例
RANK((CLOSE / DELAY(CLOSE, 20)) - 1) * 
STDDEV((CLOSE / DELAY(CLOSE, 1)) - 1, 20) * 
IF(CLOSE > DELAY(CLOSE, 1), 1, -1)

```

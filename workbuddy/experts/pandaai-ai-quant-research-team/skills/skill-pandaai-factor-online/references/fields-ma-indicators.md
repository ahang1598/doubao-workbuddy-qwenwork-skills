# 均线类指标 / Moving-average indicators

> Field catalog exported from the PandaAI backtest factor list.
> PandaAI 回测因子清单导出的字段目录。

| 字段 | 中文释义与处理参数 | 计算公式 |
|---|---|---|
| `MACD_DIFF, MACD_DEA, MACD_HIST` | 指数平滑移动平均线 MACD SHORT = 12, LONG = 26, M = 9 | DIFF = EMA(CLOSE, SHORT) - EMA(CLOSE, LONG)<br>DEA = EMA(DIFF, M)<br>HIST = (DIFF - DEA) * 2 |
| `TRIX, MATRIX` | 三重指数平均移动平均 TRIX M1 = 12, M2 = 20 | TRIX = (TR - REF(TR, 1)) / REF(TR, 1) * 100;<br>TR = EMA(EMA(EMA(CLOSE, M1), M1), M1)<br>MATRIX= MA(TRIX, M2) |
| `BOLL, BOLL_UP, BOLL_DOWN` | 布林带 BOLL N = 20, P = 2 | BOLL = MA(CLOSE, N)<br>BOLLUP = BOLL + STD(CLOSE, N) * P<br>BOLLDOWN = BOLL - STD(CLOSE, N) * P |
| `ASI, ASIT` | 震动升降指标 ASI M1= 26, M2 = 10 | LC = REF(CLOSE, 1)<br>AA = ABS(HIGH - LC)<br>BB = ABS(LOW - LC)<br>CC = ABS(HIGH - REF(LOW, 1))<br>DD = ABS(LC - REF(OPEN, 1))<br>R = IF((AA BB) & (AA CC), AA + BB / 2 + DD / 4, IF((BB CC) & (BB AA), BB + AA / 2 + DD / 4, CC + DD / 4))<br>X = (CLOSE - LC + (CLOSE - OPEN) / 2 + LC - REF(OPEN, 1))<br>SI = X _ 16 / R _ MAX(AA, BB)<br>ASI = SUM(SI, M1)<br>ASIT = MA(ASI, M2)" |
| `MA3, 5, 10, 20, 30, 55, 60, 120, 250` | 移动均线 MA N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | MA3, 5, 10… = MA(CLOSE, N) |
| `EMA3, 5, 10, 20, 30, 55, 60, 120, 250` | 指数移动均线 EMA N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | EMA3, 5, 10... = EMA(CLOSE, N) |
| `HMA3, 5, 10, 20, 30, 55, 60, 120, 250` | 高价平均线 HMA N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | HMA3, 5, 10... = MA(HIGH, N) |
| `LMA3, 5, 10, 20, 30, 55, 60, 120, 250` | 低价平均线 LMA N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | LMA3, 5, 10… = MA(LOW, N)… |
| `VMA3, 5, 10, 20, 30, 55, 60, 120, 250` | 变异平均线 VMA N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | VV = (HIGH+OPEN+LOW+CLOSE)/4<br>VMA3, 5, 10... = MA(VV, N)… |
| `AMV3, 5, 10, 20, 30, 55, 60, 120, 250` | 成本均线 AMV N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | AMOV = VOLUME * (OPEN + CLOSE) / 2<br>AMV3, 5, 10… = SUM(AMOV, N) / SUM(VOLUME, N)… |
| `VOL3, 5, 10, 20, 30, 55, 60, 120, 250` | 平均换手率(%) VOL N: 3, 5, 10, 20, 30, 55, 60, 120, 250 | HSL =100* VOLUME / CAPITAL<br>VOL3, 5, 10... = MA(HSL, N)<br>HSL 代表换手率<br>CAPITAL 代表流通股本 |
| `DAVOL5, 10, 20` | 平均换手率与 120 日平均换手率比值 DAVOL N: 5, 10, 20 | DAVOL3, 5... = VOLN / VOL120 |
| `BBI, BBIBOLL_UP, BBIBOLL_DOWN` | 多空指标 BBIBOLL M1 = 3, M2 = 6, M3 = 12, M4 = 24, M = 6, N = 11 | BBI = (MA(CLOSE, M1) + MA(CLOSE, M2) + MA(CLOSE, M3) + MA(CLOSE, M4)) / 4<br>BBIBOLLUP = BBI + M * STD(BBI, N)<br>BBIBOLLDOWN = BBI - M * STD(BBI, N)" |
| `DPO, MADPO` | 区间震荡线 DPO M1 = 20, M2 = 10, M = 6 | DPO = CLOSE - REF(MA(CLOSE, M1), M2)<br>MADPO = MA(DPO, M3) |
| `MCST` | 市场成本 MCST | MCST = DMA(AMOUNT / VOLUME, 100 * VOLUME / CAPITAL)<br>AMOUNT 代表成交额<br>CAPITAL 代表流通股本 |

# 超买超卖指标 / Overbought / oversold indicators

> Field catalog exported from the PandaAI backtest factor list.
> PandaAI 回测因子清单导出的字段目录。

| 字段 | 中文释义与处理参数 | 计算公式 |
|---|---|---|
| `OBOS` | 超买超卖指标 OBOS N = 10 | 过去 N 日股票上涨家数之和 – 过去 N 日股票下跌家数之和。 |
| `KDJ_K, KDJ_D, KDJ_J` | 随机波动指标 KDJ N = 9, M1 = 3, M2 = 3 | RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100<br>K = EMA(RSV, (M1 * 2 - 1))<br>D = EMA(K, (M2 * 2 - 1))<br>J = K * 3 - D * 2 |
| `RSI6, RSI10` | 相对强弱指标 RSI N1 = 6, 10 | LC = REF(CLOSE, 1)<br>RSI = MA(MAX(CLOSE - LC, 0), N) / MA(ABS(CLOSE - LC), N) * 100 |
| `WR` | 威廉指标 WR N = 10, L1 = 6 | WR = (HHV(HIGH, N) - CLOSE) / (HHV(HIGH, N) - LLV(LOW, N)) * 100 |
| `LWR1, LWR2` | LWR 威廉指标 LWR N = 9, M1 = 3, M2 = 3 | RSV = (HHV(HIGH,N)-CLOSE)/(HHV(HIGH,N)-LLV(LOW,N))*100<br>LWR1 = SMA_CN(RSV,M1,1)<br>LWR2 = SMA_CN(LWR1,M2,1) |
| `BIAS5, BIAS10, BIAS20` | 乖离率 BIAS L1 = 5, 10, 20 | (CLOSE - MA(CLOSE, L1)) / MA(CLOSE, L1) * 100 |
| `BIAS36, BIAS612, MABIAS` | 36 乖离 BIAS36 | BIAS36 = MA(CLOSE, 3) – MA(CLOSE, 6)<br>BIAS612 = MA(CLOSE, 6) – MA(CLOSE, 12)<br>MABIAS = MA(BIAS36, M) |
| `ACCER` | 幅度涨速 ACCER N = 8 | ACCER = SLOPE (CLOSE, N) / CLOSE |
| `CYF` | 市场能量 CYF N = 21 | CYF = 100 – 100 / (1 + EMA(HSL, N )) |
| `SWL, SWS` | 分水岭 FSL | SWL = (EMA(CLOSE,5)7+EMA(CLOSE,10)3)/10<br>SWS = DMA(EMA(CLOSE,12),MAX(1,100(SUM(VOLUME,5)/(3CAPITAL))))<br>CAPITAL 代表流通股本 |
| `ADTM, MAADTM` | 动态买卖气指标 ADTM N = 23, M = 8 | DTM = IF(OPEN<=REF(OPEN,1),0,MAX((HIGH-OPEN),(OPEN-REF(OPEN,1))))<br>DBM = IF(OPEN>=REF(OPEN,1),0,MAX((OPEN-LOW),(OPEN-REF(OPEN,1))))<br>STM = SUM(DTM,N)<br>SBM = SUM(DBM,N)<br>ADTM = IF(STM>SBM,(STM-SBM)/STM,IF(STM=SBM,0,(STM-SBM)/SBM))<br>MAADTM = MA(ADTM, M) |
| `TR, ATR` | 真实波幅 ATR N = 14，M1 = 9 | TR = SUM(MAX(MAX(HIGH - LOW, ABS(HIGH - REF(CLOSE, 1))), ABS(LOW - REF(CLOSE, 1))), M1)<br>ATR = MA(TR, N) |
| `DKX, MADKX` | 多空线 DKX M = 10 | MID = (3CLOSE+LOW+OPEN+HIGH)/6<br>DKX = (20MID+19REF(MID,1)+18REF(MID,2)+17REF(MID,3)+16REF(MID,4)+15REF(MID,5)+14REF(MID,6)+<br>13REF(MID,7)+12REF(MID,8)+11REF(MID,9)+10REF(MID,10)+9REF(MID,11)+8REF(MID,12)+7REF(MID,13)+<br>6REF(MID,14)+5REF(MID,15)+4REF(MID,16)+3REF(MID,17)+2REF(MID,18)+REF(MID,20))/210<br>MADKX = MA(DKX, M) |
| `TAPI, MATAPI` | 加权指数成交值 TAPI M = 6 | TAPI = AMOUNT / CLOSE<br>MATAPI = MA(TAPI, M)<br>AMOUNT 代表成交额 |
| `OSC` | 变动速率线 OSC N = 10 | 100 * (CLOSE – MA(CLOSE, N)) |
| `CCI` | 商品路径指标 CCI N = 14 | CCI = (TYP – MA(TYP, N)) / (0.015 * AVEDEV (TYP, N))<br>TYP = (HIGH + LOW + CLOSE) / 3 |
| `ROC` | 变形率指标 ROC N = 12 | ROC = 100 * (CLOSE – REF(CLOSE, N) / REF(CLOSE, N) |
| `MFI` | 资金流量指标 MFI N = 14 | TYP = (HIGH + LOW + CLOSE) / 3<br>V1 = SUM(IF(TYP > REF(TYP, 1), TYP * VOLUME, 0), N) / SUM(IF(TYP < REF(TYP, 1), TYP * VOLUME, 0), N)<br>MFI = 100 - ( 100 / ( 1 + V1 ) ) |
| `MTM, MAMTM` | 动量线 MTM N = 14 | MTM = CLOSE – REF(CLOSE, N)<br>MAMTM = MA(MTM, M) |
| `MARSI6, MARSI10` | 相对强弱平均线 MARSI N = 6, 10 | LC = REF(CLOSE, 1)<br>RSI = SMA(MAX(CLOSE - LC, 0), N) / SMA(ABS(CLOSE - LC), N) * 100<br>MARSI = MA(RSI, N) |
| `SKD_K, SKD_D` | 慢速随机指标 SKD N = 9, M = 3 | LOWV = LLV(LOW, N)<br>HIGHV = HHV(HIGH, N)<br>RSV = EMA((CLOSE – LOWV) / (HIGHV – LOWV) * 100, M)<br>SKD_K = EMA(RSV , M)<br>SKD_D = MA(SKD_K, M) |
| `UDL, MAUDL` | 引力线 UDL N1 = 3, N2 = 5, N3 = 10, N4 = 20, M =6 | UDL = (MA(CLOSE,N1)+MA(CLOSE,N2)+MA(CLOSE,N3)+MA(CLOSE,N4))/4<br>MAUDL = MA(UDL,M) |
| `DI1, DI2, ADX, ADXR` | 趋向指标 DMI M1 = 14, M2 = 6 | TR = SUM(MAX(MAX(HIGH - LOW, ABS(HIGH - REF(CLOSE, 1))), ABS(LOW - REF(CLOSE, 1))), M1)<br>HD = HIGH - REF(HIGH, 1)<br>LD = REF(LOW, 1) - LOW<br>DMP = SUM(IF((HD 0) & (HD LD), HD, 0), M1)<br>DMM = SUM(IF((LD 0) & (LD HD), LD, 0), M1)<br>DI1 = DMP * 100 / TR<br>DI2 = DMM * 100 / TR<br>ADX = MA(ABS(DI2 - DI1) / (DI1 + DI2) * 100, M2)<br>ADXR = (ADX + REF(ADX, M2)) / 2" |

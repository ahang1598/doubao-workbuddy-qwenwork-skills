# 能量指标 / Volume and energy indicators

> Field catalog exported from the PandaAI backtest factor list.
> PandaAI 回测因子清单导出的字段目录。

| 字段 | 中文释义与处理参数 | 计算公式 |
|---|---|---|
| `AR, BR` | 人气意愿指标 ARBR M1 = 26 | AR = SUM(HIGH - OPEN, M1) / SUM(OPEN - LOW, M1) * 100<br>BR = SUM(MAX(0, HIGH - REF(CLOSE, 1)), M1) / SUM(MAX(0, REF(CLOSE, 1) - LOW), M1) * 100 |
| `VR, MAVR` | 容量比例 VR M1 = 26, M = 6 | LC = REF(CLOSE, 1)<br>VR = SUM(IF(CLOSE LC, VOL, 0), M1) / SUM(IF(CLOSE <= LC, VOL, 0), M1) * 100<br>MAVR = MA(VR, M) |
| `CR,MACR1, MACR2, MACR3, MACR4` | CR 指标 CR N = 26, M1 = 10, M2 = 20, M3 = 40, M4 = 62 | MID = REF(HIGH+LOW, 1) / 2<br>CR = SUM(MAX(0,HIGH-MID),N)/SUM(MAX(0,MID-LOW),N)*100<br>MACR1 = REF(MA(CR,M1),1+M1/2.5)<br>MACR2 = REF(MA(CR,M2),1+M2/2.5)<br>MACR3 = REF(MA(CR,M3),1+M3/2.5)<br>MACR4= REF(MA(CR,M4),1+M4/2.5) |
| `MASS, MAMASS` | 梅斯线 MASS N1 = 9, N2 = 25, M = 6 | MASS = SUM(MA(HIGH-LOW,N1)/MA(MA(HIGH-LOW,N1),N1),N2)<br>MAMASS = MA(MASS, M) |
| `SY` | 心理线 SY N = 9 | SY = COUNT(CLOSE>REF(CLOSE,1),N)/N*100 |
| `PCNT` | 幅度比 PCNT | PCNT = (CLOSE-REF(CLOSE,1))/CLOSE*100; |
| `CYR, MACYR` | 市场强弱 CYR N = 13, M = 5 | DIVE = 0.01*EMA(AMOUNT,N)/EMA(VOLUME,N)<br>CYR = (DIVE/REF(DIVE,1)-1)*100<br>MACYR = MA(CYR, M) |
| `AMP1,AMP3,AMP5,AMP10,AMP20,AMP60` | 振幅 AMP N:1，3，5，10，20，60 | AMP1,3,5… = (HHV(HIGH,N)-LLV(LOW,N))/REF(CLOSE,N) |
| `WMA3,WMA5,WMA10,WMA20,WMA60,WMA120,WMA250` | 加权移动平均线 WMA N:3，5，10，20，60，120，250 | WMA1,3,5… = (CLOSE*N+REF(CLOSE, 1)*(N-1)+…+REF(CLOSE, N-1)/(1+2+…+N)) |
| `VOLT20, VOLT60` | 近 20 日/60 日波动率 N:20,60 | 20 日/60 日收盘价的标准差 |
| `MDD20，MDD60` | 近 20 日/60 日最大回撤 N:20,60 | 20 日/60 日收盘价的最大回撤 |
| `AROON_UP，AROON_DOWN` | 阿隆指标 N=14 | AROON_UP = [(计算期天数-最高价后的天数)/计算期天数]*100<br>AROON_DOWN = [(计算期天数-最低价后的天数)/计算期天数]*100 |
| `QTYR_5_20` | 5 日 20 日量比 N=5, M=20 | MA(VOLUME, N) / MA(VOLUME, M) |
| `OBV` | 能量潮 OBV | OBV=REF(OBV, 1) + sgn × VOLUME<br>其中，sgn 是符号函数，其数值由下式决定：<br>sgn=1 , CLOSE>REF(CLOSE, 1)<br>sgn=0, CLOSE = REF(CLOSE, 1)<br>sgn=-1 , CLOSE< REF(CLOSE, 1) |

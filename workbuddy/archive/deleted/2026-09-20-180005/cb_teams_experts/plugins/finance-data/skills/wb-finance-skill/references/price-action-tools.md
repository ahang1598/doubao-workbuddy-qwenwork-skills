# 技术指标与形态识别（price-action-tools）

> **何时参考**：用户问"K 线形态 / MACD / RSI / KDJ / 布林带 / 谐波形态 / 艾略特波浪 / 缠论 / 一目均衡表 / SMC 聪明钱 / 指标怎么用"。

## 核心目标

**多维度形态识别综合判断价格结构与转折点**——不依赖单一指标，多系统投票才有高质量信号。

## 七大形态体系（按需选用）

### 1. K 线形态
- 单根（5 类）：锤子 / 倒锤 / 射星 / 十字 / 纺陀
- 双根：吞噬 / 孕线 / 刺穿
- 三根：晨星 / 晚星 / 三白士兵 / 三黑乌鸦
- 多空形态计分生成综合信号
- **必须结合大周期背景判断**——K 线易受噪音影响

### 2. 谐波形态（基于斐波那契几何）
- Gartley：B 在 0.618 XA、D 在 0.786 XA
- Bat：B 在 0.382-0.5 XA、D 在 0.886 XA
- Butterfly：B 在 0.786 XA、D 在 1.27 XA
- Crab：B 在 0.382-0.618 XA、D 在 1.618 XA
- 精准识别 PRZ（潜在反转区）

### 3. 艾略特波浪
- 5 浪推动（1-2-3-4-5）为主趋势
- 3 浪修正（A-B-C）为反弹
- 三铁律 + 斐波那契关系校验：
  - 2 浪回撤 50-61.8%
  - 3 浪通常 = 1 浪 × 1.618
  - 4 浪回撤 38.2%

### 4. 缠论形态
- 分型 → 笔 → 中枢的自动检测
- 买卖点体系：一买 / 二买 / 三买 & 一卖 / 二卖 / 三卖
- 基于背驰与级别判断
- 主观性强，需配合其他系统交叉验证

### 5. 一目均衡表
- 转折线 Tenkan：9 周期 H/L 中点
- 基准线 Kijun：26 周期 H/L 中点
- 价格相对云图位置 + 迟行线确认
- **需 78 根 K 线热身**（52+26）——提早使用信号容易虚假

### 6. 聪明钱（ICT / SMC）
- BOS（Break of Structure）：趋势延续
- ChoCH（Change of Character）：趋势反转
- FVG（Fair Value Gap）：价格回补目标
- Order Blocks：机构订单集中区

### 7. 基础指标三维投票
- 趋势维：EMA + ADX（ADX>25 判断趋势强度）
- 均值回归维：布林带 + RSI（30/70 超卖超买）
- 量价维：OBV + 量比（OBV 上升确认参与度）

## 信号优先级建议

不同形态的信号常相互矛盾，需明确优先级：
1. 趋势方向（EMA / 缠论 / ICT）优先
2. 关键位置（谐波 PRZ / 一目云图）次之
3. 短期信号（K 线 / RSI）最后

## 避坑

- 单一指标信号 ≠ 必然成立——多系统交叉验证
- 极限值（RSI 极端 / ADX 极端）往往预示反转而非趋势加速
- 谐波形态需要完整 XABCD 结构——不能硬套
- 缠论对中国投资者直观但主观性强
- 一目均衡表热身期长，提早使用容易虚假
- 指标钝化是常见现象——长时间超买不等于必然回落
- 周期错配常见——日线信号与周线信号矛盾时优先长周期

## 可执行工具（scripts/price-action/）

⚠️ **数据 skill 的能力边界**：
- **westock 已覆盖**：MACD / KDJ / RSI / 布林带 / 均线 等**标准技术指标的实时计算值**（用 `westock-data technical <code> --group macd|kdj|rsi|boll|ma`）—— 简单指标查询**直接用 westock**，不要绕道 script
- **westock / neodata 都不覆盖、必须用 script**：
  - **K 线形态识别**（锤子 / 吞噬 / 晨星 / 三白兵 等 15 种蜡烛图形态）→ `candlestick_patterns.py`
  - **VCP / 波缩突破形态**（多轮回调收窄 + 量能同步收敛的结构判断）→ 见 `breakout-patterns.md` 配套 script
  - **斐波那契谐波形态**（Gartley / Bat / Butterfly / Crab 的 XABCD 结构 + PRZ）→ `harmonic_patterns.py`
  - **艾略特波浪计数与三铁律校验** → `elliott_wave.py`
  - **缠论分型 / 笔 / 中枢 / 123 类买卖点** → `chan_theory.py`
  - **一目均衡表**（Tenkan / Kijun / 云图 / 迟行线综合判定）→ `ichimoku.py`
  - **SMC / ICT 概念**（BOS / ChoCH / FVG / Order Block）→ `smart_money.py`

  这些都是**算法判断 + 结构识别**型任务，westock 只能给你 OHLCV 原始数据，**形态判断完全靠你自己写代码或调 script**——既然有 production 实现就**直接调，不要从零写算法**。

**fallback**：westock-data technical 不可用 / 网络故障时，`basic_indicators.py` 能本地算 MACD / KDJ / RSI / 布林带 / EMA / ADX / OBV 等所有标准指标兜底（输入 OHLCV DataFrame 即可）。

每个 script 都有 `SignalEngine` class，调用模式：`engine = SignalEngine(); signals = engine.generate({"代码": ohlcv_df})`，返回 `{代码: pd.Series}`，序列值 1=做多 / -1=做空 / 0=观望。

| 文件 | 覆盖形态 | 行数 | 额外依赖 |
|---|---|---|---|
| `candlestick_patterns.py` | 15 种蜡烛图形态（锤子 / 倒锤 / 射星 / 十字星 / 纺锤 / 吞噬 / 孕线 / 刺穿 / 乌云盖顶 / 晨星 / 暮星 / 三白兵 / 三乌鸦 等） | 590 | — |
| `elliott_wave.py` | 5 浪推动 + 3 浪修正 + 三铁律 + 斐波那契关系校验 | 458 | — |
| `basic_indicators.py` | EMA + ADX + 布林带 + RSI + OBV + 量比 三维投票 | 302 | — |
| `ichimoku.py` | Tenkan / Kijun / 云图 / 迟行线（需 78 根 K 线热身） | 195 | — |
| `harmonic_patterns.py` | 4 种斐波那契谐波（Gartley / Bat / Butterfly / Crab）+ PRZ 识别 | 510 | `pip install pyharmonics` |
| `chan_theory.py` | 缠论分型→笔→中枢自动检测，123 类买卖点 | 225 | `pip install czsc` |
| `smart_money.py` | ICT/SMC：BOS / ChoCH / FVG / Order Block | 190 | `pip install smartmoneyconcepts` |

**Setup**（基础环境，所有 script 都需要）：
```bash
pip install pandas numpy requests
```

**特殊依赖处理（chan_theory / smart_money / harmonic_patterns）**：

这三个 script 各自依赖一个第三方库（czsc / smartmoneyconcepts / pyharmonics），用户环境可能没装。**按以下流程处理，不要总是询问用户**：

1. **判断用户需求是否真的需要这个 script**：
   - 用户明确问"缠论买卖点 / SMC 概念 / Gartley 谐波" 等专门形态 → 需要
   - 用户问的是泛技术分析（"形态怎么样 / MACD 怎么样"）→ 不需要，用 `candlestick_patterns.py` / `basic_indicators.py` 就够

2. **真需要时先检测、缺失再装，并在对话中一句话告知**：
   ```bash
   # 先检测，已装就跳过 install，省时间
   python3 -c "import czsc" 2>/dev/null && echo "OK: czsc 已装" || {
     echo "正在安装 czsc 库以提供缠论分析（约 30 秒）..."
     pip install czsc 2>&1 | tail -5
   }
   ```
   **不要问用户"要不要装"**——用户已经表达需求了。**也不要每次都 install**——已装就直接进入下一步用 import 调用。

3. **安装失败时降级**：
   - 装失败（沙箱限制 / 网络问题 / 编译失败）→ 一句话告知"专门库装不上，用通用 K 线形态识别替代"，然后用 `candlestick_patterns.py` + `basic_indicators.py` 给出**结构性判断**（虽然不如专门库精确）
   - **绝不要让用户在没分析的情况下面对一个 ModuleNotFoundError**

4. **同会话内装一次即可**，后续直接 import 不再重复装。

**输入约定**：DataFrame 列名 `open / high / low / close / volume`，按时间升序。

**优先调用 CLI（更省心，等同 westock 调用成本）**：
```bash
python3 scripts/run_signal.py --engine candlestick --source westock --code sh600519 --limit 120 --pretty
python3 scripts/run_signal.py --engine ichimoku --source westock --code sh600519 --limit 120 --pretty
python3 scripts/run_signal.py --engine vcp --source westock --code sz300308 --limit 120 --pretty
```

**需要自定义数据时再走 Python API**：
```python
import sys; sys.path.insert(0, 'scripts/price-action')
from candlestick_patterns import SignalEngine
engine = SignalEngine()
signals = engine.generate({"600519": ohlcv_df})  # signals["600519"] 是 1/-1/0 序列
```

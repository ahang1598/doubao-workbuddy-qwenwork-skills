# Python 因子编写

来源：[PandaAI 因子编写与函数参考手册](https://www.pandaaiquant.com/community/article/72)，读取日期 2026-08-05。
文章也覆盖公式算子；完整算子索引见 [operators.md](operators.md)。平台行为变化时以官方文档和实际短窗口验证为准。

## 何时使用

公式适合直接的算子表达和快速迭代。用户需要路径依赖状态、复杂条件分支、较多中间步骤或明确要求 Python 时，使用 Python。两种方式都不是强制的研究导向；按用户的问题和可维护性选择。

## 返回契约

Python 因子必须定义一个继承 `Factor` 的类、实现同步方法 `calculate(self, factors)`，并返回 `Series`：名称/列为 `value`，索引为 `[symbol, date]` 多级索引。

`factors` 提供量价序列，例如 `factors['close']`、`factors['open']`、`factors['high']`、`factors['low']` 和 `factors['volume']`。

```python
class CustomFactor(Factor):
    def calculate(self, factors):
        close = factors['close']
        return close / DELAY(close, 20) - 1
```

平台公式算子可在 Python 方法中使用，例如 `DELAY`、`STDDEV`、`SUM`、`RANK`、`SCALE` 和 `IF`。使用前先查 [operators.md](operators.md)，不要假定 pandas 方法与平台运行时完全一致。

## 多步骤示例

```python
class ComplexFactor(Factor):
    def calculate(self, factors):
        close = factors['close']
        volume = factors['volume']
        high = factors['high']
        low = factors['low']

        returns = close / DELAY(close, 20) - 1
        volatility = STDDEV(close / DELAY(close, 1) - 1, 20)
        price_range = (high - low) / close
        volume_ratio = volume / DELAY(volume, 1)
        volume_ma = SUM(volume, 20) / 20
        momentum = RANK(returns)
        vol_signal = IF(volatility > DELAY(volatility, 1), 1, -1)
        return momentum * vol_signal * SCALE(volume_ratio / volume_ma)
```

这是语法和结构示例，不是推荐因子。需要判断效果时，仍应先让用户批准候选和预算，再在短窗口运行。

## CLI 与批处理

单个 Python 文件通过 CLI 的 `--file` 模式创建：

```bash
pandaai-cli --json factor_create --file complex_factor.py --name "complex-factor" \
  --start-date 20250101 --end-date 20250331 --adjustment-cycle 5 --factor-direction 1
```

批处理候选文件每行是 `名称 ~ Python文件路径 ~ 方向`，并显式选择 Python 模式：

```text
复杂状态因子 ~ factors/complex_factor.py ~ 1
```

```bash
python3 scripts/batch.py python-candidates.txt --mode python \
  --start 20250101 --end 20250331 --cycle 5 --max-runs 1
```

`batch.py` 会在调用 CLI 前检查文件编码、Python 语法、唯一 `Factor` 子类和 `calculate` 方法；它不能证明运行时数据逻辑正确。因此必须经过真实的短窗口 `factor_run`，并对返回的 IC、分组收益、换手和错误信息做检查。

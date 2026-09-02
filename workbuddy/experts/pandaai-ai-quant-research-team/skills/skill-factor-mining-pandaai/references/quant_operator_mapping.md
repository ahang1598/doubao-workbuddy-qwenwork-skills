# PandaAI native operator contract

Source: `PandaAI 因子编写与函数参考手册.html`, supplied locally and reviewed
2026-08-04. Treat the platform manual and actual platform validation as the
authority.

## Data contract

- Native fields: `CLOSE`, `OPEN`, `HIGH`, `LOW`, `VOLUME`, `AMOUNT`,
  `TURNOVER`, and `MARKET_CAP`.
- Python factors inherit `Factor`, implement `calculate(self, factors)`, and
  return a Series indexed by `symbol,date`.
- Native operators are directly callable in Python mode. Do not reimplement
  them with pandas DataFrame axis assumptions.
- Formula mode supports nested native functions and is preferred for generated
  blind-mining expressions.

## Three-stage operator space

1. Base discovery: arithmetic, `ABS`, `LOG`, `LOGABS`, `SIGN`, `POWER`,
   `SIGNEDPOWER`, `MAX`, `MIN`, `MEAN`, `IF`, and compact field combinations.
2. Time-series enhancement: `REF/DELAY`, `DELTA/DIFF`, `MA/TS_MEAN`, `SUM`,
   `PRODUCT`, `RETURNS`, `STD/STDDEV`, `VAR`, `TS_MAX`, `TS_MIN`, `TS_MIDDLE`,
   `TS_MAD`, `TS_RANK`, extrema positions, condition counts, regression trend,
   `DECAYLINEAR`, `TS_ZSCORE`, distribution moments, `EMA/WMA`, rolling
   correlation/covariance/regression, and conditional rolling sum.
3. Cross-sectional enhancement: `RANK`, `SCALE`, and `ZSCORE`.

Technical indicators are supported by the platform but should enter separate
specialist families rather than unrestricted genetic nesting. This limits
complexity and preserves attribution.

Never use `FUTURE_RETURNS` as an input feature. It is forward-looking and may
only be used as an evaluation label outside the candidate expression.

Use the machine-readable catalog and validator:

```bash
python scripts/pandaai_quant_operators.py --list --stage 2
python scripts/pandaai_quant_operators.py --validate "RANK(RETURNS(CLOSE,20))"
```

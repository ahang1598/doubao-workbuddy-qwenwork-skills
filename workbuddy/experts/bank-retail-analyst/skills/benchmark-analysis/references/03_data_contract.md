# Skill 3 · 附录 03：standard / text 数据解析契约

> **触发阅读条件**：读取 `standard/<bank>.json` 或 `text/<bank>.json`、任何一家银行数据被判空、排名参排家数异常时。

## 1. Schema 契约

Skill 1（`$RA/data/standard/<bank>.json`）与 Skill 2（`$RA/data/text/<bank>.json`）**已强制统一**到 `values[]` 数组结构：

```jsonc
// standard（Skill 1 → _schema_version: "standard-v1.0"）
{
  "standard_name": "零售分部营业净收入",
  "values": [
    {"period_label": "2025年度", "value": 191017, "unit": "百万元",
     "raw_label_in_table": "零售银行业务 营业净收入", "confidence": "high"},
    {"period_label": "2024年度", "value": 196835, "unit": "百万元",
     "raw_label_in_table": "零售银行业务 营业净收入", "confidence": "high"}
  ]
}

// text（Skill 2 → _schema_version: "text-v1.0"）
{
  "standard_name": "零售分部营业净收入(文字)",
  "category_bucket": "分部效益",
  "values": [
    {"period_label": "2025年度", "period_end_value": 1910.17, "change_pct": 5.3,
     "unit": "亿元", "raw_quote": "…零售营收1,910.17亿元…",
     "source_section": "管理层讨论与分析 > 零售银行业务", "confidence": "high"}
  ]
}
```

**不存在扁平形态**：读取前必须先校验 `data["_schema_version"]`，不匹配则报错拒绝加载，**禁止**写 fallback 兼容扁平 `metric["value"]`。如遇旧文件，运行对应 Skill 目录下的 `scripts/normalize_*_json.py --apply` 一次性迁移。

## 2. 取值参考实现

```python
STANDARD_SCHEMA = "standard-v1.0"
TEXT_SCHEMA     = "text-v1.0"

def load_standard(bank: str) -> dict:
    data = json.loads((RA_HOME / "data" / "standard" / f"{bank}.json").read_text())
    ver = data.get("_schema_version")
    if ver != STANDARD_SCHEMA:
        raise RuntimeError(
            f"{bank} standard schema={ver!r}，预期 {STANDARD_SCHEMA}。"
            f"请先运行 `scripts/normalize_standard_json.py --apply`"
        )
    return data


def extract_metric_value(metric: dict, target_period: str) -> float | None:
    """遍历 values[] 按 period_label 归一匹配取值。"""
    for v in metric.get("values") or []:
        if _period_label_matches(v.get("period_label"), target_period):
            raw = v.get("value")  # text 目录用 v.get("period_end_value")
            if raw is not None:
                return float(raw)
    return None


def _period_label_matches(label: str | None, target: str) -> bool:
    """period_label 归一匹配。target 形如 '2025年度' / '2025H1' / '2025Q1' 等。"""
    if not label or not target:
        return False
    label = label.strip()
    if label == target:
        return True
    # 年度：'2025年度' ⇔ '2025' / '2025年' / '2025年12月31日' / '报告期末' / '期末'
    if target.endswith("年度"):
        year = target[:-2]
        return (
            label == year
            or label == f"{year}年"
            or label.startswith(f"{year}年12月31日")
            or label.startswith(f"{year}年末")
            or label in ("报告期末", "期末")
        )
    return False
```

> text 数据的数值字段叫 `period_end_value` 而非 `value`——取值时需按 kind 选用对应字段（或在加载时做一次字段别名兜底，见下）。

## 3. 禁止事项

- ❌ `metric.get("value")` 单字段读取（standard/text schema 下 metric 层根本没有 `value` 字段，会永远返回 None）
- ❌ 忽略 `period_label` 直接用 `values[0]`（values 内顺序不保证为当期在前）
- ❌ 字符串 `==` 比较 `period_label`（`"报告期末"` / `"2025年12月31日"` / `"2025年"` 必须通过 `_period_label_matches` 归一）
- ❌ 对不通过 schema 校验的旧文件做兼容读取；必须先 normalize 后再读

## 4. 自检

加载数据后若某家银行在当期核心指标（如"零售分部营业净收入"）下取不到值，**必须先打印前 3 条 metric 的原始 JSON 到日志**，确认 `values[]` 内的 `period_label` 后再定位问题，**不得**默默写入 `"-"` 或 `None`。

```python
if value is None:
    log.warning(f"{bank} {period} {metric_name} 取值为 None，打印前 3 条原始 metric：")
    for m in metrics_list[:3]:
        log.warning(json.dumps(m, ensure_ascii=False))
```

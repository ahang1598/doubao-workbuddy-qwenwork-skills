---
name: naps
description: "查询日间小睡数据。当用户询问午睡、小睡、白天有没有睡觉相关问题时使用。"
metadata:
  {
    "pha": {
      "emoji": "😴",
      "category": "health-data-cli",
      "layer": "domain",
      "sections": [
        {"id": "data-fetch"},
        {"id": "interpretation"}
      ],
      "tags": ["cli", "naps", "sleep"],
      "requires": {
        "tools": ["get_naps"],
        "skills": ["healthy-shared"]
      }
    }
  }
---

# Naps 日间小睡

---

## 一、数据获取

`get_naps` 按实际发生日期存储，**无日期偏移**，直接用当天日期查询。

```
get_naps --date today          # 今天有没有午睡
get_naps --last-days 7         # 最近一周午睡规律
```

---

## 二、分析框架

**时长**：≤ 40 分钟为宜。超过 40 分钟易进入深睡，醒后反而更困，且削弱夜间睡眠驱动力。

**时间点**：下午 3 点后的小睡会减少夜间睡眠驱动力，导致入睡困难或夜间睡眠质量下降。

**与夜眠关联**：若用户同时反映夜间睡眠质量差，建议结合 `sleep-coach` 综合分析。

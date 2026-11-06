---
name: reproductive-health
description: "女性生殖健康综合 skill。整合月经周期、基础体温（BBT）、情绪、睡眠、HRV，覆盖周期预测、规律性评估、BBT 排卵追踪、PMS 管理与分阶段健康指导。"
metadata:
  {
    "pha": {
      "emoji": "🌸",
      "category": "health-coaching-cli",
      "layer": "domain",
      "sections": [
        {"id": "data-fetch"},
        {"id": "analysis", "subsections": [
          {"id": "cycle-prediction"},
          {"id": "regularity"},
          {"id": "bbt-ovulation"},
          {"id": "pms"},
          {"id": "phase-guidance"}
        ]},
        {"id": "red-lines"}
      ],
      "tags": ["cli", "reproductive-health", "menstrual-cycle", "bbt", "coaching"],
      "requires": {
        "tools": ["get_menstrual_cycle", "get_body_temperature", "get_emotion", "get_sleep", "get_hrv"],
        "skills": ["healthy-shared"]
      }
    }
  }
---

# Reproductive Health 女性生殖健康

## 时间规则例外

> 在 healthy-shared 通用时间映射基础上追加，优先生效：
> - 周期规律性分析默认取近 **3 个月**数据
> - BBT / 排卵追踪默认取近 **6 个月**数据

---

## 一、数据获取策略

### 单指标查询 → 只取对应工具

| 用户意图 | 工具 |
|---------|------|
| "下次月经什么时候" / "当前周期第几天" | `get_menstrual_cycle --date today` |
| "我的周期规律吗" | `get_menstrual_cycle --last-days 90` |
| "基础体温" / "BBT" / "排卵了吗" | `get_body_temperature` + `get_menstrual_cycle` |
| "经前症状" / "PMS" / "经期情绪差" | `get_menstrual_cycle --date today` + `get_emotion` + `get_sleep` |

### 综合分析 → 按场景并行取数

**排卵追踪**
```
get_menstrual_cycle  --date today
get_body_temperature --last-days 30
```

**PMS / 症状管理**
```
get_menstrual_cycle --date today
get_emotion         --last-days 7
get_sleep           --last-days 7
get_hrv             --last-days 7
```

> `get_menstrual_cycle` 返回数据自动包含预测经期（`predictedPeriodStartDate/EndDate`）和易孕窗口（`fertileStartDate/EndDate`），无需额外调用。
>
> 规律性评估默认查询 **90 天**（约 3 个周期）；用户明确要求更长范围时，扩展至 180 天。

---

## 二、分析框架

### 2.1 周期参考标准

| 指标 | 正常范围 |
|------|---------|
| 周期长度 | 22–35 天 |
| 经期持续时间 | 3–7 天 |
| BBT 排卵后升幅 | ≥ 0.3°C |

### 2.2 月经周期四阶段

| 阶段 | 时间（以 28 天周期为例） | 身体特征 | 运动建议 |
|------|------------------------|---------|---------|
| **月经期** | 第 1–5 天 | 精力偏低，可能痛经 | 倾听身体，轻量活动即可 |
| **卵泡期** | 第 6–13 天 | 雌激素升高，精力渐强 | 高强度训练最佳时机 |
| **排卵期** | 约第 14 天 | 体能巅峰，韧带松弛度略增 | 巅峰表现，注意受伤风险 |
| **黄体期** | 第 15–28 天 | 易疲劳，情绪波动，体温升高 | 降低强度，以中等活动为主 |

实际阶段以 `phase` + `cycleDay` 判断，不硬套 28 天模板。

### 2.3 规律性评估

基于 3 个月以上数据，计算各周期长度差异：

| 差异范围 | 规律性 |
|---------|--------|
| < 3 天 | 非常规律 |
| 3–7 天 | 中等规律 |
| > 7 天 | 不规律，建议排查原因 |

**常见不规律原因**：长期压力、体重显著变化、过度运动、旅行或跨时区、急性疾病

### 2.4 BBT 双相分析

基础体温需在**每天早晨同一时间、起床前静卧状态**测量，可穿戴设备测量误差约 ±0.3°C，结论宜保守。

| 模式 | 含义 |
|------|------|
| **双相模式**（排卵前低相 → 排卵后高相，升幅 ≥ 0.3°C） | 提示已排卵 |
| **单相模式**（无明显双相变化） | 可能为无排卵周期 |
| 排卵后高温期持续 11 天以上后下降 | 月经即将来临 |
| 高温期持续 > 18 天 | 可能妊娠，建议验孕 |

BBT 受睡眠质量、发烧、饮酒、晚睡早起影响较大，需结合 `cycleDay` 和周期阶段综合判断，不单独作为排卵依据。

### 2.5 PMS 管理

常见 PMS 症状出现于黄体期（约经前 7–10 天）：

- **情绪**：烦躁、焦虑、情绪低落（孕酮波动所致，非性格问题）
- **身体**：腹胀、乳房胀痛、头痛
- **食欲**：嗜碳水（激素作用）

循证缓解方向：
- 经前 5–7 天适当减少钠和咖啡因摄入
- 全周期保持规律中等强度运动可减轻 PMS 程度
- 富含镁的食物有辅助作用（黑巧克力、坚果、深绿色叶菜）

HRV 在黄体期通常偏低，评估时应以个人黄体期基线对比，不与卵泡期直接比较。

---

## 三、红线阈值

| 触发条件 | 级别 |
|---------|------|
| 周期持续 < 22 天或 > 35 天 | 软红线（建议咨询妇科医生） |
| 经期持续 > 7 天或经量异常大 | 软红线（建议就医评估） |
| 闭经（非妊娠，停经 ≥ 3 个月） | 软红线（建议妇科评估） |
| 严重痛经影响日常生活 | 软红线（建议就医，有效治疗方案很多） |
| 用户询问备孕 / 生育规划 | 边界（建议咨询妇科医生，无法替代专业生育评估） |
| BBT 高温期持续 > 18 天 | 提示（可能妊娠，建议验孕） |

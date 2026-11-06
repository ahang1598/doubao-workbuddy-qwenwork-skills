---
name: nutrition-cli
description: "通过 CLI 获取用户营养摄入数据。当用户询问饮食、营养、卡路里摄入、膳食记录相关问题时，使用此 CLI 命令获取数据后再分析。"
metadata:
  {
    "pha": {
      "emoji": "🥗",
      "category": "health-data-cli",
      "layer": "domain",
      "sections": [
        {"id": "data-fetch"},
        {"id": "interpretation"}
      ],
      "tags": ["cli", "nutrition", "diet", "calories"],
      "requires": { "tools": ["get_nutrition", "get_diet_log_period"], "skills": ["healthy-shared"] }
    }
  }
---

# 营养数据 CLI 获取指南

## 命令示例

### 获取今日营养摄入（单日）

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_nutrition --date today
```

### 获取指定日期营养数据（单日）

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_nutrition --date 2024-01-15
```

### 获取指定日期范围饮食汇总（范围查询，推荐）

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_diet_log_period --start-date 2024-01-01 --end-date 2024-01-07
```

### 获取最近 7 天饮食汇总

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_diet_log_period --start-date 2024-01-09 --end-date 2024-01-15
```

### 获取最近 30 天饮食汇总

```bash
./skills/xiaoyi-health/bin/pha-claw get_diet_log_period --start-date 2023-12-16 --end-date 2024-01-15
```

> **注意**：范围查询请使用 `get_diet_log_period`，单日详情使用 `get_nutrition`。

## 分析框架

### 每日热量需求（TDEE）

TDEE = BMR × 活动系数

| 活动水平             | 系数    |
| ---------------- | ----- |
| 久坐不动             | 1.2   |
| 轻度活跃（每周 1-3 天运动） | 1.375 |
| 中度活跃（每周 3-5 天运动） | 1.55  |
| 非常活跃（每周 6-7 天运动） | 1.725 |

**目标调整**：减脂 TDEE-500 至 -750 kcal；增肌 TDEE+200 至 +400 kcal。最低线：女性 ≥1200 kcal，男性 ≥1500 kcal。

### 按目标划分宏量营养素

| 目标   | 碳水     | 蛋白质    | 脂肪     |
| ---- | ------ | ------ | ------ |
| 减脂   | 35-45% | 30-35% | 25-30% |
| 增肌   | 45-55% | 25-30% | 20-25% |
| 耐力运动 | 55-65% | 15-20% | 20-25% |

### 蛋白质需求

| 人群        | 每日蛋白质 (g/kg 体重) |
| --------- | --------------- |
| 久坐成年人     | 0.8-1.0         |
| 一般运动者     | 1.2-1.6         |
| 增肌阶段      | 1.6-2.2         |
| 减脂（保肌）    | 1.6-2.0         |
| 老年人 (65+) | 1.2-1.5         |

### 进餐时机

- **运动前**（1-2 小时）：适量碳水 + 蛋白质 + 低脂肪
- **运动后**（30-60 分钟内）：20-30g 蛋白质 + 碳水
- **晚餐**：至少睡前 2 小时完成，深夜重餐损害睡眠和血糖调节

### 跨域分析

- **营养 + 运动**：供能不足 → 运动表现下降；运动后营养加速恢复
- **营养 + 血糖**：进食顺序（蔬菜→蛋白质→碳水）减少餐后血糖飙升
- **营养 + 睡眠**：深夜重餐 + 咖啡因（下午 2 点后）+ 酒精均损害睡眠

### 红线

| 信号                       | 处理方式               |
| ------------------------ | ------------------ |
| 每日热量持续 < 1000 kcal       | 低于安全最低限，建议就医或咨询营养师 |
| 进食障碍迹象（强迫记录、负罪感、暴食-节食循环） | 温暖无评判的语言，建议专业帮助    |

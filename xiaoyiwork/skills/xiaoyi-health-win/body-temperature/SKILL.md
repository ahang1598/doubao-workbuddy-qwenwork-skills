---
name: body-temperature-cli
description: "通过 CLI 获取用户体温数据。当用户询问体温、发烧、体温异常相关问题时，使用此 CLI 命令获取数据后再分析。"
metadata:
  {
    "pha": {
      "emoji": "🌡️",
      "category": "health-data-cli",
      "layer": "domain",
      "sections": [
        {"id": "data-fetch"},
        {"id": "interpretation"},
        {"id": "red-lines"}
      ],
      "tags": ["cli", "body-temperature", "fever"],
      "requires": { "tools": ["get_body_temperature"], "skills": ["healthy-shared"] }
    }
  }
---

# 体温数据 CLI 获取指南

## 时间查询规范

**趋势基线默认范围**：建立个人体温基线时，默认取最近 **30 天**数据。用户未指定时间范围时，优先拉取 30 天而非 7 天，以便计算可靠的个人正常范围并检测偏移。

## 命令示例

### 获取今日体温

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_body_temperature --date today
```

### 获取指定日期体温

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_body_temperature --date 2024-01-15
```

### 获取最近 7 天体温趋势

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_body_temperature --last-days 7
```

### 获取最近 30 天体温趋势

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_body_temperature --last-days 30
```

### 获取指定日期范围体温数据

```bash
./skills/xiaoyi-health-win/bin/pha-claw get_body_temperature --start-date 2024-01-01 --end-date 2024-01-31
```

## 参考范围

| 范围         | 状态           |
| ---------- | ------------ |
| 36.0–37.2℃ | 正常体温         |
| 37.3–38.0℃ | 低烧，建议观察      |
| 38.1–39.0℃ | 中度发烧，建议休息并补水 |
| >39.0℃     | 高烧，建议就医      |

---

## 分析框架

### 个人基线优先

始终先建立个人基线（分析过去 30 天数据），再与人群标准对比。体温每天自然波动 0.3-0.5°C，单次偏高不代表生病。

### 影响体温的因素

- **运动**：高强度运动后体温暂时升高（正常）
- **时间段**：清晨自然偏低，午后偏高
- **脱水 / 压力 / 睡眠不足**：可能引起轻微升高
- **可穿戴设备**：腕部皮肤温度与腋下/口腔测量值不同，误差约 ±0.3°C

### 跨域分析

- **体温 + 睡眠**：睡眠期间体温升高 → 可能在对抗感染或处于压力状态
- **体温 + 月经周期**：黄体期偏高是正常现象，不需要担心
- **体温 + 压力**：慢性压力可导致持续性低热

### 红线

| 信号                   | 处理方式             |
| -------------------- | ---------------- |
| 体温 > 38°C 持续超过 2 天   | 建议就医排除感染         |
| 任何时候 > 39°C          | 建议今天就看医生         |
| 持续 < 36.0°C          | 可能提示代谢问题，下次体检时提及 |
| 发热伴严重头痛、颈部僵硬、皮疹或呼吸困难 | 立即就医             |

---
name: lock-weather
description: "智能门锁天气提醒设置技能。当用户要求设置出门天气提醒（雨、雪、霾提示）时，必须使用本技能。本技能仅支持控制操作。"
---

# 门锁天气提醒设置技能

> 本技能用于**控制**门锁的天气提醒设置，**不支持查询操作**。

---

## 1. 服务ID

- **sid**：`weatherReminder`

---

## 2. 重要说明

- 当前仅对雨、雪、霾三种天气进行提示
- 需要设置合适的门锁留言、天气提醒音量，避免静音无法体验此场景
- 此场景需要门锁连接网络

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 天气提醒、出门天气提醒
- 雨天提醒、下雪提醒

---

## 4. 控制命令

### 4.1 打开天气提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "weatherReminder" \
  --data '{
    "sw": 1,
    "st": "06:00",
    "et": "10:00",
    "lng": "108.94",
    "lat": "34.21",
    "city": "610113",
    "ts": "20260408T151137Z621"
  }' \
  --verbose
```

### 4.2 关闭天气提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "weatherReminder" \
  --data '{
    "sw": 0,
    "st": "06:00",
    "et": "10:00",
    "lng": "108.94",
    "lat": "34.21",
    "city": "610113",
    "ts": "20260408T151137Z621"
  }' \
  --verbose
```

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- 需要确保门锁连接网络才能正常使用天气提醒功能
- 需要设置合适的门锁音量避免静音无法体验

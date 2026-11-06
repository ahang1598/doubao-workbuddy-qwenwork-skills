---
name: lock-volume
description: "智能门锁声音设置技能。当用户要求设置门铃音量、提示音音量、告警音音量、留言音量、开关门提示音、门未关告警等时，必须使用本技能。本技能仅支持控制操作。"
---

# 门锁声音设置技能

> 本技能用于**控制**门锁的声音相关设置，**不支持查询操作**。

---

## 1. 服务ID

- **sid**：`volumeSetting`（音量相关）
- **sid**：`alarmEventSetting`（告警相关）

---

## 2. 重要说明

**调整音量前确认门锁类型**：
- **对于二代门锁**：声音有固定值：0, 10, 20, 30 ... 100，每次只调整一档（增加或减少10）
- **对于一代门锁**：声音只有静音（0）、低（30）、中（60）、高（100），每次调整一级（调整至静音/低/中/高）

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 门锁声音、门铃音量
- 提示音、告警音
- 留言音量、声音大小
- 开关门提示音、门未关告警

---

## 4. 控制命令

### 3.1 开关门提示音设置

#### 打开开关门提示音

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"doorPromptSwitch": 1}' \
  --verbose
```

#### 关闭开关门提示音

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"doorPromptSwitch": 0}' \
  --verbose
```

### 3.2 门未关告警设置

#### 打开门未关告警

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "alarmEventSetting" \
  --data '{"doorOpenSwitch": 1}' \
  --verbose
```

#### 关闭门未关告警

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "alarmEventSetting" \
  --data '{"doorOpenSwitch": 0}' \
  --verbose
```

### 3.3 音量设置

#### 设置门铃音量（低=30）

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"ringVolume": 30}' \
  --verbose
```

#### 设置提示音音量（中=60）

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"voiceVolume": 60}' \
  --verbose
```

#### 设置告警音音量（静音=0）

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"warningVolume": 0}' \
  --verbose
```

#### 设置留言/天气提醒音量（最大=100）

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "volumeSetting" \
  --data '{"homeGreetVol": 100}' \
  --verbose
```

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- 当用户说"音量调大"或"音量调小"时，需要根据当前音量值计算新的音量值

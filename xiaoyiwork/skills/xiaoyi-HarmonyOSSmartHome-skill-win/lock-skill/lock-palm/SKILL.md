---
name: lock-palm
description: "智能门锁掌静脉识别设置技能。当用户要求设置掌静脉识别开关、识别模式、语音提醒、关门静默时长等时，必须使用本技能。本技能仅支持控制操作，不支持添加/删除掌静脉等成员管理操作。"
---

# 门锁掌静脉识别设置技能

> 本技能用于**控制**门锁的掌静脉识别相关设置，**不支持查询和成员管理操作**。

---

## 1. 服务ID

- **sid**：`securitySetting`

---

## 2. 重要说明

关门静默时长功能：关门后，掌静脉识别功能在设置时间内停用，可以避免误开锁。

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 掌静脉、掌静脉识别、掌心识别

---

## 4. 控制命令

### 4.1 掌静脉识别开关设置

#### 打开掌静脉识别

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmIdentifySwitch": 1}' \
  --verbose
```

#### 关闭掌静脉识别

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmIdentifySwitch": 0}' \
  --verbose
```

### 4.2 掌静脉识别模式设置

#### 设置为手动模式

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmDetectMode": 0}' \
  --verbose
```

#### 设置为自动模式

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmDetectMode": 1}' \
  --verbose
```

### 4.3 掌静脉语音提醒设置

#### 打开掌静脉语音提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmVoiceSwitch": 1}' \
  --verbose
```

#### 关闭掌静脉语音提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmVoiceSwitch": 0}' \
  --verbose
```

### 4.4 关门静默时长设置

#### 设置关门静默时长为10秒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmSleepTime": 10}' \
  --verbose
```

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- **不支持添加/删除掌静脉等成员管理操作**

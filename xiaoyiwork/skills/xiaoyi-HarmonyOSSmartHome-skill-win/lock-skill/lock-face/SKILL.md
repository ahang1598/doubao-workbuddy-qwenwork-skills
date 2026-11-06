---
name: lock-face
description: "智能门锁人脸识别设置技能。当用户要求设置人脸识别开关、识别模式、语音提醒、回头防误开时长等时，必须使用本技能。本技能仅支持控制操作，不支持添加/删除人脸等成员管理操作。"
---

# 门锁人脸识别设置技能

> 本技能用于**控制**门锁的人脸识别相关设置，**不支持查询和成员管理操作**。

---

## 1. 服务ID

- **sid**：`securitySetting`

---

## 2. 重要说明

- 当人脸识别开锁开关（`faceIdentifySwitch`）关闭时，其他人脸识别设置不可修改
- 回头防误开功能：关门后，人脸识别功能在设置时间内停用，可以避免出门后等电梯时回头误开锁；但在对应时间内无法自动唤醒人脸开锁，需要触摸键盘手动唤醒

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 人脸、人脸识别、面部识别、刷脸
- 回头防误开

---

## 4. 控制命令

### 4.1 人脸识别开锁设置

#### 打开人脸识别开锁

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceIdentifySwitch": 1}' \
  --verbose
```

#### 关闭人脸识别开锁

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceIdentifySwitch": 0}' \
  --verbose
```

### 4.2 人脸识别模式设置

#### 设置为手动模式

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceDetectMode": 0}' \
  --verbose
```

#### 设置为自动模式

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceDetectMode": 1}' \
  --verbose
```

### 4.3 人脸语音提醒设置

#### 打开人脸语音提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceVoiceSwitch": 1}' \
  --verbose
```

#### 关闭人脸语音提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceVoiceSwitch": 0}' \
  --verbose
```

### 4.4 回头防误开时长设置

#### 设置回头防误开时长为30秒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceSleepTime": 30}' \
  --verbose
```

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- 当人脸识别开锁开关关闭时，其他人脸识别设置不可修改
- **不支持添加/删除人脸等成员管理操作**

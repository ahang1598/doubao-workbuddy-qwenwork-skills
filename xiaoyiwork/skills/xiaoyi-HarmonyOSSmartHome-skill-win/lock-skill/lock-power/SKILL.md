---
name: lock-power
description: "智能门锁电源管理设置技能。当用户要求设置AI省电、超级省电等电源管理功能时，必须使用本技能。本技能仅支持控制操作。"
---

# 门锁电源管理设置技能

> 本技能用于**控制**门锁的电源管理设置，**不支持查询操作**。

---

## 1. 服务ID

- **sid**：`lockCommonSetting`（AI省电）
- **sid**：`catEyeSetting`（超级省电-猫眼）
- **sid**：`securitySetting`（超级省电-人脸/掌静脉模式）
- **sid**：`batteryManager`（超级省电-开关）

---

## 2. 重要说明

- 当门锁耗电较快时，可以使用AI省电功能或超级省电模式
- AI省电会自动调节人脸、掌静脉、猫眼灵敏度，兼顾续航与体验
- 超级省电模式下，将门锁调整为最低功耗模式，将人脸、掌静脉调整为手动模式，并关闭猫眼功能
- 区分一二代门锁能力集，只给出当前支持功能的建议与说明；如一代门锁Q10不支持人脸与掌静脉，不会调整为手动模式

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 电源管理、AI省电、省电模式、省电
- 超级省电

---

## 4. 控制命令

### 4.1 AI省电

默认推荐AI省电模式，该模式下，当门锁耗电较快时，自动调节人脸、掌静脉、猫眼灵敏度。

#### 打开AI省电

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "lockCommonSetting" \
  --data '{"devCfg":[{"aiEco":1,"ts":"20260427T174607Z878"}]}' \
  --verbose
```

#### 关闭AI省电

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "lockCommonSetting" \
  --data '{"devCfg":[{"aiEco":0,"ts":"20260427T174607Z878"}]}' \
  --verbose
```

### 4.2 超级省电

超级省电模式下，将门锁调整为最低功耗模式：
- 关闭猫眼功能
- 将人脸、掌静脉调整为手动模式
- 开启超级省电开关

#### 打开超级省电

需要同时执行以下4个命令：

```bash
# 关闭猫眼开关
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "catEyeSetting" \
  --data '{"peepholeEnableSwitch":0}' \
  --verbose

# 设置人脸识别为手动模式
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"faceDetectMode":0}' \
  --verbose

# 设置掌静脉识别为手动模式
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "securitySetting" \
  --data '{"palmDetectMode":0}' \
  --verbose

# 开启超级省电
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "batteryManager" \
  --data '{"lpmStatus":1}' \
  --verbose
```

#### 关闭超级省电

执行与打开相反的操作即可。

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- 当用户想要省电时，介绍两种省电方式并优先推荐AI省电
- AI省电功能开启后会自动调节人脸、掌静脉、猫眼灵敏度，可能影响使用体验
- 打开超级省电需要同时操作猫眼开关、人脸识别模式、掌静脉识别模式、超级省电开关

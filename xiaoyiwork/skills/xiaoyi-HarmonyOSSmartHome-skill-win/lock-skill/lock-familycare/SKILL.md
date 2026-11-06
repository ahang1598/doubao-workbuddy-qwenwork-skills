---
name: lock-familycare
description: "智能门锁回家提醒设置技能。当用户要求设置回家提醒功能（检测家庭成员开门回家时推送通知）时，必须使用本技能。本技能仅支持控制操作。"
---

# 门锁回家提醒设置技能

> 本技能用于**控制**门锁的回家提醒设置，**不支持查询操作**。

---

## 1. 服务ID

- **sid**：`familyCare`

---

## 2. 重要说明

- 回家提醒和回家留言是不同的功能，执行时注意根据用户要求区分
- 可以为不同的家庭成员设置独立的开关、提醒时段、每周循环
- 需要先查询用户信息获取用户id（uid）
- 设置成员回家提醒时，如果回家提醒总开关（bSwitch）处于关闭状态，必须先打开总开关（设置 bSwitch=1），再执行成员回家提醒设置操作，**并向用户说明"已为您打开回家提醒总开关，现在为您设置[成员姓名]的回家提醒"**

---

## 3. 触发关键词

当用户提到以下关键词时，应加载本技能：
- 回家提醒、家人回家提醒、成员回家提醒

---

## 4. 控制命令

### 4.1 打开回家提醒（默认用户、默认提醒时段）

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "familyCare" \
  --data '{"bSwitch":1,"uList":[],"ts":"20260408T150936Z905"}' \
  --verbose
```

### 4.2 打开单用户的回家提醒

uid根据查询用户信息获取。

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "familyCare" \
  --data '{"bSwitch":0,"uList":[{"uSwitch":1,"uid":1,"rd":"1,2,3,4,5,6,7","tList":[{"st":"12:00","et":"14:00"},{"st":"06:00","et":"08:00"}]}],"ts":"20260408T150936Z905"}' \
  --verbose
```

### 4.3 关闭回家提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "familyCare" \
  --data '{"bSwitch":0,"uList":[""],"ts":"20260408T150936Z905"}' \
  --verbose
```

### 4.4 关闭单用户的回家提醒

```bash
node common-skill/bin/smarthome-claw.js control_device \
  --dev-id "xxx" \
  --prod-id "xxx" \
  --operation "POST" \
  --sid "familyCare" \
  --data '{"bSwitch":1,"uList":["uSwitch":0,"uid":1],"ts":"20260408T150936Z905"}' \
  --verbose
```

---

## 5. 注意事项

- 本技能仅支持控制，不支持查询操作
- 回家提醒和回家留言是不同的功能
- 需要先查询用户信息获取用户id（uid）

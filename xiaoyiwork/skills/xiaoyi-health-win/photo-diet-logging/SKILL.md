---
name: photo-diet-logging-claw
description: "拍照记录饮食、照片打卡、看图识别食物。当用户发送食物图片/照片时使用，VL模型识别食物后展示结果等用户确认再打卡。"
metadata:
  {
    "pha": {
      "emoji": "📸",
      "category": "health-coaching-cli",
      "tags": ["cli", "diet", "food", "photo", "image", "logging"],
      "requires": {
        "tools": ["query_and_format_food", "log_food_entry", "get_nutrition"],
        "skills": ["healthy-shared"]
      }
    }
  }
---

# 拍照饮食录入技能（CLI 版）

当用户通过拍照/上传图片录入饮食时使用。与文字录入的核心区别：**打卡前必须展示识别结果并等用户确认**。

---

## 与文字录入的核心差异

| | 文字录入 | 图片录入 |
|---|---|---|
| 食物来源 | 用户说的文字 | VL 模型看图识别 |
| 需要确认食物名称？ | 弱匹配时需要 | **不需要**（VL 识别即采信） |
| 需要确认打卡？ | **不需要**（匹配完直接打卡） | **必须**（展示识别结果，等用户确认） |
| 可修改重量？ | 可以（修改语法） | **必须提供修改机会**（打卡前） |

---

## 步骤1：VL 识别

模型看到图片后，识别出所有食物及估算重量/份量。

> VL 识别是 Agent 侧能力，不是 CLI 工具。

---

## 步骤2：并行搜索

对所有识别出的食物**并行**调用：

```bash
query_and_format_food --food-name "<识别出的食物名>"
```

获取每个食物的营养数据（`kcal_per_100g`、`units` 预计算值等）。

---

## 步骤3：展示识别结果并等待确认（必须）

将识别结果展示给用户，**禁止直接打卡**：

```
识别到 3 样食物：
1. 红烧肉 1份(150g) ≈ 525kcal
2. 白米饭 1碗(200g) ≈ 232kcal
3. 炒青菜 1份(200g) ≈ 80kcal
合计 ≈ 837kcal

确认打卡？可以修改，如"米饭半碗""去掉青菜"
```

---

## 步骤4：处理用户回复

| 用户回复 | 处理 |
|---------|------|
| 确认（"打卡"/"确认"/"可以"/"好"/"ok"） | 并行调用 log_food_entry 打卡所有食物 |
| 修改重量（"米饭只吃了半碗"/"红烧肉200g"） | 重算营养值，**重新展示修改后的列表**再次等确认 |
| 删除某项（"去掉青菜"/"没吃青菜"） | 从列表移除，重新展示 |
| 新增（"还有一杯豆浆"） | 搜索新增食物，加入列表，重新展示 |

---

## 步骤5：打卡 + 输出结果

用户确认后：

1. **并行打卡**（每个食物一次调用）：

```bash
log_food_entry \
  --food-id "<foodId>" \
  --food-name "<foodName>" \
  --meal-type "<meal>" \
  --count <quantity> \
  --unit "<unit>" \
  --intake-weight <intakeWeight> \
  --kilocalorie <kilocalorie> \
  --protein <protein> \
  --fat <fat> \
  --carbohydrate <carbohydrate>
```

2. **查当日累计**：

```bash
get_nutrition --date today
```

3. **输出结果**（格式同文字录入第六步）：

**第1部分（本次记录，必选）**：
> [meal] [foodName] [quantity][unit] ≈ [kilocalorie]kcal，含蛋白质 [protein]g、脂肪 [fat]g、碳水 [carbohydrate]g

**第2部分（今日累计，必选）**：
> 今日累计 [totalCalories]kcal，蛋白质 [protein]g / 脂肪 [fat]g / 碳水 [carbs]g

**第3部分（点评，必选）**：结合餐别参考范围给出**一句**具体点评
- 餐别参考范围：早餐 300-500kcal / 上午加餐 <150kcal / 午餐 500-800kcal / 下午加餐 <200kcal / 晚餐 400-700kcal / 晚上加餐 <150kcal

---

## 静默原则

识别过程中、搜索过程中——不说话。只在展示识别结果等待确认时和最终输出时说话。

---

## 餐别推断

与文字录入相同：用户指定则用用户的，未指定则按当前时间推断。

- 05:00-10:00 → 早餐
- 10:00-11:30 → 上午加餐
- 11:30-14:00 → 午餐
- 14:00-17:00 → 下午加餐
- 17:00-20:30 → 晚餐
- 20:30-05:00 → 晚上加餐

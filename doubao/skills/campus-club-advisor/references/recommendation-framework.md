# 社团匹配框架

## 目录

- [1. 输入结构](#1-输入结构)
- [2. 同义词归一化](#2-同义词归一化)
- [3. 五维匹配](#3-五维匹配)
- [4. 硬约束](#4-硬约束)
- [5. 真实性状态](#5-真实性状态)
- [6. 推荐结构](#6-推荐结构)

## 1. 输入结构

`StudentClubProfile` 使用以下核心字段：

```json
{
  "school": "学校官方全称或 null",
  "campus": "校区或 unknown",
  "interests": ["摄影", "公益"],
  "personality_preferences": ["小组协作", "幕后创作"],
  "time": {
    "hours_per_week_available": 5,
    "available_periods": ["周三晚", "周末"],
    "busy_periods": ["考试周"]
  },
  "skills": {
    "have": ["视频剪辑"],
    "want_to_learn": ["活动策划"]
  },
  "goals": ["交友", "积累作品"],
  "hard_constraints": {
    "max_hours_per_week": 6,
    "exclude_tags": ["高强度户外"],
    "max_fee": 200,
    "cross_campus_ok": false
  }
}
```

候选社团的 `attributes` 使用同一组规范化标签。模型负责语义归一化，脚本只做确定性集合
比较。不要让脚本用模糊字符串相似度猜测“摄影”和“影像创作”是否等价。

## 2. 同义词归一化

建立 `normalization_notes`，把用户词和社团词映射到同一标签。例如：

| 原始表达 | 规范标签 |
| --- | --- |
| 拍照、摄影、相机 | 摄影 |
| 做视频、剪片、后期 | 视频剪辑 |
| 怕太多人、喜欢熟人小组 | 小组协作 |
| 想认识朋友、拓展圈子 | 交友 |

只合并上下文中明确同义的表达。存在歧义时保留原词并向用户确认，不能为了提高匹配分强行
归并。

## 3. 五维匹配

默认权重：

| 维度 | 权重 | 用户侧 | 社团侧 |
| --- | ---: | --- | --- |
| 兴趣 | 0.30 | `interests` | `attributes.interests` |
| 目标 | 0.20 | `goals` | `attributes.goals` |
| 互动环境 | 0.15 | `personality_preferences` | `attributes.environment_tags` |
| 技能 | 0.15 | `skills.have`、`want_to_learn` | `useful_skills`、`skill_opportunities` |
| 时间 | 0.20 | 可用小时/时段 | 预期小时/固定时段 |

集合维度按用户需求覆盖率映射为 1-5 分：`1 + 4 × 命中需求数 / 用户需求数`。技能维度
分别计算“已有技能可贡献”和“想学技能可获得”，取两者平均；某一侧为空时只用另一侧。

时间维度先检查 veto，再按周投入评估：不超过可用小时为 5 分；超出 25% 内为 3 分；
超出 25%-50% 为 2 分；超出 50% 为 1 分。时间信息未知时为 `null`。

未知维度不计为 0；总分只在已知维度上重新归一化，并同时输出 `coverage`。`coverage < 0.60`
时只能给暂定匹配，不能给确定排序。

## 4. 硬约束

以下情况默认 veto：

- 预期周投入超过用户明确的 `max_hours_per_week`；
- 社团固定活动时段与用户可用时段完全不相交；
- 社团标签命中用户明确的 `exclude_tags`；
- 明确费用超过 `max_fee`；
- 校区不同且用户明确不能跨校区。

Veto 只说明当前条件下不适合，不评价社团好坏。未知费用、时段或工作量不是 veto，而是
缺口。

## 5. 真实性状态

匹配分不得混入真实性状态：

| 状态 | 含义 | 推荐区处理 |
| --- | --- | --- |
| `verified_current` | 本学年或近 12 个月官方名录/招新信息 | 可推荐，并注明当前招新状态 |
| `verified_exists` | 36 个月内有官方存在证据，但本期招新未确认 | 可推荐，必须提示确认本期招新 |
| `probable` | 只有近期非官方一致线索 | 只放待核验区 |
| `stale` | 只有超过 36 个月的官方材料 | 只放待核验区 |
| `unverified` | 无可定位来源或工具不可用 | 不作为真实校内社团推荐 |
| `conflict` | 名称、状态、校区或招新信息冲突 | 暂停推荐，列出冲突 |

## 6. 推荐结构

推荐列表包含 2-4 个稳妥候选和最多 1 个探索候选。每项必须同时展示：

- `match_score` 与 `coverage`；
- 最强匹配点和最主要顾虑；
- veto（若有）；
- `verification.status`、访问日期和官方来源；
- 本期招新是否已确认；
- 用户下一步。

不要因低匹配否定用户的兴趣，也不要因高匹配替用户做最终决定。推荐应帮助用户缩小体验
范围，而不是制造“唯一正确社团”。

用户选定候选并进入报名、面试、试演、作品集或笔试准备时，继续使用
[社团招新准备](recruitment-preparation.md)，不要把通用预测写成该社团已核验的选拔要求。

## 7. 脚本校验边界

- `verified_current`：以 `verification.checked_at` 为基准，必须有不超过 12 个月的官方来源。
- `verified_exists`：以 `verification.checked_at` 为基准，必须有不超过 36 个月的官方来源；超过 36 个月的唯一官方证据只能是 `stale`。
- 每条来源必须同时提供 `title`、`url`、`publisher`、`published_or_updated_at`、`source_type` 和 `supports`；缺少发布主体或发布日期/更新时间时不得判为已核验。
- 2020 年及更早的旧来源不得进入推荐区；评分器即使计算出高匹配分，也必须由 validator 拒绝 `verified_exists`，并由输出验证器拒绝 `recommended*`。
- `probable`、`stale`、`unverified`、`conflict` 只能进入 `holds`，不能进入 `recommended` 或 `recommended_recruitment_unconfirmed`。

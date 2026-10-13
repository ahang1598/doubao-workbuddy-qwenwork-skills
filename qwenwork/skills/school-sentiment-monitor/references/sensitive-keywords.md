# 预警敏感词库

本文档定义了舆情预警的三级敏感词库，用于辅助判断舆情严重程度。

## 一级敏感词（直接触发紧急预警）

命中任何一级敏感词时，无论互动量多少，均标记为 `severity: critical`。

```
死亡、自杀、性侵、猥亵、中毒、爆炸、坍塌、
踩踏、失踪、绑架、非法拘禁、贩毒、持刀
```

## 二级敏感词（降低预警阈值）

命中二级敏感词时，negative_threshold 降低 30 分（即 >= 50 分即触发重点关注）。

```
举报、曝光、投诉、打人、欺凌、体罚、辱骂、
乱收费、歧视、不公、腐败、泄题、作弊、
性骚扰、强制、威胁、恐吓、虐待、暴力、
隐瞒、造假、掩盖、违规、违法
```

## 三级敏感词（纳入重点关注）

命中三级敏感词时，标记为 `severity: important`（仅在同时为负面情感时生效）。

```
差评、失望、愤怒、抗议、维权、上访、媒体采访、
退学、转学、罢课、联名、请愿、拉横幅、
不满、质疑、追责、问责、处分、开除
```

## 预警触发规则

```
IF 内容包含一级敏感词:
    severity = "critical"    → 立即推送紧急预警

ELIF 内容包含二级敏感词 AND sentiment_score >= 50:
    severity = "important"   → 纳入重点关注

ELIF sentiment == "negative" AND sentiment_score >= 80 AND interaction >= 100:
    severity = "important"   → 纳入重点关注

ELIF 内容包含三级敏感词 AND sentiment == "negative":
    severity = "important"   → 纳入重点关注

ELSE:
    severity = "normal"      → 正常记录
```

## 自定义规则

用户可在任务配置中添加自定义敏感词：
- `alert_rules.sensitive_keywords`: 自定义关键词列表（按二级敏感词处理）
- `alert_rules.negative_threshold`: 自定义负面阈值（默认 80）
- `alert_rules.interaction_threshold`: 自定义互动量阈值（默认 100）
- `alert_rules.keyword_threshold_reduction`: 敏感词触发时阈值降低值（默认 30）

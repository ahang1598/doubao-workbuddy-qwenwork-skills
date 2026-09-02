# 依赖关系 | 劳动争议仲裁申请书

> 版本: 3.3.0

## 1. 上游技能（推荐）

> **§17.19 技能独立性声明**：本技能无硬依赖。以下上游技能均为**弱引用（推荐）**——缺失不影响基本功能运行，仅影响输出质量。本技能可独立生成仲裁申请书。

| 技能 | 必需程度 | 依赖说明 | 引用类型 |
|------|---------|---------|---------|
| labor-evidence-guide | 推荐 | 整理举证清单，生成证据-请求映射 | 弱引用 |
| labor-limitation-analysis | 推荐 | 分析仲裁时效，逐项/逐月审查 | 弱引用 |
| labor-seniority-calc | 推荐 | 确认工龄计算，经济补偿金/赔偿金基数 | 弱引用 |
| labor-wage-arrears-calc | 推荐 | 计算欠薪金额，精确到元 | 弱引用 |
| labor-injury-identification | 条件性 | 工伤认定申请场景使用 | 弱引用 |
| labor-dispute-strategy | 可选 | 案件策略分析，P0诉前评估参考 | 弱引用 |

## 2. 下游技能

| 技能 | 关系说明 |
|------|---------|
| labor-arbitration-defense | 仲裁答辩书，对方当事人可能使用 |

## 3. 平行技能

| 技能 | 关系说明 |
|------|---------|
| labor-lawsuit-complaint | 仲裁后不服起诉，使用起诉状 |
| labor-lawsuit-answer | 仲裁后对方起诉，使用答辩状 |
| labor-collective-dispute | 10人以上集体争议，使用专门技能 |

## 4. 共享资源

| 资源 | 来源 | 使用方式 |
|------|------|---------|
| cross-skill-standards.md | 全局 | 跨技能通用标准 |
| 劳动法规库 | labor-skill-catalog.md | 共享法律依据 |

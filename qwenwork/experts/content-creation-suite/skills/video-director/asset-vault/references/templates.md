# 文件模板

> 本文件在工作流 2 Phase 3（归类写入）、工作流 3（投喂）时读取。
> 新建文件时按对应模板创建。

---

## 1. 项目 metadata.json

```json
{
  "status": "in_progress | delivered | completed | interrupted | abandoned",
  "client": "",
  "project": "",
  "industry": "",
  "category": "",
  "platform": "",
  "date": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DDTHH:mm:ss",
  "content_goal": "",
  "tags": [],
  "brief_summary": {
    "original_selling_points": [],
    "selected_selling_points": [],
    "selling_point_expressions": []
  },
  "steps_count": 0,
  "script_type": "",
  "script_structure": "",
  "hook_type": "",
  "compliance": {
    "hit_rules": [],
    "modifications": ""
  },
  "interruption": {
    "interrupted_at": null,
    "reason": null
  },
  "performance": {
    "views": null,
    "likes": null,
    "comments": null,
    "status": "待回填"
  }
}
```

**status 枚举说明**：

| status | 含义 |
|--------|------|
| `in_progress` | 项目进行中 |
| `delivered` | 脚本已交付，待资产沉淀 |
| `completed` | 资产沉淀已完成 |
| `interrupted` | 用户中断但保留进度，后续可补做 |
| `abandoned` | 用户明确放弃，终态 |

---

## 2. 汇总文件模板（patterns/ 下通用）

```markdown
---
title: {类型名}
type: pattern
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_count: 1
tags: []
---

## 结构特征

（从案例中抽象的通用描述，随新案例持续更新）

## 适用场景

（什么行业、什么平台、什么类型的内容适合用这个模式）

## 来源案例

- **YYYY-MM-DD** | 项目名 → 效果：待回填

## 效果规律

（来自 Part 3 的数据反馈，持续更新）

## 分歧（如有）

（不同案例的矛盾发现）

## 踩坑记录（如有）

（失败经验：被用户否定的方案、合规打回的内容等）
```

---

## 3. 方法论文件模板（patterns/methodologies/ 下）

```markdown
---
title: {方法论名称}
type: methodology
version: 1
created: YYYY-MM-DD
updated: YYYY-MM-DD
iteration_count: 1
---

## 当前方法论

（当前版本的完整方法论描述，包括：步骤、判断依据、注意事项）

## 适用条件

（什么场景下使用本方法论最有效）

## 关键判断点

（方法论执行中的关键决策节点及其判断依据）

## 迭代记录

- **v1 | YYYY-MM-DD** | 来源：项目名
  - 初始版本
  - 核心发现：...

## 历史版本

（被迭代替换的旧方法论存放在此，供回溯参考）
```

**方法论更新规则**：
- 方法论不是追加案例，而是持续迭代同一份文件
- 每次更新需标注迭代版本和本次优化点
- 旧版本方法论不删除，放在"历史版本"段

---

## 4. 卖点规律模板（patterns/selling-points/ 下）

```markdown
---
title: {卖点类型}
type: selling_point_pattern
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_count: 1
---

## 类型特征

（这类卖点的共性特征）

## 有效表达方式

（用什么表达方式呈现这类卖点效果好）

## 用户偏好

（用户在选择卖点时，对这类卖点的偏好程度和选择规律）

## 行业关联

（哪些行业/品类常出现这类卖点？效果如何？）

## 来源案例

- **YYYY-MM-DD** | 项目名
  - 原声卖点：...
  - 最终选定：...
  - 表达方式：...

## 踩坑记录（如有）

（被用户否定、合规打回的卖点表达方式）
```

---

## 5. 行业知识模板（industry/{行业}/_summary.md）

```markdown
---
title: {行业名} 行业知识总览
type: industry_summary
created: YYYY-MM-DD
updated: YYYY-MM-DD
project_count: 1
---

## 行业概览

（该行业的内容创作整体认知）

## 目标受众特征

（来自 audience.md 的精华概括）

## 内容策略建议

（基于 what_works.md 的总结）

## 关键词池

（来自 keywords.md 的 Top 关键词）

## 竞品格局

（来自 competitors.md 的概括）

## 注意事项

（踩过的坑、客户常见偏好等）
```

---

## 6. 操作记录模板（_log/operations.md）

每条记录格式：

```markdown
## [YYYY-MM-DD HH:MM] {操作类型} | {项目名}

- 新建 projects/YYYY-MM/YYYYMMDD_项目名/（含 N 步骤 + 最终脚本）
- 新建 patterns/script-structures/类型名.md
- 更新 patterns/hooks/Hook类型.md（+1 案例）
- 更新 industry/行业/keywords.md（+N 词）
- 更新 _index/catalog.md（+1 项目）
```

操作类型：`沉淀` | `投喂` | `数据回填` | `整理`

---

## 7. 索引 catalog.md 模板

```markdown
# 资产库目录

> 最后更新：YYYY-MM-DD | 项目总数：N

## 项目归档（projects/）

| 日期 | 客户 | 项目 | 行业 | 平台 | 脚本类型 | 状态 |
|------|------|------|------|------|---------|------|

## 内容模式（patterns/）

### 脚本结构
（列出类型及案例数）

### Hook 句式
（列出类型及案例数）

### 卖点规律
（列出类型及案例数）

### 创作技巧
（列出技巧名称）

### 平台规律
（列出已覆盖平台）

### 方法论
（列出方法论名称及版本号）

## 行业知识（industry/）

（列出行业及项目数）

## 数据基准（benchmarks/）

（列出覆盖范围）
```

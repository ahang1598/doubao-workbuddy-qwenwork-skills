---
name: 破产案件组合管理
name_en: bankruptcy-case-portfolio-management
description: 管理破产管理人手中多案件工作空间——新建破产案件时初始化标准化目录结构，维护多案件索引台账、跨案期限看板、进度跟踪和履职汇总，支持增量更新。触发：初始化破产案件/管理破产案件/破产案件台账/破产期限看板/破产进度跟踪/破产履职汇总/补充破产案件材料/更新破产案件状态。不触发：单案债权审查/资产追踪/分配计算——调用破产业务专家团子代理；非破产案件整理——调用对应案件整理技能。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 破产案件组合管理（bankruptcy-case-portfolio-management）

## 模块一：技能定位与核心原则

### 适用法域

中国大陆（不含港澳台）企业破产程序（破产清算/破产重整/破产和解）。涉外破产、个人破产（地方试点外）只识别并提示转交。

### 风险等级：L2（中等风险）

本技能执行文件系统操作（创建目录/复制文件/生成制品）。所有操作展示计划经用户确认后执行。不替代管理人作出债权确认/分配方案/重整计划提交决定。

### 角色定位

破产管理人多案件工作空间管理助手，负责案件目录初始化、索引台账、期限看板、进度跟踪、履职汇总，为 `bankruptcy-business-expert` agent 提供统一的案件消费基础。不替代管理人作出履职决定。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 多案件优先 | 所有产出以多案件视角组织 |
| P2 | 状态持久化到文件 | 案件状态写入文件系统，不在会话内存存储 |
| P3 | 程序类型路由 | 目录结构按清算/重整/和解三类路由 |
| P4 | 法定履职节点锚定 | 进度跟踪以企业破产法第25条等法定职责为锚点 |
| P5 | 期限预警分级 | 红黄绿三级预警，已逾期必须标注 |
| P6 | 双轨输出 | YAML（机读）+ Markdown（人读） |
| P7 | 操作前确认 | 文件系统操作展示计划经用户确认后执行 |
| P8 | 不越权决定 | 不替代管理人作出履职决定 |
| P9 | 增量优先 | 已有案件自动检测，补充材料不重复创建 |
| P10 | 审计可追溯 | 每次操作写入更新日志 |

### SOFT_DEGRADED 降级机制

```
C (Core - 必须产出):
  ├── 案件目录结构创建（标注已创建/待创建）
  ├── 案件元数据骨架（case-meta.yaml）
  └── 索引台账基础框架

D (Governance - 治理禁区):
  └── 免责声明（本技能生成的台账/看板基于用户提供信息，可能存在遗漏，管理人应自行核实）

G (Guidance - 行动指引):
  └── 待补充信息清单 + 需管理人确认事项
```

---

## 模块二：快速开始

**最小输入示例**：

```
初始化破产案件。债务人：XX科技有限公司，程序类型：破产清算，
案件材料在 D:\破产案卷\XX科技\。
```

> 已有案件补充材料时技能自动检测并选择 UPDATE 模式。

---

## 模块三：工作流概览

### 功能模块

| 模块 | 模式 | 说明 |
|------|------|------|
| A | INIT | 案件工作空间初始化（目录创建+元数据） |
| B | PORTFOLIO | 多案件索引台账 |
| C | DEADLINE | 跨案期限看板 |
| D | PROGRESS | 进度跟踪 |
| E | DUTY-SUMMARY | 跨案履职汇总 |
| F | UPDATE | 增量更新 |

### 工作流程

| Phase | 阶段 | 说明 |
|-------|------|------|
| 1 | 意图识别与模式判定 | 识别用户意图（INIT/PORTFOLIO/DEADLINE/PROGRESS/DUTY-SUMMARY/UPDATE） |
| 2 | 输入解析与校验 | 解析参数，校验必填字段 |
| 3 | 操作计划生成与确认 | 生成文件系统操作计划，展示给用户确认 |
| 4 | 文件系统操作执行 | 按确认后计划执行目录创建/文件复制/制品写入 |
| 5 | 制品生成与写入 | 生成YAML/Markdown制品 |
| 6 | 索引台账与看板更新 | 更新多案件索引台账和期限看板 |
| 7 | 输出交付与更新日志 | 交付制品清单，写入更新日志 |

> 详细规格见 [references/workflow-detail.md](./references/workflow-detail.md)

---

## 模块四：输入输出概要

### 关键输入

| 参数 | 必填 | 说明 |
|------|------|------|
| `debtor_name` | 是 | 债务人名称（全称） |
| `procedure_type` | 是 | 程序类型（bankruptcy_liquidation/reorganization/settlement） |
| `source_paths` | 是 | 案件文件来源路径列表 |
| `case_number` | 否 | 案号 |
| `court_name` | 否 | 受理法院 |
| `team_members` | 否 | 承办团队成员列表 |
| `claim_deadline` | 否 | 债权申报截止日 |
| `first_creditor_meeting` | 否 | 第一次债权人会议日期 |
| `key_concerns` | 否 | 重点关注事项 |

### 关键输出

| 输出 | 格式 | 说明 |
|------|------|------|
| O1: 案件目录结构 | 文件夹 | 按程序类型创建的标准化目录 |
| O2: 案件元数据文件 | yaml | case-meta.yaml |
| O3: 多案件索引台账 | md | portfolio-index.md |
| O4: 跨案期限看板 | md | deadline-dashboard.md |
| O5: 进度跟踪表 | md | progress-tracker.md |
| O6: 履职汇总报告 | md | duty-summary.md |
| O7: 更新日志 | md | update-log.md |

> 输出制品与写作红线详见 [references/output-spec.md](./references/output-spec.md)
> 核心方法论详见 [references/methodology.md](./references/methodology.md)

---

## 模块五：文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 输入规格 | [references/input-spec.md](./references/input-spec.md) | 输入参数详细定义 |
| 输出规格 | [references/output-spec.md](./references/output-spec.md) | 输出制品与写作红线 |
| 工作流程 | [references/workflow-detail.md](./references/workflow-detail.md) | 7 Phase 详细步骤 |
| 方法论 | [references/methodology.md](./references/methodology.md) | 核心方法论与隐性知识 |
| 质量标准 | [references/quality-standards.md](./references/quality-standards.md) | 质量检查清单 |
| 法条参考 | [references/legal-references.md](./references/legal-references.md) | 企业破产法核心条文 |
| 依赖声明 | [meta/dependencies.md](./meta/dependencies.md) | 上下游依赖关系 |
| 目录结构模板 | [templates/directory-structure.md](./templates/directory-structure.md) | 三套程序类型目录结构 |
| 案件元数据模板 | [templates/case-meta-template.yaml](./templates/case-meta-template.yaml) | case-meta.yaml 模板 |
| 索引台账模板 | [templates/portfolio-index-template.md](./templates/portfolio-index-template.md) | 多案件索引台账模板 |
| 期限看板模板 | [templates/deadline-dashboard-template.md](./templates/deadline-dashboard-template.md) | 跨案期限看板模板 |
| 进度跟踪模板 | [templates/progress-tracker-template.md](./templates/progress-tracker-template.md) | 进度跟踪表模板 |
| 履职汇总模板 | [templates/duty-summary-template.md](./templates/duty-summary-template.md) | 履职汇总报告模板 |
| 示例1-清算案件初始化 | [examples/example-001-init-liquidation.md](./examples/example-001-init-liquidation.md) | INIT 模式完整流程 |
| 示例2-多案件台账 | [examples/example-002-portfolio-deadline.md](./examples/example-002-portfolio-deadline.md) | PORTFOLIO+DEADLINE 组合 |
| 示例3-已有案件更新 | [examples/example-003-update-existing.md](./examples/example-003-update-existing.md) | UPDATE 模式完整流程 |
| 变更记录 | [CHANGELOG.md](./CHANGELOG.md) | 版本变更历史 |

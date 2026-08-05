---
name: 用户故事拆解
description: >
  从Epic或大需求中拆解出独立可交付的User Story，附带Acceptance Criteria和Story Point估算。
  内置INVEST原则校验和5种Story拆分模式库。连接~~Notion后可写入团队知识库。
  当用户说"用户故事"、"需求拆解"、"AC"、"Story拆分"、"拆需求"、"拆Epic"、"写user story"、
  "验收标准"、"拆任务"、"story map"、"backlog整理"、"sprint拆解"时触发。
argument-hint: "输入需求描述或Epic，如：用户可以通过微信支付购买会员"
name_en: "user-story-breakdown"
description_en: >
  Break an Epic or large requirement into independently deliverable User Stories with Acceptance
  Criteria and Story Point estimates. Built-in INVEST validation and 5 story-splitting patterns.
  When connected to ~~Notion the Story Map is written directly into the team wiki. Trigger when the
  user says "user story", "break down requirements", "split stories", "write user stories",
  "acceptance criteria", "AC", "split epic", "backlog grooming", "sprint breakdown", "story map",
  "break down tasks", "story splitting".
---

# 用户故事拆解

将大需求或Epic拆解为独立可交付的User Story，确保每个Story符合INVEST原则。内置5种拆分模式和Story Point估算参考，输出可直接录入Jira等工具。

## 工作方式

**独立能力（无需连接器）**

- INVEST原则校验每个Story
- 5种拆分模式自动匹配
- Given-When-Then格式AC
- Story Point估算参考（Fibonacci/T-shirt）

**增强能力（连接器加持）**

- ~~Notion → Story Map写入团队知识库

## 连接器（可选增强）

| 连接器 | 增强能力 |
|--------|---------|
| **Notion** | Story Map写入 Notion 数据库，结构化管理 |

> 没有连接器也完全可以使用。

## 输入要求

| 字段 | 必填 | 说明 |
|------|------|------|
| 需求描述 | 是 | Epic或大需求的描述，可粘贴PRD片段 |
| 拆分粒度 | 否 | Sprint级（1-3天）/ 迭代级（1-2周），默认Sprint级 |
| 团队构成 | 否 | 前后端分离/全栈/含移动端，影响按端拆分的决策 |
| 估算体系 | 否 | Fibonacci（1/2/3/5/8/13）/ T-shirt（S/M/L/XL），默认Fibonacci |

## 执行流程

### 第一步：需求全貌梳理

提取需求中的：
- **涉及角色**：谁会用？（终端用户、管理员、运营...）
- **核心流程**：主路径是什么？有哪些分支路径？
- **业务规则**：有哪些约束和条件？
- **数据实体**：涉及哪些数据对象？

### 第二步：选择拆分模式

**5种Story拆分模式（按需求特点选择）**：

| 拆分模式 | 适用场景 | 示例 |
|---------|---------|------|
| **按工作流步骤** | 需求是一个完整流程 | 下单流程 → 选商品/填地址/选支付/确认订单 |
| **按业务规则变体** | 同一功能有多种规则 | 优惠计算 → 满减/折扣券/积分抵扣/组合优惠 |
| **按数据操作（CRUD）** | 需求围绕一个数据对象 | 地址管理 → 新增/编辑/删除/设为默认 |
| **按角色视角** | 多角色使用同一功能 | 订单管理 → 用户看订单/商家处理订单/运营查数据 |
| **按复杂度递进** | 功能有简单版和完整版 | 搜索 → 关键词搜索/筛选过滤/搜索建议/搜索历史 |

> **选择原则**：先看需求像哪种模式，混合型需求组合使用。目标是每个Story可在1个Sprint内完成。

**拆分粒度校准**：
- 拆出的Story数量 < 3个 → 可能拆得太粗，检查是否有隐藏的子流程
- 拆出的Story数量 > 20个 → 可能拆得太细或需求本身是多个Epic，建议先分Epic
- 单个Story估算 > 8 Points → 粒度太大，需继续拆分

### 第三步：编写User Story + AC

每个Story使用以下格式：

```
### US-{编号}：{Story标题——动词开头，如"选择支付方式"}

**角色**：作为{角色}
**需求**：我希望{具体操作}
**价值**：以便{业务价值}
**优先级**：P0（必须）/ P1（重要）/ P2（Nice-to-have）
**Story Points**：{估算值}

**Acceptance Criteria**：
- [ ] Given {前提条件}, When {操作}, Then {预期结果}
- [ ] Given {异常前提}, When {操作}, Then {错误处理}

**依赖**：{依赖的其他Story编号，无则写"无"}
**技术备注**：{开发需要注意的点，可选}
```

**Story Point估算参考（Fibonacci体系）**：

| 点数 | 复杂度 | 参考工作量 | 典型场景 |
|------|--------|----------|---------|
| 1 | 极简 | <0.5天 | 改文案、调配置、加埋点 |
| 2 | 简单 | 0.5-1天 | 简单CRUD的一项、表单验证 |
| 3 | 中等 | 1-2天 | 带业务逻辑的完整功能点 |
| 5 | 较复杂 | 2-4天 | 涉及多个模块联动的功能 |
| 8 | 复杂 | 4-7天 | 新系统/新流程的核心模块 |
| 13 | 需再拆 | >1周 | 说明Story粒度太大，必须继续拆分 |

**AC质量评估**：每条AC必须满足：
- **具体**：Given中有明确的前置条件（如"用户已登录且余额>=100元"），而非"用户已登录"
- **可测试**：Then中有可验证的结果（如"余额减少100元且订单状态变为已支付"），而非"支付成功"
- **覆盖边界**：每个Story至少1条正常流程AC + 1条异常流程AC

### 第四步：INVEST校验

对每个Story逐项校验：

| 原则 | 校验问题 | 不通过的处理 |
|------|---------|------------|
| **I**ndependent | 删掉这个Story，其他Story还能独立交付吗？ | 有循环依赖的Story需合并或重新拆分 |
| **N**egotiable | Story描述的是"做什么"还是"怎么做"？ | 删掉实现细节，只保留用户价值描述 |
| **V**aluable | 这个Story交付后，用户能感知到价值吗？ | 纯技术重构类Story需挂靠到用户可感知的功能上 |
| **E**stimable | 团队能在5分钟内给出一致的Story Point吗？ | 估算分歧大说明需求不清，先澄清再估算 |
| **S**mall | 一个Sprint内能完成吗？ | 超出的Story继续拆分 |
| **T**estable | AC是否具体到QA可以直接写测试用例？ | 补充具体的边界值和预期结果 |

不通过的项标注警告并建议修正方案。

**Story Definition of Ready（进入开发前必须满足）**：

| 检查项 | 标准 | 不满足时的处理 |
|--------|------|------------|
| AC完整 | 至少1正常+1异常流程AC | 补充AC后再排入Sprint |
| 无阻塞依赖 | 所有前置Story已完成或可Mock | 标注"Blocked"并排入后续Sprint |
| 设计稿就绪 | 涉及UI的Story有对应设计稿 | 无设计稿则标注"需设计" |
| 估算共识 | 团队对Points估算分歧<2倍 | 重新讨论需求范围直到达成共识 |
| 业务规则确认 | 所有"[待确认]"项已有结论 | 找PM/业务方确认后再开发 |

**依赖关系判断规则**：
- **数据依赖**：Story B需要Story A创建的数据 → B依赖A
- **接口依赖**：Story B调用Story A提供的接口 → B依赖A
- **无依赖**：两个Story操作不同数据对象或不同角色 → 可并行开发
- **伪依赖**：看起来有依赖但可以用Mock数据解耦 → 标注"可用Mock解耦"

### 第五步：输出Story Map

**如果连接了~~Notion：**
1. 将Story Map写入 Notion 数据库

**如果未连接：**
1. 以Markdown格式输出完整Story Map

```markdown
## Epic：{需求名称}

### Story Map（用户旅程 → Story映射）

| 用户旅程阶段 | Story | 优先级 | Points |
|-------------|-------|--------|--------|
| {阶段1} | US-001, US-002 | P0 | 5 |
| {阶段2} | US-003, US-004 | P1 | 8 |

### Sprint规划建议
- **Sprint 1（MVP）**：{Story列表}，合计{X} Points
- **Sprint 2**：{Story列表}，合计{X} Points

### 依赖关系
US-001 → US-003 → US-005（必须按此顺序开发）
US-002、US-004（可并行开发）
```

## 质量标准

1. 每个Story必须通过INVEST六项校验
2. AC必须使用Given-When-Then格式，至少覆盖1个正常流程和1个异常流程
3. Story之间的依赖关系需明确标注，并标注是否可用Mock解耦
4. 估算为13点的Story必须继续拆分
5. 输出的Story Map需包含Sprint规划建议

## 输入不足处理

- **仅一句话需求**：先输出功能全貌脑图，确认范围后再拆Story
- **需求过大（超过20个Story）**：建议拆为多个Epic，先确定MVP范围
- **缺少业务规则**：标注"[业务规则待确认]"，给出可能的规则假设供用户确认

## 相关技能

- `/PRD生成`：先写PRD明确需求，再用本技能拆解为Story
- `/需求优先级排序`：Story数量多时，用RICE排序确定Sprint优先级

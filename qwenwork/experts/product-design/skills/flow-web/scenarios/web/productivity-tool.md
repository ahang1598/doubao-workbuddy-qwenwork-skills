# Scenario: 生产力 / 团队协作工具（Productivity / Team Workspace Tool）

## Identity

**Platform**: Web
**Definition**: 面向个人或小团队（5-20 人）的轻量生产力 / 协作工具，核心价值是「快速捕捉 + async 共享」——用户能在低中断成本下记录 / 整理 / 沉淀工作内容，并让团队默认可见以替代同步会议。
**Canonical Examples**: Notion（笔记 / 知识库）、Linear retrospective（sprint 回顾）、Wonder/Wave（异步周报）、Coda（文档 + 数据）、DesignRetro 这类周复盘工具
**Not this scenario if**:
- 企业级流程管理（→ Internal Ops，有审批层级）
- 数据监控看板（→ Data Analytics）
- AI 对话是主界面（→ AI Product）
- 公开内容发布平台（→ Community & Social）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 个人创作者 / 团队成员（贡献 + 消费内容）/ 团队 leader（消费 + 反馈）|
| **核心目标** | 快速记录想法 / 沉淀工作产物 / 让团队 async 看到自己的思考 / 看到他人在做什么 |
| **心智模型** | 「数字化的工作日记」——比文档轻、比社交平台正式、跟 IM 互补，能沉淀但不打扰 |
| **使用频率** | 中高频（每周 1-3 次主动写入；每周 3-5 次浏览团队）；每次 2-10 分钟 |
| **决策模式** | 自主驱动（用户主动写）+ async 消费（leader / 同事按节奏看） |
| **容错期望** | 高：草稿自动保存是底线；提交前预览；重要操作（删除 / 公开 / 团队可见）有明确提示 |

---

## IA Template

**导航模式**：顶部水平导航（3-5 项）+ 右上角账户菜单

理由：生产力工具的核心动作是"创作"和"浏览"两类，左侧 Sidebar 太重；顶部导航更轻，符合"轻量"定位。如果团队规模超过 20 人或多个项目空间，可升级到 Sidebar。

**页面层级**：≤ 3 层

```
L1: 主导航项（如 新建 / 看板 / 设置）
L2: 列表 / 创作流程的多屏分步
L3: 单条详情 / 编辑态
```

**权限角色**：

- 个人模式（无团队）：仅本人可见所有内容
- 团队成员：自己创建的内容默认团队可见；他人内容只读 + 可评论
- 团队 leader / Admin：增加团队成员管理 + 隐私设置权限

**数据密度**：低-中。核心视图是卡片流 / 列表 / 单屏表单，避免数据 Table 这种重视图。

**主要容器模式**：

- **多屏分步**（Welcome → Form → Preview → Done）：用于创作流程，避免单屏过长
- **卡片网格 / 单列流**：团队看板默认布局，按响应式断点切换
- **详情页**：单条内容详情，含元数据（作者、时间、已读状态）

### 导航骨架图（ASCII）

```
┌─────────────────────────────────────────────────────────────┐
│ Logo  [新建] [看板] [设置]              [搜索] [通知] [头像] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              [主内容区：创作流程 / 卡片流 / 详情]            │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Canonical Flows（候选用户流程）

### Flow 1 — 内容创作（核心）

```
Welcome（首次访问引导，可跳过）
  → Form（核心输入：1-3 个字段，避免长表单）
  → Preview（可返回修改）
  → Done（完成确认 + 团队可见提示 + 连续完成状态）
```

**关键设计点**：
- 草稿自动保存（localStorage 或后端定时同步）
- 字段数量严控：单屏内可见，不滚屏
- 完成态强反馈（视觉确认 + 鼓励元素）

### Flow 2 — 团队浏览

```
Team Board（默认本周视图，卡片网格）
  → Detail（单条完整内容 + 已读列表 + 评论区）
  → 翻页历史 / 切换成员
```

**关键设计点**：
- 空状态文案：明确告诉用户"为什么是空的，下一步该做什么"
- 已读列表（avatar 横向排列）：让创作者感知有人在看
- 卡片密度：3 列（≥1280px）/ 2 列（768-1279px）/ 1 列（<768px）

### Flow 3 — 团队设置 / 加入

```
Auth（邮箱登录 / 邀请链接）
  → Team Join or Create（首次完成创作后引导）
  → Team Create / Team Join 分支
  → Team Settings（成员、隐私、通知）
```

**关键设计点**：
- 不在第一次创作前强制要求加入团队（破坏 onboarding）
- 邀请链接 vs 邀请码二选一，简化加入流程

### Flow 4 — 个人设置（次要）

```
Settings → Profile / Notifications / Account
```

---

## 状态覆盖要求

每个 page 必须覆盖以下状态（按 Brief.design_criteria.qualitative 验收）：

| 状态 | 设计要求 |
| --- | --- |
| **Initial / 首次访问** | Welcome 引导，预设示例答案可一键填充 |
| **Empty** | 不只是"暂无数据"，给出下一步动作（CTA） |
| **Loading** | Skeleton 占位（避免白屏）；异步操作 ≥ 200ms 触发 |
| **Typing / 草稿中** | 自动保存提示（"已保存 X 秒前"）|
| **Submitting** | 按钮变 loading 态，禁用重复提交 |
| **Success** | 强反馈（toast / 完成屏 / 动效），鼓励持续动作 |
| **Error** | 友好提示 + 草稿保留 + 重试通道 |
| **Streak / 连续完成** | 视觉计数器；里程碑（如第 4/8/12 周）触发轻量动效 |
| **Read by team** | 已读成员头像横向列出；零状态时显示"邀请团队"CTA |

---

## 组件清单（推荐使用 SparkDesign / shadcn / antd）

**核心组件**：
- Card（团队看板卡片）
- Textarea（创作输入）
- Button（多种 variant：primary / secondary / ghost）
- ProgressIndicator（多屏分步进度）
- Avatar（成员头像）
- Toast（成功 / 错误反馈）

**辅助组件**：
- Tabs（看板视图切换：本周 / 历史）
- Comment / CommentInput（评论交互）
- Modal / Sheet（确认 / 二级表单）
- Skeleton（加载占位）
- Switch（设置开关）

**自定义组件**（按需）：
- WeekStreak / DayStreak（连续打卡视觉计数器）
- ReadByAvatars（已读成员头像横排）
- ContentCard（聚合内容卡片，可复用于看板和详情页）

---

## 与 Brief 的强关联点

如果上游有 brief.json，特别关注以下字段并体现到设计：

- `brief.design_criteria.quantitative['首屏到完成 ≤ X 分钟']`：影响 flow 步骤数量（多屏分步不能超过 4-5 屏）
- `brief.strategy_dimensions['情感化设计']`：影响完成态、连续打卡、团队反馈等鼓励元素的设计
- `brief.strategy_dimensions['用户引导']`：影响 onboarding 长度（推荐 30 秒以内）
- `brief.constraints` 中"Web 优先不做 Mobile App"：必须做响应式降级（不是不做 Mobile）
- `brief.out_of_scope` 中"不做 AI 自动生成内容"：核心创作必须保留用户主动输入

---

## 反例：什么不是这个 scenario

- 数据 Table 为主的视图 → Internal Ops / Data Analytics
- 跨团队大规模协作（100+ 人） → SaaS Management / Internal Ops
- 公开内容发布（任何人可见） → Community & Social / Marketing Site
- 实时多人编辑（Figma / Google Docs 风格） → Design Tools
- 主要靠 AI 生成内容 → AI Product

如果 brief 描述的产品同时含有"轻量协作"和上述某项特征，可能需要双 scenario 组合（如 Productivity Tool + AI Product），由 Skill 在 Step 2 提示用户选择主导 scenario。

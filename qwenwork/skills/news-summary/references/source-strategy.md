# 信息源策略与核验规则

Module B 执行前必须读取本文件。

---

## 信息源选择策略

根据主题类型选择信息源组合，优先检索官方和权威来源。

| 主题类型 | 优先信息源 | 补充信息源 | 搜索关键词示例 |
|---------|-----------|-----------|--------------|
| AI / 科技 | 官方博客（OpenAI、Google AI、Meta AI）、arXiv、GitHub | Hacker News、Product Hunt、TechCrunch | "OpenAI official blog"、"AI research paper 2026" |
| 区块链 / Web3 | 项目官网、CoinDesk、The Block | Twitter/X、Discord 公告 | "blockchain official announcement"、"crypto news" |
| 游戏 | 官方公告、IGN、GameSpot | Steam 社区、Reddit r/gaming | "game official announcement"、"game release" |
| 金融 / 财经 | 官方公告、Reuters、Bloomberg | SEC Filings、FT | "fintech news"、"financial regulation" |
| 医疗 / 生物 | Nature、Science、FDA 公告 | PubMed、STAT News | "biotech breakthrough"、"FDA approval" |
| 通用 / 综合 | Google News、权威媒体（新华社、Reuters） | 社交媒体、行业论坛 | 根据具体主题构建 |

---

## 查询构建模板

每条查询由三部分拼成：**主题词 + 角度词 + 时间限定**。以下是各轮的角度词选择指南：

| 轮次 | 角度 | 查询模板 | 示例（主题=AI） |
|------|------|---------|----------------|
| 第 1 轮 | 官方/权威 | `"{主题} official announcement {月份 年份}"` | `"AI official announcement March 2026"` |
| 第 2 轮 | 产品/技术 | `"{主题} product launch OR release {时间}"` | `"AI product launch this week"` |
| 第 3 轮 | 研究/突破 | `"{主题} research breakthrough OR paper {时间}"` | `"AI research breakthrough March 2026"` |
| 第 4 轮 | 资本/市场 | `"{主题} funding OR acquisition {时间}"` | `"AI startup funding 2026"` |
| 第 5 轮 | 中文补充 | `"{主题} 最新消息 OR 动态 {时间}"` | `"AI 最新消息 2026年3月"` |

### 关键词规则

- 英文检索为主，中文检索为辅（第 5 轮或额外补充轮）
- 每条查询 5-6 个词为宜，避免整句
- 必须包含时间限定词（"this week"、"March 2026"、"latest"）
- 若主题是特定公司/项目，第 1 轮直接用公司名 + "blog OR announcement"

---

## 检索收敛判断

每完成一轮 `WebSearch` + 时间核验后，执行以下决策：

```
已核验候选 ≥ 15 条？ ──是──→ 停止检索，进入 Module C
        │ 否
累计轮数 ≥ 5 轮？ ──是──→ 停止检索，进入 Module C
        │ 否
本轮新增有效候选 = 0 且上一轮也 = 0？ ──是──→ 停止检索（主题已饱和）
        │ 否
更换角度词或信息源，执行下一轮
```

**补充规则**:
- "已核验候选"指通过时间核验且未被去重的条目数
- 若停止时候选 < 5 条，在 C5 向用户说明数据量偏少并建议放宽条件
- 若某轮返回结果与前轮高度重叠（>80%），视同"新增有效候选 = 0"

---

## 时间核验操作指引

每条候选新闻必须通过时间核验，否则不纳入报告。

### 核验步骤（按优先级依次尝试）

**步骤 1 — 页面内时间（最可靠）**:
使用 `fetch` 获取页面后，按以下顺序查找发布时间：
- HTML 中的 `<time datetime="2026-03-25T10:30:00Z">` 标签
- 正文中"Published:"、"发布于"、"日期："附近的日期文本
- `<span class="date">`、`<div class="publish-time">` 等常见 class 名

**步骤 2 — URL 日期模式**:
检查 URL 路径中是否包含日期段，常见格式：
- `/2026/03/25/article-title` → 2026-03-25
- `/2026-03-25-article-title` → 2026-03-25
- `?date=20260325` 或 `?published=2026-03-25` → 2026-03-25

**步骤 3 — Meta 标签**:
在 `fetch` 返回的页面中查找：
- `<meta property="article:published_time" content="2026-03-25T10:30:00Z">`
- `<meta name="datePublished" content="2026-03-25">`
- `<meta property="og:updated_time" content="...">`（注意：这是更新时间而非发布时间，仅作辅助参考）

**步骤 4 — 搜索引擎标注（可靠性最低）**:
`WebSearch` 结果中的时间标注，仅在以上三步均无结果时使用，且须在报告中标记"时间来源：搜索引擎标注（未交叉验证）"

### 核验规则

| 情况 | 处理方式 |
|------|---------|
| 发布时间在时间窗口内 | 保留，标注时间来源（页面/URL/meta/搜索引擎） |
| 发布时间在时间窗口外 | 直接剔除 |
| 页面时间与 URL 时间矛盾 | 以页面内时间为准 |
| 四步均无法确认发布时间 | 不纳入报告，计入统计的"时间不明"类别 |

### 统计记录

Module B 完成后须记录以下统计数据（用于报告附录）：

- 检索总数：`WebSearch` 返回的候选总数
- 通过核验数：发布时间在窗口内的条目数
- 剔除数（窗口外）：确认发布时间但在窗口外的条目数
- 剔除数（时间不明）：无法确认发布时间的条目数
- 信息源分布：各来源的条目数

---

## 去重规则

### 保留优先级

同一事件被多个来源报道时，保留质量最高的来源：

**官方来源 > 权威媒体（Reuters/Bloomberg/TechCrunch） > 行业媒体 > 社区讨论 > 转载**

被淘汰来源在详情中补充提及（如"本消息亦被XX、YY报道"）。

### 去重三步判定法

**第一步 — 事件聚类**: 根据事件核心（什么主体 + 做了什么事）将候选分组。描述同一事件的不同报道归为一组。

**第二步 — 组内选源**: 每组内按保留优先级选出最佳来源作为主条目，其余来源在详情中列出。

**第三步 — 边界判定**: 以下情况视为"不同条目"，不应合并：
- 同一公司、不同产品线的新闻（如 Google 发布 Gemini 2.0 与 Google Cloud 推出新服务）
- 同一领域、不同公司的类似动作（如 OpenAI 发模型与 Anthropic 发模型）
- 同一主体、时间间隔 >3 天的不同事件

### 去重实操示例

**场景**: AI 主题检索后得到以下候选：

| # | 标题 | 来源 | 时间 |
|---|------|------|------|
| 1 | "OpenAI Releases GPT-5" | OpenAI 官方博客 | 2026-03-24 |
| 2 | "GPT-5 正式发布，支持多模态推理" | 36氪 | 2026-03-24 |
| 3 | "GPT-5 来了！详细测评" | 少数派 | 2026-03-25 |
| 4 | "Google Announces Gemini 2.5" | Google AI Blog | 2026-03-23 |
| 5 | "OpenAI Launches New API Pricing" | TechCrunch | 2026-03-25 |

**判定过程**:
- #1、#2、#3 描述同一事件（GPT-5 发布）→ 聚为一组 → 保留 #1（官方来源），详情中提及"36氪、少数派亦有报道"
- #4 是不同公司的不同事件 → 独立条目
- #5 是同一公司（OpenAI）但不同事件（API 定价 ≠ 模型发布）→ 独立条目
- **去重结果**: 3 条（#1 合并版、#4、#5）

### 同一主体多更新合并

同一公司/项目在时间窗口内有多条更新时：
- 合并为一条，标题用最重要的更新
- 详情中按时间排列各更新要点
- 保留所有原文链接

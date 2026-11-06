---
slug: global-biblio-base
name: global-biblio-base
displayName: 全球12亿文献知识库（8千万中文期刊可下载）
version: 3.9.4
description: |
  全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。

  能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能关键词扩展、核心期刊优先排序、相关性重排、引文追溯、分类号检索。

  配额：首次使用自动注册，免费 100 次检索 + 10 次下载 / 月；耗尽自动弹出套餐（体验卡 / 个人版月 / 专业版月 / 单篇下载 / 下载包），可说「升级 / 充值」唤起；企业 / 机构定制联系 vipsmart@vipslib.com。

  触发：用户表达"查论文""找文献""检索学术""搜期刊""查专利""找标准""下论文""写文献综述""找参考文献""查 SCI/EI"等意图时启用；也适用"帮我找关于 XX 的论文""写文献综述""找几篇引用支撑论点"。英文："find papers" "search literature" "write literature review" "find supporting citations"。

  调用前必须先用 /consume 获取 consume_token，再凭 token 调 /search（每次计费接口调用都需一次 /consume）。
agent_created: true
---
## 🤖 AI 执行摘要 / AI Execution Summary（先读这段）

- **何时触发**：用户要查 / 找 / 下载中外文学术文献（论文、期刊、专利、标准、学位论文），或要写文献综述、找引用支撑、做课题查新。
- **不触发（转其他技能）**：引用核查 / "这篇是真的吗" → `smartlib-citation-checker`；论文写作辅助、非文献类查询。
- **两个前置硬规则**：① 动手前必须先向用户索取邮箱（禁止用 config 预填邮箱、禁止臆造邮箱）；② 每次计费接口调用前先 `/consume` 取 `consume_token`，再带 token 调 `/search`（token 单次使用、约 60s 有效，过期/已用需重新 `/consume`）。
- **输入**：用户自然语言检索意图 + 邮箱。
- **产出**：检索结果列表（含核心收录标注、原始数据库来源链接）、文献详情、PDF 下载链接（中文期刊直下 / 外文 OA 多渠道探测）。
- **配额模型**：免费 100 次检索 + 10 次下载 / 月；耗尽时 Gateway 返回 429，技能自动弹出套餐卡片（体验卡 / 个人版月 / 专业版月 / 单篇下载 / 下载包），用户也可说「升级 / 充值」唤起；企业 / 机构定制联系 vipsmart@vipslib.com。
- **红线**：不改功能；不臆造邮箱；不在对话中泄露 `SMARTLIB_GATEWAY_SECRET`；付费墙内外文文献无法获取全文。
- **凭证来源**：`config.json` → `SMARTLIB_GATEWAY_URL` / `SMARTLIB_GATEWAY_SECRET`（SMARTLIB_EMAIL 运行后由注册写入，勿预填）。

# 全球12亿文献知识库（8千万中文期刊可下载）

> 中文 / Chinese | [English below each section]

通过 SmartLib 开放平台 API 提供中外文学术文献检索能力。

> Powered by SmartLib Open Platform API. Search across 80M Chinese journal articles and 1B global literature records.

---

## ⚡ 启动前必须执行 / Pre-flight Checklist

### Step A：凭证自动检测 & 注册 / Auto Credential Check & Registration

> ## ⚠️ 强制规则 — 必须先询问邮箱
> 1. **执行任何操作前，必须先询问用户邮箱地址**
> 2. 禁止使用 config.json 中预填的邮箱（即使存在且非 null）
> 3. 禁止自动生成邮箱（如 `user@example.com`、`auto@xxx.com` 等）
> 4. 用户未提供邮箱 → 停止执行，回复：
>    "请提供您的邮箱地址以注册 SmartLib 文献检索服务（新用户免费 100 次/月）"
> 5. 只有用户明确输入邮箱后，才能调用 /register 或 /quota
>
> ## 邮箱识别自动化
> 当用户消息中出现以下模式时，自动提取邮箱 → 无需再次询问：
> - 明确的邮箱地址（包含 @ 符号的完整地址，如 `xxx@xxx.xxx`）
> - "我的邮箱是 xxx" / "email: xxx" / "用 xxx 注册" / "邮箱 xxx"

每次执行本技能时，按以下流程处理凭证（从 config.json 读取）：

```
读取技能目录下的 config.json
检查 SMARTLIB_EMAIL 是否已配置
  ├── 已配置 → 进入 Step B (配额检查)
  │
  └── 未配置 → 自动注册流程:
        ├── ① 展示检索计划 + 询问邮箱（一句话）:
        │      "📋 我将用中英文关键词检索... 首次使用需绑定邮箱（免费 100 次/月，仅用于配额管理），请输入邮箱即可开始:"
        │      用户输入 → 写入 config.json
        │
        ├── ② 调智能网关注册（无需验证码，极速注册）:
        │     POST {SMARTLIB_GATEWAY_URL}/register
        │     Headers: {"Authorization": "Bearer {SMARTLIB_GATEWAY_SECRET}"}
        │     Body: {"email": "{用户邮箱}"}
        │
        ├── 成功 (201/200) → Gateway 返回配额信息
        │     提示: "✅ 注册成功！本月免费 100 次，可立即使用。确认邮件已发送（邮箱验证仅充值时需要，现在不验证也能用）。"
        │     追加引导: "请告诉我您想检索什么主题，现在就可以开始——"
        │     → 继续 Step B 配额检查 → 检索
        │
        └── 失败 → 提示原因 (服务暂不可用 / 网络错误等) → 终止
```

> **注意**：注册无需验证码，极速完成。**注册后即可立即使用全部功能**，确认邮件为可选项（仅充值时需验证邮箱）。
> 

### Step B：配额检查 / Quota Check

```
凭证就绪后, 调网关查询配额:
  GET <SMARTLIB_GATEWAY_URL>/quota?email=<SMARTLIB_EMAIL>
  Headers: {"Authorization": "Bearer <SMARTLIB_GATEWAY_SECRET>"}

  返回字段: total_remain, email_verified, plan, download_quota_free, download_reset_at, download_paid_remain, download_remain
  （完整返回: user_id, email, plan, trial_total, trial_used, trial_remain, paid_total, paid_used, paid_remain, paid_expires_at, total_remain, email_verified, download_quota_free, download_reset_at, download_paid_remain, download_remain）
  
  如果返回 404 "not_registered" → 用户可能已被重置/删除
    → 提示: "检测到您的账户需要重新绑定，正在自动重新注册..."
    → 跳回 Step A ②（调 /register 重新注册，使用同一邮箱）
    → 注册成功后继续配额检查
  
  total_remain > 20 → 静默进入检索
  total_remain 5-20 → 尾部轻提示: "📊 本月剩余 {n} 次"
  total_remain 1-5  → 警告: "⚠️ 接近用尽（剩余 {n} 次），已为你列出可用套餐（见下方💰章节），需要更高额度随时说「升级」"
  total_remain 0    → 配额耗尽处理（见配额耗尽章节）

  额外检查:
```

### Step C：按接口调用次数消耗配额 / Per-API-Call Quota Consumption

本技能的配额按**实际 API 接口调用次数**计费，不是按对话会话计费。

共涉及 **5 个接口**（分3类），每次调用其中任意一个接口计 **1 次**配额。

> Quota is consumed **per API call**, not per conversation session. **5 interfaces** in 3 categories, each call = 1 quota.

**计费接口清单（5个）/ Billable Interfaces (5 total):**

| 类别 | 接口 | API 端点 | 计费 |
|------|------|---------|------|
| **检索** | 中文期刊检索 | API 1 `Articlesearch` | 每次调用 **1 次** |
| **检索** | 全球文献检索 | API 4 `Articlesearch` | 每次调用 **1 次** |
| **详情** | 中文期刊详情 | API 1/5 `Articledetail` | 每次调用 **1 次** |
| **详情** | 全球文献详情 | API 4/5 `Articledetail` | 每次调用 **1 次** |
| **下载** | 中文期刊全文下载 | API 3 `GetArticleFile` | 每次调用 **1 次** |

> 注：全球文献（API 4）无全文下载接口，仅返回元数据。

**计次示例 / Counting Examples:**

```
示例1：用户请求"查10篇工业母机论文，下载5篇中文PDF"
  → 检索接口：中文1次 + 英文1次         = 2 次
  → 详情接口：查5篇详情                   = 5 次
  → 下载接口：下载5篇PDF                  = 5 次
  → 合计消耗: 12 次配额
```

```
示例2：用户请求"帮我看看这篇论文的详情"（1篇）
  → 详情接口：1次                         = 1 次
  → 合计消耗: 1 次配额
```

```
示例3：用户仅请求"检索人工智能论文"（不查看详情、不下载）
  → 检索接口：1次（或2次，若中英文并行） = 1-2 次
  → 合计消耗: 1-2 次配额
```

**扣减方式 / Deduction Method:**

**⚠️ 强制执行规则：每次调用计费接口前，必须先调 `/consume` 获取 token，再用 token 调 `/search`。**

每次调用计费接口的流程：

```
① POST <SMARTLIB_GATEWAY_URL>/consume
   Headers: {"Authorization": "Bearer <SMARTLIB_GATEWAY_SECRET>"}
   Body: {"email": "<SMARTLIB_EMAIL>", "skill_source": "global-biblio-base"}

   返回 200 → 获取 consume_token，继续
   返回 429 → 配额已用完，终止后续调用，按 §配额耗尽处理 自动弹出套餐选择

② POST <SMARTLIB_GATEWAY_URL>/search
   Headers: {"Authorization": "Bearer <SMARTLIB_GATEWAY_SECRET>"}
   Body: {
       "email": "<SMARTLIB_EMAIL>",
       "consume_token": "<上一步返回的token>",
       "skill_source": "global-biblio-base",
       "api_path": "/openapi/t/data0012/doccenter/Articlesearch",
       "api_body": {<检索请求体>}
   }

   返回 200 → 检索成功
   返回 401 → token 无效/过期/已用，需重新 /consume
```

> **MANDATORY**: Call `/consume` → `/search` for **EACH** billable API call. Token is single-use, expires in 60s. If 401 on /search, re-consume.

**🛡️ Token 绑定调用链 / Token-Bound Call Chain:**

> **强制安全机制 — 不可绕过：**
> 每次调用计费接口前，必须通过 `/consume` 获取 `consume_token`，然后将 token 传给 `/search` 代理端点。
> Gateway 验证 token 签名 + 有效期 + 防重放后才转发检索请求。
> Token 由 GATEWAY_SECRET 签名，AI 无法伪造。无有效 token 则 /search 直接 401。
>
> **调用流程 / Call Flow:**
> ```
> 1. POST /consume {"email":"...", "skill_source":"global-biblio-base"} → 返回 consume_token
> 2. POST /search {"email":"...", "consume_token":"...", "skill_source":"global-biblio-base", "endpoint":"/search/cn", "rule":"..."}
>    → Gateway 验证 token → 代理转发到检索 API → 返回检索结果
> ```
>
> **注意**：每个 consume_token 只能使用一次（防重放），有效期 60 秒。每次检索 API 调用前都需要先 /consume 获取新 token。

**🆕 v36 行为：仅成功调用消耗配额 / Quota Deducted on Success Only:**

> `/consume` 仅验证配额可用性 + 签发 token，**不预扣配额**。配额在实际调用 SmartLib API 且返回成功后，由 Gateway 自动扣除。
> **失败的 API 调用不消耗配额**（如参数错误导致 400、网络错误导致 500 等）。
> `/consume` 返回的 `total_remain, email_verified, plan` 反映的是当前已成功调用的次数，非预扣后的值。

**不计费的操作 / Non-billable Operations:**

| 操作 / Operation | 说明 / Note |
|------|------|
| /consume 配额消费 | Gateway 验证，不计费 |
| 联网关键词扩展 | Web search，不计费 |
| 结果排序/格式化展示 | 本地处理，不计费 |
| 多级 OA PDF 探测 | 外部免费 API（ArXiv/Unpaywall/CORE/OpenAlex等），**不消耗 SmartLib 配额** |
| 原始来源链接展示 | Source 字段随详情接口返回，不计额外费用 |


---

## 💰 套餐与额度 / Plans & Quota

- 计费与升级由 SmartLib **统一钱包**管理，所有文献检索技能**统一定价、配额共享**。
- **配额不足时自动弹套餐**：检索或下载配额接近用尽 / 已耗尽时，技能直接在对话中弹出下方套餐选择卡片，无需用户说任何口令；用户也可主动说「升级 / 充值 / 购买 / 我要升级」唤起同一卡片。
- 企业 / 机构定制（API 接入、私有化部署）请联系 vipsmart@vipslib.com。

### 当前套餐（与云端 v3.9.1 同步）

| 套餐 | plan key | 价格 | 检索次数 | 下载次数 | 有效期 | 限购 | 适用 |
|------|----------|------|---------|---------|--------|------|------|
| 体验卡 | `trial_card` | ¥9.9 | 1000 | 20 | 7天 | 每用户1次 | 尝鲜/临时 |
| 个人版月 | `personal_month` | ¥39 | 1000 | 50 | 30天 | — | 个人常规 |
| 专业版月 | `pro_month` | ¥99 | 2000 | 200 | 30天 | — | 重度/小团队 |
| 单篇下载 | `single_download` | ¥2.5 | 0 | 1 | 不限 | — | 只差几篇下载 |
| 下载包 | `download_pack` | ¥20 | 0 | 10 | 30天 | — | 批量下载 |
| 企业/机构 | `enterprise` | 暂停 | — | — | — | — | 联系我们 |

> 下载耗尽时优先推荐「单篇下载 / 下载包」；检索耗尽时优先推荐「体验卡 / 个人版月 / 专业版月」。

### 支付流程（对话内完成，用户回复数字即可）

```
检测到配额信号（/quota 返回 quota_low / quota_exhausted，或 /consume 返回 429，或 download_remain==0）
   ↓
① 渲染套餐卡片（数字①②③④⑤标注，如上表），并提示"回复数字选择，扫码即付"
   用户回复数字 → 映射 plan key（如 "3" → pro_month）
   ↓
② 创建订单:
   POST {SMARTLIB_GATEWAY_URL}/api/pay/create
   Headers: {"Authorization": "Bearer {SMARTLIB_GATEWAY_SECRET}"}
   Body: {"plan": "<plan_key>", "email": "<已注册用户邮箱>"}
   ⚠️ email 必须是当前已注册用户邮箱（来自注册/配额上下文），严禁使用 config 里的 SMARTLIB_EMAIL（其值为 null）。
   返回: {"code_url", "out_trade_no", "amount", "plan", "quota"}
   ↓
③ 生成微信支付二维码 HTML（用 qrcode.js 渲染 code_url；页面含套餐名/金额/配额/二维码/订单号；禁止显示用户邮箱）
   ↓
④ 轮询支付状态:
   GET {SMARTLIB_GATEWAY_URL}/api/pay/status?out_trade_no=<out_trade_no>
   （3s 轮询，最多 20 次≈60s；超时提示重新发起）
   支付成功返回 {"status":"paid","auto_recharged":true,...} → 对话通知"✅ 支付成功，已到账 N 次" + 自动重试上次中断的检索
```

### 安全机制
- `out_trade_no` UNIQUE 防重复充值；二维码 5 分钟有效
- `/api/pay/status` 为公开端点（无需 Bearer），可直接轮询
- `SMARTLIB_GATEWAY_SECRET` 仅后端调用，不在对话中输出
- 生成的支付页面**禁止显示用户邮箱**

---

## 🔒 配额耗尽处理 / Quota Exhaustion

配额耗尽后，**暂停新的检索请求**，不再展示任何部分结果，并**自动弹出套餐选择卡片**（见上方💰章节），不再要求用户说「我要升级」。

| 状态 | 行为 |
|------|------|
| **配额充足** (>0) | 正常执行检索，完整展示所有结果（含详情查看、全文下载、智能排序） |
| **配额偏低** (≤10 且无付费余额) | 尾部轻提示 + 自动弹出套餐卡片（软引导） |
| **配额耗尽** (=0) | Gateway 返回 429，拒绝服务，**自动弹出套餐卡片**（硬引导）；企业 / 机构定制仍联系我们 |

配额耗尽时的引导格式：

```
⚠️ 您的 SmartLib 配额已用尽，已为您列出可用套餐：

① 体验卡 ¥9.9 — 1000 检索 + 20 下载 / 7天
② 个人版月 ¥39 — 1000 检索 + 50 下载 / 30天
③ 专业版月 ¥99 — 2000 检索 + 200 下载 / 30天
④ 单篇下载 ¥2.5 — 1 次下载
⑤ 下载包 ¥20 — 10 次下载 / 30天

回复数字选择，或说「升级 / 充值」重新唤起。
企业 / 机构批量定制、API 接入或私有化部署请联系：
📧 vipsmart@vipslib.com  ☎️ 023-63016015  🌐 https://www.vipslib.com/
```

**重要规则**：
- 配额耗尽后，所有检索请求一律拒绝，不展示任何结果
- 不再要求用户说「我要升级」——配额信号会自动唤起套餐卡片
- 企业 / 机构定制仍联系我们


## 输出规范 / Output Standards

**每次检索结果末尾必须展示配额状态：**

```
📊 本次消耗 3 次 | 剩余 82 次 (共 100 次/月)
```
或接近耗尽时：
```
⚠️ 剩余 3 次 (共 100 次/月)，已为你列出可用套餐（回复数字即可购买，或说「升级」唤起）
```

```
```

## 核心能力 / Core Capabilities

| 能力 / Capability | 说明 / Description |
|------|------|
| **中文期刊检索 / Chinese Journal Search** | 8000万篇授权中文期刊文献，支持全文下载 / 80M authorized Chinese journal articles with full-text download |
| **全球文献检索 / Global Literature Search** | 10亿篇中外文文献元数据（含中英文论文、专利、标准、学位论文等）/ 1B global literature metadata (papers, patents, standards, theses) |
| **文献详情 / Article Detail** | 查看摘要、DOI、基金资助、核心收录等完整信息 / View abstracts, DOI, funding, core journal indexing |
| **全文下载 / Full-text Download** | 授权中文期刊支持 PDF 全文下载 / PDF download for authorized Chinese journals |
| **原始来源链接 / Source Links** | 每篇文献提供多个原始数据库详情链接（覆盖300+数据库，如Scopus/WoS/EI/PubMed等），覆盖率100%，平均4.75个/篇，可直接验证文献真实性 / Multi-database source links for authenticity verification |
| **OA文献免费下载 / OA Free Download** | 十级多渠道自动探测OA文献PDF（ArXiv/Unpaywall/CORE/OpenAlex等），Gold/Hybrid/Bronze/Green OA免费获取，**不消耗SmartLib配额** / OA PDF auto-detection via 10 channels, no quota consumption |
| **智能关键词扩展 / Smart Keyword Expansion** | 联网检索中英文同义词/近义词，自动扩展检索词，提升召回率 / Web search for synonyms to expand search terms |
| **核心期刊优先排序 / Core Journal Priority** | 联网查询核心收录情况（SCI/EI/北大核心/CSSCI等），优先展示高水平文献 / Rank by core journal indexing (SCI/EI/CSSCI etc.) |
| **相关性智能排序 / Relevance Ranking** | 基于题名、关键词、摘要语义分析，对检索结果进行二次相关性排序 / Semantic relevance re-ranking |
| **少结果智能扩展 / Low-result Expansion** | 结果过少时自动推荐上位词、相关机构、学科分类号等多种扩展策略 / Auto-suggest broader terms and alternative strategies |

## 能力边界 / Capability Boundaries

### 支持的功能 / Supported

- 中文期刊论文检索、详情、全文下载（8000 万篇授权文献）
- 全球文献元数据检索（10 亿篇，含论文/专利/标准/学位论文等）
- 关键词智能扩展、核心期刊优先排序、少结果自动扩展
- 自然语言输入，无需学习检索语法

### 不支持的功能 / Not Supported

- **付费墙内英文文献全文下载**：通过 SmartLib API 4 查到的全球文献仅返回元数据。本技能已集成十级多渠道下载策略（ArXiv/Unpaywall/CORE/OpenAlex/Semantic Scholar/Crossref/DOI.org/Europe PMC/bioRxiv/medRxiv + CDP浏览器），可免费获取 OA 版本（Gold/Hybrid/Bronze/Green OA），**OA 下载不消耗 SmartLib 配额**。但付费墙内（closed access）文献无法获取全文
- **付费墙内文献**：不提供需单独购买的文献全文
- **批量导出**：不提供 EndNote/BibTeX 等格式的批量导出功能
- **文献查重/查新**：不具备论文查重或科技查新功能

### 使用限制 / Limitations

| 限制项 / Limit | 说明 / Description |
|------|------|
| **单次查询条数 / Per-query limit** | PageSize 20-1000，建议 ≤100 以保证速度 / Recommend ≤100 |
| **翻页上限 / Max pages** | 无硬限制，但建议不超过 50 页（共 1000 条）/ No hard limit, but ≤50 pages recommended |
| **请求频率 / Rate limit** | 有频率限制（未公开数值），触发 429 时自动等待重试 / Undisclosed limit; auto-retry on 429 |
| **Token 有效期 / Token TTL** | Access Token 30 秒，Refresh Token 2 小时。系统自动管理刷新 / Access Token 30s, Refresh Token 2h. Auto-managed. |
| **下载链接有效期 / Download URL TTL** | 约 10 分钟，过期需重新调用下载接口 / ~10min, re-call download API |
| **依赖 / Dependencies** | 完全依赖 SmartLib API 和网络连接，离线不可用 / Requires network + SmartLib API |

### 触发意图区分 / Trigger Intent Differentiation

| 用户表达 / User Expression | 系统行为 / System Behavior | 区分逻辑 / Rationale |
|------|------|------|
| "查论文"、"找文献"、"检索XX" / "Search XX papers" | **触发本 Skill**，精准检索，默认平衡策略 | 明确的检索意图 |
| "写文献综述"、"帮我写综述" / "Write a literature review" | **触发本 Skill**，切换为综述模式：宽检索策略、去重合并、按主题聚类 | 综述需更全的覆盖范围和聚类分析 |
| "帮我写论文开头/引言" / "Write paper intro, need citations" | **触发本 Skill**，窄检索策略：找 3-5 篇最相关引用，核心期刊优先 | 写作引用需要精准而非全面 |
| "这段论述有文献支撑吗"、"找几篇引用" / "Find supporting citations" | **触发本 Skill**，窄检索 + 核心期刊优先，提供可引用的高质量文献 | 文献支撑场景需要高可信度来源 |
| "这篇论文是真的吗"、"核查引用" / "Verify this citation" | **不触发本 Skill**，应转至 smartlib-citation-checker | 引用核查是独立能力 |

<!-- 本技能正文已按华为小艺平台 5000 token 上限精简，完整版见来源仓库 -->

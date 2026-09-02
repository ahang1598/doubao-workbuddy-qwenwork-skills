---
name: linkfox-plugin-web-data-crawler
description: 采集 Amazon/SHEIN 商品详情页数据（标题、价格、图片、评分、五点、规格等）。用户说 采集/抓取/爬取 商品链接/ASIN、"帮我查下这个 ASIN"、给了 ASIN（B 开头 10 位字母数字）或 amazon.*/dp/ 或 shein.com 商品链接、要获取图片/五点/A+/评论等页面才能拿到的字段时触发。即使用户没提"采集"，给了 ASIN 或商品链接就应触发。Also: "crawl/scrape" product URLs, bare ASINs, "get product details/images/reviews" for amazon/sheim — trigger even without "crawl"/"scrape". 分流：后端接口能直接查的（类目树/搜索/关键词分析）走 linkfox-amazon-product-detail；列表页/搜索页不走本 skill。
---

# 跨境电商商品详情页采集

## Overview

通过 `startCrawlTask` 接口把采集工作流投递给浏览器插件执行。覆盖 Amazon（全站点）和 SHEIN。
**CLI 封装了 URL 构造、OPEN_TAB 剥离、品类字段注入、图片后处理**——AI 只需调对命令，不需要手动拼接管道或逐步骤操作 workflow JSON。

**核心规则**：
- 修复失败的 workflow 时，🔴 **绝不 Write/Edit `sites/` 目录下任何文件**——修复在内存中，通过临时文件 + `send` 子命令重试
- 下游执行器**不支持并发**——同一时间只能有一个 workflow 运行，必须等待当前任务完整结束
- Workflow 步骤内置 `onFailure` 自愈机制（selector 过期时自动 FIND_SELECTOR 重试），AI 只在自愈也失败时介入

## When to Use

触发场景（匹配任一）：
- 用户给 Amazon ASIN（`B` 开头 10 位字母数字，如 `B0C5J7X5N5`）
- 用户给 `amazon.com/dp/` 或 `amazon.com/gp/product/` URL
- 用户给 `shein.com/` URL
- 用户要"采集/爬取/抓取 Amazon/Shein 商品详情"，"获取商品详情/价格/评分"
- 用户提供商品标识符未说明平台（ASIN 模式明显 → 默认 Amazon）

**不适用**：
- 后端接口能直接返回的数据（走对应接口 skill）
- 列表页/搜索页（本 skill 仅覆盖详情页）
- 需要登录/付费墙后的内容

## ⚠️ Critical Rules

| # | Rule | Why |
|---|---|---|
| 🔴 1 | **绝不 Write/Edit `sites/` 目录** | 修复在内存中，通过临时文件 + `send` 重试 |
| 🔴 2 | **重试前剥离 OPEN_TAB** | 重复导航 = 验证码第一触发源 |
| 🔴 3 | **严格串行** | 下游不支持并发 |
| 🔴 4 | **修复 selector 时追加而非替换** | `"old"` → `["new", "old"]`，旧选择器在其他页面仍有效 |
| 🟡 5 | **Probe → Scrape 必须 `--reuse-tab`** | 复用 tab 避免重复导航 |
| 🟡 6 | **终端 workflow 以 CLOSE_TAB 收尾** | 否则 tab 泄漏 |
| 🟡 7 | **先读站点 README 再执行采集** | frontmatter `known_gotchas` 包含该站点特有的坑 |

## Execution Flow

| Step | Action | CLI / Reference |
|---|---|---|
| 0 | 健康检查 | `python scripts/run_crawl.py health` |
| 1 | 匹配站点 | 读 `sites/INDEX.md` → 确定 site key 和 `--site` 参数 |
| 2 | 读站点 README | `sites/<site>/README.md`（优先消费 frontmatter 中的 `known_gotchas`） |
| 3 | 品类探测 | （条件执行）`python scripts/run_crawl.py probe --site <key> --url <url>` |
| 4 | 采集 | `python scripts/run_crawl.py scrape --site <key> --url <url> [--reuse-tab] [--category <cat>]` |
| → SUCCESS | 展示结果 | 图片已自动后处理（CLI 根据 README frontmatter `post_process` 自动执行） |
| → FAILED | 进入 Part 2 | 读 `references/part2-repair.md` |
| → TIMEOUT | 重试 | 最多 3 次，退避 1s→2s→4s |
| → 生成报告 | 进入 Part 3 | 读 `references/part3-report.md`，AI 分析数据 + 脚本生成 HTML |

### Step 1 — 站点匹配

读 `sites/INDEX.md`，对照 Site Map 表匹配用户输入：

1. **URL 域名** → 匹配 Domain 列，从 Locale(s) 列确定 `--site` 参数（如 `amazon.co.jp` → `amazon-jp`）
2. **产品 ID 匹配站点 README frontmatter 的 `product_id_pattern`** → 确定 site key。Amazon ASIN（`B` + 9 位字母数字）是典型例子，默认 `--site amazon-us`
3. **用户明确说出站点名** → 匹配 Display Name 列
4. **均不匹配** → **追问用户**

`--site` 合法值见 INDEX.md Site Map 表 + 站点 README 的 Locale 参考表。

### Step 3 — 品类探测

**前提**：`sites/<site>/_category-probe.json` 存在。不存在则跳过，直接执行 Step 4。

**跳过探针**（满足任一）：
- 用户明确轻量意图（"只要价格"、"多少钱"）
- 用户输入匹配站点 README 品类关键词表中的关键词 → 直接确定 `--category <key>`

**标准流程**：
1. 检查用户输入是否命中 README 中的品类关键词 → 命中则推断 categoryKey，跳过探针
2. `python scripts/run_crawl.py probe --site <key> --url <url>`
3. 对照 `sites/<site>/categories/INDEX.md` 解析 `breadcrumb` + `detail_keys`，匹配品类
4. 不命中 → 默认 generic（仅用 base-full，不注入品类字段）

### Step 4 — 采集

```bash
# 标准采集（无品类、无探针）
python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0XXX

# 品类采集（probe 之后，复用 tab）
python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0XXX --reuse-tab --category books

# 用户指定品类（跳过 probe）
python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0XXX --category electronics
```

**轻量意图**（用户只要部分字段）：CLI 当前仅内置 `--scenario full`。需要裁剪时，AI 从 `base-full.json` 读取步骤，手动构造 `OPEN_TAB + WAIT + 目标 EXTRACT + CLOSE_TAB`，通过 `send` 子命令发送：

```bash
python scripts/run_crawl.py send --site amazon-us --file /tmp/lightweight.json --url <url>
```

### 评论采集

```bash
python scripts/run_crawl.py reviews --site amazon-us --url https://www.amazon.com/product-reviews/B0XXX/
```

各站点的评论采集差异（如 Shein 评论在商品页底部懒加载）见对应 README 的 `known_gotchas`。

## Part 2 — Failure Diagnosis

失败时读 `references/part2-repair.md`。三层递进：

| Layer | Trigger | Action |
|---|---|---|
| 1 | 自动（AI 无感知） | onFailure 自愈：FIND_SELECTOR → 自动重试该 step |
| 2 | AI 收到 FAILED | 读 errorMsg：captcha/403/登录/客户端不在线 → **STOP**，报告用户 |
| 3 | selector 过期 | GET_PAGE_INFO → GET_DOM → VERIFY_SELECTOR → 内存修复 → `send` 重试 |

最多 4 次总尝试（含原始执行）。全失败 → 输出诊断摘要。

> ⚠️ **修复重试与后处理**：`send` 子命令不执行图片后处理（`scrape` 才做）。修复验证通过后，如果结果是完整商品详情（非轻量意图），建议用 `scrape` 重跑一次获得含后处理的完整结果。
>
> ⚠️ **修复后不要传 `--category`**：如果修复后的 workflow 已自包含全部步骤（包括修复后的品类字段），不要传 `--category` 参数——否则 CLI 会从 `categories/fields/` 注入原始未修复的品类字段，覆盖修复后的步骤。`--category` 仅用于原始 workflow 的品类注入。

## 输出

采集结果自动落盘到会话目录：

```
<linkfox_root>/<YYYY-MM-DD>/<session>/data/linkfox-plugin-web-data-crawler-<ts>.json
```

stdout 同步打印 `[Saved] <路径>` 和完整结果，供 AI 当场消费。

**生成报告**：采集完成后需生成产品情报 HTML 报告，进入 Part 3（`references/part3-report.md`）：

1. AI 分析原始采集 JSON → 产出标准化 `clean_data.json`
2. 调用 `python scripts/generate_report.py <clean_data.json> <output.html>`

脚本是纯模板注入引擎，不做数据解析。模板位于 `templates/amazon-report.html`。

## 缺参追问

分类型分轮，**禁止混在一句话**：

- **开放输入**（商品 URL、ASIN）→ 自然语言直接问，如「请提供要采集的商品详情页 URL」
- **仅 ASIN 无 URL**：默认 `--site amazon-us`，**不追问**。仅当上下文有明显线索指向非 US 站（如用户之前聊的是日本站商品）时才用 `AskUserQuestion` 确认站点（≤4 个选项，不含"跳过"）
- **URL 已含域名** → 从域名推断 `--site` 参数（对照 `sites/INDEX.md` 的 Domain 列），不追问
- **`LINKFOX_AGENT_API_KEY` 未配**：提示用户前往 https://skill.linkfox.com/linkfoxskills/guide.htm 申请并设置环境变量后重试。`LINKFOX_TOOL_GATEWAY` 未配用默认值，不问

## 失败处理

- `TIMEOUT` / 网络异常 / 5xx：最多 3 次重试，退避 1s→2s→4s
- `FAILED` + "客户端不在线"：不重试，提示用户打开插件
- `FAILED` + 其它：进入 Part 2 诊断修复

## 新增站点

1. 创建 `sites/<site-key>/base-full.json`（站点特有选择器）
2. 创建 `sites/<site-key>/README.md`（含 frontmatter 元数据 + 品类关键词表）
3. 可选创建 `_category-probe.json` + `categories/`
4. 更新 `sites/INDEX.md` 添加一行
5. 有必要时添加 `scripts/<site-key>_image_post.py`（CLI 自动发现并执行）

**扩展现有站点的 locale**：更新 `run_crawl.py` 的 `AMAZON_SITE_DOMAINS` + `sites/INDEX.md` Locale(s) 列。

## 限制

- 仅覆盖商品**详情页**
- SHEIN 选择器需定期校准
- 仅支持 Amazon ASIN→URL 自动拼接
- 仅走同步 `startCrawlTask`

## 反馈

按 `references/api.md` 末尾 Feedback API 上报。

# PDF Runtime · 附录 02：LOGO 缺失时的主 Agent 直连下载兜底

> **触发阅读条件**：`build_by_bank_vis.py --auto-download` 因银行官网反爬失败、`quality_report.grade=F`、需要补下载 LOGO 时。

## 1. 背景与路径选择

当 `build_by_bank_vis.py --auto-download` 因银行官网反爬（常见：`UNSAFE_LEGACY_RENEGOTIATION_DISABLED`、JS 渲染 SPA、HTTP 465 反爬）失败时，**首选由主 Agent 自己用 web_fetch / web_search / curl 定位并下载 LOGO**，再让 Python 层（`llm_subagent_logo_fetcher.py`）做严格核验和落盘。

> **为什么不首选派 subagent 代下载？**
>
> 2026-04-29 实测：派出的 code-explorer / 默认 subagent 常因权限或工具限制无法完成 WebFetch 下载（返回 `not_found` 或 HTML 而非二进制）。主 Agent 自身具备 `web_fetch` / 终端 curl 能力，直接下载更可靠。subagent 模式保留作为降级备用。

## 2. 路径 A：主 Agent 直连下载（首选）

```
主 Agent
  │  [1] 发现 by_bank/<bank>/logo/logo.png 缺失（或 quality_report.grade=F）
  │
  ├─ [2] 主 Agent 用自己的 web_fetch / WebSearch 在该行官网定位 LOGO 直链
  │       来源限定：
  │         - 银行官网首页 / header 里的 <img>、<link rel="icon">
  │         - 品牌中心 / 媒体资源 / 投资者关系页
  │         - cninfo 已收录的官方附件
  │       禁止：搜索引擎图片首图、AI 生成图、第三方图标站二改
  │
  ├─ [3a] 若拿到 LOGO 直链 URL，直接调 Python 层下载+核验：
  │        python3 _vendor/pdf_report_builder_runtime/scripts/llm_subagent_logo_fetcher.py \
  │            ingest-url <bank> <url> \
  │            --referer-url <page_url> --comment "..."
  │
  ├─ [3b] 若主 Agent 已经把字节拿到本地（例如 web_fetch 返回二进制 → 落到 /tmp/），
  │        走 ingest（本地路径）或 ingest-stdin（pipe 字节流）：
  │        python3 ... ingest <bank> /tmp/xxx.png --source-url <url> --comment "..."
  │        cat /tmp/xxx.svg | python3 ... ingest-stdin <bank> --suffix .svg --source-url <url>
  │
  └─ [4] Python 层自动完成：
          a. 根据 magic bytes 识别 PNG/JPG/SVG（ingest-url / ingest-stdin 内置）
          b. 抠白底 → 透明 PNG（阈值 >240 设为 alpha=0）
          c. 裁剪透明边 → 升采样 LANCZOS 到 height ≥ 200px
          d. 生成 logo_base64.txt
          e. 写 logo_source.txt（download_mode=main_agent_direct + 银行识别词）
          f. 写 brand.yaml::subagent_provenance（含 source_url / sha256 / ingested_at）
          g. 跑 asset_quality.audit() 全 10 项核验
          h. grade ∈ {A, B} → 成功；C → 警告；F → 重试或请求人工
```

## 3. 路径 B：LLM Subagent 代下载（备用）

当主 Agent 由于环境限制无法直接下载（如沙箱禁用 web_fetch）时，可退化到 subagent 模式：

```bash
# 第 1 步：生成标准采集 prompt
python3 _vendor/pdf_report_builder_runtime/scripts/llm_subagent_logo_fetcher.py \
    prompt <bank> > /tmp/logo_fetch_prompt.md

# 第 2 步：主 Agent 用 Task 派出 subagent，把 prompt 内容传进去

# 第 3 步：subagent 把 LOGO 下载到 /tmp/，stdout 末尾返回 JSON
#         {"status":"ok","local_path":"/tmp/...","source_url":"...","referer_url":"...","comment":"..."}

# 第 4 步：主 Agent 用 ingest 核验落盘
python3 ... ingest <bank> <local_path> --source-url <...> --referer-url <...> --comment <...>

# 第 5 步：audit
python3 _vendor/pdf_report_builder_runtime/scripts/build_by_bank_vis.py --bank <bank> --audit-only
```

## 4. 强制硬规则（A/B 路径通用）

| 约束 | 说明 |
|---|---|
| 下载与核验分离 | 无论 A/B 路径，**核验与落盘必须走** `ingest_from_url` / `ingest_from_bytes` / `ingest_and_verify`；禁止主 Agent / subagent 自己写 `report_assets/by_bank/` |
| 核验不可绕过 | 即便来源是"官方 URL"，也必须通过 10 项 audit（透明度 / 尺寸 / 宽高比 / 身份词 / 色相 ΔE / ...） |
| 身份词必须命中 | `logo_source.txt` 中必须出现该行识别词（短名 / 全称 / 别名 / 股票代码）中任一；否则 `audit_identity` critical fail |
| 色相交叉校验 | LOGO 主色 ΔE 与 `banks.yaml::primary_official` 相差 ≥ 25 时，自动用官方色修正 palette.primary（LOGO 保留，palette 以官方色为准） |
| 审计可溯源 | `brand.yaml::subagent_provenance` 必含 `download_mode / source_url / referer_url / sha256 / ingested_at` |
| 禁止自行绘制 | **禁止让任何 Agent 用 AI 生图/绘图工具**生成 LOGO。无论失败多少次，宁可人工兜底也不生成假 LOGO |

## 5. LOGO 格式与质量标准（放宽 · 2026-04-29）

**不强制 SVG**。实操中大量银行只提供 PNG / JPG（官网 header img、年报封面抽取等），SVG 是"加分项"不是硬门槛。格式优先级如下：

| 格式 | 优先级 | 说明 |
|------|--------|------|
| **PNG** | ★★★ 首选 | 直接处理；有 alpha 最好，白底 PNG 脚本会自动抠白 |
| **JPG / JPEG** | ★★★ 首选 | 视为白底 PNG 处理；同样会自动抠白到透明 |
| **SVG** | ★★ 可选 | 仅在 macOS `brew install librsvg`（提供 `rsvg-convert`）或 `pip install cairosvg` + `libcairo` 时接受；否则 `ingest_from_url` 会抛 `SVGConverterUnavailable` 并提示主 Agent 换一个 PNG/JPG 直链 |

**尺寸要求**：高度 ≥ 200px（不足会 LANCZOS 升采样但质量下降）；宽高比 1.3 ~ 6.5。

**典型可用直链来源**（一般都是 PNG / JPG）：
- 银行官网 header 里的 `<img src="...">`（浏览器开发者工具一看即得）
- 维基百科 / 百度百科条目 infobox 图片（File:<BankName>_logo.svg/png）
- 银行年报封面（pdftocairo -f 1 -l 1 抽取首页 → 裁剪 logo 区）
- 腾讯 / 新浪财经股票页的公司 logo

## 6. 示例（光大银行，路径 A 首选）

```bash
# 主 Agent 先用 web_fetch / 浏览器开发者工具定位到官网 LOGO 直链（PNG 首选），然后：
python3 _vendor/pdf_report_builder_runtime/scripts/llm_subagent_logo_fetcher.py \
    ingest-url 光大 \
    "https://upload.wikimedia.org/wikipedia/zh/e/ec/China_Everbright_Bank_logo.png" \
    --referer-url "https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%9B%BD%E5%85%89%E5%A4%A7%E9%93%B6%E8%A1%8C" \
    --comment "zh.wikipedia infobox 官方 logo；含中英文行名；829x120"

# 验收
python3 _vendor/pdf_report_builder_runtime/scripts/build_by_bank_vis.py \
    --bank 光大 --audit-only
# 期望 grade=A 或 B
```

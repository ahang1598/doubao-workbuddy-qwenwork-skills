# SmartLib 全链路检索下载管线优化指南 / Pipeline Optimization Guide

> 中文 / Chinese | English follows each section

本文件记录 SmartLib 文献检索技能中"检索→详情→下载"全链路的架构设计、性能优化策略和实战基准数据。面向技能调用者（AI Agent）和开发者，提供最优执行路径参考。

> This document covers the architecture, optimization strategies, and real-world benchmarks for the SmartLib literature search → detail → download pipeline. Designed for skill invokers (AI Agents) and developers as the authoritative execution reference.

---

## 1. 管线架构 / Pipeline Architecture

```
用户请求 / User Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  PHASE 1: 并行检索 / Parallel Search                 │
│  ├─ CN: API 1 (中文期刊) ─── 独立 Token，并行发起   │
│  └─ EN: API 4 (全球文献) ─── 独立 Token，并行发起   │
│  预计耗时: 1-3s (5 并发检索)                         │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│  PHASE 2: 批量获取详情 / Batch Fetch Details         │
│  ├─ CN: 无需此步（API 3 直接用 Identifier 下载）     │
│  └─ EN: API 5 (文章详情) ─── 8 并发获取 DOI + 元数据 │
│  预计耗时: 0.3-2s (50 篇以内)                        │
│  关键优化: Token 缓存复用，无需每次重新认证           │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│  PHASE 3: 并行下载 / Parallel Download               │
│  ├─ CN: API 3 (GetArticleFile) ─── 10 并发下载       │
│  └─ EN: 多渠决策树 ─── 10 并发，每篇独立路由         │
│       ├─ ArXiv (最快)                                │
│       ├─ Unpaywall OA 探测 (最全面)                   │
│       ├─ SpringerOpen / PLOS / PMC (出版商专用)       │
│       └─ DOI 重定向 (兜底)                            │
│  预计耗时: 5-15s (10 篇) / 20-40s (50 篇)            │
└──────────────────┬──────────────────────────────────┘
                   ▼
              📊 汇总报告 / Summary Report
```

**设计原则 / Design Principles:**
- **分阶段并行 / Phased Parallelism**: 每阶段内部并行，阶段间串行（依赖数据传递）
- **独立无锁 / Lock-Free**: 每篇论文的下载互不依赖，无共享状态
- **失败隔离 / Failure Isolation**: 单篇失败不影响其他论文
- **Gateway 代理 / Gateway Proxy**: 所有 API 调用通过 Gateway /consume → /search 代理，Token 由 Gateway 管理

---

## 2. 核心优化技术 / Core Optimizations

### 2.1 Gateway 统一管理 Token / Gateway Token Management

**问题 / Problem**: 每次 API 调用前走 OAuth 两步认证 (code→token)，耗时 ~0.8s。50 篇论文=50 次认证=40s 浪费。

**优化 / Optimization**: SmartLib OAuth Token 由 Gateway 全权管理，技能无需获取或缓存 Token。

**架构 / Architecture:**
```
技能 (Skill) → Gateway (/consume → /search) → SmartLib API
                    ↑
              Token 缓存 + 自动刷新 + 分布式同步
```

- Gateway 维护 OAuth 凭证（APPID + APPSECRET）
- 技能通过 config.json 中的 GATEWAY_SECRET 调用 Gateway API
- 技能**无需持有** APPID/APPSECRET
- Gateway 自动处理 Token 刷新与缓存（含跨实例分布式同步）

### 2.2 提前终止 / Early Termination

**问题 / Problem**: 传统策略是对所有渠道逐一尝试，但 closed-access 论文注定失败。

**优化 / Optimization**: Unpaywall 探测后立即判断：

| OA 状态 | 策略 | 原因 |
|------|------|------|
| `gold` | 全渠道重试 | 几乎必定能下 |
| `hybrid` | 先试 Unpaywall PDF URL | 大概率能下 |
| `green` | 试 ArXiv + Unpaywall + 机构库 | 作者自存档版本 |
| `bronze` | 尝试一次后 curl 兜底 | ⚠️ 大概率被防盗链拦截 |
| `closed` | **立即终止**，不浪费后续尝试 | 100% 付费墙内 |

**效果 / Effect**: closed-access 论文从 ~8s (7个渠道轮询) 降至 ~1s (仅一次 Unpaywall 查询)。

### 2.3 智能渠道路由 / Publisher-Aware Routing

**问题 / Problem**: 不同出版商的 PDF 获取方式差异大，统一策略效率低。

**优化 / Optimization**: 根据出版商名称路由到最优渠道：

```python
PUBLISHER_ROUTES = {
    "springer":  ["springer", "unpaywall", "arxiv"],   # SpringerOpen 直链最快
    "elsevier":  ["unpaywall", "arxiv", "green"],       # Elsevier 大概率付费墙
    "mdpi":      ["unpaywall", "direct"],                # MDPI 几乎全 OA
    "frontiers": ["unpaywall", "direct"],                # Frontiers 全 OA
    "plos":      ["plos", "unpaywall"],                  # PLOS 专用 API
    "biomed":    ["springer", "unpaywall", "pmc"],       # BMC = Springer 子品牌
}
```

**效果 / Effect**: SpringerOpen/BMC 论文直接从 `link.springer.com/content/pdf/` 拿 PDF，跳过 Unpaywall，节省 1-2s/篇。

### 2.4 HTTP 连接复用 / Connection Reuse

**问题 / Problem**: 每次 `urllib.request.urlopen()` 创建新 TCP 连接 + TLS 握手，开销 ~200ms。

**优化 / Optimization**: 
- 使用 `build_opener()` + `Connection: keep-alive` header
- 同 host 的连续请求复用底层 TCP 连接

**效果 / Effect**: 50 篇同 host 下载可节省 ~5s。

### 2.5 curl 兜底 / Curl Fallback for Problematic URLs

**问题 / Problem**: Python `urllib` 对某些服务器（OUP Bronze OA）返回 `IncompleteRead` 或截断 PDF。

**优化 / Optimization**: 下载失败时自动切换为 `curl` subprocess 重试。

```python
# curl 对 HTTP chunked encoding 和 unstable connections 处理更鲁棒
result = subprocess.run(["curl", "-sL", "--max-time", "25", "-o", "-", url], ...)
```

**效果 / Effect**: 将 Bronze OA 论文成功率从 ~20% 提升至 ~60%。

---

## 3. 下载渠道路由决策树 / Channel Routing Decision Tree

```
论文有 Identifier + 来源 = API 1 (中文期刊)?
  ├─ YES → API 3 (GetArticleFile) → 获取 PDF URL → 下载
  │        成功率: >95%  |  耗时: ~1s/篇
  │
  └─ NO (全球文献)
       ├─ 标题含 arXiv ID? → https://arxiv.org/pdf/{id}
       │   成功率: >99%  |  耗时: ~2s/篇
       │
       ├─ 获取 DOI (API 5) → Unpaywall 探测
       │   ├─ is_oa = false / oa_status = "closed"
       │   │   → ⛔ 立即终止，标记 "paywall_closed"
       │   │
       │   ├─ oa_status = "gold" → 全渠道并发尝试
       │   │   1. Unpaywall best_oa_location.url_for_pdf
       │   │   2. DOI redirect (Accept: application/pdf)
       │   │   3. 出版商专用路由 (SpringerOpen/PLOS/MDPI)
       │   │   成功率: >90%
       │   │
       │   ├─ oa_status = "hybrid" → Unpaywall PDF URL 优先
       │   │   成功率: ~80%
       │   │
       │   ├─ oa_status = "green" → ArXiv + Unpaywall + DOI redirect
       │   │   成功率: >85%
       │   │
       │   └─ oa_status = "bronze" → ⚠️ 高风险
       │       1. Unpaywall PDF URL (常规)
       │       2. curl 兜底 (绕过 urllib 限制)
       │       3. 出版商专用路由
       │       成功率: ~40-60% (出版商防盗链)
       │
       └─ 无 DOI → 标记 "no_doi"，仅展示元数据
```

---

## 4. 性能基准 / Performance Benchmarks

### 4.1 实测数据 / Real-world Test Results

测试环境 / Test Environment: Windows 10, Python 3.14, 中国网络环境 (GFW)

#### 完整 5 领域多渠测试 (multi_channel_test.py) / 5-Field Multi-Channel Test

| 领域 / Field | 检索 / Searched | 下载成功 / Downloaded | 成功率 / Rate | 主要渠道 / Dominant Channel |
|------|:--:|:--:|:--:|------|
| 化学催化 / Chemistry Catalysis | 10 | **10** | 100% | Unpaywall Gold OA (MDPI/Frontiers) |
| AI/深度学习 / AI Deep Learning | 10 | **10** | 100% | ArXiv + Unpaywall Gold |
| 生物技术 CRISPR / Biotech CRISPR | 10 | 2 | 20% | Unpaywall Gold OA |
| 环境/气候 / Environment Climate | 10 | 3 | 30% | Unpaywall Gold + Green OA |
| 制药/mRNA / Pharma mRNA | 10 | **0** | 0% | 全部付费墙 (Elsevier/Nature/Wiley) |

**总计 / Total: 25/50 (50%)**

#### 优化管线 Demo 测试 / Optimized Pipeline Demo

| 指标 / Metric | 值 / Value |
|------|------|
| 检索 / Search | 5 CN + 5 EN in 1.3s |
| 详情 / Details | 5 EN in 0.3s (Token 缓存) |
| CN 下载 / CN Download | 5 in 4.4s (0.88s/篇) |
| EN 下载 / EN Download | 5 in 5.7s (1.14s/篇) |
| **总计 / Total** | **10 in 11.7s (1.17s/篇)** |
| 成功率 / Success Rate | 10/10 (100%) |

### 4.2 速度对比 / Speed Comparison

| 阶段 / Phase | 优化前 / Before | 优化后 / After | 提升 / Improvement |
|------|:--:|:--:|:--:|
| Token 获取 (50篇) | ~40s (每次重新认证) | ~2s (缓存复用) | **20x** |
| EN 详情获取 (50篇) | ~40s (串行) | ~2s (8并发+Token复用) | **20x** |
| CN 下载 (10篇) | ~30s (串行) | ~8s (10并发) | **3.75x** |
| EN 下载 (10篇) | ~60s (全渠道串行轮询) | ~12s (路由+提前终止) | **5x** |
| closed 论文判定 | ~8s (7渠道失败) | ~1s (立刻终止) | **8x** |

### 4.3 渠道贡献分析 / Channel Contribution Analysis

基于 50 篇 5 领域实测 + 10 篇优化管线测试 = 60 篇总样本:

| 渠道 / Channel | 成功数 / Success | 占比 / Share | 平均耗时 / Avg Time |
|------|:--:|:--:|:--:|
| API 3 (中文期刊) | 5 | 14% | ~0.9s |
| ArXiv | 5 | 14% | ~2s |
| Unpaywall Gold OA | 22 | 60% | ~3s |
| Unpaywall Hybrid OA | 1 | 3% | ~4s |
| Unpaywall Green OA | 2 | 5% | ~5s |
| SpringerOpen Direct | 1 | 3% | ~2s |

---

## 5. 使用指南 / Usage Guide

### 5.1 快速启动 / Quick Start

```bash
# Demo 模式: 1 个 CN + 1 个 EN 检索，各 5 篇
python optimized_pipeline.py --preset demo --pagesize 5

# 完整测试: 5 个领域 EN 检索，各 10 篇
python optimized_pipeline.py --preset test --pagesize 10

# 自定义检索 / Custom Search
python optimized_pipeline.py \
  --cn "深度学习::K=深度学习 AND TY=3" \
  --en "CRISPR::(K=CRISPR OR K=gene editing) AND TY=3" \
  --pagesize 10 \
  --out ./my_downloads
```

### 5.2 编程调用 / Programmatic Usage

```python
from optimized_pipeline import PipelineOrchestrator

orch = PipelineOrchestrator(out_dir="./papers")

result = orch.run(
    cn_queries=[{"name": "AI_CN", "rule": "K=人工智能 AND TY=3"}],
    en_queries=[{"name": "LLM_EN", "rule": "(K=transformer) AND (K=large language model)"}],
    page_size=10
)

print(f"Downloaded: {result['totals']['downloaded']}")
print(f"Time: {result['timing']['total']}s")
print(f"Channels: {result['stats']}")
```

### 5.3 AI Agent 调用建议 / Agent Invocation Tips

当 AI 助手调用本技能进行文献下载时，建议遵循以下执行路径：

1. **检索阶段**: 中文用 API 1，英文用 API 4，并行发起（同一批 Token）
2. **详情阶段**: 仅对 EN 文献调 API 5 获取 DOI（CN 可直接下载）
3. **下载阶段**: CN 和 EN 并行下载；EN 内部 10 并发
4. **失败处理**: closed-access 标记后直接跳过，bronze OA 用 curl 兜底

**关键 / Critical**: 绝对不要逐篇串行下载 N 篇论文！必须并行。

---

## 6. 排障指南 / Troubleshooting

| 现象 / Symptom | 原因 / Cause | 解决 / Solution |
|------|------|------|
| 所有 EN 论文下载失败 | Token 未正确缓存 | 检查 `TokenManager._expires_at` 是否正确设置 |
| Unpaywall 返回空 | 邮箱未提供或格式错误 | 确认 `email=` 参数正确 |
| 下载的 PDF 无法打开 (几 KB) | 服务器返回 HTML 错误页而非 PDF | 开启 curl 兜底；检查 `%PDF` magic bytes 验证 |
| Bronze OA 全部 403 | 出版商防盗链 (OUP/IEEE) | 启用 curl 兜底；长期方案：部署 Chromium CDP |
| 中文期刊 PDF URL 过期 | URL 有效期 ~10min | 重新调用 API 3 获取新 URL |
| `failed_no_doi` 比例高 | API 5 返回的元数据不含 DOI | 该论文确实无 DOI，建议用户通过标题在 Google Scholar 手动搜索 |

---

## 7. 依赖 / Dependencies

- Python 3.8+
- `urllib` (标准库)
- `curl` (系统工具，用于 PDF 兜底下载)
- SmartLib Gateway (腾讯云 SCF，管理 OAuth 凭证与 Token 缓存)
- Unpaywall API (免费，需提供邮箱)

---

## 8. 版本 / Version

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-05-27 | 初始发布。基于 5 领域 50 篇多渠测试 + 优化管线 Demo 10 篇实战数据。 |

# MCP 工具调用契约

本文档定义 7 个 LDH MCP 工具的输入参数、输出结构和调用约束。

## 1. ldh_discover_countries

**用途**：列出所有可用国家及其文档数和来源数（发现层级 1 — 数据集）。

**参数**：无

**输出**：

```json
{
  "status": "ok",
  "countries": [
    {
      "country": "EU",
      "document_count": 12345,
      "source_count": 8
    }
  ]
}
```

**调用时机**：会话首次遇到外国法/跨境问题时调用一次，缓存结果。

---

## 2. ldh_discover_sources

**用途**：列出某国家的所有数据源（发现层级 2 — 数据集）。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `country` | string | 是 | LDH 规范国家代码，如 `EU`、`UK`、`US` |

**输出**：

```json
{
  "status": "ok",
  "country": "EU",
  "sources": [
    {
      "source_id": "EU/CURIA",
      "namespace": "case_law",
      "court": "CJEU",
      "court_tier": 1,
      "date_range": { "start": "1952-01-01", "end": null },
      "document_count": 5000
    }
  ]
}
```

**校验规则**：
- `country` 必须在 `ldh_discover_countries` 返回的目录中。
- `source_id` 必须完整匹配，不做模糊猜测。

---

## 3. ldh_get_filters

**用途**：返回某来源内的可用筛选值（发现层级 3 — 筛选值）。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source` | string | 是 | Source ID，如 `EU/CURIA` |
| `namespace` | string | 是 | `case_law` / `legislation` / `doctrine` |

**输出**：

```json
{
  "status": "ok",
  "source": "EU/CURIA",
  "namespace": "case_law",
  "filters": {
    "courts": ["CJEU", "General Court"],
    "court_tiers": [1, 2],
    "jurisdictions": ["..."],
    "judgment_types": ["judgment", "order", "opinion"],
    "languages": ["en", "fr", "de", "..."],
    "date_range": { "start": "1952-01-01", "end": "2026-08-03" }
  }
}
```

**校验规则**：
- `source` 必须在 `ldh_discover_sources` 返回的目录中。
- 过滤器不可用或没有请求值时，不得静默透传未经确认的过滤值给 `ldh_search`。

---

## 4. ldh_search

**用途**：在 `case_law`、`legislation` 或 `doctrine` 中进行语义 + 关键词混合检索 — 主要研究工具。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | 是 | 核心法律术语 + 用户主题 + 地区词 |
| `country` | string | 是 | LDH 规范代码，仅一个 |
| `namespace` | string | 是 | `case_law` / `legislation` / `doctrine` |
| `source` | string | 否 | Source ID，已验证时才传 |
| `court` | string | 否 | 先经 `ldh_get_filters` 校验 |
| `court_tier` | int | 否 | `1` / `2` / `3`，先经校验 |
| `jurisdiction` | string | 否 | 先经校验 |
| `language` | string | 否 | 先经校验 |
| `date_start` | string | 否 | `YYYY-MM-DD` |
| `date_end` | string | 否 | `YYYY-MM-DD` |
| `top_k` | int | 否 | `1..100`，默认 `10` |
| `alpha` | float | 否 | `0..1`，语义/关键词权重，默认 `0.7` |
| `result_detail` | string | 否 | `snippet` / `summary_only` / `full_text` / `full_metadata` |

**输出**：

```json
{
  "status": "ok",
  "hits": [
    {
      "source": "EU/CURIA",
      "source_id": "62000CJ0123",
      "title": "Case C-123/00 ...",
      "date": "2000-06-08",
      "url": "https://...",
      "snippet": "...",
      "score": 0.95,
      "country": "EU"
    }
  ],
  "jurisdiction_audit": {
    "country_validated": true,
    "rejected_hits": [],
    "unverified_country_hit_count": 0
  }
}
```

**约束**：
- 一次只能传一个 `country`。多法域比较必须"一法域一请求"。
- 检索前校验：国家代码 → Source ID → 过滤值。
- 检索后反向审计：读取 `jurisdiction_audit`，被拒命中不得引用。
- `score` 不可跨法域比较。

---

## 5. ldh_get_document

**用途**：按 source + source_id 获取文档全文。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source` | string | 是 | Source ID |
| `source_id` | string | 是 | 文档 ID |

**输出**：

```json
{
  "status": "ok",
  "document": {
    "source": "EU/CURIA",
    "source_id": "62000CJ0123",
    "title": "Case C-123/00 ...",
    "date": "2000-06-08",
    "url": "https://...",
    "content": "<全文>",
    "metadata": { "court": "CJEU", "ecli": "ECLI:EU:C:2000:123", "..." : "..." }
  }
}
```

**约束**：只对准备引用的命中调用，不批量获取。

---

## 6. ldh_resolve_reference

**用途**：将松散引用（ECLI、CELEX、条款号、案号）解析为精确文档。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `reference` | string | 是 | 用户原始引用，如 `CELEX 32016R0679 Article 17` |
| `hint_country` | string | 否 | LDH 国家代码提示 |
| `hint_type` | string | 否 | `legislation` / `case_law` / `doctrine` |

**输出**：

```json
{
  "status": "ok",
  "resolved": {
    "source": "EU/EUR-Lex",
    "source_id": "32016R0679",
    "title": "Regulation (EU) 2016/679",
    "url": "https://..."
  }
}
```

**约束**：
- 只用于用户给出的松散法律引用，不接收 `ldh_search` 的命中 ID。
- `resolve` 返回空时改走同法域主题检索一次。

---

## 状态码通用契约

| status | 含义 | 动作 |
|---|---|---|
| `ok` | 调用成功且有可用数据 | 继续 |
| `empty` | 调用成功但无命中 | 改写查询一次，之后降级 |
| `bad_request` | 参数、代码、Source ID 或过滤值错误 | 修正一次 |
| `not_configured` | 当前环境未配置 LDH MCP 工具 | 使用预置源 |
| `auth_failed` | MCP 服务器鉴权失败 | 本会话停用 LDH，使用预置源 |
| `quota_exhausted` | 限流或额度不可用 | 不循环重试，使用预置源 |
| `unavailable` | MCP 服务不可用 | 使用预置源 |
| `error` | 未分类错误 | 使用预置源并记录限制 |

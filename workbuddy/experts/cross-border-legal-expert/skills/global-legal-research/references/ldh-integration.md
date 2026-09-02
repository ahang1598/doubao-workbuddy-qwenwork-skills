# LDH 精准检索集成

本文定义 LegalDataHunter（LDH）在本技能中的发现、校验、检索、全文锚定和降级契约。
LDH 是检索增强层，不因接入 LDH 而降低 `verification-engine.md` 的证据要求。

## 1. 不变量

1. 只能通过 `scripts/ldh_client.py` 调用，禁止自行拼接 HTTP 请求。
2. 自然语言国家名不得直接传入检索；先运行 `scripts/jurisdiction_resolver.py`。
3. 实时 `coverage` 和 `discover-sources` 是本次检索的权威目录；静态源文件只是离线快照。
4. `precise-search` 一次只能传一个 LDH 法域代码。
5. 主题检索与引用解析是两条链路：

```text
主题：resolve jurisdiction → discover → precise-search → get
引用：resolve reference → get
```

6. 搜索命中使用 `source + source_id` 获取全文；`resolve` 不接收搜索结果 ID。
7. 任何 LDH 命中都要按发布者和材料性质分类，不能把 LDH 等同于官方来源。

## 2. 命令能力

| 命令 | 用途 | 核心输出 |
|---|---|---|
| `health` | 会话级可用性探测 | `status`, `ldh_available` |
| `coverage` | 实时 LDH 国家/地区目录 | `coverage` |
| `discover-sources` | 指定法域的数据源目录 | `country`, `sources` |
| `discover-filters` | 指定源的法院、层级、语言、管辖过滤值 | `source`, `namespace`, `filters` |
| `precise-search` | 校验 country/source/filter 后执行单法域搜索并审计命中 | `hits`, `jurisdiction_audit` |
| `search` | 低层通用检索；仅在无需精准编排时使用 | `hits` |
| `resolve` | 把用户给出的松散引用解析成精确文档 | `resolved` |
| `get` | 按 `source + source_id` 获取全文和元数据 | `document` |

脚本始终输出单个 JSON 且退出码为 0。调用方只能依据 JSON 的 `status` 决策。

## 3. 法域解析

基本调用：

```bash
python scripts/jurisdiction_resolver.py --text "<用户完整问题>"
```

如已把 `coverage` 响应保存为临时 JSON，可用实时代码集合限制解析：

```bash
python scripts/jurisdiction_resolver.py \
  --text "<用户完整问题>" \
  --allowed-codes-file "<coverage.json>"
```

输出示意：

```json
{
  "status": "ok",
  "targets": [
    {
      "mention": "欧洲人权法院",
      "ldh_country": "CoE",
      "entity_level": "institution",
      "region": null,
      "query_terms": [],
      "source_hints": ["CoE/HUDOC"],
      "confidence": 1.0
    }
  ],
  "ambiguous_mentions": [],
  "requires_clarification": false
}
```

解析顺序为机构规则、次国家地区、特殊法域、国家名、显式代码、引用模式。规则优先级用于解决
“中国香港”同时命中中国和香港等重叠问题。两字母代码只在用户显式使用大写代码或整个输入就是
该代码时识别，防止把英文 `in`、`as` 等普通词误判为国家。

特殊约定：

| 自然语义 | LDH 目标 |
|---|---|
| 欧盟、CJEU、CURIA、CELEX | `EU` |
| 欧洲委员会、欧洲人权法院、HUDOC | `CoE` |
| 英国、GB、GBR | `UK` |
| 香港 / 澳门 / 台湾 | `HK` / `MO` / `TW` |
| California / 广东省等 | 父级 `US` / `CN` + `region/query_terms` |

`ambiguous` 和 `unresolved` 都是阻断态。只有用户澄清或精确引用模式能消解时才继续。

## 4. 实时发现和过滤校验

先验证代码和数据源：

```bash
python scripts/ldh_client.py coverage
python scripts/ldh_client.py discover-sources --country EU
```

Source ID 必须完整匹配实时目录，不做模糊猜测。映射器给出的 `source_hints` 只是候选：

- 候选存在：可传给 `precise-search --source`；
- 候选不存在：记录审计信息，去掉 source 限制，保留 country；
- 实时目录没有该国家代码：停止 LDH 检索，进入降级链。

需要细粒度过滤时：

```bash
python scripts/ldh_client.py discover-filters \
  --source EU/CURIA \
  --namespace case_law
```

过滤器发现路径可由部署环境配置；客户端不会向用户暴露内部路由。`precise-search` 在传入
`court`、`court_tier`、`jurisdiction` 或 `language` 时自动读取并校验过滤目录：

- 值存在：执行检索；
- 值不存在：返回 `bad_request`，不发送搜索；
- 目录不可用：返回 `unavailable`，不静默透传未经确认的过滤值。

次国家地区只有在实时过滤目录明确提供匹配 `jurisdiction` 时才可使用过滤器。否则把地区名称和
本地语言词加入查询，并在全文阶段核对地域。

## 5. 精确搜索

基本调用：

```bash
python scripts/ldh_client.py precise-search \
  --q "right to erasure GDPR Article 17" \
  --country EU \
  --namespace case_law \
  --source EU/CURIA \
  --top-k 10 \
  --result-detail snippet
```

参数：

| 参数 | 规则 |
|---|---|
| `--q` | 必填；包含核心法律术语，次国家地区追加映射器 `query_terms` |
| `--country` | 必填且仅一个；必须是实时目录中的 LDH 规范代码 |
| `--namespace` | `case_law` / `legislation` / `doctrine` |
| `--source` | 可重复；必须精确存在于该法域实时源目录 |
| `--court` | 先经实时 filters 校验 |
| `--court-tier` | `1` / `2` / `3`，先经实时 filters 校验 |
| `--jurisdiction` | 先经实时 filters 校验 |
| `--language` | 先经实时 filters 校验 |
| `--date-start`, `--date-end` | `YYYY-MM-DD` |
| `--top-k` | `1..100` |
| `--alpha` | `0..1`，默认 `0.7` |
| `--result-detail` | `snippet` / `summary_only` / `full_text` / `full_metadata` |

`precise-search` 的检索前校验：

1. 规范化代码，但对 `GB/GBR` 返回 `bad_request` 并提示使用 `UK`；
2. 检查国家代码是否在实时目录；
3. 检查 Source ID 是否精确存在；
4. 如有细粒度过滤，检查过滤值；
5. 通过后才发送搜索。

检索后反向审计：

- 返回 country 与目标不一致的命中放入 `rejected_hits`；
- 指定 source 后，返回 source 不一致的命中被拒；
- 命中未提供 country 时保留，但累计为 `unverified_country_hit_count`，引用前必须二次确认；
- 所有审计信息写入 `jurisdiction_audit`。

## 6. 多法域比较

不得使用一个多 country 请求完成比较。应为每个法域构建独立且同条件的检索：

```text
EU  → precise-search(top_k=10, namespace=case_law)
UK  → precise-search(top_k=10, namespace=case_law)
```

比较时：

1. 相同研究问题、日期范围、namespace 和 top_k；
2. 每个法域单独保留候选、拒绝项和覆盖限制；
3. 默认按法域分组报告；
4. 如需统一排序，使用法域等权的 reciprocal rank fusion；
5. 不直接比较不同法域返回的原始 score；
6. 每个“法域 × 结论维度”必须有独立证据。

## 7. 引用解析和全文

用户提供案号、ECLI、CELEX、法规编号或条文引用时：

```bash
python scripts/ldh_client.py resolve \
  --reference "CELEX 32016R0679 Article 17" \
  --hint-country EU \
  --hint-type legislation
```

从响应中读取真实 `source` 和 `source_id`，再调用：

```bash
python scripts/ldh_client.py get \
  --source EU/EUR-Lex \
  --source-id "<真实 source_id>"
```

`resolve=empty` 时只允许改走同法域主题搜索，不得扩大法域。主题搜索命中则直接 `get`，
不再经过 `resolve`。

全文锚定至少记录：

- `source`、`source_id`；
- 标题、发布/裁判日期、版本或生效信息；
- 官方 URL；
- 法规条文号，或案件案号/ECLI、法院；
- 支持结论的原文片段和定位方式；
- 验证日期。

## 8. 状态契约

| status | 含义 | 动作 |
|---|---|---|
| `ok` | 调用成功且有可用数据 | 继续 |
| `empty` | 调用成功但无命中 | 改写一次，之后降级 |
| `bad_request` | 参数、代码、Source ID 或过滤值错误 | 修正一次 |
| `not_configured` | 当前环境未配置 LDH | 使用预置源 |
| `auth_failed` | 会话鉴权失败 | 本会话停用 LDH |
| `quota_exhausted` | 限流或额度不可用 | 不循环重试，使用预置源 |
| `unavailable` | 网络、服务或所需发现能力不可用 | 使用预置源 |
| `error` | 未分类错误 | 使用预置源并记录限制 |

旧名称 `rate_limited`、`unreachable`、`unauthorized` 不属于当前脚本契约，不得据此分支。

## 9. 来源权威与报告标签

LDH namespace 只描述索引类型，不证明发布者身份。使用下列分类：

| 判断依据 | 来源类别 | 确定性处理 |
|---|---|---|
| 官方公报、立法机关、政府法规库 | `[官方/法律法规]` | 原文和版本核验后可为 L1 `[法规原文]` |
| 法院或官方判例库 | `[司法/案例]` | 一手司法材料；不得标 `[法规原文]` |
| 监管机构决定、规则、指南 | `[监管/行政]` | 说明其法律效力，不一概等同法律 |
| 标准组织或行业机构 | `[标准/行业]` | 核查是否被法律引用或强制采用 |
| 律所、商业数据库、学术、新闻 | `[第三方/背景]` | 通常 L2/L3，不作唯一法律依据 |
| 无法确认发布者或原始 URL | `[待核查]` | 不能支撑确定性结论 |

`search/get` 成功不自动等于 `[已验证]`。只有标题、发布者、法域、锚点和回链 URL 均能复核时，
才可标已验证。

脚注示意：

```markdown
[^1]: [司法/案例] [已验证] Case title, Court, ECLI/案号, 日期。
     Source ID: EU/CURIA；source_id: <id>
     原始链接: <hit.url>
     锚点: <段落/页码/关键原文>
     发现渠道: LegalDataHunter；验证日期: YYYY-MM-DD
```

## 10. 降级和安全

降级顺序：

```text
source-index.md
→ LDH 实时 discover 目录 / resources.md
→ 联网定位官方 URL
→ verification-engine.md Level A/B/C
→ 无法核验则列入待查清单
```

不得以模型训练数据补全条文或判例。来源冲突必须并列。

平台凭证、鉴权方式、内部网关地址和完整请求属于内部信息：不得读取、打印、转述或写入报告。
只可对用户说明“由平台内部鉴权并自动注入”。本技能不执行 LDH 写操作。

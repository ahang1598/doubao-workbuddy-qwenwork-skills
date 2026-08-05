# 飞书文档 doc.md 合同（第二阶段首选）

仅当用户明确回复“生成飞书文档”或等价表达后读取本文件。第二阶段首选中间产物不再是 `payload.json`，而是 `work/<板块>_doc.md`；旧 `payload` 链路保留为 legacy fallback。

## 1. 目标

- `doc.md` 是第二阶段的结构化中间产物，用来承接第一阶段已验证的 `facts.json` 与 `分析草稿.md`。
- `doc.md` 不是自由写作 Markdown，也不是通用 Markdown-to-XML 编译输入；它是一份“可读的结构化文档”。
- 最终目标仍是生成与当前 skill 基本一致的飞书文档：章节顺序、核心指标、双轨热度、10 股表、四组分化、信号、风险和来源口径保持一致。

## 2. 主链路

```bash
python3 scripts/generate_doc_markdown.py work/<板块>_facts.json work/<板块>_分析草稿.md -o work/<板块>_doc.md
python3 scripts/validate_doc_markdown.py work/<板块>_doc.md
python3 scripts/render_feishu_xml_from_doc.py work/<板块>_doc.md -o work/<板块>_feishu.xml
```

若主链路失败，可回退到 legacy payload 路径：

```bash
python3 -m json.tool work/<板块>_payload.json >/dev/null
python3 scripts/hydrate_payload_from_facts.py work/<板块>_facts.json work/<板块>_payload.json
python3 scripts/check_payload_against_chat.py work/<板块>_分析草稿.md work/<板块>_payload.json
python3 scripts/check_market_facts.py work/<板块>_payload.json
python3 scripts/validate_doc_payload.py work/<板块>_payload.json
```

## 3. 原则

- `doc.md` 文本仍以第一阶段正文为唯一母版；标题、摘要、直接回答、模块结论、催化、信号、风险和来源只允许原句搬运或结构化拆分。
- 10 股行情、四组分化、代表股角色、近 7 日数据等仍以 `facts.json` 为准，不在文档生成阶段现场补造。
- 第二阶段首选直接消费 `facts + chat` 生成 `doc.md`，避免先生成 `payload.json` 再水合/比对/转 XML 的重复开销。
- `doc.md` 追求“人可读 + 机可解析”，不是通用数据仓格式；结构固定优先于表达自由。

## 4. 文件格式

`doc.md` 固定由两部分组成：

1. YAML front matter：保存文档顶部元数据。
2. 固定顺序的 Markdown section：保存飞书模板需要的结构化块。

### 4.1 front matter

固定包含：

- `sector`
- `market`
- `timestamp`
- `index_caliber`
- `selected_stocks`
- `data_mode`
- `composite_score`
- `gauge_pill`
- `info_score`
- `market_score`

示例：

```yaml
---
sector: "光伏"
market: "A股"
timestamp: "2026-06-29"
index_caliber: "光伏产业(931151)"
selected_stocks:
  - "隆基绿能"
  - "通威股份"
data_mode: "full"
composite_score: 2
gauge_pill: "温和"
info_score: 3
market_score: 2
---
```

### 4.2 section 顺序

以下 section 顺序固定，不得增删改名：

1. `headline`
2. `summary`
3. `key_chips`
4. `divergence`
5. `answer`
6. `section_summaries`
7. `dimensions`
8. `catalysts`
9. `stocks`
10. `divergence_groups`
11. `watch_signals`
12. `risks`
13. `sources`
14. `_facts_hydration`

其中：

- `headline` / `summary` 为普通文本 section
- 其余 section 统一使用 fenced `json` 代码块保存结构化对象或数组

示例：

```markdown
## headline
消息驱动为主的超跌修复，资金面尚未形成共振

## answer
```json
{
  "restate": "...",
  "conclusion": "...",
  "next": "..."
}
```
```

## 5. 字段语义

`doc.md` 各 section 的语义与 legacy payload 等价：

- `headline` / `summary`：开篇核心结论
- `key_chips`：4 个核心指标
- `divergence`：双轨热度卡
- `answer`：直接回答三行
- `section_summaries`：模块 1-5 本段结论
- `dimensions`：模块 1 四维度
- `catalysts`：模块 2 时间线
- `stocks` / `divergence_groups`：模块 3 个股与四组
- `watch_signals`：模块 4 盯盘信号
- `risks`：模块 5 风险
- `sources`：模块 6 来源
- `_facts_hydration`：来自 facts 的水合留痕

## 6. 生成要求

- `generate_doc_markdown.py` 必须直接读取 `facts.json` 与 `分析草稿.md` 生成 `doc.md`。
- 文本字段不得在第二阶段重新写一版判断；找不到原句时，回第一阶段补正文。
- `stocks`、`divergence_groups` 和 `_facts_hydration` 应复用现有水合逻辑，以保证与 legacy payload 的行为尽量一致。
- `render_feishu_xml_from_doc.py` 只负责按 `feishu-doc-style.md` 模板把 `doc.md` 渲染成 XML，不负责兜底修数据。

## 7. 校验要求

`validate_doc_markdown.py` 至少要保证：

- front matter 元数据齐全
- `headline` / `summary` 非空
- `key_chips` 恰好 4 个
- `dimensions` 恰好 4 个且顺序固定
- `stocks` 恰好 10 只
- `divergence_groups` 四组齐全
- `catalysts` 3-6 条
- `watch_signals` 至少 3 条
- `risks` 至少 3 条
- `sources` 至少 1 条
- `_facts_hydration` 存在，且股票与分组未脱离 facts

## 8. 与 payload 的关系

- `payload_contract.md` 仍然有效，但仅作为 legacy fallback 合同。
- 当新链路可用时，优先使用 `doc.md -> XML -> 飞书`。
- 当新链路解析失败、校验失败或与当前飞书模板明显不一致时，可临时回退到 payload 路径。

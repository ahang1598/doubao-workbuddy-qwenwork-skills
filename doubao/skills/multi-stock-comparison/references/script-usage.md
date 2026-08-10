# 脚本输入合同

脚本只处理本地结构化输入，不获取行情、公告或一致预期。需要外部金融数据时先按 `capability-financial-data-search.md` 同批检索比较对象，完成口径对齐后再写入脚本输入。调用前运行 `python3 <script> --help`；首次使用或修改后运行对应脚本的 `--self-test`。

## 目录

- [delivery_mode 交付门禁](#delivery_mode-交付门禁)
- [报告内容质量门禁](#报告内容质量门禁)
- [飞书高级图表](#飞书高级图表)
- [A/H 折溢价与执行条件筛查](#ah-折溢价与执行条件筛查)
- [证据账本审计](#证据账本审计)
- [反向 DCF](#反向-dcf)

## delivery_mode 交付门禁

研究开始前建立 JSON 交付清单并运行计划门禁；最终回复前更新同一文件并运行完成态门禁：

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/delivery_gate.py" --phase plan delivery-manifest.json
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/delivery_gate.py" --phase final delivery-manifest.json
```

`TEXT` 示例；四项检查必须全部为 `true`，且 `advanced_components` 必须为空：

```json
{
  "delivery_mode": "TEXT",
  "mode_reason": "只比较一个同口径指标，三段内可无损回答",
  "text_checks": {
    "single_decision_question": true,
    "answer_within_three_short_paragraphs": true,
    "no_structured_comparison_or_navigation": true,
    "no_advanced_component_needed_or_generated": true
  },
  "advanced_components": [],
  "visual_family_ids": [],
  "doc_created": false,
  "doc_url": "",
  "fetch_verified": false
}
```

`LARK_DOC` 的计划阶段可保留未完成字段；最终阶段必须把 `doc_created`、`fetch_verified` 设为 `true`，填入可访问的 `/docx/` 或 `/wiki/` 链接，并完整列出高级组件：

```json
{
  "delivery_mode": "LARK_DOC",
  "mode_reason": "需要横向富表格、胜负分栏与同业象限图",
  "text_checks": {},
  "advanced_components": ["rich_comparison_table", "quadrant_svg_whiteboard"],
  "visual_family_ids": ["peer-positioning"],
  "editorial_gate_passed": true,
  "doc_created": true,
  "doc_url": "https://example.feishu.cn/docx/REPLACE_WITH_REAL_TOKEN",
  "fetch_verified": true,
  "visuals_fetch_verified": true
}
```

`visual_family_ids` 必须与质量清单中 `include=true` 的图表 ID 一致；没有图表时使用空数组。存在图表时 `advanced_components` 不得为空，最终拉取文档并逐图复核后才能设置 `visuals_fetch_verified=true`。`LARK_DOC` 最终阶段还要求 `editorial_gate_passed=true`；该字段只能在 `editorial_gate.py --phase final` 实际通过后设置。交付脚本不创建文档，也不判断比较结论是否正确。只有输出 `DELIVERY_GATE_PASS` 才表示对应阶段通过；失败时不得结束任务或把 `LARK_DOC` 降级成聊天 Markdown。

## 报告内容质量门禁

研究完成、正式起草前建立质量清单并运行计划门禁；文档写入并拉取复核、删除低质量和重复内容后，再运行最终门禁：

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/editorial_gate.py" --phase plan editorial-manifest.json
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/editorial_gate.py" --phase final editorial-manifest.json
```

```json
{
  "core_question": "A 与 B 谁的盈利兑现更强？",
  "document_profile": "standard",
  "deep_dive_reason": "",
  "core_financial_snapshot": {
    "status": "included",
    "companies": ["公司 A", "公司 B"],
    "metrics": [
      "price",
      "market_cap",
      "revenue_ttm",
      "operating_margin_ttm",
      "free_cash_flow_ttm",
      "forward_pe"
    ],
    "metric_categories": [
      "market_data",
      "valuation",
      "financial_scale",
      "profitability",
      "cash_flow"
    ],
    "presentation": "compact_comparison_table",
    "coverage": "同一估值日与共同 TTM",
    "evidence_ids": ["snapshot-a", "snapshot-b"],
    "valuation_date_verified": true,
    "periods_aligned_or_labeled": true,
    "currency_units_complete": true,
    "missing_values_not_fabricated": true
  },
  "price_analysis": false,
  "kline_plan": {
    "status": "not_needed"
  },
  "visual_plan": [],
  "visual_budget_reason": "",
  "sections": [
    {
      "title": "核心结论",
      "include": true,
      "role": "core_conclusion",
      "decision_relevance": "直接回答选择问题并给出翻转条件",
      "new_information": true,
      "reader_takeaway": "A 当前兑现更强，但订单放缓会翻转结论",
      "evidence_quality": "mixed",
      "evidence_ids": ["claim-a-margin", "claim-a-orders"]
    },
    {
      "title": "普通公司简介",
      "include": false,
      "exclusion_reason": "属于通用背景，不改变比较结论"
    }
  ],
  "document_checks": {
    "conclusion_first": true,
    "answers_core_question_directly": true,
    "no_generic_background": true,
    "no_unranked_news_dump": true,
    "no_repeated_claims": true,
    "tables_answer_one_question": true,
    "visuals_have_information_job": true,
    "visuals_rendered_and_legible": true,
    "visuals_nonredundant": true,
    "visual_sources_units_complete": true,
    "visual_text_fallbacks_present": true,
    "only_material_data_gaps": true,
    "low_quality_content_removed": true,
    "compression_pass_completed": true
  }
}
```

`role` 使用 `core_conclusion`、`analysis`、`risk`、`validation` 或 `appendix`。`evidence_quality` 使用 `primary`、`standardized_data`、`consensus`、`derived`、`authoritative_media`、`supported_inference` 或 `mixed`。`one_pager`、`standard`、`deep_dive` 最多保留 5、8、12 个分析章节，默认最多保留 1、3、5 个视觉家族；上限不是配额。只有 `EDITORIAL_GATE_PASS` 才表示对应阶段通过。

`core_financial_snapshot` 默认使用 `status=included`。`metric_categories` 只使用 `market_data`、`valuation`、`financial_scale`、`growth`、`profitability`、`cash_flow`、`balance_sheet`、`capital_efficiency`；必须包含前两项和至少两个经营财务类别，`metrics` 至少 5 个。最终四个验证字段均须为 `true`。

确认不相关时使用：

```json
{
  "core_financial_snapshot": {
    "status": "not_relevant",
    "reason_code": "single_fact_query",
    "reason": "只核对同口径毛利率定义",
    "decision_impact": "其他财务金融数据不会改变该定义性答案"
  }
}
```

允许的 `reason_code` 为 `single_fact_query`、`narrow_nonfinancial_scope`、`user_explicitly_excluded` 和 `other_material_reason`。部分数据缺失、取数困难、篇幅或已有定性判断不能使用；这些情况下仍保留可得核心快照并标注覆盖边界。

每个候选图表都进入 `visual_plan`。保留图表示例：

```json
{
  "id": "valuation-sensitivity",
  "include": true,
  "title": "WACC × 永续增长敏感性",
  "chart_type": "heatmap",
  "format": "html5_block",
  "information_job": "显示估值对两个核心假设的非线性敏感程度",
  "decision_relevance": "判断当前相对估值结论是否依赖窄假设区间",
  "new_information": true,
  "reader_takeaway": "公司 A 的排序只在低 WACC 情景成立",
  "why_visual_beats_text_or_table": "二维网格的梯度和边界比逐格叙述更易识别",
  "evidence_ids": ["dcf-grid-a", "dcf-grid-b"],
  "redundancy_group": "valuation-sensitivity",
  "rendering_verified": true,
  "source_and_units_verified": true,
  "text_summary_present": true
}
```

`format` 只允许 `html5_block`、`svg_whiteboard` 或 `mermaid_whiteboard`。同一 `redundancy_group` 只能保留一个视觉家族；排除的候选图需要 `include=false` 和 `exclusion_reason`。最终三个验证字段必须为 `true`。超过档位默认图表预算时填写 `visual_budget_reason`，说明为什么每个额外视觉都不可由现有图或表替代。

涉及价格路径、涨跌、相对强弱或事件反应时必须设置 `price_analysis=true`。默认 K 线计划如下；计划阶段可以暂未完成两个验证字段，最终阶段必须均为 `true`：

```json
{
  "price_analysis": true,
  "kline_plan": {
    "status": "included",
    "coverage": "A、B 两只决策相关标的；共同交易窗口日线，前复权",
    "evidence_ids": ["ohlc-a", "ohlc-b"],
    "rendering_verified": true,
    "same_window_frequency_adjustment_verified": true
  },
  "visual_plan": [
    {
      "id": "price-kline-family",
      "include": true,
      "title": "A/B 同窗口价格路径",
      "chart_type": "kline",
      "format": "html5_block",
      "information_job": "核对价格路径、波动与事件窗口",
      "decision_relevance": "区分端点收益接近但路径风险不同的标的",
      "new_information": true,
      "reader_takeaway": "A 的事件后波动收敛快于 B",
      "why_visual_beats_text_or_table": "影线、跳空和波动聚集无法由端点表完整表达",
      "evidence_ids": ["ohlc-a", "ohlc-b"],
      "redundancy_group": "price-path",
      "rendering_verified": true,
      "source_and_units_verified": true,
      "text_summary_present": true
    }
  ]
}
```

无法可靠生成时使用可审计例外：

```json
{
  "price_analysis": true,
  "kline_plan": {
    "status": "not_applicable",
    "reason_code": "missing_complete_ohlc",
    "reason": "可靠来源只提供收盘价，无法补齐开高低且不得猜测"
  }
}
```

允许的 `reason_code` 为 `missing_complete_ohlc`、`no_continuous_trading_series`、`universe_too_large_for_readable_kline`、`incompatible_windows_or_frequency`、`user_explicitly_declined`、`single_price_point_only` 和 `other_material_reason`。最后一项必须写清会使 K 线失真、误导或无法可靠生成的重大事实；篇幅、制作成本、已有收益表/折线图和审美偏好不能使用。

## 飞书高级图表

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" kline company-a-kline.json --output company-a-price-path.html
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" timeseries relative-performance.json --output relative-performance.html
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" heatmap valuation-grid.json --output valuation-grid.html
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" quadrant peer-quadrant.json --output peer-quadrant.svg
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" waterfall margin-bridge.json --output margin-bridge.svg
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/lark_visuals.py" timeline event-timeline.json --output event-timeline.svg
```

`kline` 输入包含 `title` 和按交易日严格升序的 `series`；每根 K 线必须有 `date/open/high/low/close`，可选 `volume`。顶层可选 `symbol`、`market`、`currency`、`adjustment`、`palette`（`cn` 或 `global`）、`events` 和 `source_note`。输出为无外部依赖的单文件 HTML，包含响应式 K 线、成交量、悬停明细和事件标记。生成器一次为一只证券生成一个 HTML；2–4 只决策相关标的分别运行并在飞书中成组装配，统一窗口、频率、时区、复权和尺寸。超过 4 只时，全样本使用统一基期表现图/表，并为焦点或决策相关子集生成 K 线、记录选择依据。只有收盘价时不要补造 OHLC。

`quadrant` 输入包含 `title`、`x_axis`、`y_axis` 和 `points`。两条轴均定义 `label/min/max/split`，可选 `low/high`；每个点包含 `label/x/y`，可选 `size/group`。顶层可选 `quadrants`、`subtitle`、`as_of` 和 `source_note`。输出为自包含 SVG，可按线上最新版 `lark-doc`/`lark-whiteboard` 流程导入画板。

`timeseries` 输入包含 `title` 和 1–8 个 `series`；每个序列使用唯一 `name` 和 2–600 个共同日期的 `{date,value}`。可选 `normalize_to_100`、`unit`、`events`、`subtitle` 和 `source_note`。脚本拒绝日期未对齐的序列；输出为带悬停、事件标记和区间变化摘要的自包含 HTML。

`heatmap` 输入包含 `title`、`rows`、`columns` 和对应的二维 `values`；空值使用 `null`。可选 `scale=sequential|diverging`、`center`、`value_format=number|percent|multiple`、`precision`、`unit` 和 `source_note`。输出为保留精确数值与色阶图例的自包含 HTML；稀疏矩阵或少量情景应改用表格。

`waterfall` 输入包含 `title`、`start` 和 1–12 个 `{label,value}` 的 `changes`；可选 `start_label`、`end_label`、`unit`、`precision` 和 `source_note`。输出为自包含 SVG。只有桥接项可复算且起终点一致时使用。

`timeline` 输入包含 `title` 和 2–14 个按日期升序的事件；每项使用 `date/label`，可选 `category/stage/effect/note`，其中 `effect` 为 `positive|negative|mixed|neutral`。输出为自包含 SVG。需要区分事件发生、发布、生效/执法和可交易时间时，应在输入标签和阶段中明确，不用颜色代替文本。

自定义供应链、传导链、风险网络等 SVG 可按 `advanced-lark-visuals.md` 和写入时最新版 `lark-doc`/`lark-whiteboard` 流程制作；不要为了避免做选择而把所有关系压成一个通用流程图。

`.html`、`.svg` 等生成文件只允许作为飞书文档写入的中间产物。一旦生成，`delivery_mode` 必须为 `LARK_DOC`，把它登记进 `visual_plan`，并完成文档创建/更新和拉取复核；不得直接发送文件、截图、源码、本地路径或下载链接。

## A/H 折溢价与执行条件筛查

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/ah_premium.py" ah-input.json --output ah-output.json
```

输入包含 `as_of` 和非空 `pairs`。每一项必须提供：

- `issuer`；
- `a.code/price_cny/timestamp`；
- `h.code/price_hkd/timestamp`；
- `fx.cny_per_hkd/timestamp`；
- 可选 `a_units_per_h_share`，默认 1，但必须先核实股份经济权利；
- 可选 `cost_rates`，各项以小数表示；
- 可选 `execution_checks`：股份转换/交割、两腿交易、借券、法律路径、交收与汇率是否已验证。

脚本输出 H 股每一 A 股经济单位的 CNY 等值价格、A 相对 H 溢价、成本后的指示性绝对价差、理论方向、时间戳和执行条件警告。即使所有布尔检查为真，输出也只表示“已声明条件齐备，仍需实时验证”，不证明可锁定套利。首次使用或修改后运行：

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/ah_premium.py" --self-test
```

## 证据账本审计

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/audit_ledger.py" ledger.json
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/audit_ledger.py" ledger.json --json
```

首次使用或修改后运行：

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/audit_ledger.py" --self-test
```

脚本检查：

- 根级截止日和观察项必填字段；
- observation 与 comparison ID；
- 期间、指标、单位、币种和集团/分部/产品层级；
- 一致预期所需的供应商、快照和覆盖数；
- 衍生计算的公式、输入引用及外部来源；
- 比较中的错期、错层、单位和币种不一致。

退出码为 0 表示没有错误；警告需要人工判断。脚本只验证结构和可比性，不能证明输入数据真实，也不能代替研究判断。

## 反向 DCF

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/reverse_dcf.py" company-a.json --output company-a-dcf.json
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/reverse_dcf.py" company-b.json --output company-b-dcf.json
```

首次使用或修改后运行：

```bash
python3 "$MULTI_STOCK_COMPARISON_SKILL_DIR/scripts/reverse_dcf.py" --self-test
```

输入包含 `params`，可选 `target_enterprise_value`、`solve`、`sensitivities` 和 `grid`。模型输出企业价值，不自动处理净债务、少数股东、非经营资产或每股价值。必须满足 `wacc > terminal_growth` 且 `terminal_roic > terminal_growth`。

跨公司比较时分别建模，统一企业价值桥、预测期、税项和变量定义；WACC、终值增长、利润率或资本效率可以因公司风险与商业模式不同而不同，但必须解释理由。脚本输出不能作为事实来源。

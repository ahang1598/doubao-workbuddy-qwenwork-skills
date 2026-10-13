# 脚本输入合同

脚本只处理本地结构化输入，不获取行情、新闻或一致预期。需要标准化金融数据时先按 `capability-financial-data-retrieval.md` 调用 `/seed_finance_search`，核对口径后再写入脚本输入。所有比例使用小数，例如 8% 写作 `0.08`；日期使用 `YYYY-MM-DD`；价格序列按交易日严格升序并保持同一复权口径。

调用前运行 `python3 <script> --help` 查看参数。首次使用或修改后运行 `python3 <script> --self-test`。

## delivery_mode 交付门禁

研究开始前建立 JSON 交付清单，并运行计划门禁：

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/delivery_gate.py" --phase plan delivery-manifest.json
```

最终回复前更新同一文件，并运行完成态门禁：

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/delivery_gate.py" --phase final delivery-manifest.json
```

`TEXT` 示例；四项检查必须全部为 `true`，且 `advanced_components` 必须为空：

```json
{
  "delivery_mode": "TEXT",
  "mode_reason": "单一估值口径解释，三句内可无损回答",
  "text_checks": {
    "single_decision_question": true,
    "core_conclusion_within_three_sentences": true,
    "no_structured_comparison_or_navigation": true,
    "no_advanced_component_needed_or_generated": true
  },
  "advanced_components": [],
  "data_consistency_verified": true,
  "core_financial_data_status": "not_relevant",
  "core_financial_data_reason": "单一估值口径解释，不涉及具体证券分析",
  "price_analysis": false,
  "kline_status": "not_price_analysis",
  "doc_created": false,
  "doc_url": "",
  "fetch_verified": false
}
```

`LARK_DOC` 的计划阶段可先保留未完成字段；最终阶段必须把 `doc_created`、`fetch_verified` 设为 `true`，填入可访问的 `/docx/` 或 `/wiki/` 链接，并完整列出已生成的高级组件。`fetch_verified=true` 只表示最后一次写入后的文档已重新拉取并复核；若随后又修改文档，必须重新拉取后才能恢复为 `true`。

```json
{
  "delivery_mode": "LARK_DOC",
  "mode_reason": "需要同业比较表、情景估值与多象限图",
  "text_checks": {},
  "advanced_components": ["rich_table", "quadrant_html_block"],
  "data_consistency_verified": true,
  "visual_purposes": {
    "quadrant_html_block": "哪些同业同时具备估值吸引力和盈利确定性"
  },
  "core_financial_data_status": "included",
  "core_financial_data_fields": [
    "price",
    "market_cap",
    "revenue_growth",
    "net_margin",
    "free_cash_flow",
    "net_debt",
    "forward_pe"
  ],
  "required_sections": [
    "核心结论",
    "核心金融与财务快照",
    "同业与估值",
    "风险与验证"
  ],
  "actual_sections": [
    "核心结论",
    "核心金融与财务快照",
    "同业与估值",
    "风险与验证"
  ],
  "price_analysis": false,
  "kline_status": "not_price_analysis",
  "doc_created": true,
  "doc_url": "https://example.feishu.cn/docx/REPLACE_WITH_REAL_TOKEN",
  "fetch_verified": true,
  "quality_checks": {
    "conclusion_first": true,
    "every_section_changes_decision": true,
    "evidence_traceable_and_current": true,
    "low_quality_information_removed": true,
    "redundant_content_removed": true,
    "styles_serve_content": true,
    "required_structure_preserved": true,
    "logic_chain_explicit": true,
    "reader_navigation_clear": true,
    "accounting_bases_unambiguous": true
  },
  "visual_checks": {
    "unique_decision_question": true,
    "source_units_labeled": true,
    "no_duplicate_encoding": true,
    "rendering_verified": true
  },
  "html_block_checks": {
    "embedded_in_lark_document": true,
    "source_file_not_delivered": true
  }
}
```

`data_consistency_verified=true` 只能在最终交付前完成跨产物数据对账后设置，且适用于 `TEXT` 和 `LARK_DOC`。核对聊天摘要、正文、表格、图表、附录和其他交付物中的对象、期间、币种、单位、口径与数值；冲突时先采用更权威来源，权威性相当时采用截至信息截止日更新的数据，并从上游修正所有相关产物。

十项 `quality_checks` 只有在按 `writing-quality.md` 拉取文档并完成独立结构审阅、口径复核和删稿后才能设为 `true`。`logic_chain_explicit` 表示结论可沿经营/事件、盈利、预期和估值传导追踪；`reader_navigation_clear` 表示核心结论、章节标题和下钻顺序清楚；`accounting_bases_unambiguous` 表示相似口径已清楚标注、可比且与估值分母一致。`required_structure_preserved` 表示 `actual_sections` 已覆盖全部 `required_sections`，控篇幅时没有删掉承担独立分析功能的章节。覆盖矩阵检查过但证据质量不足的内容应从正文删除，不能靠免责声明或“仅供参考”保留。

所有任务都必须声明核心金融与财务数据状态：

- 计划态通常使用 `core_financial_data_status=planned`，并用 `core_financial_data_fields` 列出预计进入正文的字段；
- 完成态改为 `included`；若已纳入可得字段但仍有实质缺口，使用 `included_with_gaps`，并以 `core_financial_data_gaps` 列出缺口；
- 只有按 `core-financial-snapshot.md` 确信这些数据不会改变答案时，才使用 `not_relevant` 并填写具体 `core_financial_data_reason`；
- 完成态不得停留在 `planned`。数据难找、篇幅有限或结构复杂不是 `not_relevant` 的理由。

所有 `LARK_DOC` 在计划态都要用 `required_sections` 锁定 2–12 个必需章节；完成态用 `actual_sections` 记录拉取后实际存在的结构。任一必需章节缺失时，最终门禁失败。控制长度应压缩节内内容或移走审计细节，不能静默简化结构。

`advanced_components` 中只要存在 HTML block 视觉，就必须：

- 在计划态用 `visual_purposes` 为每个视觉写一个唯一、非空的决策问题；
- 在完成态确认 `visual_checks.unique_decision_question`、`source_units_labeled`、`no_duplicate_encoding` 和 `rendering_verified` 全部为 `true`。

两个图回答相同问题、缺少单位/来源、与表格重复或未实际检查飞书渲染时，最终门禁不得通过。

`advanced_components` 中只要存在名称含 `html_block` 的组件，完成态还必须提供：

```json
{
  "html_block_checks": {
    "embedded_in_lark_document": true,
    "source_file_not_delivered": true
  }
}
```

只有 HTML 已作为 block 实际写入目标飞书文档、拉取后确认该 block 存在且渲染正常，并且没有把 `.html` 文件、附件、源码或本地链接交付给用户时，才能把两项设为 `true`。

每次任务还必须设置 `price_analysis` 和 `kline_status`：

- 非实质性股价分析：`price_analysis=false`、`kline_status=not_price_analysis`；
- 实质性单股股价分析且生成 K 线：`price_analysis=true`、`kline_status=included`，`advanced_components` 必须包含 `kline_html_block`，且 `delivery_mode` 必须为 `LARK_DOC`；
- K 线不适用：`price_analysis=true`、`kline_status=not_applicable`，并将 `kline_exception` 设为 `user_declined_visual`、`single_point_question`、`reliable_ohlc_unavailable`、`multi_asset_comparison`、`corporate_action_or_data_break` 或 `price_path_not_relevant` 之一。

“耗时”“文档复杂”或“聊天输出更方便”不是允许的例外。若只有收盘价且趋势仍有价值，运行 `lark_visuals.py price` 生成股价 HTML，`advanced_components` 列出 `price_chart_html_block`，并把 `kline_exception` 记录为 `reliable_ohlc_unavailable`。

`advanced_components` 包含 `price_chart_html_block` 或 `kline_html_block` 时，必须提供：

```json
{
  "chart_generation_modes": {
    "price_chart_html_block": "script",
    "kline_html_block": "script"
  }
}
```

股价图和 K 线只允许 `script`。不得使用其他值，不得手写 HTML。脚本未覆盖所需交互或数据结构时，改用表格、段落或省略该图。

脚本只验证交付状态，不创建文档，也不能代替人工判断研究结论是否正确。`DELIVERY_GATE_PASS` 才表示对应阶段通过；失败时不得结束任务或把 `LARK_DOC` 降级成聊天 Markdown。

## 市场与股价分析

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/market_analysis.py" market.json --output market-output.json
```

输入包含 `series.asset`，可选 `series.benchmarks`、`analysis`、`events` 和 `pricing_bridge`。价格至少包含 `date` 与正的有限 `close`；OHLC、成交额、换手率和成交量均可选。

- Benchmark 只使用共同交易日计算相对收益、相关性和 Beta。
- `phases` 按方向变化阈值给出每段起止、涨跌、高低点、最大回撤和平均成交活跃度；阈值属于方法参数，不按事后新闻调整。
- 事件窗口锚定事件日当日或之后首个交易日；输入前核对发布时间和交易时段。
- `phase_threshold` 是机械阶段划分阈值，不是交易信号。
- `pricing_bridge` 仅在前后预测期、指标、会计和股本口径一致时使用。

## 组合风险

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/portfolio_risk.py" portfolio.json --output portfolio-output.json
```

输入包含 `positions`，可选 `returns`、`benchmark`、`correlation_windows`、`participation_rate` 和 `scenarios`。`weight` 为净值权重，可为负；流动性天数要求同时提供 `shares` 与 `adv_shares`；缺失情景冲击必须单列，不能当作零风险。

## 反向 DCF

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/reverse_dcf.py" reverse-dcf.json --output reverse-dcf-output.json
```

输入包含 `params`、`target_enterprise_value`、`solve`，可选 `sensitivities` 与 `grid`。模型输出企业价值，不自动处理净债务、少数股东、非经营资产或每股价值。必须满足 `wacc > terminal_growth` 且 `terminal_roic > terminal_growth`。

## 股票筛选

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/equity_screen.py" screen.json --output screen-output.json
```

输入包含 `as_of`、`candidates`、`filters`、`factors`，可选 `group_by`、`missing_policy` 和 `top_n`。流程为硬过滤、分位数缩尾、z-score、方向与权重、排名。权重非负，方向使用 `high` 或 `low`。

## 飞书高级图表

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_visuals.py" price price.json --output price-chart.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_visuals.py" kline kline.json --output price-path.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_visuals.py" quadrant quadrant.json --output peer-quadrant.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_charts.py" trend trend.json --output kpi-trend.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_charts.py" waterfall waterfall.json --output profit-bridge.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_charts.py" heatmap heatmap.json --output valuation-sensitivity.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_charts.py" timeline timeline.json --output catalyst-timeline.html
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/lark_charts.py" flow flow.json --output transmission-flow.html
```

`price` 输入包含 `title`、`previous_close` 和按时间严格升序的 `series`；每个价格点包含 `time` 或 `date` 与 `close`，可选 `average`、`volume`。顶层可选 `symbol`、`market`、`currency`、`timeframe`、`adjustment`、`palette`（`cn` 或 `global`）、`theme`（`terminal-light` 或 `terminal-dark`）、`price_decimals`、`events` 和 `source_note`。输出为无外部依赖的单文件 HTML，包含响应式价格线、均价线、昨收/基准线、成交量、悬停明细和事件标记。输入模板：`assets/chart-templates/price-chart.template.json`。

`kline` 输入包含 `title` 和按交易日严格升序的 `series`；每根 K 线必须有 `date/open/high/low/close`，可选 `volume`。顶层可选 `symbol`、`market`、`currency`、`timeframe`、`adjustment`、`palette`（`cn` 或 `global`）、`theme`（`terminal-light` 或 `terminal-dark`）、`ma_windows`（2–250 的整数，最多 5 项）、`show_volume`、`events` 和 `source_note`。输出为无外部依赖的单文件 HTML，包含响应式 K 线、均线、成交量、悬停明细和事件标记。只有收盘价时不要补造 OHLC，改用 `price`。输入模板：`assets/chart-templates/kline-chart.template.json`。

`quadrant` 输入包含 `title`、`x_axis`、`y_axis` 和 `points`。两条轴均定义 `label/min/max/split`，可选 `low/high`；每个点包含 `label/x/y`，可选 `size/group`。顶层可选 `quadrants`、`subtitle`、`as_of` 和 `source_note`。输出为自包含、响应式多象限 HTML。

`trend` 输入包含 `title`、2–36 个 `categories` 和 1–5 个 `series`；每组序列包含唯一 `name` 及与 categories 等长的有限数值 `values`。可选 `y_min/y_max`、`unit`、`subtitle`、`as_of` 和 `source_note`。输出为自包含、响应式趋势 HTML；不同量纲不得强行放在同一图。

`waterfall` 输入包含 `title` 和 3–14 个 `items`。首项 `kind=start`、末项 `kind=end`、中间项 `kind=change`；每项含 `label/value`，且终点必须等于起点加全部变化。输出为自包含、响应式瀑布 HTML，不平衡的桥接会被拒绝。

`heatmap` 输入包含 `title`、2–16 个 `x_labels`、2–16 个 `y_labels` 和等尺寸的有限数值矩阵 `values`。可选 `scale`（`diverging`/`sequential`）、`center`、`decimals`、`baseline.x/y`、`unit` 和来源元数据。输出为无外部依赖的 HTML block，保留每格数值、悬停明细和基准格。

`timeline` 输入包含 `title` 和按日期升序的 2–10 个 `events`；每项含 `date/label`，可选 `category/note`。输出为自包含、响应式时间线 HTML。只放会改变判断或验证结论的节点，不把完整日历可视化。

`flow` 输入包含按阅读顺序排列的 2–10 个 `nodes` 和 1–14 个 `edges`。每个节点包含唯一 `id`、`title`，可选 `note` 与 `tone`（`neutral`/`positive`/`negative`/`warning`）；每条边包含 `from/to`，可选 `label`，且只能指向后续节点。输出为自包含传导链 HTML。只表达已由证据支持的关系，不把相关性写成因果。

生成文件后按 `advanced-lark-visuals.md` 解释图形、检查口径，并立即按线上最新版 `lark-doc` 流程把 `.html` 作为 HTML block 的输入载荷写入目标飞书文档。每个视觉在交付清单写一个唯一、非空的 `visual_purposes`；相同问题不得用多个图重复回答。最终 HTML block 的写入语法与责任边界以写入时线上最新版 `lark-doc` skill 为准。

所有生成的 HTML 文件只允许作为飞书 HTML block 写入的中间载荷。生成文件本身、附件、源码、本地路径或下载链接均不是交付物。必须完成飞书文档创建/更新、组件实际写入和拉取复核，再向用户返回核心结论与飞书文档链接；写入失败时不得改为发送本地文件、截图或源码。

## 会计口径调节桥

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/accounting_basis_bridge.py" \
  accounting-basis.json --output accounting-basis-output.json
```

输入模板：`assets/accounting-basis-bridge.template.json`。`basis_pair` 支持 `ifrs_non_ifrs`、`gaap_non_gaap` 和 `reported_adjusted`；每个期间提供法定/报告值、调整后值及公司披露的调节项。调节项 `amount` 使用“从法定/报告口径加到调整后口径”的正负方向，并标记 `recurrence` 与 `cash_effect`。

脚本验证调节桥是否平衡，计算差额、盈亏方向切换、调整依赖和调节项特征，并为每个期间输出可交给 `lark_charts.py waterfall` 的 `waterfall_input`。没有完整调节表时可只计算口径差额，但必须保留脚本警告，不得猜测调节项。分析与写作规则见 `accounting-basis-analysis.md`。

## A/H 与跨上市地折溢价

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/cross_listing_spread.py" cross-listing.json --output cross-listing-output.json
```

输入包含 `as_of` 与 `pair`。`pair` 必须提供 `a_symbol`、`h_symbol`、`a_price_cny`、`h_price_hkd` 和 `cny_per_hkd`；若两类证券每股代表的经济权益不是 1:1，再提供 `a_claim_units_per_share` 与 `h_claim_units_per_share`。可选：

- `history`：严格按日期升序的同口径价格与汇率，用于历史分位和 z-score；
- `costs.total_estimated_cost_bps`：已经外部核验的总成本缓冲；
- `implementation`：`fungible_or_convertible`、`short_high_leg_available`、`long_low_leg_accessible`、`settlement_and_funding_aligned` 四项执行条件。

脚本计算同币种、同经济权益单位的 A/H 溢价和 H 股相对折价。只要四项执行条件有一项未明确为 `true`，输出分类即为 `relative_value_only`；全部为真也只标记 `mechanically_executable_candidate`，仍需人工核验税费、股息、汇率、融券召回、停牌和制度变化。历史统计不证明价差必然回归。

## 报告校验与引用

```bash
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/report_pipeline.py" source.md facts.json --check-only
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/report_pipeline.py" source.md facts.json --output display.md
python3 "$EQUITY_RESEARCH_SKILL_DIR/scripts/report_pipeline.py" source.xml facts.json --format lark-xml --output display.xml
```

该脚本检查事实表结构、claim ID、日期、占位符和引用是否存在，然后把 `{fact:...}` 转换为读者引用并生成数据来源章节。默认输入输出为 Markdown；`--format lark-xml` 接受飞书文档 XML 片段，要求以 `<title>` 开始，并以包含规定免责声明的 `<p>` 结束，生成 XML 格式的数据来源章节。它不判断报告观点是否正确，也不强制固定栏目名称。

`display.xml` 只解决事实引用与来源编排，不代替飞书文档设计。最终写入前仍须读取线上最新版 `lark-doc` skill，并按 `lark-doc-delivery.md` 选择高亮块、分栏、表格和 HTML block 等组件。

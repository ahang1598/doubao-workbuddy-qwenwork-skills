# 报告规格规范

`report-spec.json` 是数据与页面之间的事实和交互契约。`content-blueprint.json` 在它之上定义故事主线与逐页内容；正式页面必须同时通过内容确认和主题确认。只生成用户需要的输出形态，不为了展示能力默认生成阅读、演示和打印三套页面。

## 顶层结构

```json
{
  "schema_version": "1.0",
  "report": {},
  "sources": [],
  "metrics": [],
  "findings": [],
  "charts": [],
  "drilldowns": [],
  "sections": [],
  "privacy": {},
  "modes": {},
  "validation": {}
}
```

## report

至少包含：

- `title`、`subtitle`、`period`；
- `audience`、`purpose`；
- `confidentiality`：`internal`、`external_masked`、`public`；
- `snapshot_at`；
- `content_authority`：是否以人工报告为内容上限；
- `language`；
- `output_name`。

## sources

每个来源包含：

- `id`、`name`、`type`；
- `base_id`、`table_id`、`view_id`；
- `record_count`；
- `primary_key`；
- `field_catalog_path`、`snapshot_path`；
- `relationship`：与其他来源的连接键及未匹配记录数；
- `sensitivity`。

文档类来源记录文件路径、版本、人工确认状态和可引用段落。

## metrics 与 findings

遵守 `evidence-and-metrics.md`。`expected_value` 是快照计算结果，不允许先写页面数字再反向修改 expected value 让测试通过。

## charts

```json
{
  "id": "chart_rating_distribution",
  "title": "评价结果分布",
  "question": "各评价档次分别有多少人？",
  "type": "bar",
  "source_id": "people",
  "dimension": "rating",
  "measure": "employee_id",
  "aggregation": "count_distinct",
  "filters": [],
  "sort": {"by": "business_order", "values": ["胜任", "适任", "待提升", "不合格"]},
  "zero_policy": "show_required_categories",
  "null_policy": "show_as_unclassified",
  "drilldown_id": "drill_rating",
  "evidence": ["metric_rating_counts"]
}
```

图表必须回答明确管理问题。只是“字段可以画图”不是保留图表的理由。

## drilldowns

下钻采用领域无关的“触发元素 → 记录成员集合”契约，不根据月份、状态、部门、区域、产品等字段名写死规则。每个下钻至少定义：

```json
{
  "id": "drill_example",
  "source_id": "source_main",
  "trigger": {"type": "chart|metric|text|table", "ref_id": "visible_element_id"},
  "membership": {
    "filter_ast": {},
    "expected_record_count": 40,
    "verification": "exact"
  },
  "columns": ["由数据画像选择的业务字段"],
  "title_field": "稳定业务编号",
  "record_url_field": "真实记录链接字段",
  "mode": "full"
}
```

要求：

- **全覆盖（硬性，`validate_report_spec.py` 强制）**：每个有 `group_by` 的数据图表、每个热力图、每个统计数字指标（`data_fact` / `rule_calculation`）都必须声明下钻；漏一个则 spec 不通过。确实不该下钻的项（纯目标趋势线、占位、无行级来源的合成值）用 `drilldown_required: false` + `drilldown_opt_out_reason` 显式豁免。
- **一图一模板（推荐）**：一个图表声明一个不含固定 `filter_ast` 的 chart-trigger 下钻，runtime 按点击类别用 `aggregation.group_by` 字段自动筛选，一个声明即覆盖全部类别，无需逐类别枚举（枚举容易漏）。热力图用双字段 `filter_ast`（如 `{"and":[{"op":"eq","field":"区域",...},{"op":"eq","field":"月份",...}]}`）逐格声明或模板化。
- `trigger` 指向页面中真实存在的图表、指标、正文数字或表格行；
- `membership.filter_ast` 是可执行、可复现的过滤表达式，不能用显示文本做模糊搜索；
- `expected_record_count` 必须由冻结快照独立计算；
- 计数和求和值通常映射到贡献记录集合；均值映射到参与计算的记录；比率和对比需显式定义分子、分母或两组成员；无法唯一还原成员集合时不得设为可下钻；
- 定义列表列、默认排序、搜索字段、单条记录标题和真实记录 URL 字段；
- 定义无权限、无链接、零结果和 iframe 失败状态；
- `mode` 为 `full`、`local_only` 或 `aggregate_only`；
- 主题可以改变视觉布局和弹窗样式，但不能改变成员集合、交互层级、返回语义或权限边界。

## sections

章节包含：

- `id`、`label`、`title`；
- `purpose`：本章回答什么；
- `finding_ids`、`metric_ids`、`chart_ids`；
- `reading_layout`；
- `presentation_layout`；
- `print_break`；
- `speaker_note`（可选）。

不要按字段顺序自动生成章节。章节应按受众的决策路径组织：先结论，再证据，再行动。

## privacy

至少声明：

- 允许进入聚合的字段；
- 允许进入明细列表的字段；
- 只允许在钉钉原始记录展示的字段；
- 需要哈希、遮蔽或删除的字段；
- HTML 是否可嵌入明细数据；
- 外发模式是否禁用行级链接。

## modes

默认只启用固定 16:9 演示稿。`reading-first` 是演示稿内容密度，不是连续阅读模式。只有用户明确要求长页面分析报告、网页看板或连续阅读时，才启用 `reading`。

```json
{
  "presentation": {"enabled": true, "stage": "1920x1080", "density": "reading-first"},
  "reading": {"enabled": false, "requested_by_user": false},
  "pdf": {"enabled": true, "source": "presentation-slides"},
  "mobile": {"enabled": true, "behavior": "scale-fixed-stage"}
}
```

常见路由：

- “做 PPT、现场汇报”：演示模式；PDF 可选。
- “做可视化报告、长页分析”：连续阅读模式；需要现场汇报时再加演示模式。
- “做数据看板”：阅读/交互模式，不默认生成演示稿。
- “既要现场讲又要会后传播”：两个模式可以同时启用，但必须共用同一事实规格和内容蓝图。

## validation

记录：

- 精确指标数量和允许误差；
- 至少五个证据抽查项；
- 每张图的期望分组与总数；
- 至少一个可自动点击的下钻案例；
- 所有非 `aggregate_only` 下钻入口的自动点击覆盖率；
- 桌面与手机视口；
- 打印页数或关键分页；
- 禁止出现的文字与敏感字段。

## 规格确认原则

以下情况必须在完整页面生成前让用户确认：

- 报告主问题或受众不明确；
- 有两个以上合理指标口径；
- 跨表键不唯一；
- 人工报告与数据事实冲突；
- 需要公开含个人信息的页面；
- AI 推断要进入正式结论。

颜色、圆角、动效细节不属于规格阻塞项，通过风格预览确认。

即使上述口径都没有歧义，原始数据生成正式演示稿时仍要先按 `content-blueprint.md` 生成核心框架与逐页内容清单，取得一次整体内容确认。该确认不是逐页审批。

---

## 文档溯源

### 生成提示词

```text
我计划生成一个 skill，让用户自己能基于自己的 AI 表格生成可视化报告
```

### 依赖文档

| 文档 | 用途 |
|---|---|
| `evidence-and-metrics.md` | 指标和结论字段定义 |
| `frontend-slides-engine.md` | 阅读与演示的布局约束 |

### 生成信息

- **生成时间**：2026-08-14
- **生成工具**：Codex（GPT-5）
- **数据处理**：定义数据、分析、交互和多形态页面共享的报告契约。

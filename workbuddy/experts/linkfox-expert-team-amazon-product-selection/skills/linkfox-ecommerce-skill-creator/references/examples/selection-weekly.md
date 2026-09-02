# 示例：每周选品流程 skill

本示例展示一个完整的流程型 skill 产物片段。可作为生成期的对照样板，**不要**在生成时原样照抄业务字段，必须按访谈纪要落地。

---

## 访谈纪要摘录（来自 `.draft/interview.md`）

- 业务目标：每周二上午跑一次，从美国站给定关键词出 5 个候选 ASIN，用于运营会议讨论是否上新。
- 输入参数：`seed_keywords`（关键词列表）、`country=US`、`time_window=last7d`、`min_margin=0.25`。
- 交付物：一份 md 报告，含"候选 ASIN 对比表 / 关键词流量结构 / 风险提示 / 推荐结论"四章。
- 节奏：每周一次。

## 产物目录

```
selection-weekly/
├── SKILL.md                      大纲：执行编排 + 流水线总览表（6 步 → 已大纲化）
├── scripts/
│   ├── response_io.py            （从生成器复制）
│   └── step_3_aggregate.py       跨多个 skill 结果做去重/排序的合并脚本
└── references/
    ├── steps/                    单步详情，SKILL.md 大纲指向它，agent 按步加载
    │   ├── S1.md … S6.md
    ├── workflow.md
    ├── data-fields.md
    └── report-template.md
```

> 本流程 6 步 ≥ 4，触发大纲化：SKILL.md 只放总览表，单步血肉（含落盘段落）落在 `references/steps/S<N>.md`。下方先给 SKILL.md 大纲节选，再给一个 `steps/S2.md` 详情节选作样板。

## SKILL.md 节选

```markdown
---
name: selection-weekly
description: 美国站周度选品流程。每周根据种子关键词产出 5 个候选 ASIN 与对比报告。涵盖关键词市场扫描、候选挖掘、流量结构分析、风险扫查、推荐结论。当用户说"每周选品"、"周度选品流程"、"美国站选品周报"、"种子词选品"、"候选 ASIN 周度筛选"、"weekly product selection"、"weekly sourcing pipeline"、"weekly Amazon sourcing report"、"seed keyword sourcing"、"candidate ASIN weekly screening" 时触发。仅适用于周期性流程；一次性的市场分析或单点 ASIN 解读不在范围。
---

# 美国站周度选品流程

## 适用场景

| 场景 | 说明 |
|------|------|
| 周二选品例会前 | 周一晚跑完，运营周二早带 5 个候选进会 |
| 新品类摸底 | 同一种子词 4 周连跑，看候选稳定度 |

## 不适用

- 单次市场分析（直接调 `linkfox-jiimore-get-niche-info-by-keyword` 即可）
- 实时 ASIN 调研（用 linkfox-amazon-product-detail）
- 跨站点联合选品（暂不支持，列入局限）

## 输入参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| seed_keywords | string | — | 逗号分隔的种子关键词，1–5 个 |
| country | string | US | 站点；当前仅支持 US |
| time_window | string | last7d | last7d / last4w |
| min_margin | float | 0.25 | 候选入选的最低毛利率阈值 |
| out_dir | string | ./reports | 报告输出目录 |

## 流水线

### 执行编排

- **第 1 层（并行）**：S1 种子词市场扫描、S2 候选 ASIN 挖掘 —— 都只依赖运行时入参、互不消费对方输出，同一轮并行发起。
- **第 2 层**：S3 候选去重初筛 —— 依赖 S2。
- **第 3 层（并行）**：S4 流量结构核查、S5 风险扫查 —— 都依赖 S3、彼此独立，并行发起。
- **第 4 层**：S6 推荐结论与报告 —— 依赖 S1 + S4 + S5。

| 步骤 | 做什么（一句话） | 依赖 | 用途 | 详情 |
|------|----------------|------|------|------|
| S1 种子词市场扫描 | 按种子词拉市场机会评分 | 无 | S6 市场可入性判定；报告"关键词流量结构" | `references/steps/S1.md` |
| S2 候选 ASIN 挖掘 | 按毛利/BSR/评分筛候选 | 无 | S3 输入 | `references/steps/S2.md` |
| S3 候选去重与初筛 | 跨种子词去重、排序、取 Top20 | S2 | S4 / S5 输入 | `references/steps/S3.md` |
| S4 流量结构核查 | 批量查 ASIN 流量曝光结构 | S3 | S6 流量健康度判定；报告"对比表" | `references/steps/S4.md` |
| S5 风险扫查 | 文字商标 + 实用专利侵权预警 | S3 | 报告"风险提示"；命中下沉 | `references/steps/S5.md` |
| S6 推荐结论与报告 | 综合挑 5 个 ASIN 出报告 | S1, S4, S5 | 交付运营周会 | `references/steps/S6.md` |

## 报告产物

每次执行后，按访谈纪要章节生成报告，命名 `report_<yyyymmdd>__weekly.{md,html}`，写入 `out_dir`。

报告章节（由本 skill 准备数据，样式由 `linkfox-report-generator` 接管）：
- 候选 ASIN 对比表：来自步骤 4 的 `naturalSearchExposureRatio` / `sponsoredProductsExposureRatio` + 步骤 2 的 ASIN/标题/价格/月销
- 关键词流量结构：来自步骤 1 的 `market_summary[]`
- 风险提示：来自步骤 5 的 `risk_flags`
- 推荐结论：来自步骤 6

元信息：生成时间 / 参数快照 / 数据来源清单 / 局限性说明。

> **⚠ 如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。**
> 本 skill 只准备业务数据；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。
> 不要在此处复制报告样式或 html 模板。

## 执行自检

- [ ] 每个候选 ASIN 在报告中都出现于"对比表"+"流量结构"+"风险提示"三处
- [ ] 步骤 4 落盘文件存在且非空
- [ ] 报告头的参数快照与本次入参一致
- [ ] 推荐结论给出 5 个；不足 5 个时降级到"现有候选不足"提示

## 已知局限

- 仅支持 US 站点（步骤 1 jiimore 同时支持 US/JP/DE，但其他步骤受限于 utility-patent-detection 仅美国，整链锁 US）
- 跨站点联合选品未实现
- 风险扫查仅覆盖 US 文字商标 + 实用专利；外观专利可加 `linkfox-ruiguan-detection-patent-design` 但未接入
```

## `references/steps/S2.md` 节选（单步详情样板）

> 大纲表里 S2 只有一行；执行到 S2 时 agent 才 Read 本文件，把这一步的血肉（含落盘段落）加载进上下文。其余 S1/S3…S6 同理各一个文件。

```markdown
# 步骤 2：候选 ASIN 挖掘

- **输入**：`seed_keywords`
- **依赖**：无（与 S1 同属第 1 层，可并行）
- **操作**：调用 `linkfox-sellersprite-product-search`，按 `min_margin` + BSR + 评分筛选
- **输出**：`candidates_raw[]`（ASIN、标题、价格、月销、评分、卖家类型）
- **用途**：作为步骤 S3 的输入

## 大响应处理（落盘）

候选列表分页返回，含长文本字段（标题、品牌名），强制落盘：

​```bash
python scripts/response_io.py run \
    --script /root/.linkfox/.ce/skills/linkfox-sellersprite-product-search/scripts/sellersprite_product_search.py \
    --out-dir <out_dir>/.cache \
    --label S2_candidates \
    --timeout 300 \
    '{"keyword":"wireless earbuds","country":"US","minMargin":0.25,"pageSize":1000}'
​```

主脚本（LinkFox 官方 skill 自带）从 argv[1] 接到 JSON 参数包，请求结果写 stdout；response_io.py 落盘后给出预览。预览含 `_error` 时先按 `stderr_snippet` 排错。

读取时只取下游需要的字段：

​```bash
python scripts/response_io.py read <文件路径> \
    --fields "data[*].asin,data[*].title,data[*].price,data[*].monthlySales,data[*].rating" \
    --format jsonl
​```
```

## DAG 校验示意（生成期临时记录）

```
seed_keywords ─（并行）→ S1 market_summary ──────────────────→ S6 推荐结论 ─→ 报告"关键词流量结构"
              ─（并行）→ S2 candidates_raw ─→ S3 top20 ─（并行）→ S4 traffic ─→ S6 推荐结论 ─→ 报告"对比表"
                                                        ─（并行）→ S5 risk_flags ─→ S6 推荐结论 ─→ 报告"风险提示"
```

分层：L1{S1,S2} → L2{S3} → L3{S4,S5} → L4{S6}。每步至少一条出边落到下游步骤或报告章节，无孤岛。

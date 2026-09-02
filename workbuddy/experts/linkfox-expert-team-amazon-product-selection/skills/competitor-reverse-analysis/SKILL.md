---
name: competitor-reverse-analysis
description: 竞品全景透视专家：输入 ASIN + 站点，并行拉取 Keepa 历史曲线、Sorftime 日销趋势、SIF 流量关键词与流量结构总览四大数据源，经 Python 量化分析（价格弹性回归、Deal 回落周期、评论异常检测、生命周期阶段判定、BSR 月度波动、流量结构占比）后输出 11 章节 HTML 深度报告，覆盖 US/UK/DE/JP/FR/CA/IT/ES/IN/MX/BR/AU/AE/SA 共 14 个站点。当用户提到竞品逆向分析、竞品全景透视、ASIN 深度解析、竞品拆解、竞品全方位诊断、价格策略逆向、Deal 效果评估、评论增长分析、生命周期判断、BSR 趋势分析、流量结构拆解、Keepa 数据深度分析、竞品复盘、competitor reverse analysis, ASIN deep dive, competitor teardown, competitor 360 analysis, price strategy analysis, lifecycle diagnosis, Deal effectiveness, review anomaly detection, traffic structure breakdown, BSR trend analysis, competitor autopsy 时触发。即使用户没有明确说"逆向分析"或"全链路"，只要意图涉及对特定 ASIN 进行多维度数据驱动的深度竞品研究（而非只看价格或只看关键词等单点查询），也应触发本 skill。
---

# 竞品逆向分析

输入一个 ASIN + 站点，并行采集 Keepa / Sorftime / SIF / 卖家精灵四大数据源，经 Python 量化分析后生成涵盖价格策略、BSR 趋势、评论曲线、Deal 效果、流量结构、生命周期等 10+ 维度的 HTML 深度报告。

## 适用场景

对特定竞品 ASIN 进行全方位数据驱动的逆向拆解，输出可执行的战略建议。

| 场景 | 说明 |
|------|------|
| 竞品入选前深度审查 | 跑一遍全链路分析，判断该 ASIN 的真实竞争力、价格策略、生命周期阶段 |
| 价格策略逆向 | 量化竞品的价格弹性、Deal 效果、促销手段矩阵，指导自身定价 |
| 流量结构拆解 | 自然流量 vs 付费流量占比、核心关键词排名、AC 徽章分布 |
| 生命周期判断 | BSR + 销量 + 评论三维度交叉验证，判定产品处于哪个阶段 |
| Deal 效果验证 | 分析每次 Deal 后 BSR 回落幅度和恢复周期，评估促销 ROI |

## 不适用

- 单点查询（只看价格、只看 BSR、只看关键词）——直接调用对应数据源 skill 即可
- 批量 ASIN 筛选——本 skill 单次处理一个 ASIN，批量场景在外层循环中调用
- 评论文本情感分析——使用 `linkfox-voc-review-analysis`
- 关键词拓词 / 选品——使用 ABA 或选品 skill
- 需要专利 / 商标 / 版权检测——使用睿观系列 skill

## 输入参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| asin | string | 必填 | 亚马逊 ASIN |
| marketplace | string | US | 站点代码（US/UK/DE/JP/FR/CA/IT/ES/MX/BR/AU/AE/SA） |
| days | integer | 365 | Keepa 历史回看天数（1-365） |

## 已挂载能力约束

| skill | 用途 | 调用位置 | 状态 |
|-------|------|----------|------|
| linkfox-keepa-product-series | 价格/BSR/评分/卖家数历史曲线 | S1 | 已挂载 |
| linkfox-sorftime-amazon-product-detail | 日销/收入/Deal/价格趋势 | S1 | 已挂载 |
| linkfox-sif-asin-keywords | 流量关键词反查（排名/CVR/流量占比） | S1 | 已挂载 |
| linkfox-sif-asin-summary | 流量结构总览（自然/付费占比、关键词进出） | S1 | 已挂载 |
| linkfox-keepa-product-request | 商品详情快照（FBA费用/材质/13月月销/BSR均值） | S2 | 已挂载（可选，限流时跳过） |
| linkfox-report-generator | HTML 报告样式、排版、导出 | S4 | 已挂载 |

## 流水线

### 执行编排

- 第 1 层（并行）：S1 拉取 4 源原始数据——Keepa Series、Sorftime、SIF Keywords、SIF Summary 互不依赖，同一轮并行发起。
- 第 2 层：S2 补充拉取 Keepa Product Request——依赖 S1 完成（需确认 Keepa token 是否充裕），可选执行。
- 第 3 层：S3 Python 量化分析——依赖 S1 + S2 全部返回，运行 `step_3_analyze.py` 输出统一分析 JSON。
- 第 4 层：S4 生成 HTML 报告——依赖 S3，调用 `linkfox-report-generator`。

### 流水线总览

| 步骤 | 做什么（一句话） | 依赖 | 用途 | 详情 |
|------|----------------|------|------|------|
| S1 并行拉取 4 源数据 | Keepa 历史曲线 + Sorftime 日销趋势 + SIF 关键词 + SIF 流量总览 | 无 | S3 量化分析的原始数据来源 | `references/steps/S1.md` |
| S2 补充 Keepa 商品详情 | 拉 FBA 费用/材质/尺寸/13 月月销/BSR 均值 | S1 | 补充 S3 缺失字段（限流时跳过） | `references/steps/S2.md` |
| S3 量化分析 | 运行 Python 脚本对 10 个维度逐一计算 | S1, S2 | S4 报告章节的评分与数据输入 | `references/steps/S3.md` |
| S4 生成 HTML 报告 | 调用 report-generator 输出多维度深度报告 | S3 | 最终交付给用户的决策依据 | `references/steps/S4.md` |

## 报告产物

每次执行流程后，按以下章节生成 HTML 诊断报告，落盘到会话目录 `reports/`。

报告必备元信息：
- 生成时间（ISO 8601，本地时区）
- 参数快照（ASIN、marketplace、days）
- 数据来源清单（步骤 → skill / 参数）
- 局限性说明（数据延迟、Keepa 限流降级、覆盖空白）

业务章节：
- **KPI 总览**：当前 BSR / 月销量 / 评分 / 利润率
- **关键时间线**：首次在售、首单、BSR 里程碑
- **BSR 深度解析**：月度统计、小类排名、趋势图
- **评论曲线与异常检测**：增长趋势、异常激增日、月度增量、评分历史
- **价格策略量化分析**：三阶段演变、弹性回归、促销手段矩阵
- **Deal 效果评估**：每次 Deal 前后 BSR 对比、回落幅度、恢复周期
- **销量趋势与季节性**：月度汇总、环比增长、阶段划分
- **流量结构分析**：自然 vs 付费占比、关键词进出、AC 徽章
- **生命周期判断**：三段切分、阶段表、交叉验证
- **SWOT 综合研判**：四象限
- **行动建议**：Insight List

> **⚠ 如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。**
> 本 skill 只准备业务数据；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。
> 不要在此处复制报告样式或 html 模板。

## 执行自检

每次跑完流程，在收尾时确认：

- [ ] S1 至少 3 个数据源返回了非空数据（Keepa 限流降级时至少 Sorftime + SIF 可用）
- [ ] S3 分析脚本没有报错，10 个分析模块都有输出
- [ ] 报告各章节均有数据来源，无数据的章节标"暂无数据"
- [ ] 参数快照（ASIN、marketplace、days）已写入报告头
- [ ] 综合建议与各维度分析结论一致
- [ ] Keepa 限流时已在报告局限性章节注明降级情况

## 已知局限

- **Keepa token 限流**：Keepa API 共享 token 池，高频调用可能触发 429。S2 为可选步骤，限流时跳过并用 Sorftime 数据兜底；S1 的 Keepa Series 也可能限流，此时价格/BSR 历史曲线降级为 Sorftime 数据（精度略低但覆盖面足够）
- **单 ASIN**：一次只能分析一个 ASIN；批量需外层循环
- **Sorftime 趋势天数**：免费查询返回 15 天趋势，长周期需指定 `queryTrendStartDate` / `queryTrendEndDate`（成本翻倍）
- **SIF 数据延迟**：SIF 关键词和流量数据有约 3-7 天延迟，最新一周数据可能不完整
- **评论历史**：Keepa 的 ratingCount 历史取决于 Keepa 追踪覆盖；部分新品可能无历史评论数据
- **Deal 检测**：Sorftime dealTrend 仅覆盖部分 Deal 类型；Keepa 无独立 Deal 字段，需从价格波动推断
- **阈值假设**：评论异常阈值（>20 条/天）、生命周期阶段判定阈值（销量变化 ±10%/±20%）、Deal 回落判定（7 天窗口）均基于经验值，不同类目可能需要调整

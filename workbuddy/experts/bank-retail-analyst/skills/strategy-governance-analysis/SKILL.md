---
name: strategy-governance-analysis
description: 银行战略与治理分析器。以"财务数据+管理层行为+组织演进"三位一体视角，对基准银行 vs 对标银行的战略定力、决策质量与治理韧性进行穿透式分析，输出领导更替下的战略延续性评估、关键节点反事实推演与治理韧性评分，回答"在不确定环境中，如何实现一张蓝图绘到底"。**用户需指定基准银行和对标银行**，如"以A银行为基准、对比B/C/D/E银行生成战略与治理穿透分析报告"。
triggers:
  # —— 推荐的精准激活表述（显式指定基准行） ——
  - 以某某银行为基准的战略与治理穿透分析
  - 以xxx银行为基准生成战略与治理穿透报告
  - 以xxx银行为对标主体的战略延续性分析
  - 以xxx为基准行的治理韧性评分
  - 生成以xxx银行为基准的一张蓝图绘到底分析
  - 基准银行战略与治理分析
  # —— 业务维度激活词 ——
  - 战略与治理分析
  - 战略定力
  - 战略延续性
  - 战略摇摆
  - 一张蓝图绘到底
  - 言行比对
  - 言行一致度
  - 叙事分析
  - 董事长致辞
  - 行长报告
  - 领导更替
  - 历任董事长
  - 历任行长
  - 高管稳定性
  - 组织演进
  - 组织变革热力图
  - 一级部室
  - 反事实推演
  - 关键节点决策
  - 钱荒
  - 资管新规
  - 治理韧性
  - 治理结构
  - 董事会专业委员会
  - 股权结构变化
  - 风险边界
  - 分红策略
  - 战略隔离带
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - file   # 读取 output/ 对标结果与 data/reports/ 原文，写出战略与治理穿透 PDF 报告
---

## ✅ 能力边界

**能做：**
- 以"财务数据 + 管理层行为 + 组织演进"三位一体视角，对**基准行 vs 对标行**做战略定力、决策质量、治理韧性的穿透分析
- 输出领导更替下的战略延续性评估、关键节点反事实推演、治理韧性评分，回答"一张蓝图绘到底"
- 结合董事长致辞/行长报告原文做言行比对，需用户指定基准行与对标行清单

**不能做（超出范围）：**
- 不下载财报、不提取原始数据、不做基础对标计算（依赖上游 ①②③④）
- 言行比对依赖 cninfo-bank-reports 已下载的报告原文，缺原文则不臆断
- 不替代 strategic-insight 的通用战略洞察，本 Skill 聚焦战略延续性与治理韧性
- 分析对象仅限上市银行公开披露信息

# 银行战略与治理分析器

> **当前 schema_version：`sg-v1.1`**
> 本 Skill 的主输出 `strategy_governance_result.json` 的 `meta.schema_version` 必须写入此值，供下次执行做增量判断。

## 📚 渐进式加载索引（按需阅读）

| 触发条件 | 阅读文件 |
|---|---|
| 首次使用 / Step 0 preflight / 大文件写入规约 / 增量判断 | `references/01_directory_and_preflight.md` |
| 执行任何阶段分析前必读；排查 partial/sg_*.json 异常 | `references/02_analysis_phases.md` |
| 生成 result.json / report.md 前必读；输出不合规时 | `references/03_output_contract.md` |
| **任何 PDF 生成任务**（base_bank / 模板样式 / build_report） | `references/04_pdf_delivery.md` + `_vendor/pdf_report_builder_runtime/RUNTIME.md` |
| 执行完整分析 / Team 配置 / 编辑 config/*.yaml 示例 | `references/05_team_and_configs.md` |

> **默认工作流**：Agent 读本 SKILL.md 后按触发条件判断加载 references。
> **关键约束**：PDF 生成任务必须先 `read_file` `references/04_pdf_delivery.md` 和 `_vendor/.../RUNTIME.md`。

## 共享 PDF Runtime（已随包内置）

本 Skill 生成 PDF 所需的共享 PDF Runtime 已随包内置在 `_vendor/pdf_report_builder_runtime/` 下，**独立安装态（发布包）无需执行任何初始化命令**，可直接生成 PDF 报告。

> 仅仓库开发态需要从共享源码重新注入：执行 `python3 scripts/release.py --sync-paths`（`release.py` 仅存在于仓库开发态，发布包中不含此脚本，无需也无法运行）。

## 角色定位

> 你是一位拥有 **20 年经验的"全球银行业战略与治理顶尖分析师"**，擅长通过 **"财务数据 + 管理层行为 + 组织演进"三位一体**的视角，穿透式地分析银行的决策智慧与战略定力。

## 分析目标

针对**基准银行**（或用户指定的基准行），对比**4 家标杆银行**，回答：

> **"在不确定环境中，如何实现'一张蓝图绘到底'？"**

并量化评估各行在**领导更替与环境冲击**下的**战略延续性**与**决策质量**。

## 定位

在 skill4（当下洞察）和 skill3（财务数据对标）之上，再叠加**时间纵深**与**治理结构**两个新维度，完成从"看报表"到"看决策"的穿透。

**三位一体视角**：

| 视角 | 抓取内容 | 数据来源 |
|---|---|---|
| **财务数据** | 资源投向（零售贷款占比、零售人员费用、科技投入、财富AUM等）的长序列变化 | `~/RetailAnalysis/data/benchmark_database.json` + `data/{standard,text}/<bank>.json` |
| **管理层行为** | 董事长致辞 / 行长报告 / 业绩说明会纪要中的战略关键词与口径演变 | `~/RetailAnalysis/data/extracted_text/<bank>/` |
| **组织演进** | 一级部室（零售、科技、风险）的生灭变并、董事会专业委员会议事频率 | 年报"公司治理" / "组织架构图" / "董事会专门委员会"章节 |

## 对标范围（与 skill4 / skill3 不同）

本 Skill **聚焦 5 家**（用户指定的"基准行 + 4 标杆"）。用户必须指定基准行，以下为推荐的对标组合：

| 简称 | 全称 | 本 Skill 定位 |
|---|---|---|
| **中信** | 中信银行 | **基准行**（分析主体） |
| 招商 | 招商银行 | "一张蓝图绘到底"正面范本（高管稳定性 + 零售定力） |
| 兴业 | 兴业银行 | 同业之王 → 商行+投行战略转型，决策逻辑对比标杆 |
| 浦发 | 浦发银行 | 长三角+对公为主，战略摇摆案例参考 |
| 平安 | 平安银行 | 强执行力 + 高管更替下的"换届式创新"对比案例 |

> **基准行由用户指定**：本 Skill 不设默认基准行。用户可从上述 5 家中指定基准行，也可指定其他银行。
> 若用户未指定，Agent 应主动询问："请指定基准银行和对标银行（如：以A银行为基准，对比B、C、D、E银行）。"
> 用户指定非上述 5 家的基准行时，本 Skill 仍按原 5 家做同业参照，分析主体切换到用户指定的银行。详见 `references/04_pdf_delivery.md` 第 2 节。

## 典型用户请求

- "**生成某某银行战略治理穿透分析的PDF格式报告**"
- "**基准行在历次领导更替中的战略摇摆点在哪里？**"
- "**A银行为什么能一张蓝图绘到底？**对比4家标杆银行给出量化依据。"
- "**口头说重视零售但资源是否真的倾斜？**请给出言行一致度评分。"
- "2013 年钱荒时点，**A银行坚持压降非标 vs B银行守势**背后的决策逻辑是什么？"
- "为基准行设计一套**战略隔离带**与**治理韧性**提升方案。"

## 前置条件与数据依赖

本 Skill 依赖前序 Skill 的产出数据。**执行前必须确认以下数据已就绪**，否则需先运行对应 Skill：

| 所需数据 | 路径 | 来源 Skill | 检查方法 | 缺失时执行 |
|---------|------|-----------|---------|-----------|
| 标准数据 | `~/RetailAnalysis/data/standard/<bank>.json` | **Skill 1**（标准数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/standard/<bank>.json'))"` | 运行 Skill 1，参考 `skills/skill1-standard-data-extraction/SKILL.md` |
| 文字数据 | `~/RetailAnalysis/data/text/<bank>.json` | **Skill 2**（文字数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/text/<bank>.json'))"` | 运行 Skill 2，参考 `skills/skill2-text-data-extraction/SKILL.md` |
| 对标数据库 | `~/RetailAnalysis/data/benchmark_database.json` | **Skill 3**（对标分析） | `python -c "import json; d=json.load(open('~/RetailAnalysis/data/benchmark_database.json')); assert d['meta']['schema_version']=='benchmark-v1.0'"` | 运行 Skill 3，参考 `skills/skill3-benchmark-analysis/SKILL.md` |
| 战略洞察 | `~/RetailAnalysis/data/insight_result.json` | **Skill 4**（战略洞察） | `python -c "import json; d=json.load(open('~/RetailAnalysis/data/insight_result.json')); assert d['meta']['schema_version']=='insight-v1.0'"` | 运行 Skill 4，参考 `skills/skill4-strategic-insight/SKILL.md` |
| 财报原文 | `~/RetailAnalysis/data/extracted_text/<bank>/` | **cninfo-bank-reports** + Skill 1 DocParse | `ls ~/RetailAnalysis/data/extracted_text/<bank>/*_md_full.md` | 运行财报下载 + Skill 1 DocParse 流程 |

> **执行顺序**：财报下载 → Skill 1 标准提取 → Skill 2 文字提取 → Skill 3 对标分析 → Skill 4 战略洞察 → **Skill 5 战略与治理分析**
>
> **基准行与对标行**：用户必须指定一个基准行（分析主体）和至少 2 家对标行。本 Skill 不设默认基准行。
> 若用户未指定，Agent 应主动询问："请指定基准银行和对标银行（如：以A银行为基准，对比B、C、D、E银行）。"

## 输入/输出 Schema（权威契约）

### 依赖声明

Schema 注册表文件由 `release.py` 在打包前从仓库根 `shared/config-schemas/` 自动注入到本 Skill 的 `config/schemas/` 下，**打包后运行时按下表中的 skill 相对路径读取**。

| 数据文件 | Schema 版本 | 契约定义位置（打包后） |
|---|---|---|
| `~/RetailAnalysis/data/standard/<bank>.json` | `standard-v1.0` | `config/schemas/standard-v1.0.yaml` |
| `~/RetailAnalysis/data/text/<bank>.json` | `text-v1.0` | `config/schemas/text-v1.0.yaml` |
| `~/RetailAnalysis/data/benchmark_database.json` | `benchmark-v1.0` | 参见 `skill3-benchmark-analysis` 内的 `references/04_dimensions_and_schema.md` |
| `~/RetailAnalysis/data/insight_result.json` | `insight-v1.0` | 参见 `skill4-strategic-insight` 内的 `config/output_format.md` |
| `~/RetailAnalysis/data/strategy_governance_result.json`（产出） | `sg-v1.1` | `references/03_output_contract.md` |

> 开发期 schema 的唯一 source of truth 在仓库根 `shared/config-schemas/`；请不要直接修改本 skill 的 `config/schemas/` 副本，由 `python scripts/release.py --sync-paths` 统一同步。

### 消费约束

- **读取前必须校验 `_schema_version`**（或 benchmark/insight 的 `meta.schema_version`）；不匹配直接拒绝，不做兼容。
- **字段路径**：统一从 `by_period[<期间>].metrics[*].values[*]` 取数，比率类指标直接使用百分比数值（不再 /100）。
- **bucket 过滤**（text-v1.0）：使用 `category_bucket` 精确匹配（AUM / 客户数 / 财富收入 / 信用卡 / 分部效益 / 量价 / 渠道 / 其他），禁止仅用 `standard_name` 子串。
- **未披露语义**：`values=[]` 表示未披露；做反事实推演 / 治理评分时必须将其标记为"缺失"而非 0 / 跳过。

### LLM subagent 消费约束

Skill 5 的战略/治理分析 subagent 在 prompt 中必须：
1. 显式引用上表中的 Schema 版本号；
2. 声明"若发现字段与契约不符，输出 blocking error 并要求重跑上游"；
3. 禁止对缺失字段做静默兜底。

## 前置条件

| 输入 | 最低要求 | 强烈建议 |
|---|---|---|
| `~/RetailAnalysis/data/standard/<bank>.json` | 5 家银行，至少 2015~至今 | 2004 起 |
| `~/RetailAnalysis/data/text/<bank>.json` | 5 家银行，近 3 年 | 近 10 年 |
| `~/RetailAnalysis/data/benchmark_database.json` | skill3 已跑过，含 5 家银行的长序列派生指标 | — |
| `~/RetailAnalysis/data/extracted_text/<bank>/<year>/`（董事长致辞 + 行长报告 + 组织架构 + 公司治理章节） | 近 5 年 | 10 年以上 |
| `~/RetailAnalysis/data/insight_result.json`（skill4 输出） | 可选，用作上下文 | 推荐 |

### 降级规则（摘要）

1. **文本章节缺失**：仅对已有年份做叙事分析；**不做插值填充**
2. **领导画像缺失**：引导用户根据年报封面与"董事长、行长简历"章节填写
3. **2004~2014 段数据缺失**：输出时明确把"周期一（经济过热）""周期二（四万亿）"降级为"基于年报回溯的文字性判断"

> **前置核查脚本 `skill5_preflight.sh` 详见 `references/01_directory_and_preflight.md` 第 3 节。**

## 分析指令（四阶段 / 四步法）

> 完全对齐用户 Prompt 的四阶段；每一阶段的输入、输出、落盘位置都固定下来以便 Team 并行。
> **详细 Step 定义（关键口径、配对示例、量化公式、反事实红线）见 `references/02_analysis_phases.md`。**

| 阶段 | 目标 | 产物（`~/RetailAnalysis/data/partial/`） |
|---|---|---|
| **第一阶段：数据重构与周期对齐** | 把"2004~至今"切成统一分析时间骨架 | `sg_cycle_timeline.json`、`sg_leader_profiles.json`、`sg_org_heatmap.json` |
| **第二阶段：穿透式"言行比对"** | 量化"说的"vs"做的"一致度；识别真战略 / 口号 / 话术 | `sg_narrative_matrix.json`、`sg_consistency_matrix.json`、`sg_continuity_score.json` |
| **第三阶段：关键节点"反事实"推演** | 2013 钱荒 / 2016 MPA / 2018 资管新规 / 2020 疫情 / 2022 房地产；基准行 what-if 模拟 | `sg_scenario_context.json`、`sg_decision_logic.json`、`sg_counterfactual.json` |
| **第四阶段：治理结构影响机制评估** | 董事会议事频率 × 业绩相关性；股东意志传导；战略韧性评分 | `sg_board_activity.json`、`sg_shareholder_impact.json`、`sg_resilience_score.json` |

## 执行流程

> **默认执行模式**：第一、二、四阶段的三个 Step 内部相互独立，**必须使用 Team 并行模式**（详见 `references/05_team_and_configs.md`）。第三阶段因涉及"同一节点下多行差异对比 + 反事实模拟"，由 main 串行推理。

### Step 0：前置核查（必跑）

执行 `skill5_preflight.sh`。三段输出：数据就绪度 / leaders 填充度 / VIS 资产就绪度。任一 `BLOCK` 必须停下补齐后重跑。

### Step 0.5：增量判断

读取 `~/RetailAnalysis/data/strategy_governance_result.json` 的 `meta.schema_version` 与 `meta.generated_at`，结合当前 SKILL `schema_version: sg-v1.1` 以及 `benchmark_database.json` 的 mtime，判定走【复用】/【增量升级】/【全量重建】。
**详见 `references/01_directory_and_preflight.md` 第 6 节。**

### Step 1~4：四阶段分析

**默认用 Team 并行**执行第一、二、四阶段；第三阶段的 3.2/3.3 由 main 做。详细流程见 `references/05_team_and_configs.md`。

### 汇总阶段（main 执行）

1. **风险点识别**：从 phase2 偏离度 + phase3 决策逻辑 + phase4 韧性评分中，用合取逻辑挑出基准行的摇摆点
2. **建议生成**：按"战略隔离带 / 治理韧性 / 关键人事"三类组织，每类 3~5 条，每条带四要素
3. **质量红线检查**（见 `references/03_output_contract.md` 第 5 节）
4. **MCD 落盘**：
   - `~/RetailAnalysis/data/strategy_governance_result.json`（一次性写入，≤ 80KB）
   - `~/RetailAnalysis/output/<bank>/strategy_governance_report.md`（**必须分 8 节追加**，不得单次写入全文）
5. **补齐 partial/sg_*.json**：12 个中间产物必须全部落盘
6. **生成正式报告**：唯一入口是 `scripts/render_strategy_governance_report.py`。适配器会强制校验 `sg-v1.1`、基准行、12 个 partial、标准模板与上下文完整性，再以临时 PDF 渲染并在终验通过后原子替换正式文件。**禁止任何临时脚本直接生成 HTML/PDF，禁止直接调用 `build_report()` / Playwright / pypdf 绕过适配器。**
7. PDF 交付物与验收：详见 `references/04_pdf_delivery.md`

## 输出要求（三条硬性约束）

> **详见 `references/03_output_contract.md`**：
> 1. **硬性要求 1**：严禁陈述财报已知事实，必须输出"数据背后的逻辑"（数据 + 决策 + 治理三段式）
> 2. **硬性要求 2**：识别风险点——至少 2 个基准行摇摆点案例，每个含时点 + 前后口径对照 + 诱因（4 类枚举）+ 三类证据（至少齐备 2 类）+ 代价评估
> 3. **硬性要求 3**：建议方案——战略隔离带 / 治理韧性 / 关键人事安排三类，每类 3~5 条，每条含四要素（动作 → 理由 → 数据依据 → 预期效果）

## 输出文件

| 文件 | 内容 | 面向 |
|---|---|---|
| `~/RetailAnalysis/data/strategy_governance_result.json` | 结构化主输出：5 家银行画像卡 + 四阶段分析结果 + 战略韧性评分 + 基准行风险点 + 建议方案 | 机器可读 |
| `~/RetailAnalysis/output/<bank>/strategy_governance_report_context.json` | 主结果 + 12 个 partial 的完整模板上下文 | 生成审计 |
| `~/RetailAnalysis/output/<bank>/strategy_governance_report.md` | 分析报告（Markdown，八节结构） | 人类阅读 |
| `~/RetailAnalysis/output/<bank>/战略与治理分析报告.pdf` | 默认 PDF 交付物 | 董事会 / 战略委员会 |

> **Markdown 八节结构 + JSON Schema 详见 `references/03_output_contract.md`。**

## 关键规则（摘要 · 完整清单见 `references/03_output_contract.md` 第 5 节质量红线）

1. **禁止复述财报事实**：三段式"数据解读 + 行为归因 + 治理解释"
2. **战略摇摆点 ≥ 2 个**，诱因从 4 类中选（leader_turnover / shareholder_will / regulator_push / org_inertia）
3. **建议四要素齐备、三类分栏齐备**
4. **反事实必须标注"模型推演，非事实" + 置信度 + 区间**
5. **言行一致度必须量化**：给出 ρ 值与判定
6. **数据缺失不补**：显式降级，不插值、不臆测
7. **领导画像来源明示**：任期起止必须注明来自具体年报
8. **大文件禁止单次写入 >8KB**；`sg_*.json` 12 个中间产物必须齐备
9. **前置核查 BLOCK 未解决禁止进入四阶段**
10. **临时脚本规范**：仅允许用 `_runtime_generate_sg_` 前缀生成分析中间数据，完成后立即删除；临时脚本不得生成 `.html` / `.pdf`，不得写入 `~/RetailAnalysis/output/` 根目录
11. **正式 PDF 验收**：第 2 页必须是目录页，须命中八节主干及“建议方案 / 战略隔离带 / 治理韧性 / 关键人事”；不得以“管理建议”作为可见标题校验词

## 与已有 Skill 的边界

| 维度 | skill4 战略洞察 | skill3 同业财报 | **skill5 战略与治理**（本 Skill） |
|---|---|---|---|
| 时间深度 | 最近 2~3 年 | 2015~至今 | **2004~至今（含周期划分）** |
| 核心单位 | 洞察条目（3-5 条） | 指标矩阵 | **领导任期 / 决策节点 / 治理结构** |
| 数据视角 | 财务 + 高频词 | 财务数据 | **财务 + 叙事 + 组织 + 股权** |
| 输出形态 | 战略洞察 PDF | 财报数据分析 PDF | **战略与治理分析报告（含反事实）** |
| 对标范围 | 7 家 | 7 家 | **5 家（基准行+4标杆）** |
| 是否反事实 | 否 | 否 | **是**（关键节点 what-if） |

> 三者**互补不替代**：skill3 给出"现状与排名"，skill4 给出"近期核心判断"，skill5 给出"治理与战略的时间纵深解释"。

## 依赖

- Python 3.10+
- pyyaml
- pandas（可选，用于 phase2/phase4 相关性计算）
- numpy（可选，用于反事实区间模拟）
- jinja2（PDF 交付物模板渲染）
- playwright（HTML → PDF）
- Pillow（PDF 校验）

---

## 金融免责声明

> ⚠️ 本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。投资有风险，决策需谨慎。

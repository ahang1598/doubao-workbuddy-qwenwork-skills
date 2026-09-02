---
name: benchmark-analysis
description: 股份制银行财报数据分析。基于Skill 1和Skill 2获取的数据，从2015年起建立连贯的头部7家股份制银行零售业务对标数据库，形成营收结构、减值损失、营业支出、存贷利差等多维趋势分析，并进行同业排名和变化追踪。**用户需指定基准银行和对标银行**，如"以A银行为基准、对比B/C/D银行生成同业对标分析"。
triggers:
  # —— 推荐的精准激活表述（显式指定基准行） ——
  - 以某某银行为基准的同业对标分析
  - 以xxx银行为基准生成零售业务对标报告
  - 以xxx银行为对标主体的同业对标分析
  - 以xxx为基准行的同业趋势分析
  - 基准银行
  - 基准行
  - 对标主体
  - 同业对标分析
  - 零售业务对标
  # —— 业务维度激活词 ——
  - 数据分析
  - 趋势分析
  - 同业对比
  - 排名分析
  - 营收趋势
  - 减值损失趋势
  - 存贷利差
  - 零售营收占比
  - 非息收入占比
  - 成本收入比
  - 同业排名
  - 对标数据库
  - 历史数据
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - file   # 读取 data/standard/、data/text/ 下的 JSON，写出 output/ 下的对标数据库与 PDF 报告
---

## ✅ 能力边界

**能做：**
- 基于 standard/text 提取结果，建立头部股份制银行零售业务**对标数据库**（自 2015 年起连贯时序）
- 生成营收结构、减值损失、营业支出、存贷利差等**多维趋势分析**，并做同业排名与变化追踪
- 按用户指定的**基准行 + 对标行**产出可视化 PDF 报告，PDF 渲染运行时已内置于 `_vendor/`

**不能做（超出范围）：**
- 不下载财报、不提取原始数据（依赖上游 ①②③ 已把 JSON 放入 `data/standard/`、`data/text/`）
- 数据缺失时不臆造，只对已有数据做分析与排名
- 不生成战略洞察/治理穿透结论（属于 strategic-insight、strategy-governance-analysis）
- 分析对象仅限上市银行公开披露数据

# 股份制银行财报数据分析

## 📚 渐进式加载索引（按需阅读）

| 触发条件 | 阅读文件 |
|---|---|
| 首次使用 / F/G 回填排错 / 日志规约 / 临时脚本规范 | `references/01_directory_and_logging.md` |
| **任何 PDF 生成任务**（LOGO 校验、基准行解析、视觉资产、build_report） | `references/02_pdf_runtime.md` + `_vendor/pdf_report_builder_runtime/RUNTIME.md` |
| 读取 standard/<bank>.json 任何一家银行数据判空 / 排名参排异常 | `references/03_data_contract.md` |
| 计算派生指标 / 排名校验 / benchmark_analysis_result.json Schema / 完整维度表 | `references/04_dimensions_and_schema.md` |
| 执行完整分析 / Team 并行配置 | `references/05_team_parallel.md` |

> **默认工作流**：Agent 读本 SKILL.md 后按触发条件判断是否继续加载 references，避免一次性全量加载。
>
> **关键约束**：首次 PDF 生成任务必须先 `read_file` `references/02_pdf_runtime.md` 和 `_vendor/.../RUNTIME.md`，否则 `build_report(runtime_acknowledged=True)` 不合规。

## 共享 PDF Runtime（已随包内置）

本 Skill 生成 PDF 所需的共享 PDF Runtime 已随包内置在 `_vendor/pdf_report_builder_runtime/` 下，**独立安装态（发布包）无需执行任何初始化命令**，可直接生成 PDF 报告。

> 仅仓库开发态需要从共享源码重新注入：执行 `python3 scripts/release.py --sync-paths`（`release.py` 仅存在于仓库开发态，发布包中不含此脚本，无需也无法运行）。

## 定位

根据 Skill 1（标准数据提取器）和 Skill 2（文字数据提取器）获取的数据，**从2015年起建立连贯的头部7家股份制银行零售业务对标数据库**，并在此基础上形成多维度趋势分析和同业比较。

## 头部7家股份制银行

本 Skill 聚焦以下 **7家头部股份制银行**（按零售业务重要性排序）：

| 简称 | 全称 | 股票代码 | 备注 |
|------|------|---------|------|
| 中信 | 中信银行 | 601998.SH | 对标主体 |
| 招商 | 招商银行 | 600036.SH | 零售标杆 |
| 平安 | 平安银行 | 000001.SZ | 零售转型标杆 |
| 兴业 | 兴业银行 | 601166.SH | 同业之王 |
| 浦发 | 浦发银行 | 600000.SH | 对公+零售 |
| 光大 | 光大银行 | 601818.SH | 财富管理 |
| 民生 | 民生银行 | 600016.SH | 小微特色 |

## 典型用户请求

- "帮我生成各行零售业务分部营收的历史趋势PDF报告"
- "分析基准行零售减值损失在全行中的占比变化。"
- "比较各行零售存贷利差的变化趋势。"
- "基准行零售业务各项指标在同业中排名第几？排名有没有变化？"
- "7家股份制银行零售业务对标分析。"

## 输入/输出 Schema（权威契约）

### 依赖声明

Schema 注册表文件由 `release.py` 在打包前从仓库根 `shared/config-schemas/` 自动注入到本 Skill 的 `config/schemas/` 下，**打包后运行时按下表中的 skill 相对路径读取**（不再回看仓库根）。

| 数据文件 | Schema 版本 | 契约定义位置（打包后） | 读取前校验 |
|---|---|---|---|
| `~/RetailAnalysis/data/standard/<bank>.json` | `standard-v1.0` | `config/schemas/standard-v1.0.yaml` | 顶层 `_schema_version == "standard-v1.0"` |
| `~/RetailAnalysis/data/text/<bank>.json` | `text-v1.0` | `config/schemas/text-v1.0.yaml` | 顶层 `_schema_version == "text-v1.0"` |
| `~/RetailAnalysis/data/benchmark_database.json` | `benchmark-v1.0` | `references/04_dimensions_and_schema.md` | `meta.schema_version == "benchmark-v1.0"` |

> 开发期 schema 的唯一 source of truth 在仓库根 `shared/config-schemas/`；请不要直接修改各 skill 内的 `config/schemas/` 副本，修改共享源后由 `python scripts/release.py --sync-paths` 统一同步。

### 消费约束

- **读取前必须校验 `_schema_version`**；不匹配则拒绝继续，不做向下兼容。
- **禁止探索字段**：不得使用 `item.get("name") or item.get("metric")` 等旧字段兜底写法；必须按契约 `standard_name` / `category_bucket` / `values[]` 读取。
- **bucket 过滤**：消费 text 数据时必须用 `category_bucket` 精确过滤（AUM / 客户数 / 财富收入 / 信用卡 / 分部效益 / 量价 / 渠道 / 其他），禁止只用 `standard_name` 子串匹配。
- **schema drift 处理**：若发现上游产出字段与契约不符，报错并提示运行 Skill 1 / Skill 2 的 normalize 脚本，不得自行兼容。

## 前置条件与数据依赖

本 Skill 依赖前序 Skill 的产出数据。**执行前必须确认以下数据已就绪**，否则需先运行对应 Skill：

| 所需数据 | 路径 | 来源 Skill | 检查方法 | 缺失时执行 |
|---------|------|-----------|---------|-----------|
| 财报 PDF | `~/RetailAnalysis/reports/<bank>/` | **cninfo-bank-reports**（财报下载） | `ls ~/RetailAnalysis/reports/<bank>/*.pdf` | 运行财报下载 Skill：`python scripts/download_reports.py --bank-name <银行名> --report-type 年度报告` |
| 标准数据 | `~/RetailAnalysis/data/standard/<bank>.json` | **Skill 1**（标准数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/standard/<bank>.json'))"` | 运行 Skill 1 标准数据提取，参考 `skills/skill1-standard-data-extraction/SKILL.md` |
| 文字数据 | `~/RetailAnalysis/data/text/<bank>.json` | **Skill 2**（文字数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/text/<bank>.json'))"` | 运行 Skill 2 文字数据提取，参考 `skills/skill2-text-data-extraction/SKILL.md` |

> **执行顺序**：财报下载 → Skill 1 标准提取 → Skill 2 文字提取 → **Skill 3 对标分析**
>
> **基准行与对标行**：用户必须指定一个基准行（分析主体）和至少 2 家对标行。本 Skill 不设默认基准行。
> 若用户未指定，Agent 应主动询问："请指定基准银行和对标银行（如：以A银行为基准，对比B、C、D银行）。"

## 核心规则

### 数据库管理规则

1. **时间跨度**：从2015年起，逐年/逐半年积累数据
2. **银行范围**：头部7家股份制银行（中信、招商、平安、兴业、浦发、光大、民生），用户需从中指定基准行和对标行
3. **数据冲突处理**：前后两期数据不一致时，**以最新期的为准**，原值记入备注
4. **数据存储**：`~/RetailAnalysis/data/benchmark_database.json`

## 分析维度（概要 · 详表见 `references/04_dimensions_and_schema.md`）

> **口径说明**：除另外注明外均为集团口径；财富管理中收不含资管托管；平安私行门槛低于同业；招行私行门槛高于同业；兴业/浦发不披露零售分部损益数据。
> **DB 内部单位**：金额存储为百万元；比率直接存 %；客户数为万户；AUM 存百万元。

五大分析维度：

1. **维度一：效益（亿元）** —— 零售营收/利润/非息占比，财富管理中收
2. **维度二：量价结构（亿元）** —— AUM、个人存款、零售贷款、存贷利差
3. **维度三：资产质量** —— 零售贷款不良率、减值损失、拨备覆盖率
4. **维度四：费效比** —— 减值负担率、减值成本率、全行成本收入比
5. **维度五：客户** —— 零售客户数、私行客户数/AUM

**同业排名与变化追踪**：排名变化、与前/后一名差距变化，重点关注差距缩小/领先扩大。

## 执行流程（高层）

> **默认执行模式**：Step 3（派生指标计算）按银行拆分天然独立，Step 4（排名计算）按指标维度拆分也天然独立，**必须使用 Team 并行模式**（详见 `references/05_team_parallel.md`）。Step 1-2、Step 5-6 为串行阶段，由主 Agent 执行。

### Step 1: 加载数据

- 读取 `~/RetailAnalysis/data/standard/<bank>.json`（Skill 1 主输出）
- 读取 `~/RetailAnalysis/data/text/<bank>.json`（Skill 2 主输出）
- 读取 `~/RetailAnalysis/data/benchmark_database.json`（历史数据库，如存在）

> ⚠️ **standard / text schema 契约**：两份 JSON 均已强制统一到 `values[]` 数组结构（`standard-v1.0` / `text-v1.0`）。读取前必须校验 `_schema_version`，取值必须走 `extract_metric_value()` + `_period_label_matches()`，**禁止**读 `metric.get("value")` 扁平字段。**详见 `references/03_data_contract.md`。**
> 某家银行在当期核心指标下取不到值时，必须先打印原始 JSON 到日志，不得默默写 "-"。

### Step 2: 更新数据库

1. 将本期数据合并入历史数据库
2. 检查数据冲突：本期上期数据 vs 数据库已有上期数据
3. 如不一致，以本期披露的为准，原值移入备注
4. **F/G 类回填**：对每家银行，检查 `text:零售分部营业净收入(文字)` 等 F/G 类字段是否有值，按回填映射表执行回填（详见 `references/01_directory_and_logging.md` 第 3 节）
5. 保存 `~/RetailAnalysis/data/benchmark_database.json`

### Step 3: 计算派生指标

按维度一至四的公式计算所有派生指标。

### Step 4: 计算排名

对每个指标、每个年度，在**7家银行**范围内：
1. 计算基准行（或用户指定银行）排名
2. 计算与前/后一名的差距
3. 与上期排名对比，标注变化

### Step 5: 生成分析报告

输出 `~/RetailAnalysis/output/<bank_short>/benchmark_analysis.md`（按基准行隔离），包含数据总览表、趋势分析、排名变化追踪、重点发现。

### Step 6: 生成结构化输出

保存 `~/RetailAnalysis/output/<bank_short>/benchmark_analysis_result.json`。

### Step 7: 完整性校验（2026-04-29 强制）

生成 `benchmark_analysis_result.json` 后，**必须**在输出前做一次结构化自检：
- `meta.dimensions` 长度 >= 4
- 覆盖本期/上期 rankings
- 核心指标 2025 年参排银行数 >= 3
- 必要时执行降级策略（全行口径替代零售分部口径）

**详见 `references/04_dimensions_and_schema.md` 第 3 节。**

### Step 8: `benchmark_analysis_result.json` Schema

固定 Schema（meta/results/rankings 三层结构），**详见 `references/04_dimensions_and_schema.md` 第 4 节**。

## 输出

| 文件 | 说明 |
|------|------|
| `~/RetailAnalysis/data/benchmark_database.json` | 历史对标数据库（持续积累，7家银行） |
| `~/RetailAnalysis/output/<bank>/benchmark_analysis.md` | 分析报告 |
| `~/RetailAnalysis/output/<bank>/benchmark_analysis_result.json` | 结构化分析结果 |
| `~/RetailAnalysis/output/<bank>/同业财报数据分析.pdf` | PDF 交付物 |

## PDF 交付物

在 `benchmark_analysis.md` 与 `benchmark_analysis_result.json` 已生成的基础上，生成面向高层审阅的专业 PDF 报告。

**前置条件**：
- `benchmark_analysis_result.json` 通过 Step 7 完整性校验
- VIS 资产已固化（通过 `build_by_bank_vis.py --bank <short>` 构建）
- Agent 已 `read_file` `references/02_pdf_runtime.md` 和 `_vendor/.../RUNTIME.md`
- `validate_bank_logo(base_bank)` 通过

**调用约定**（详见 `references/02_pdf_runtime.md` 第 3 节）：

```python
from html_to_pdf import build_report
from bank_context import resolve

ctx = resolve(base_bank=base_bank_param, query=user_query)
build_report(
    ctx=report_ctx,
    template_path=str(skill_dir / "assets" / "report_template.html"),
    output_html=str(ctx.output_path("benchmark_analysis_report.html")),
    output_pdf=str(ctx.output_path("同业财报数据分析.pdf")),
    style_overrides_path=str(skill_dir / "assets" / "style_overrides.css"),
    base_bank=ctx.short_name,
    header_text=f"{ctx.full_name}视角 · 同业财报数据分析",
    runtime_acknowledged=True,
)
```

## 关键规则

1. **银行范围锁定7家**：所有排名、对比、趋势分析仅在头部7家范围内进行
2. **以最新期为准**：数据冲突时采用最新期年报数据，原值记入备注
3. **排名变化必须标注**：任何排名变化都必须明确标注方向和幅度
4. **差距变化格外指出**：与前/后一名的差距变化属重点关注事项
5. **数据缺失不补**：缺失时不参与排名计算，不做插值填充
6. **计算公式透明**：所有派生指标的计算公式必须在输出中说明
7. **备注不可省略**：口径变化、数据修订、来源冲突的备注是输出质量关键
8. **按基准行隔离产物**：所有产物必须写到 `~/RetailAnalysis/output/<bank_short>/`，禁止直接写到 output/ 根目录
9. **LOGO 校验必跑**：每次 `build_report` 前必须先 `validate_bank_logo(base_bank)`，失败时走文字降级
10. **日志必留**：每次运行（无论成功失败）必须生成 `logs/skill3/<session_id>.log`
11. **临时脚本规范**：所有一次性脚本必须使用 `_runtime_generate_` 前缀，完成后立即删除

## 依赖

- Python 3.10+
- pandas
- pyyaml
- jinja2（PDF 交付物模板渲染）
- playwright（HTML → PDF）
- Pillow（PDF 校验）

---

## 金融免责声明

> ⚠️ 本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。投资有风险，决策需谨慎。

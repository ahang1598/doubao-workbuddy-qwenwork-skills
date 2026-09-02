---
name: strategic-insight
description: 战略洞察生成器。基于财报分析生成3-5条核心战略洞察，重点关注零售业务相关高频词和组织架构变化，按优先级排序输出增长机会、风险预警和效率提升建议。**用户需指定基准银行**，如"以A银行为基准/为主角生成零售战略洞察报告"。
triggers:
  # —— 推荐的精准激活表述（显式指定基准行 / 报告主角） ——
  - 以某某银行为基准生成战略洞察报告
  - 以xxx银行为基准的零售战略洞察
  - 以xxx银行为主角的战略洞察分析
  - 给xxx银行零售高管看的战略洞察报告
  - 基于对标数据，生成以xxx银行为基准的战略洞察
  - 基准银行战略洞察
  # —— 业务维度激活词 ——
  - 战略洞察
  - 经营洞察
  - 核心判断
  - 高频词分析
  - 组织架构变化
  - 增长机会
  - 风险预警
  - 效率提升
  - 零售战略
  - 经营建议
  - 管理层关注
  - 战略方向
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - file   # 读取 output/ 下的对标分析结果，写出战略洞察 PDF 报告
---

## ✅ 能力边界

**能做：**
- 基于 benchmark-analysis 的对标结果，生成 **3–5 条核心战略洞察**（增长机会 / 风险预警 / 效率提升），按优先级排序
- 结合零售业务高频词与组织架构变化，产出面向高管视角的战略洞察 PDF 报告
- 按用户指定的**基准行 / 报告主角**定制洞察结论

**不能做（超出范围）：**
- 不下载财报、不提取数据、不做原始对标计算（依赖上游 ①②③④）
- 无对标数据时不产出洞察，不脱离数据主观臆断
- 不做治理韧性/言行比对等穿透分析（属于 strategy-governance-analysis）

# 战略洞察生成器

## 共享 PDF Runtime（已随包内置）

本 Skill 生成 PDF 所需的共享 PDF Runtime 已随包内置在 `_vendor/pdf_report_builder_runtime/` 下，**独立安装态（发布包）无需执行任何初始化命令**，可直接生成 PDF 报告。

> 仅仓库开发态需要从共享源码重新注入：执行 `python3 scripts/release.py --sync-paths`（`release.py` 仅存在于仓库开发态，发布包中不含此脚本，无需也无法运行）。

## 📁 目录约定（所有 Skill 共享）

> **重要**：本 Skill 系列不再把配置/数据/输出放在仓库里，统一落到用户主目录：
>
> ```
> ~/RetailAnalysis/              # 默认 Home；可通过 RETAIL_ANALYSIS_HOME 覆盖
> ├── config/                    # 全局共享配置（降级兜底）
> ├── data/
> │   ├── extracted_text/        # 财报解析产物（章节检索输入）
> │   ├── standard/              # Skill 1 主输出：<bank>.json（本 Skill 输入）
> │   ├── text/                  # Skill 2 主输出：<bank>.json（本 Skill 输入）
> │   ├── partial/<bank_short>/  # 本 Skill 按客户隔离的中间产物
> │   └── insight_result.json    # 向后兼容的机器可读入口
> ├── output/<bank_short>/
> │   ├── insight_result.json
> │   ├── strategic_insight_report.html
> │   └── 同业战略洞察报告.pdf
> ├── report_assets/             # PDF 生成所需视觉资产（LOGO/palette/封面图等）
> └── logs/
> ```
>
> **本 Skill 本地配置**（优先于全局 config/）：
>
> ```
> skills/skill4-strategic-insight/
> ├── config/                    # Skill 4 本地配置副本（pack/publish 前由 shared/config-sources 生成）
> │   ├── banks.yaml             # 银行列表
> │   ├── warning_rules.yaml     # 预警阈值
> │   └── output_format.md       # 输出格式
> └── assets/
> ```
>
> 详细目录约定见 Skill 1 `SKILL.md` 开头。

## 📖 生成 PDF 前必读：RUNTIME.md（2026-04-29 新增·强制）

> **Agent 在首次触发 PDF 生成前必须 `read_file` 运行时规约**：
> `skills/skill4-strategic-insight/_vendor/pdf_report_builder_runtime/RUNTIME.md`
>
> 该文件覆盖：模板完整性守卫、rich_text 过滤器、按行视觉资产、自动下载与多级质量核验、
> P0 VIS 验收、5 项 PDF 校验。调用 `build_report(...)` 时须传 `runtime_acknowledged=True`。

## 🎯 基准行（base_bank）解析规则（2026-04-29 新增·强制）

> **与 skill3 / skill5 共享本规则**。详见 `skills/skill3-benchmark-analysis/SKILL.md` → "基准行（base_bank）解析规则"小节。本节只列 skill4 的专属差异。

**解析优先级**：显式参数 > `RETAIL_ANALYSIS_BASE_BANK` 环境变量 > 从用户 query 抽取。**无默认值**——若三者均未命中，Agent 必须主动询问用户指定基准银行。
解析由 `shared/pdf-report-builder-runtime/scripts/bank_context.py::resolve()` 统一实现。

**按行产物**：本 Skill 的所有产物写入 `~/RetailAnalysis/output/<bank_short>/`：
- `insight_result.json`
- `strategic_insight_report.html`
- `同业战略洞察报告.pdf`

**按行视觉资产**：与 skill3 共用 `report_assets/by_bank/<bank>/`，由 `build_by_bank_vis.py` 维护。PDF 生成前必须执行 `bank_context.BankContext.assets_ready()` 自检，未就绪时先运行 `build_by_bank_vis.py --bank <short>`。

**`build_report` 调用**：一律传入 `base_bank=ctx.short_name`，让共享 PDF Runtime 自动按行选取 LOGO / palette。具体示例见 skill3 SKILL.md 的 `build_report` 章节。

## 定位

基于 Skill 1（标准数据）和 Skill 2（文字数据）的提取结果，自动生成 **3-5 条核心战略洞察**，重点关注：
1. 零售业务相关的**高频词和战略表述变化**
2. **组织架构中关于零售业务的设置变化**
3. **历史战略执行效果评估**

洞察按优先级排序：**增长机会点 > 风险预警点 > 效率提升点**

## 前置条件与数据依赖

本 Skill 依赖前序 Skill 的产出数据。**执行前必须确认以下数据已就绪**，否则需先运行对应 Skill：

| 所需数据 | 路径 | 来源 Skill | 检查方法 | 缺失时执行 |
|---------|------|-----------|---------|-----------|
| 标准数据 | `~/RetailAnalysis/data/standard/<bank>.json` | **Skill 1**（标准数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/standard/<bank>.json'))"` | 运行 Skill 1，参考 `skills/skill1-standard-data-extraction/SKILL.md` |
| 文字数据 | `~/RetailAnalysis/data/text/<bank>.json` | **Skill 2**（文字数据提取） | `python -c "import json; json.load(open('~/RetailAnalysis/data/text/<bank>.json'))"` | 运行 Skill 2，参考 `skills/skill2-text-data-extraction/SKILL.md` |
| 对标数据库 | `~/RetailAnalysis/data/benchmark_database.json` | **Skill 3**（对标分析） | `python -c "import json; d=json.load(open('~/RetailAnalysis/data/benchmark_database.json')); assert d['meta']['schema_version']=='benchmark-v1.0'"` | 运行 Skill 3，参考 `skills/skill3-benchmark-analysis/SKILL.md` |

> **执行顺序**：财报下载 → Skill 1 标准提取 → Skill 2 文字提取 → Skill 3 对标分析 → **Skill 4 战略洞察**
>
> **基准行**：用户必须指定基准银行（分析主体）。本 Skill 不设默认基准行。
> 若用户未指定，Agent 应主动询问："请指定基准银行（如：以A银行为基准生成战略洞察报告）。"

## 典型用户请求

- "基于2025年的数据，生成给零售高管看的战略洞察PDF报告。"
- "今年年报中零售业务有哪些值得关注的变化？"
- "各行零售战略方向有什么新动向？"
- "组织架构有没有变化？"

## 输入/输出 Schema（权威契约）

### 依赖声明

Schema 注册表文件由 `release.py` 在打包前从仓库根 `shared/config-schemas/` 自动注入到本 Skill 的 `config/schemas/` 下，**打包后运行时按下表中的 skill 相对路径读取**。

| 数据文件 | Schema 版本 | 契约定义位置（打包后） | 读取前校验 |
|---|---|---|---|
| `~/RetailAnalysis/data/standard/<bank>.json` | `standard-v1.0` | `config/schemas/standard-v1.0.yaml` | 顶层 `_schema_version` |
| `~/RetailAnalysis/data/text/<bank>.json` | `text-v1.0` | `config/schemas/text-v1.0.yaml` | 顶层 `_schema_version` |
| `~/RetailAnalysis/data/benchmark_database.json` | `benchmark-v1.0` | 参见 `skill3-benchmark-analysis` 内的 `references/04_dimensions_and_schema.md` | `meta.schema_version` |
| `~/RetailAnalysis/data/insight_result.json`（产出） | `insight-v1.0` | `config/output_format.md` | `meta.schema_version` |

> 开发期 schema 的唯一 source of truth 在仓库根 `shared/config-schemas/`；请不要直接修改本 skill 的 `config/schemas/` 副本，由 `python scripts/release.py --sync-paths` 统一同步。

### Python 代码 Schema 约束（`scripts/build_strategic_insight.py`）

以下函数必须严格使用 `text-v1.0` 字段（已适配，禁止回退）：

| 函数 | 必须使用的字段 | 禁止使用 |
|---|---|---|
| `normalize_text_metrics()` | `metric["standard_name"]`, `metric["category_bucket"]` | `metric.get("name")`, `metric.get("metric")` |
| `metric_change()` | `record["values"][0]["change_pct"]`（或 `change_value` + `change_unit="%"` 兜底） | `record.get("change_pct")` 扁平读取、`record.get("change")` |
| `_text_period_end_value()` | `record["values"][i]["period_end_value"]` | `record.get("value")` 扁平读取 |

**读取时强制校验**：入口 `main()` 加载 text_payloads 后立即核对 `_schema_version == "text-v1.0"`，不匹配直接抛 `ValueError`，不做兼容读取。

### LLM subagent 消费约束

Skill 4 的分析型 subagent（战略洞察 5 条生成）在读取 standard / text / benchmark JSON 前，必须先在 prompt 中声明：
- 字段取值路径（如 `by_period[<期间>].metrics[*].values[*].period_end_value`）
- bucket 过滤约束（`category_bucket` 精确匹配，禁止子串）
- 未披露语义（`values=[]` 表示未披露，禁止推算）

## 前置条件

- Skill 1 已执行，`~/RetailAnalysis/data/standard/<bank>.json` 存在（每家银行一个 JSON，内部按期组织）
- Skill 2 已执行，`~/RetailAnalysis/data/text/<bank>.json` 存在
- Skill 3 已执行，`~/RetailAnalysis/data/benchmark_database.json` 存在（用于战略执行评估和同业对照）
- 如需做高频词和组织架构检索，还需要 `~/RetailAnalysis/data/extracted_text/` 中有对应银行的解析产物（Markdown / JSON）

## 输入

- `~/RetailAnalysis/data/standard/<bank>.json` — 标准化表格数据（Skill 1 主输出，按银行聚合多期）
- `~/RetailAnalysis/data/text/<bank>.json` — 文字描述数据（Skill 2 主输出，按银行聚合多期）
- `~/RetailAnalysis/data/extracted_text/*` — 各银行财报的章节文本（用于高频词统计、组织架构检索）

## 执行流程

> **默认执行模式**：Step 1-3 是三个**相互独立**的分析维度，**必须使用 Team 并行模式**并发执行（见下方"Team 并行模式"章节）。Step 4-6 为串行汇总步骤，由主 Agent 执行。

### Step 1: 高频词与战略表述分析

对每家银行的零售业务章节文本：

1. **提取高频词**：统计关键词频次，重点关注业务方向词（如"财富管理""数字化""养老金融"）、产品创新词、风控相关词
2. **与上期对比**：识别新增、消失、频次显著变化的高频词
3. **跨行对比**：识别行业共同趋势和基准行特有表述

### Step 2: 组织架构变化检测

搜索组织架构相关章节，检查：
- 零售相关部门的设立/撤销/合并
- 财富管理/私人银行/信用卡的组织隶属关系调整
- 新设部门（数字金融/客群经营/生态平台等）

### Step 3: 历史战略执行效果评估

- 回顾各行上期零售战略目标
- 对照本期实际表现
- 识别"说了没做到"或"做了没说"的领域

### Step 4: 生成 3-5 条核心洞察

每条洞察包含：
- **标题**：一句话核心判断
- **优先级类型**：增长机会 / 风险预警 / 效率提升
- **数据依据**：具体数值、排名或高频词变化
- **业务含义**：对零售经营的解读
- **行动建议**：后续关注方向或经营动作
- **风险提示**：口径差异、数据局限性
- **来源标注**：已披露事实 / 模型判断

**优先级排序**：增长机会点 > 风险预警点 > 效率提升点

### Step 5: 质量检查

每条洞察必须通过：
1. ✅ 有数据依据
2. ✅ 明确标注事实/判断
3. ✅ 说明口径差异风险
4. ✅ 建议有具体方向
5. ✅ 避免脱离数据推测
6. ✅ 语言适合高管阅读

### Step 6: 生成输出

保存为 `~/RetailAnalysis/data/insight_result.json`，包含：
- `executive_summary`：3-5句总体判断
- `insights`：洞察列表
- `high_frequency_analysis`：高频词分析结果
- `org_structure_changes`：组织架构变化

## 输出

| 文件 | 说明 |
|------|------|
| `~/RetailAnalysis/data/partial/<bank_short>/insight_freqword.json` | Step 1 按客户隔离的中间产物 |
| `~/RetailAnalysis/data/partial/<bank_short>/insight_orgchange.json` | Step 2 按客户隔离的中间产物 |
| `~/RetailAnalysis/data/partial/<bank_short>/insight_stratreview.json` | Step 3 按客户隔离的中间产物 |
| `~/RetailAnalysis/data/insight_result.json` | 向后兼容的机器可读入口 |
| `~/RetailAnalysis/output/<bank_short>/insight_result.json` | 当前客户结构化洞察交付物 |
| `~/RetailAnalysis/output/<bank_short>/同业战略洞察报告.pdf` | 当前客户 PDF 交付物 |

## Team 并行模式（默认执行方式）

**触发条件**：本 Skill **默认使用 Team 并行模式**（Step 1-3 是三个相互独立的分析维度，天然适合并行）。

**核心思想**：将三个互不依赖的分析维度拆分为三个 team member 并发执行，main 负责 Step 4-6 的汇总推理和输出。

### 流程

```
Step 0: 加载 ~/RetailAnalysis/data/standard/<bank>.json + ~/RetailAnalysis/data/text/<bank>.json
  │
  ├─ Step 1: team_create("skill4-insight")
  ├─ Step 2: 同一批次并行 spawn 3 个 task
  │    ├─ s4-freqword    → Step 1：高频词与战略表述分析
  │    │     输出 ~/RetailAnalysis/data/partial/insight_freqword.json
  │    │     (每家银行零售章节的高频词 Top20、与上期对比、跨行对比)
  │    ├─ s4-orgchange   → Step 2：组织架构变化检测
  │    │     输出 ~/RetailAnalysis/data/partial/insight_orgchange.json
  │    │     (零售部门增/撤/并、隶属关系调整、新设部门清单)
  │    └─ s4-stratreview → Step 3：历史战略执行效果评估
  │          输出 ~/RetailAnalysis/data/partial/insight_stratreview.json
  │          (上期战略目标 vs 本期实际表现，"说了没做到"/"做了没说")
  │    每个 member 完成后 send_message 汇报关键发现
  │
  ├─ Step 3: main 等待 3 个 member 全部完成
  ├─ Step 4: main 执行 Step 4：整合 3 个 partial 文件 + 数据指标，生成 3-5 条核心洞察
  │    按 增长机会 > 风险预警 > 效率提升 的优先级排序
  ├─ Step 5: main 执行 Step 5：质量检查（6项红线）
  ├─ Step 6: main 生成 ~/RetailAnalysis/data/insight_result.json
  ├─ Step 7: main shutdown 所有 member + team_delete
  └─ Step 8: 向用户汇报
```

### Member 职责边界

| Member | 工作内容 | 产出 |
|--------|---------|------|
| **s4-freqword** | 统计所有银行零售章节的高频词，与上期对比，跨行对比 | `insight_freqword.json` |
| **s4-orgchange** | 检索"组织架构"章节，识别零售相关部门的设立/撤销/合并/调整 | `insight_orgchange.json` |
| **s4-stratreview** | 对比各行上期战略目标与本期实际数据，标注执行偏差 | `insight_stratreview.json` |
| **Main** | 洞察合成（Step 4）、质量检查（Step 5）、输出（Step 6） |   `insight_result.json` |

> **为何洞察合成必须由 main 执行**：洞察生成需要同时参考"数据事实""高频词""组织变化""战略执行"四类信息，且要进行优先级排序和质量红线检查，属于"全局推理"任务，不适合拆分到 member。

## 质量红线

- **不得脱离数据编造结论**
- **不得把推测写成事实**
- **高频词分析必须基于实际文本统计**
- **组织架构变化必须有年报文本依据**
- **建议必须有具体方向，避免空泛表述**
- **增长机会 > 风险预警 > 效率提升 的优先级排序必须遵守**

## 🧹 运行时临时脚本命名与清理约束

> **详细规范见 `skills/skill1-standard-data-extraction/SKILL.md` → "运行时临时脚本命名与清理约束（全 Skill 统一）"小节。**

1. Agent 为本 Skill 临时撰写的洞察分析脚本（如 `analyze_org_changes.py`、`extract_org_changes_v*.py`、`generate_insight_pdf.py`）**必须**统一命名为 `_runtime_generate_<用途>_<时间戳>.py`
2. 落盘至 `~/RetailAnalysis/work/` 或 `~/RetailAnalysis/data/partial/`，**严禁**提交到 `scripts/`
3. 本 Skill 已沉淀的**正式脚本**仅包括：`build_strategic_insight.py`、`paths.py`
4. 任何一次性 PDF 生成、临时抽样分析、实验性规则验证脚本仍属于临时脚本，必须遵守 `_runtime_generate_*` 命名规范
5. 任务完成（`insight_result.json` 生成且用户验收）后，**立即删除**该临时脚本
6. 兜底：`_runtime_generate_*` 已写入 `.gitignore`；`scripts/cleanup_runtime_scripts.py` 可批量清理

## 依赖

- Python 3.10+
- pyyaml
- jinja2（PDF 交付物模板渲染）
- playwright（HTML → PDF）
- Pillow（PDF 校验）

---

## PDF 交付物（"同业战略洞察报告"）

基于本 Skill 的主输出 `~/RetailAnalysis/data/insight_result.json`，生成符合基准行 VIS 风格的 PDF 报告。

> **PDF 生成由共享 PDF Runtime（`shared/pdf-report-builder-runtime`）统一提供**。本 Skill 只负责准备数据上下文 `ctx` 和业务模板。

### 前置条件

- `~/RetailAnalysis/data/insight_result.json` 已生成
- VIS 资产已固化（见共享 PDF Runtime 的 `P0 强制前置流程`）

### 报告结构（固定 8 节）

1. **封面页**：LOGO + 标题"同业战略洞察报告"+ 副标题 + 生成日期
2. **目录页**
3. **Executive Summary**：5 句话摘要
4. **第一部分 行业全景**（高频词 / 组织架构 / 战略执行）
5. **第二部分 五大核心洞察**（按优先级排序）
6. **第三部分 基准行 vs 同业战略雷达**
7. **第四部分 给管理层的 5 条建议**
8. **附录**：数据局限 / 数据与产物索引 / 免责声明

### 样式规范

- **基础样式**：由共享 PDF Runtime 的 `style_guide.css` 统一提供
- **业务覆盖**：当前 Skill 的 `assets/style_overrides.css`（如需微调）
- **配色**：由 `~/RetailAnalysis/report_assets/vis/palette.json` 驱动
- **优先级标签**：增长机会=绿色 / 风险预警=红色 / 效率提升=蓝色

### 生成方式

调用当前 Skill 内 vendored 的共享 PDF Runtime `build_report`：

```python
import pathlib
import sys

skill_dir = pathlib.Path("<当前业务 Skill 根目录>")
vendor_scripts = skill_dir / "_vendor" / "pdf_report_builder_runtime" / "scripts"
sys.path.insert(0, str(vendor_scripts))

from html_to_pdf import build_report

build_report(
    ctx=insight_result,  # insight_result.json 内容，meta.base_bank_short 必填
    template_path=str(skill_dir / "assets" / "report_template.html"),
    output_html="~/RetailAnalysis/output/<bank_short>/strategic_insight_report.html",
    output_pdf="~/RetailAnalysis/output/<bank_short>/同业战略洞察报告.pdf",
    style_overrides_path=str(skill_dir / "assets" / "style_overrides.css"),  # 如文件不存在可省略
    base_bank="<bank_short>",
    runtime_acknowledged=True,
    margin_top="25mm",
    margin_bottom="16mm",
    header_text="同业战略洞察报告",
)
```

> `scripts/release.py` 会在 pack/publish 前自动把共享 PDF Runtime 的公共 assets/config/scripts 注入到当前 Skill 的 `_vendor/pdf_report_builder_runtime/` 下，因此运行时不需要跨目录读取共享源码。

### 产物结构

```
~/RetailAnalysis/
├── data/
│   └── insight_result.json               # 向后兼容的机器可读入口
├── report_assets/                        # VIS 资产（与共享 PDF Runtime / skill3 / skill5 共享）
└── output/<bank_short>/
    ├── insight_result.json               # 当前客户结构化交付物
    ├── strategic_insight_report.html     # 中间 HTML
    └── 同业战略洞察报告.pdf              # 最终 PDF

skills/skill4-strategic-insight/
├── SKILL.md
├── config/
├── scripts/
│   └── paths.py                          # 共享路径模块
├── assets/
│   ├── report_template.html              # 业务模板（继承共享 PDF Runtime 的 base_template）
│   └── style_overrides.css               # 业务覆盖样式（可选）
├── _vendor/
│   └── pdf_report_builder_runtime/       # pack/publish 前由 release.py 自动注入
│       ├── assets/
│       ├── config/
│       └── scripts/
```

### 报告用字规范

- 标题固定为 **"同业战略洞察报告"**
- 免责声明统一为 **"本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐"**
- 所有引用数据必须带来源标注
- 每条洞察区分"已披露事实"与"模型判断"

### 执行模式

- **默认串行**：主流程完成后由 main 串行调用当前 Skill 内 vendored 的共享 PDF Runtime，不新建 team
- **默认产物**：除兼容数据入口外，默认将 JSON、HTML、PDF 写入 `~/RetailAnalysis/output/<bank_short>/`

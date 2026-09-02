---
name: standard-data-extraction
description: 财报标准数据提取器。自动识别并提取股份制银行财报中常态化披露的、标准化程度高、行业共识性强的零售业务表格类数据，包括分部报告效益类、零售存贷款结构与定价、资产质量、银行卡手续费及全行拨备等。
triggers:
  - 提取标准数据
  - 提取表格数据
  - 提取分部报告
  - 零售分部数据
  - 存款结构
  - 贷款结构
  - 资产质量
  - 不良率
  - 拨备覆盖率
  - 五级分类
  - 银行卡手续费
  - 存款成本率
  - 贷款收益率
  - 提取效益指标
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - file   # 读取 ~/RetailAnalysis/data/reports/ 下的 PDF，写出 data/standard/ 下的 JSON
---

## ✅ 能力边界

**能做：**
- 从已下载的银行财报 PDF 中提取**表格类标准数据**：分部报告效益、零售存贷款结构与定价、资产质量（不良率/五级分类/拨备）、银行卡手续费、全行拨备等
- 面向**股份制银行**常态化、标准化披露的口径，输出结构化 JSON 到 `~/RetailAnalysis/data/standard/`
- 支持多银行、多报告期批量提取与 Team 并行

**不能做（超出范围）：**
- 不下载财报（依赖上游 cninfo-bank-reports 已把 PDF 放入 `data/reports/`）
- 不提取文字描述中的指标（AUM/客户数/财富管理收入等属于 text-data-extraction）
- 不做跨行对标或趋势分析（属于 benchmark-analysis）
- 主 Agent / Member 不直接调用外部 LLM API，精筛统一走平台子代理机制

# 财报标准数据提取器

## 📚 渐进式加载索引（按需阅读）

| 触发条件 | 阅读文件 |
|---|---|
| 首次使用 / 路径 / release.py / 临时脚本规范 | `references/01_directory_and_runtime.md` |
| 需要调指标清单（五大类）、bundle 契约、子代理 prompt、宿主适配 | `references/02_extraction_contract.md` |
| 执行 merge / 跨期校验 / 规则 S1/S2 告警排查 | `references/03_cross_period_validation.md` |
| ≥ 2 个 (银行×期) 目标 / Team 并行 / 腾讯云解析细节 / 完整示例 | `references/04_team_and_examples.md` |

> **默认工作流**：Agent 读本 SKILL.md 后按下表判断是否继续加载 references。
> 核心原则：**只读必要部分，避免把全部细节塞进上下文**。

## 定位

自动识别并提取股份制银行财报中**常态化披露**的、**标准化程度高**、**行业共识性强**的零售业务相关数据。这些数据一般以**表格形式**披露，口径相对稳定，可直接用于跨行对比和时序分析。

## 典型用户请求

- "提取某某银行 2025 年年报中的零售分部报告数据。"
- "把各家银行的零售存贷款结构和定价数据整理出来。"
- "提取信用卡贷款和非信用卡贷款的不良率。"
- "整理各行的拨备覆盖率和五级分类迁徙数据。"

## 前置条件

财报 PDF 文件已存在于 `~/RetailAnalysis/data/reports/` 目录下。

## 提取范围（概要 · 细节见 `references/02_extraction_contract.md`）

本 Skill 聚焦以下五大类**表格类标准化数据**：

1. **效益类指标（分部报告）**：零售分部 + 全行的营业净收入、利息/非利息、减值损失、业务费用、税前利润
2. **零售存款结构与定价**：个人存款活期/定期/合计的时点/平均余额 + 个人存款成本率
3. **零售贷款结构与定价**：信用卡 + 非信用卡（按揭/消费/经营/其他）细分的余额 + 个贷贷款收益率
4. **零售贷款资产质量**：信用卡 + 非信用卡细分的不良贷款额/率
5. **全行关键风控与收费指标**：银行卡手续费、全行拨备覆盖率/贷款拨备率、五级分类迁徙等

## 执行流程（高层）

> **默认执行模式**：
> - 待提取目标 **≥ 2 个** `(银行 × 报告期)` 组合时，**必须使用 Team 并行模式**（外层 bank×period 并行）
> - 待提取目标 **= 1 个**时，不创建 team，但 Step 4 的**精筛必须并行 spawn 子代理**（默认并发 3）
> - 任何场景下都**禁止**主 Agent 顺序读 bundle 自行抽取

### Step 1: 加载配置

读取当前 Skill 自带配置（仓库中由 `shared/config-sources/` 同步生成）：
- `config/banks.yaml` - 银行列表
- `config/metrics.yaml` - 指标字典和同义词

覆盖优先级：`--metrics-yaml` → `$RETAIL_ANALYSIS_CONFIG_DIR/skill1/metrics.yaml` → Skill 自带配置；禁止读取 `~/RetailAnalysis/config/`。

### Step 2: 文档解析（腾讯云专业解析服务）

使用 `scripts/tencent_doc_parser.py` 通过 COS 上传 + SSE 流式响应进行结构化解析。
首次执行前必须安装依赖并配置 `.env`。详见 `references/04_team_and_examples.md` 第 3 节。

### Step 3: 粗筛（关键字/规则，无 LLM）

**脚本**：`scripts/coarse_filter.py`
**目标**：把待提取内容压缩到原文的 5%–15%，避免把整份 Markdown 塞给 LLM
**产物**：`$RA/work/<bank>_<period>/coarse.json`（章节候选 + 表格候选，按 category_bucket 分组）

### Step 4: 精筛（LLM 子代理，**强制并行 spawn**）

**脚本**：`scripts/fine_extractor.py` + `scripts/fine_extractor_prompt.md`

`prepare` 阶段已经生成**机器可读的子代理任务清单** `fine_tasks.json`，含 `tasks[]` 和 `batches[]`。

**执行规则（硬性约束，违反则任务视为失败）**：

1. **严禁**主 Agent 自己顺序读取 bundle 并在主上下文中抽取
2. **必须**读取 `fine_tasks.json`，**按 `batches` 顺序**处理，**同一 batch 内并发 spawn** 所有 `task_id`
3. **每个 task_id 对应一个独立子代理**，使用该 task 的 `spawn_prompt` 作为 prompt
4. **默认并发度 = 3**；如需调整：`prepare --concurrency N`
5. 所有子代理完成后，主 Agent 才能进入 Step 5 的 merge

> **详细契约（bundle 结构 / 子代理输出格式 / 宿主适配）见 `references/02_extraction_contract.md`。**

### Step 5: 数据校验与合并

**脚本**：`scripts/extract_standard_metrics.py merge`

**两道校验**（自动执行）：
1. 单指标校验（单位 / valid_range / 类型）
2. 规则 S2 细项加总校验（个人存款活期+定期≈合计，信用卡+按揭+消费+经营+其他≈个人贷款合计）

**产物**：`~/RetailAnalysis/data/partial/standard_<bank>_<period>.json`

### Step 6: 生成输出（按银行聚合）

```bash
python scripts/merge_partials.py --kind standard
```

**产物**：`~/RetailAnalysis/data/standard/<bank>.json`（一家银行一个 JSON，内部按 period 组织）

**为什么不聚合为单个大文件**：
- 按银行拆分后，单个 JSON 体量可控（< 1 MB）
- 下游 Skill 3/4 天然支持"读一家算一家"的渐进处理
- 单家银行数据修正（重跑某期）不影响其他银行
- 跨年积累只需追加/替换对应银行文件

`<bank>.json` 结构（**schema 严格契约，写脚本前必读**）：

```json
{
  "bank": "某某银行",
  "bank_key": "某某",
  "kind": "standard",
  "_schema_version": "standard-v1.0",
  "bank_aliases": ["某某银行股份有限公司", "某某"],
  "periods": ["2024年度", "2025年度"],
  "by_period": {
    "2025年度": {
      "period":   "2025年度",
      "metrics":  [ /* MetricItem[]，见下方 */ ],
      "notes":    [ /* 口径/单位换算说明 */ ],
      "warnings": [ /* 超量程/加总不等等校验告警 */ ],
      "source_markdown": "/abs/.../extracted_text/某某_2025.md"
    }
  },
  "updated_at": "2026-04-30T14:48:00+08:00"
}
```

**`MetricItem` 字段契约**（每条 metric 的结构，**临时脚本必须按此过滤**）：

```json
{
  "standard_name": "零售分部营业净收入",       // 规范名，来自 config/metrics.yaml（Skill 1/2 共用字典）
  "values": [
    {
      "period_label": "2025年度",             // 原表披露的期间字面量，已归一化
      "value": 191017,                        // 数值（int 或 float）；比率类为百分比本身（如 2.35 表示 2.35%）
      "unit": "百万元",                        // "百万元" | "亿元" | "%" | "BPs"，与 config/metrics.yaml 对齐
      "raw_label_in_table": "零售银行业务 营业净收入",
      "source_line_range": [3850, 3851],
      "candidate_id": "t01",                   // 回溯到 coarse.json 中的候选表格
      "confidence": "high",                    // "high" | "medium" | "low"
      "note": "含/不含减值口径说明（可选）"
    }
  ]
}
```

**字段规则**：

1. `values` 永远是数组——同一指标在同一银行×期可能有多条（本期+上期同表、集团+本行双口径等），每条独立
2. **禁止**把 `value`/`unit` 扁平挂在 metric 上；如需承载"默认口径"元数据，请放到 `values[*]`
3. `value` 必须是数值（`int` / `float`），**不得使用字符串**；原表字符串（如 `"1,234.56"`/`"—"`）由 merge 阶段清洗
4. 比率类指标（收益率/成本率/不良率）`unit="%"`、`value` 是百分比数值本身（2.35 表示 2.35%）
5. 未披露即 `values: []`，**禁止**相减、插值或写占位 0
6. 跨期不一致/超量程/加总偏差等异常写入 `by_period.<period>.warnings`，不污染 `metrics`
7. `by_period.<period>` 是**扁平 dict**，**禁止**再嵌套 `by_period`/`periods`/`kind` 等顶层字段

**临时脚本书写指引**：

```python
# 按 standard_name 取指定期的数值
def get_value(metric: dict, target_period: str) -> float | None:
    for v in metric.get("values") or []:
        if _period_matches(v.get("period_label"), target_period):
            raw = v.get("value")
            return float(raw) if raw is not None else None
    return None
```

- 查某指标必须走 `standard_name` 精确匹配（合法取值由 `config/metrics.yaml` 定义），不要用中文子串匹配
- 查取值时**必须**遍历 `values[]` 并按 `period_label` 归一比对 `target_period`；不得只取 `values[0]`
- `period_label` 归一化：`"2025年度"` / `"2025年"` / `"2025年12月31日"` / `"报告期末"` 语义等价于 `2025年度`，详见 Skill 3 `references/03_data_contract.md`

### Step 7: 汇报结果

向用户汇报：
1. 提取了多少家银行、多少项指标
2. 缺失的数据项及原因
3. 校验异常的数据项（含规则 S1 跨期不一致、规则 S2 加总不等）
4. 需要人工确认的数据（confidence: low 的项）

## 特殊场景处置（跨期一致性校验）

标准数据**至少披露本期与上期两期数据**。提取完成后必须执行 S1、S2 规则校验。
**详见 `references/03_cross_period_validation.md`。**

## 输出

| 文件 | 说明 |
|------|------|
| `~/RetailAnalysis/data/partial/standard_<bank_key>_<period>.json` | 单次 (bank × period) 抽取落盘，可重跑 |
| `~/RetailAnalysis/data/standard/<bank_key>.json` | **主输出**：按银行聚合的多期 JSON（Skill 3/4 的输入） |

## 关键规则

1. **粗筛不调用 LLM**：Step 3 必须完全由 `coarse_filter.py` 的规则/关键字完成
2. **精筛必须结构化**：Step 4 的子代理按 `fine_extractor_prompt.md` 契约输出**纯 JSON**
3. **精筛必须并行 spawn**：读 `fine_tasks.json`、按 `batches` 分批、批内并发 spawn 独立子代理（默认并发 3）
4. **优先从表格提取**：本 Skill 的数据主要存在于财报表格中
5. **提取本期和上期**：如表格中同时披露，两期均需提取
6. **单位统一**：所有金额统一为百万元或亿元（选择表格原始单位，元数据中标注）
7. **两大分类必须遵守**：零售贷款必须分为"信用卡"和"非信用卡"两大类
8. **全行数据同步提取**：分部报告中全行合计数据必须同步提取
9. **跨期校验必须执行**：规则 S1、S2 为必选校验项
10. **禁止编造**：精筛子代理若在 candidates 中找不到某指标，必须返回 `values: []`
11. **临时脚本规范**：所有一次性脚本必须使用 `_runtime_generate_` 前缀（详见 `references/01_directory_and_runtime.md`）

## 依赖

- Python 3.10+
- 所有依赖统一写在 `requirements.txt`，首次使用先执行：
  ```bash
  pip install -r requirements.txt
  ```
- 核心依赖：`tencentcloud-sdk-python>=3.0.1334`、`cos-python-sdk-v5>=1.9.35`、`requests>=2.31.0`、`pyyaml>=6.0`
- 可选兜底（腾讯云服务不可用时）：`pdfplumber`、`PyMuPDF` (fitz)

---

## 金融免责声明

> ⚠️ 本工具提取的财报数据均来自上市银行公开披露信息。提取结果仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。投资有风险，决策需谨慎。

---
name: text-data-extraction
description: 财报文字数据提取器。自动识别并提取股份制银行财报中在文字描述中披露的核心零售指标，包括：(A)AUM、(B)客户数、(C)财富管理收入、(D)信用卡经营、(E)其他量化指标，以及(F)分部效益类指标（零售营收/利润/非息/减值，当Skill 1表格未提取到时必须补充）和(G)量价类指标（存款成本率/贷款收益率/不良率等）。**采用"粗筛(Python) + 精筛(SubAgent 子代理)"架构，严禁主 Agent / Member 自己调用 LLM API。**
triggers:
  - 提取文字数据
  - 提取AUM
  - 零售AUM
  - 客户数
  - 财富管理收入
  - 理财收入
  - 保险收入
  - 基金收入
  - 信用卡发卡量
  - 信用卡交易量
  - 私人银行客户数
  - 提取零售业务文字指标
  - 文字描述提取
  - 零售营收
  - 零售税前利润
  - 零售非息收入
  - 存款成本率
  - 贷款收益率
  - 零售贷款不良率
  - 分部效益补充
category: finance
version: "20260731"
author: 腾讯云商业银行团队
permissions:
  - file   # 读取 ~/RetailAnalysis/data/reports/ 下的 PDF，写出 data/text/ 下的 JSON
---

## ✅ 能力边界

**能做：**
- 从银行财报 PDF 的**文字描述**中提取零售指标：AUM、客户数、财富管理收入、信用卡经营、私人银行等量化指标
- 当 standard-data-extraction 的表格未覆盖时，补充分部效益（零售营收/利润/非息/减值）与量价指标（存款成本率/贷款收益率/不良率）
- 采用"粗筛（Python 规则）+ 精筛（平台子代理）"架构，输出结构化 JSON 到 `~/RetailAnalysis/data/text/`

**不能做（超出范围）：**
- 不下载财报（依赖上游 cninfo-bank-reports）
- 不提取标准表格数据的主口径（以 standard-data-extraction 为准，本 Skill 仅做文字侧补充）
- 不做跨行对标或战略分析（属于下游 Skill）
- **严禁主 Agent / Member 自己调用外部 LLM API**，精筛只能走平台子代理机制

# 财报文字数据提取器

## 📚 渐进式加载索引（按需阅读）

| 触发条件 | 阅读文件 |
|---|---|
| 首次使用 / 路径 / 命名规范 / 临时脚本 | `references/01_directory.md` |
| 需要查具体指标清单（A-H 七类 bucket）、同义词、子代理输出格式 | `references/02_bucket_details.md` |
| 执行 merge / 跨期校验 / T1/T2/T3 告警排查 | `references/03_validation_rules.md` |
| ≥ 2 个 (银行×期) 目标 / Team 并行 / fine_tasks.json 契约 / 完整示例 | `references/04_team_and_examples.md` |

> **默认工作流**：Agent 读本 SKILL.md 后按触发条件判断是否继续加载 references，避免一次性全量加载。

## 🚫 核心架构铁律（必读）

**本 Skill 采用"粗筛（纯 Python 规则） + 精筛（SubAgent 子代理）"架构，与 Skill 1 保持一致。**

| 阶段 | 执行者 | 职责 | 成本 |
|------|--------|------|------|
| 粗筛 | **Python 规则**（`prepare_text_extraction.py prepare`） | 按章节关键词 + 指标同义词定位候选段落、分 bucket、构造 bundle | 毫秒级、零 LLM |
| 精筛 | **SubAgent 子代理**（按 `text_extractor_prompt.md` 契约） | 对单 bucket 做结构化抽取，输出可回溯的指标值 JSON | 秒级、按 bucket 分批 |
| 合并 | Python（`prepare_text_extraction.py merge`） | 汇总、规则 T2 停披校验，写 partial JSON | 毫秒级 |

### 硬性约束（违反即视为任务失败）

1. **主 Agent / Member 严禁**自己调用 LLM API（腾讯云混元 / OpenAI / 等任何 LLM 接口）
2. **粗筛不调用 LLM**：`prepare_text_extraction.py` 必须完全由规则/关键字完成，保证可复现、低成本
3. **精筛必须通过子代理**：读取 `fine_tasks.json`，按 `batches` 分批、批内并发 spawn 独立子代理，每个子代理只负责**单一 bucket**
4. **禁止顺序读 bundle 自行抽取**：这会导致①主上下文爆炸；②无法并发；③上下文泄漏
5. **精筛子代理必须按 `text_extractor_prompt.md` 契约输出纯 JSON**（不带 markdown 代码块）
6. **旧的 `legacy/extract_with_llm*.py`、`legacy/final_llm_extract.py`、`legacy/extract_regex_fallback.py` 等脚本已归档**，严禁再在新代码中引用

## 定位

自动识别并提取股份制银行财报中**在文字描述中披露**的、行业比较关心的核心零售指标。这些数据有两个重要特点：

1. **口径不稳定**：经常出现"本期余额 - 本期变化 ≠ 上期披露值"的情况，因此**每一期均需记录本期规模及变动**，不能通过两期规模相减计算变化
2. **可能部分时期不披露**：只能通过前后期数据反推

## 典型用户请求

- "提取某某银行 2025 年报中的零售分部报告数据"
- "提取某某银行 2025 年年报中的零售AUM和客户数。"
- "把各家银行的财富管理收入、理财收入、保险收入整理出来。"
- "提取各行信用卡发卡量、有效卡、流通卡、交易量数据。"
- "整理私人银行客户数和AUM。"

## 前置条件

财报 PDF 文件已存在于 `~/RetailAnalysis/data/reports/`，或已有 DocParse 产物（zip/md）在 `~/RetailAnalysis/data/extracted_text/`。

## 核心提取范围（概要 · 细节见 `references/02_bucket_details.md`）

**重点章节**：管理层讨论与分析 → 主要业务回顾 → 零售银行业务；辅助：董事长/行长致辞、经营概述等

**8 个 bucket**（A~H）：
- **A. AUM**：零售AUM、私行AUM
- **B. 客户数**：个人客户、财富管理客户、私人银行客户
- **C. 财富收入**：财富管理收入、理财、保险、基金
- **D. 信用卡**：发卡量、有效/流通卡、交易量
- **F. 分部效益**：零售营收/利润/非息/减值（**Skill 1 无法从表格提取时必须从文字补充**）
- **G. 量价**：个人存款余额/成本率、零售贷款收益率/不良率
- **E/H. 渠道/其他**：手机银行MAU、代发客户数、理财规模等其他量化指标

## 执行流程（高层）

> **默认执行模式**：
> - 待提取目标 **≥ 2 个** `(银行 × 报告期)` 组合时，**必须使用 Team 并行模式**（外层 bank×period 并行）
> - 待提取目标 **= 1 个**时，不创建 team，但 Step 3 的**精筛必须并行 spawn 子代理**（默认并发 3）
> - 任何场景下都**禁止**主 Agent 顺序处理 bundle 自行抽取

### Step 1: 加载文本数据 + 粗筛（prepare 阶段）

**脚本**：`scripts/prepare_text_extraction.py prepare`

**职责**：
1. 从 DocParse zip / Markdown / 目录加载文本
2. 按章节关键词定位主要章节窗口
3. 在章节窗口内按指标同义词 + 数字单位 pattern 定位候选段落
4. 把候选段落按 `category_bucket` 分组
5. 为每个 bucket 构造 `input_bundle`
6. 生成 `fine_tasks.json`（子代理任务清单）+ `manifest.json`

**产物**：
```
$RA/work/text_<bank>_<period>/
├── coarse.json              # 粗筛结果
├── text_bundles/            # 每个 bucket 一个 bundle JSON
├── text_extraction/         # 空目录，等子代理写入
├── fine_tasks.json          # 子代理任务清单
└── manifest.json            # 编排清单
```

### Step 2: 定位零售业务章节（自动，由 prepare 完成）

粗筛自动定位"管理层讨论与分析 → 零售银行业务"等章节的行号/页码范围。

### Step 3: 精筛 —— **SubAgent 子代理并行 spawn**（强制规约）

`prepare` 阶段已生成 `fine_tasks.json`。主 Agent 必须：

1. **严禁**主 Agent / Member 自己读 bundle 并在主上下文中抽取
2. **严禁**调用任何 LLM API
3. **必须**读取 `fine_tasks.json`，按 `batches` 顺序处理，同一 batch 内并发 spawn 所有 `task_id`
4. **每个 `task_id` 对应一个独立子代理**，只负责单一 bucket
5. **默认并发度 = 3**
6. 所有子代理完成后才能进入 Step 4 merge

> **详细契约（fine_tasks.json 格式 / 宿主适配 / spawn_prompt）见 `references/04_team_and_examples.md`。**
> **子代理输出格式见 `references/02_bucket_details.md` 末尾。**

### Step 4: 合并与校验（merge 阶段）

**脚本**：`scripts/prepare_text_extraction.py merge`

```bash
python scripts/prepare_text_extraction.py merge \
    --manifest "$RA/work/text_某某_2025年度/manifest.json" \
    --prior-partial "$RA/data/partial/text_某某_2024年度.json"   # 可选，触发 T2 停披校验
```

**职责**：
1. 读取 `text_extraction/*.json`（子代理产出）
2. 合并 metrics / alerts / notes / warnings
3. 规则 T2 停披校验（需要 `--prior-partial` 参数）
4. 写 `$RA/data/partial/text_<bank>_<period>.json`

### Step 5: 跨期校验（规则 T1 / T3，由主 Agent 执行）

**T1、T3 需要跨期视野**，由主 Agent 在所有 member/子代理完成后统一执行。
**详见 `references/03_validation_rules.md`。**

告警输出到 `~/RetailAnalysis/data/text/<bank>.json` 的 `by_period.<period>.alerts` 数组中。

### Step 6: 按银行聚合输出

```bash
python scripts/merge_partials.py --kind text
```

把 `$RA/data/partial/text_*_*.json` 聚合为 `$RA/data/text/<bank>.json`（一家银行一个 JSON，内部按 period 组织）。

**`$RA/data/text/<bank>.json` 结构**（**schema 严格契约，写脚本前必读**）：

```json
{
  "bank": "某某银行",
  "bank_key": "某某",
  "kind": "text",
  "_schema_version": "text-v1.0",                    // 规范化后才有；缺失说明是旧格式，请先跑 normalize
  "periods": ["2024年度", "2025年度"],
  "by_period": {
    "2025年度": {
      "period":   "2025年度",
      "metrics":  [ /* MetricItem[]，见下方 */ ],
      "alerts":   [ /* AlertItem[]：跨期/停披告警 */ ],
      "notes":    [ /* 子代理记录的口径/换算说明 */ ],
      "warnings": [ /* 冲突候选、候选未命中等 */ ]
    }
  },
  "updated_at": "2026-04-30T14:48:00+08:00"
}
```

**`MetricItem` 字段契约**（每条 metric 的结构，**临时脚本必须按此过滤**）：

```json
{
  "standard_name": "零售分部营业净收入(文字)",      // 规范名，见下方命名表；F/G bucket 带"(文字)"后缀
  "category_bucket": "分部效益",                    // 枚举，脚本过滤优先用它，勿仅靠 standard_name 字符串匹配
  "values": [
    {
      "period_label": "2025年度",                  // "YYYY年度" | "YYYY半年度" | "YYYY一季度"/"三季度"
      "period_end_value": 1234.56,                 // 本期规模/金额；比率类为百分比数值（如 2.35 表示 2.35%）
      "change_value": 123.45,                      // 同比/较上年末的绝对变动；比率类单位见下方 change_unit
      "change_pct": 11.10,                         // 同比变动百分比（%），无披露则 null
      "change_unit": "亿元",                       // "亿元"|"万户"|"%"|"BPs"|"Pct"，与 period_end_value 单位对齐
      "unit": "亿元",                              // period_end_value 的单位
      "raw_quote": "报告期内…实现营业净收入 XXX 亿元，同比增长 YYY%。",
      "source_section": "管理层讨论与分析 > 零售银行业务",
      "source_page": 45,
      "candidate_id": "p01",                        // 回溯到 coarse.json 中的候选段落
      "calibration_note": "来自文字段，非分部报告表格；集团口径",
      "confidence": "high"                          // "high" | "medium" | "low"
    }
  ]
}
```

**`category_bucket` 枚举值（唯一合法值）**：

`AUM` | `客户数` | `财富收入` | `信用卡` | `分部效益` | `量价` | `渠道` | `其他`

**`standard_name` 规范命名**（**来自附录 02，F/G bucket 必须带 `(文字)` 后缀，否则跨 Skill 对标会识别错行**）：

| bucket | standard_name 规范值 |
|---|---|
| `AUM` | `零售AUM规模`、`私行AUM` |
| `客户数` | `个人客户数`、`财富管理客户数`、`私人银行客户数` |
| `财富收入` | `财富管理收入`、`理财收入`、`保险收入`、`基金收入` |
| `信用卡` | `信用卡累计发卡量`、`信用卡有效卡量`、`信用卡流通卡量`、`信用卡交易量` |
| `分部效益` | `零售分部营业净收入(文字)`、`零售分部税前利润(文字)`、`零售非息净收入(文字)`、`零售信用减值损失(文字)` |
| `量价` | `个人存款余额(文字)`、`个人存款成本率(文字)`、`零售贷款收益率(文字)`、`零售贷款不良率(文字)` |
| `渠道` / `其他` | 自由命名，保留原文表述 |

**⚠️ 临时脚本书写指引（避免"以为提取错了"的误判）**：

1. **按 bucket 过滤**优先使用 `metric["category_bucket"]`，**不要**仅对 `standard_name` 做"零售 in name / 分部 in name"等子串匹配——F bucket 的规范名是 `零售分部营业净收入(文字)`，G bucket 是 `个人存款成本率(文字)`，AUM/客户数/财富收入/信用卡 bucket 的名字里**根本不含"零售"或"分部"**，用子串过滤会漏掉绝大多数 metric。
2. 查"分部效益"应写：`[m for m in metrics if m.get("category_bucket") == "分部效益"]`。
3. 查名字时必须兼容后缀：`name.rstrip("(文字)").rstrip("（文字）")`，不要 hardcode 精确等号。
4. `values` 是**数组**（因为同一指标可能在同一 period 内有多个候选/多口径），脚本统计覆盖率时按 `len(m["values"]) > 0` 判断是否真正提取到。
5. `values[*].period_end_value` 和 `change_value` 为 `null` 时表示"原文未披露"，**禁止**做相减推算。
6. 比率类指标（成本率/收益率/不良率）`unit = "%"`，`period_end_value` 是**百分比数值本身**（如 `2.35`），不是小数 `0.0235`。
7. 调试打印时推荐：`print(f"{m['category_bucket']} | {m['standard_name']} | n_values={len(m['values'])}")`。

**⚠️ Schema 版本强制校验**

- 任何读取 `$RA/data/text/<bank>.json` 的脚本，必须先校验 `_schema_version == "text-v1.0"`，**不兼容旧版本**
- 精筛子代理产出 / `merge_partials.py` 聚合时必须按上述契约写入，禁止保留 `name`/`metric`/`value_unit`/`change_amount` 等历史别名
- 若遇到旧格式 JSON，用 `scripts/normalize_text_json.py --apply` 一次性迁移；完成后该脚本不再作为常规流程的一部分

### Step 7: 汇报结果

向用户汇报：
1. 各 bucket 提取到的指标数 / 覆盖率
2. 规则 T1（反推不一致）、T2（停披）、T3（口径变化）触发的告警
3. confidence = low 的数据项（需人工复核）

## 输出

| 文件 | 说明 |
|------|------|
| `~/RetailAnalysis/data/partial/text_<bank_key>_<period>.json` | 单次 (bank × period) 抽取落盘，可重跑 |
| `~/RetailAnalysis/data/text/<bank_key>.json` | **主输出**：按银行聚合的多期 JSON（Skill 3/4 的输入） |

## 关键规则

1. **禁止自己调 LLM**：主 Agent / Member 严禁调用任何 LLM API，精筛必须通过 SubAgent 子代理完成
2. **粗筛不调用 LLM**：`prepare_text_extraction.py` 必须完全由规则/关键字完成
3. **精筛必须并行 spawn**：读 `fine_tasks.json` → 按 `batches` 分批、批内并发 spawn 独立子代理（默认并发 3）
4. **子代理输出必须结构化**：按 `text_extractor_prompt.md` 契约输出纯 JSON（不带 markdown 代码块）
5. **规模和变动独立记录**：每期的 `period_end_value` 和 `change_value` 必须从原文分别提取，严禁通过两期规模相减计算变动
6. **口径备注必须保留**：文中任何对数据口径的说明必须完整记录到 `calibration_note`
7. **缺失即缺失**：如果某行某期未披露某指标，`values: []`，不做推算
8. **原文必须保留**：每个数值必须有 `raw_quote` 和 `candidate_id` / `source_page`
9. **区分章节来源**：同一指标如在多个 candidate 中出现且冲突，两个都输出并在 `warnings` 中说明优先来源
10. **特殊场景校验必须执行**：规则 T1、T2、T3 为必选校验项
11. **临时脚本规范**：所有一次性脚本必须使用 `_runtime_generate_` 前缀（详见 `references/01_directory.md`）

## 依赖

- Python 3.10+
- `pyyaml>=6.0`
- 不再需要 `tencentcloud-sdk-python`（LLM 调用已迁移到宿主子代理，本 Skill 脚本**零 LLM 依赖**）
- 可选：`pdfplumber` / `PyMuPDF`（仅在没有 DocParse 产物时做本地兜底）

---

## 金融免责声明

> ⚠️ 本工具提取的财报数据均来自上市银行公开披露信息。提取结果仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐。投资有风险，决策需谨慎。

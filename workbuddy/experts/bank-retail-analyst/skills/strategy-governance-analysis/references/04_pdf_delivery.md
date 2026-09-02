# Skill 5 · 附录 04：PDF 交付物生成

> **触发阅读条件**：任何 PDF 生成任务、base_bank 解析、模板样式调整、`build_report` 调用前必读。

## 1. 生成 PDF 前必读：RUNTIME.md（强制）

> **Agent 在首次触发 PDF 生成前必须 `read_file` 运行时规约**：
> `skills/skill5-strategy-governance/_vendor/pdf_report_builder_runtime/RUNTIME.md`
>
> 该文件覆盖：模板完整性守卫、rich_text 过滤器、按行视觉资产、自动下载与多级质量核验、P0 VIS 验收、5 项 PDF 校验。调用 `build_report(...)` 时须传 `runtime_acknowledged=True`。

## 2. 基准行（base_bank）解析规则

> **与 skill3 / skill4 共享本规则**。详见 `skills/skill3-benchmark-analysis/references/02_pdf_runtime.md` → "基准行解析规则"小节。本节只列 skill5 的专属差异。

**解析优先级**：显式参数 > `RETAIL_ANALYSIS_BASE_BANK` 环境变量 > 从用户 query 抽取。**无默认值**——若三者均未命中，Agent 必须主动询问用户指定基准银行。

**skill5 基准行可扩展性**：用户需指定基准行和对标行。当用户以**非默认 5 家**中的银行为基准行时（例如"分析某某银行战略与治理"），本 Skill 仍按原 5 家范围做同业参照，但报告**基准行画像 + 风险点 + 治理建议**切换到用户指定的银行；若指定的基准行不在 5 家范围内，则自动将其**并入对标组**以保证分析可行，需要在报告首页明确标注"分析主体为 XX"。

**按行产物**：本 Skill 的所有产物写入 `~/RetailAnalysis/output/<bank_short>/`：
- `strategy_governance_result.json`
- `strategy_governance_report.md`
- `strategy_governance_report.html`
- `战略与治理分析报告.pdf`

**按行视觉资产**：与 skill3/skill4 共用 `report_assets/by_bank/<bank>/`，由 `build_by_bank_vis.py` 维护。

**`build_report` 调用**：一律传入 `base_bank=ctx.short_name`，让共享 PDF Runtime 自动按行选取 LOGO / palette。

## 3. 前置条件

- `~/RetailAnalysis/data/strategy_governance_result.json` 与 `~/RetailAnalysis/output/<bank>/strategy_governance_report.md` 都已存在且为本次最新
- VIS 资产已固化（见共享 PDF Runtime 的 `P0 强制前置流程`）

## 4. 报告结构（10 节）

| # | 节 | 关键组件 |
|---|---|---|
| 1 | **封面页** | `.cover` + `.tag` "SKILL 5 · STRATEGY & GOVERNANCE" |
| 2 | **目录页** | 8 节目录 |
| 3 | **执行摘要** | `.executive-summary` + `.kpi-row` + `.radar-card` |
| 4 | **第一部分 时间骨架** | `.landscape-table` + **`.leader-timeline`** + **`.org-heatmap`** |
| 5 | **第二部分 言行比对** | `.landscape-table` + `.two-col` + **`.continuity-tag`** |
| 6 | **第三部分 关键节点反事实** | `.insight-card` + `.evidence-table` + **`.counterfactual-range`** |
| 7 | **第四部分 治理结构** | `.evidence-table` + `.insight-card` + `.radar-card` |
| 8 | **第五部分 战略摇摆点诊断** | **`.swing-card`** |
| 9 | **第六部分 建议方案** | **`.recommendation-col` × 3** |
| 10 | **收尾 · 数据与免责声明** | `.appendix-box` + `.disclaimer` |

### skill5 专属组件（由 `assets/style_overrides.css` 定义）

1. `.leader-timeline` 横向 Gantt
2. `.org-heatmap` 组织变革热力图
3. `.continuity-tag` 战略延续性三色标签
4. `.counterfactual-range` 反事实置信区间条形图
5. `.swing-card` 战略摇摆诊断卡
6. `.recommendation-col` 建议三栏布局

## 5. 样式规范

- **基础样式**：由共享 PDF Runtime 的 `style_guide.css` 统一提供
- **业务覆盖**：当前 Skill 的 `assets/style_overrides.css`
- **配色**：由 `~/RetailAnalysis/report_assets/vis/palette.json` 驱动
- **LOGO 尺寸**：305 × 94 px（与 skill3 一致）
- **封面 kicker**：`SKILL 5 · STRATEGY & GOVERNANCE`

## 6. 正式报告生成方式

必须使用 Skill 5 适配器。它会合并 `strategy_governance_result.json` 与 12 个 `partial/sg_*.json`，补齐领导时间线、组织热力图、言行矩阵、五节点反事实、董事会/股东治理、摇摆点及三类建议：

```bash
python scripts/render_strategy_governance_report.py \
  --base-bank 某某 \
  --result-json ~/RetailAnalysis/output/某某/strategy_governance_result.json \
  --write-enriched-result
```

禁止直接把原始 `strategy_governance_result.json` 传给 `build_report()`。原始 JSON 字段位于 `phase1_timeline`、`phase2_narrative`、`phase3_counterfactual`、`phase4_governance`，而模板读取 `phase1`~`phase4`；绕过适配器会导致报告大量降级为“待填充”。

> **唯一入口硬规则**：正式 HTML/PDF 只能由上面的适配器生成。任何 `_runtime_*.py` 临时脚本都不得直接调用 Playwright、`build_report()`、pypdf 或手工拼接 HTML，不得把产物写到 `~/RetailAnalysis/output/` 根目录。适配器会强制校验 `sg-v1.1`、12 个 partial、上下文红线、第 2 页目录、10~30 页范围及 Runtime 五项视觉检查；终验通过前所有产物仅写唯一临时文件，失败时不覆盖正式交付物。

## 7. 报告用字规范

- 标题固定为 **"战略与治理分析报告"**
- 免责声明统一为 **"本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐"**
- 封面 `.tag` 使用 `SKILL 5 · STRATEGY & GOVERNANCE`
- 数值精度：战略韧性得分整数、言行一致度 ρ 保留 2 位小数、反事实区间用 `+X.XXpp ~ +Y.YYpp`
- **以中文为主**；英文仅保留在 `.section-kicker`、LOGO 原始字符、通用技术缩写
- 反事实结论每处必须带 **"模型推演，非事实"** + 置信度（低/中/高）

## 8. 产物结构

```
~/RetailAnalysis/report_assets/         ← 与共享 PDF Runtime / skill3 / skill4 共享
├── annual_report/<bank>_<year>_annual_report.pdf
├── logo/{logo.png, logo_base64.txt, logo_source.txt}
└── vis/{cover,toc,finance}-*.png, palette.json

skills/skill5-strategy-governance/
├── assets/
│   ├── report_template.html              ← 业务模板（继承共享 PDF Runtime 的 base_template）
│   └── style_overrides.css               ← 业务覆盖样式
└── _vendor/
    └── pdf_report_builder_runtime/       ← pack/publish 前由 release.py 自动注入

~/RetailAnalysis/output/<bank>/
├── strategy_governance_report.md
├── strategy_governance_report.html
├── 战略与治理分析报告.pdf
└── pdf_check/skill5-*.png
```

## 9. 执行模式

- **默认串行**：主流程完成后由 main 串行调用当前 Skill 内 vendored 的共享 PDF Runtime，不新建 team
- **默认产物**：除 JSON + MD 外，默认继续生成 `~/RetailAnalysis/output/<bank>/战略与治理分析报告.pdf`

## 10. 与 skill4 / skill3 PDF 的边界

| 对比项 | skill4 PDF | skill3 PDF | **skill5 PDF** |
|---|---|---|---|
| **样式基础** | 共享 PDF Runtime `style_guide.css` | 共享 PDF Runtime `style_guide.css` | 共享 PDF Runtime `style_guide.css` |
| 封面 kicker | `SKILL 3 · STRATEGIC INSIGHT` | `同业对标分析` | **`SKILL 5 · STRATEGY & GOVERNANCE`** |
| 核心页数 | 8 节 | 10 节 | **10 节（含反事实专章）** |
| 专属组件 | 优先级洞察卡 | 5 维度横截面表 | **领导时间线 + 反事实置信区间图 + 战略摇摆诊断卡 + 五角雷达** |
| 面向受众 | 零售高管 | 零售对标分析师 | **董事会与战略委员会** |

> 三份 PDF **装订风格完全一致**，可合订为《某某银行零售业务战略参阅集》。

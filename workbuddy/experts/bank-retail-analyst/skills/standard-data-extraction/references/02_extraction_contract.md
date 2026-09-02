# Skill 1 · 附录 02：粗筛 + 精筛契约与子代理调用规范

> **触发阅读条件**：需要调试精筛质量、修改 bundle 构造、spawn 子代理、多宿主适配时。

## 1. 提取范围（五大类表格类标准化数据）

### ① 效益类指标（分部报告）

**数据位置**：财务附注 → 业务分部报告
**提取对象**：零售金融分部/零售银行分部 + 全行合计

| 指标 | 说明 | 单位 |
|------|------|------|
| 营业净收入 | 零售分部营业净收入（=利息净收入+非利息净收入） | 百万元/亿元 |
| 内部利息净收入 | 零售分部内部资金往来利息净收入 | 百万元/亿元 |
| 外部利息净收入 | 零售分部对外利息净收入 | 百万元/亿元 |
| 利息净收入 | 零售分部利息净收入合计 | 百万元/亿元 |
| 手续费及佣金净收入 | 零售分部中间业务收入 | 百万元/亿元 |
| 信用减值损失 | 零售分部信贷减值拨备 | 百万元/亿元 |
| 折旧及摊销 | 零售分部折旧摊销费用 | 百万元/亿元 |
| 业务费用 | 零售分部营业支出（含/不含减值损失） | 百万元/亿元 |
| 税前利润 | 零售分部税前利润 | 百万元/亿元 |

> **同时提取全行口径**的同名指标，以便计算零售占比。
> **提取本期和上期（如披露）**，以便计算同比变化。

### ② 零售存款结构与定价

**数据位置**：管理层讨论与分析 → 负债结构，或财务附注 → 客户存款

| 指标 | 单位 |
|------|------|
| 个人存款-活期-时点余额 | 百万元/亿元 |
| 个人存款-定期-时点余额 | 百万元/亿元 |
| 个人存款-合计-时点余额 | 百万元/亿元 |
| 个人存款-活期/定期/合计-平均余额 | 百万元/亿元 |
| 个人存款成本率 | % |

### ③ 零售贷款结构与定价

**数据位置**：管理层讨论与分析 → 资产结构/零售贷款，或财务附注 → 发放贷款

提取时**必须将细项分为两大类**：

**信用卡贷款**：信用卡贷款-时点/平均余额

**非信用卡贷款（按细项）**：
- 住房按揭贷款-时点/平均余额
- 消费贷款-时点/平均余额
- 经营贷款-时点/平均余额
- 其他个人贷款-时点余额
- 个人贷款-合计-时点/平均余额
- 个贷贷款收益率（%）

### ④ 零售贷款资产质量

**信用卡贷款资产质量**：信用卡-不良贷款额、信用卡-不良贷款率

**非信用卡贷款资产质量（按细项，如有披露）**：
- 住房按揭-不良贷款额/率
- 消费贷-不良贷款额/率
- 经营贷-不良贷款额/率
- 个人贷款-合计-不良贷款额/率

### ⑤ 全行关键风控与收费指标

| 指标 | 说明 | 单位 |
|------|------|------|
| 银行卡手续费收入（集团口径） | 含在手续费及佣金收入明细中 | 百万元/亿元 |
| 银行卡手续费收入（本行口径） | 如有单独披露 | 百万元/亿元 |
| 全行拨备覆盖率 | 贷款损失准备/不良贷款 | % |
| 全行贷款拨备率 | 贷款损失准备/贷款总额 | % |
| 全行拨备变化 | 本期计提、转回、核销等 | 百万元/亿元 |
| 五级分类迁徙情况 | 正常→关注→次级→可疑→损失的迁徙率 | % |

## 2. 粗筛机制（Step 3 · 无 LLM）

**目标**：在完整的 Markdown 中快速定位与五大类指标相关的**候选章节**和**候选表格**，将待提取内容压缩到原文的 5%–15%。

**脚本**：`scripts/coarse_filter.py`

**匹配规则**（三层递进）：
1. **章节级**：基于 `CHAPTER_KEYWORDS`（分部报告 / 存款 / 贷款 / 资产质量 / 拨备 / 手续费）定位标题
2. **表格级关键字**：对每个 Markdown 表格取其上下文（默认向上 20 行、向下 5 行），按 `metrics.yaml` 的 `standard_name + synonyms` 做子串匹配
3. **章节感知兜底**：表格若落在某 CHAPTER 内，触发该章节的短词集合（如"营业净收入"、"税前利润"、"不良率"），按章节映射补登命中指标

**产物**：
```
$RETAIL_ANALYSIS_HOME/work/<bank>_<period>/coarse.json
{
  "chapter_candidates": [ { chapter_group, heading, line_no, matched_keywords } ],
  "table_candidates":   [ { start_line, end_line, heading_chain, hit_metrics[], hit_keywords[], score, context_markdown } ],
  "table_candidates_by_category": { "分部报告": [...], "零售存款": [...], ... }
}
```

每个 candidate 带**命中指标 ID + 相关性 score**，按 score 降序排列。

## 3. 精筛阶段（Step 4 · LLM 子代理，强制并行 spawn）

**脚本**：`scripts/fine_extractor.py` + `scripts/fine_extractor_prompt.md`

**分批策略**：按 `category_bucket`（分部报告 / 零售存款 / 零售贷款 / 资产质量 / 收费指标 / 风控指标 / 五级分类）拆分 bundle，**每个 bucket 必须对应一个独立子代理任务**。

**bundle 结构**（`extract_standard_metrics.py prepare` 会自动调用 `fine_extractor.build_bundles`）：
```json
{
  "bank": "某某银行",
  "period": "2025年度",
  "category_bucket": "分部报告",
  "target_metrics": [ { standard_name, unit, synonyms, valid_range } ],
  "candidates":     [ { candidate_id, heading_chain, context_markdown, hit_metrics, score } ]
}
```

### 3.1 子代理任务清单 `fine_tasks.json`

`prepare` 阶段已经为主 Agent 生成了机器可读的子代理任务清单：

```
$RETAIL_ANALYSIS_HOME/work/<bank>_<period>/fine_tasks.json
{
  "bank": "某甲银行",
  "period": "2025年度",
  "concurrency": 3,
  "prompt_template": "/abs/…/fine_extractor_prompt.md",
  "extraction_dir": "/abs/…/work/<bank>_<period>/extraction",
  "tasks": [
    {
      "task_id": "fine-某甲银行-2025年度-分部报告",
      "bucket": "分部报告",
      "bundle_path": "/abs/…/bundles/bundle_分部报告.json",
      "output_path": "/abs/…/extraction/分部报告.json",
      "batch_index": 0,
      "spawn_prompt": "你是 Skill1 精筛子代理，负责…"
    },
    …
  ],
  "batches": [
    ["fine-…-分部报告", "fine-…-零售存款", "fine-…-零售贷款"],
    ["fine-…-资产质量", "fine-…-收费指标", "fine-…-风控指标"],
    ["fine-…-五级分类"]
  ]
}
```

### 3.2 执行规则（硬性约束）

1. **严禁**主 Agent 自己顺序读取 bundle 并在主上下文中抽取 —— 这会造成：①主上下文爆炸；②无法并发；③上下文泄漏到后续步骤。
2. **必须**读取 `fine_tasks.json`，**按 `batches` 顺序**处理，**同一 batch 内并发 spawn** 所有 `task_id`。
3. **每个 task_id 对应一个独立子代理**，使用该 task 的 `spawn_prompt` 作为 prompt；子代理只负责**单一 bucket**的提取。
4. **默认并发度 = 3**；如需调整：`prepare --concurrency N`，`batches` 会自动重新切分。
5. 所有子代理完成后（`extraction_dir` 下 N 个文件齐全），主 Agent 才能进入 Step 5 的 merge。

### 3.3 宿主适配（CodeBuddy / Cursor / WorkBuddy）

| 宿主 | 子代理调用方式 | 并发实现 |
|------|---------------|---------|
| **CodeBuddy** | `task` 工具，`subagent_name="code-explorer"`（或自定义子代理），`prompt=spawn_prompt`。如需持久 team，可加 `name=task_id, team_name="skill1-fine-<bank>-<period>"` 走 Team 模式 | 在**同一个响应内**把同 batch 的所有 `task` 调用放到同一个 tool call 块 |
| **Cursor** | 右侧 Chat → "Agent" 模式下的「Run in background / Send to background」；或「Spawn parallel agents」命令，prompt 粘贴 `spawn_prompt` | 同 batch 内为每个 task 各开一个后台 Agent |
| **WorkBuddy** | 并行子任务入口（"新建子任务" / "后台任务"），prompt 粘贴 `spawn_prompt` | 同 batch 内一次性派发所有 task |

### 3.4 子代理输出契约

子代理必须按 `scripts/fine_extractor_prompt.md` 的契约，**输出纯 JSON**（不带 markdown 代码块），写入 task 指定的 `output_path`：

```json
{
  "bank": "某某银行", "period": "2025年度", "category_bucket": "分部报告",
  "metrics": [
    {
      "standard_name": "零售分部营业净收入",
      "values": [
        { "period_label": "2025年度", "value": 98829, "unit": "百万元",
          "raw_label_in_table": "零售银行业务 营业净收入",
          "candidate_id": "t01", "source_line_range": [3850, 3851],
          "confidence": "high" }
      ]
    }
  ],
  "notes": [...], "warnings": [...]
}
```

**严格约束**：
- 只能从 `candidates[*].context_markdown` 取值，找不到必须返回 `values: []`，**禁止编造**
- value 必须是数值型（int/float），禁止字符串
- 单位必须与 `target_metrics.unit` 一致；原表单位不同时做换算并在 `notes` 注明
- 本期 + 上期都要提取（若表格同时披露）
- 值超出 `valid_range` 必须降级为 `confidence: "low"` 并记录到 `warnings`

## 4. 设计原则：粗筛 + 精筛

| 阶段 | 执行者 | 职责 | 成本/速度 |
|------|--------|------|----------|
| 解析 | 腾讯云 lkeap | PDF → Markdown | 10 秒级、固定成本 |
| **粗筛** | **Python 规则**（`coarse_filter.py`） | 关键字定位候选章节/表格 | 毫秒级、零 LLM 成本 |
| **精筛** | **LLM 子代理**（`fine_extractor_prompt.md`） | 按 schema 结构化提取 | 秒级、按 bucket 分批 |
| 校验 | Python 规则（`fine_extractor.validate_extraction` + S2 加总） | 单位/量程/加总校验 | 毫秒级 |
| 合并 | Python 规则（`extract_standard_metrics.py merge`） | 聚合 bucket、输出 partial JSON | 毫秒级 |

**为什么要分两阶段？**
- 粗筛把 LLM 的上下文从整份 Markdown（动辄 100k+ tokens）压缩到单 bucket 的 < 8KiB，**成本降低 10x+**
- LLM 只做它最擅长的"表格语义 → 标准 schema 对齐"
- 粗筛规则可复现、可 diff

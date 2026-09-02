# Skill 5 战略与治理分析 · 输出格式

本文件定义本 Skill 最终产物的章节、字段与写作规范。所有生成内容必须严格遵守。

---

## 主输出：`~/RetailAnalysis/data/strategy_governance_result.json`

顶层字段顺序固定为：

```
meta
phase1_timeline
phase2_narrative
phase3_counterfactual
phase4_governance
citic_swing_points      # 中信战略摇摆点（≥2 个，含诱因归因）
recommendations         # 战略隔离带 + 治理韧性 + 关键人事
risk_disclosure         # 数据缺失、降级、模型不确定性披露
```

### meta
- `base_bank`, `peer_banks`, `analysis_window` (2004-至今), `data_window` (实际有数据覆盖的年份), `generated_at`, `data_sources` (引用的 partial/standard/text 文件清单)

### phase1_timeline
- `cycles`：来自 cycles.yaml
- `leader_profiles[银行][...]`：基于 leaders_template.yaml 填入真实数据
- `org_heatmap[银行][年份][条线]`：零售/科技/风险三条线在该年的一级部室变动次数

### phase2_narrative
- `narrative_matrix[银行][年份][战略主题]`：关键词频次
- `consistency_score[]`：每条记录含 bank / keyword_group / resource / rho / lag / 判定 / 证据年份
- `continuity_score[银行][任期id]`：drift_rate + 判定（进化式继承 / 渐进式调整 / 换届式创新）

### phase3_counterfactual
- `key_nodes[]`：每个节点含 context（彼时环境）+ decisions（各行决策）+ logic（三维归因：资本约束/风险偏好/业务结构依赖）
- `citic_what_if[]`：每项含 node / scenario / impact_nlr / impact_roe / confidence（低/中/高）
- 所有 what-if 项必须带 `disclaimer: "模型推演，非事实"`

### phase4_governance
- `board_activity_corr[银行]`：董事会专业委员会议事频率 vs 业绩波动的相关系数
- `shareholder_impact[银行][事件]`：股权变化事件 → 风险边界/分红策略的影响
- `resilience_score[银行]`：含 4 个维度子分、总分、等级（A~E）、解读

### citic_swing_points
每个摇摆点包含：
- `year`, `event`（简短事件描述）
- `root_cause`：**必须**归因到 {领导更替 / 股东意志 / 监管驱动 / 组织惯性} 之一（可并列）
- `evidence`：**≥3 类证据**（年报口径变化 / 组织架构调整 / 资源投向反转 / 关键词漂移，至少 2 项）
- `lesson`：本摇摆点的教训提炼（用于衔接第六部分建议方案）

### recommendations
按三类组织，每类 3~5 条，每条字段：
```
action           # 动作：做什么
rationale        # 理由：为什么
data_evidence    # 数据依据：引用 phase1-4 的哪个子项
expected_effect  # 预期效果：3 年维度的可量化预期
responsible_role # 责任方：董事会 / 战略委员会 / 行长办公室 / 人力资源条线
time_window      # 时间窗口：3 个月内 / 1 年内 / 3 年内
```

三类命名：
- `strategy_insulation`（战略隔离带）
- `governance_resilience`（治理韧性）
- `key_personnel`（关键人事）

### risk_disclosure
- 数据缺失项（精确到银行 × 年份 × 字段）
- 降级说明（如 2004~2014 段仅有文字判断）
- 模型不确定性（反事实推演的置信度分布）

---

## 辅助输出：`~/RetailAnalysis/output/<bank_short>/strategy_governance_report.md`

### 章节顺序（与 PDF 对齐）

```
# 战略与治理分析报告
## 执行摘要
## 一、时间骨架：周期划分与领导者画像
## 二、言行比对：战略关键词 × 资源投向
## 三、关键节点反事实推演
## 四、治理结构影响机制
## 五、战略摇摆点诊断
## 六、建议方案
## 数据与免责声明
```

### 写作要求

1. **执行摘要 ≤ 600 字**：5 条核心结论 + 五家行战略韧性评分榜单
2. **禁止复述财报事实**：任何段落不得以"X 银行 YYYY 零售营收 xxx 亿"起句；必须以"数据背后的逻辑"切入
3. **言行比对表格**：每家行必须给出一张"战略关键词 × 资源投向 × ρ × 判定"的横表
4. **反事实结论必须标注**："模型推演，非事实"+置信度
5. **战略摇摆点卡片**：每个卡片固定结构
   ```
   ▍年份：YYYY
   ▍事件：一句话
   ▍诱因：{领导更替 / 股东意志 / 监管驱动 / 组织惯性}
   ▍三类证据：
     1. 年报口径变化：<具体>
     2. 组织架构调整：<具体>
     3. 资源投向反转：<具体>
   ▍教训：<一句话>
   ```
6. **建议方案**：禁止"建议关注/建议重视"等空泛表述；每条建议包含"动作—理由—数据依据—预期效果—责任方—时间窗"
7. **数据与免责声明**：结尾固定一段，注明
   - 分析窗口 2004-至今，实际数据窗口 <具体年份>
   - 降级条目清单
   - "本报告仅作研究参考，不构成任何投资建议"

---

## PDF 输出（可选）：`~/RetailAnalysis/output/<bank_short>/战略与治理分析报告.pdf`

**设计参考**：完全对齐 **skill4 同业战略洞察报告**——直接复用 `skills/skill4-strategic-insight/assets/style_guide.css` 与封面 / 目录 / 章节 / 卡片骨架；仅在 skill5 专属组件（时间线 / 反事实区间 / 摇摆卡 / 五角雷达）通过 `assets/style_overrides.css` 追加变量。详见 SKILL.md § "PDF 交付物"。

章节与 MD 对齐，10 节固定结构（封面 + 目录 + 摘要 + 6 部分 + 收尾）。

关键组件（skill5 专属，需在 overrides.css 中实现）：
- **历任领导时间线** `.leader-timeline`（5 行横向 Gantt 风格，按 `internal/system/regulator/external` 分别用 `--primary`/`--accent`/`--efficiency-blue`/`--growth-green`）
- **组织变革热力图** `.org-heatmap`（行 × 年份 × 条线三维热力表，底色 `--primary-light → --primary` 深浅映射变动次数）
- **言行一致度矩阵** 复用 `.landscape-table`（单元格底色按 ρ 值用 `--growth-green`/`--bg-light`/`--risk-red` 标注真战略 / 口号 / 话术）
- **战略延续性三色标签** `.continuity-tag.evolution/.incremental/.rupture`
- **反事实置信区间图** `.counterfactual-range`（纯 CSS 条形图，置信度用 `--text-secondary`/`--accent`/`--primary` 三档）
- **战略韧性五角雷达图** 基于 `.radar-card`（5 行叠加，中信用 `--primary`、其余用 `--accent`/`--efficiency-blue`/`--growth-green`/`--text-secondary`）
- **战略摇摆点诊断卡** `.swing-card`（基于 `.insight-card.risk` 变体，复用 skill4 头部 + 4 段 section 结构）
- **建议三栏布局** `.recommendation-col.strategy-insulation/.governance-resilience/.key-personnel`（CSS Grid 3 列，每列内嵌 `.insight-card`）

---

## 质量红线自检清单（main 生成前必须勾选）

- [ ] 所有结论段落都不是"财报事实复述"
- [ ] 反事实推演全部标注"模型推演，非事实"+置信度
- [ ] 言行一致度给出 ρ 数值而非仅描述
- [ ] 中信战略摇摆点 ≥ 2 个，且每个有 ≥ 2 类证据
- [ ] 建议方案三类齐全，每类 3~5 条
- [ ] 每条建议含六要素（动作/理由/依据/效果/责任/时间）
- [ ] 数据窗口与降级条目在 `risk_disclosure` 中显式列出
- [ ] 领导画像引用了具体年报/公告出处

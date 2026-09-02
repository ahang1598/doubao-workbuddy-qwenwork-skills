# Skill 5 · 附录 05：Team 并行模式与配置文件示例

> **触发阅读条件**：执行完整分析、team 配置、编辑 cycles.yaml / leaders_template.yaml / key_nodes.yaml 等。

## 1. Team 并行模式（默认执行方式）

> **默认执行模式**：第一、二、四阶段的三个 Step 内部相互独立（分别按周期/叙事/治理维度拆分），**必须使用 Team 并行模式**。第三阶段因涉及"同一节点下多行差异对比 + 反事实模拟"，由 main 串行推理。第三阶段结束后由 main 合成最终输出。

### 流程

```
Step 0: main 加载
        ~/RetailAnalysis/data/standard/<bank>.json
        ~/RetailAnalysis/data/text/<bank>.json
        ~/RetailAnalysis/data/benchmark_database.json
        ~/RetailAnalysis/data/insight_result.json（可选）
        skills/skill5-strategy-governance/config/{cycles,leaders_template,key_nodes,governance_scoring,narrative_keywords}.yaml
  │
  ├─ Step 1: team_create("skill5-sg")
  ├─ Step 2: 同一批次并行 spawn 5 个 task（第一/二/四阶段各 step 为独立 member）
  │    ├─ s5-cycle        → 第一阶段 1.1 周期划分 + 1.2 领导者画像 + 1.3 组织演进建模
  │    │     读 cycles.yaml / leaders_template.yaml / extracted_text/
  │    │     输出 ~/RetailAnalysis/data/partial/sg_cycle_timeline.json
  │    │            sg_leader_profiles.json
  │    │            sg_org_heatmap.json
  │    ├─ s5-narrative    → 第二阶段 2.1 叙事提取 + 2.2 动量校验
  │    │     读 narrative_keywords.yaml / extracted_text/（董事长致辞/行长报告）
  │    │         + benchmark_database.json（资源指标）
  │    │     输出 sg_narrative_matrix.json / sg_consistency_matrix.json
  │    ├─ s5-continuity   → 第二阶段 2.3 偏离度计算（依赖 s5-narrative 和 s5-cycle 的领导者画像）
  │    │     spawn 时用 message 说明"允许等待 s5-narrative 先落盘"
  │    │     输出 sg_continuity_score.json
  │    ├─ s5-governance   → 第四阶段 4.1 权力重心 + 4.2 股东意志传导
  │    │     读 extracted_text/（公司治理章节）+ benchmark_database.json
  │    │     输出 sg_board_activity.json / sg_shareholder_impact.json
  │    │     （4.3 战略韧性评分由 main 汇总，本 member 不做）
  │    └─ s5-scenario     → 第三阶段 3.1 决策情景重构
  │          读 key_nodes.yaml + benchmark_database.json
  │          输出 sg_scenario_context.json
  │          （3.2/3.3 由 main 做，因需综合前述结果）
  │    每个 member 完成后 send_message 汇报关键发现
  │
  ├─ Step 3: main 等待 5 个 member 完成（允许 s5-continuity 延后几十秒）
  ├─ Step 4: main 执行 第三阶段 3.2 差异化逻辑识别 + 3.3 基准行反事实模拟
  ├─ Step 5: main 执行 第四阶段 4.3 战略韧性评分（汇总 s5-governance + phase2 均值）
  ├─ Step 6: main 执行 风险点识别 + 建议生成 + 质量红线检查
  ├─ Step 7: main 生成 strategy_governance_result.json + strategy_governance_report.md
  ├─ Step 8: main shutdown 所有 member + team_delete
  └─ Step 9: 向用户汇报（附加 TOP3 风险点 + TOP5 建议摘要）
```

### Member 职责边界

| Member | 工作内容 | 依赖 | 产出 |
|---|---|---|---|
| **s5-cycle** | 周期划分、领导者画像、组织变革热力图 | 无（独立） | 3 个 partial JSON |
| **s5-narrative** | 叙事关键词矩阵、言行一致度矩阵 | 无（独立） | 2 个 partial JSON |
| **s5-continuity** | 战略延续性打分（领导更替前 3 年） | 依赖 s5-narrative + s5-cycle | 1 个 partial JSON |
| **s5-governance** | 董事会议事频率相关性、股东意志传导 | 无（独立） | 2 个 partial JSON |
| **s5-scenario** | 关键节点情景重构（彼时行业/监管/资产负债表状态） | 无（独立） | 1 个 partial JSON |
| **Main** | 第三阶段差异化逻辑 + 反事实模拟（3.2/3.3）<br>第四阶段战略韧性评分（4.3）<br>风险点识别 + 建议生成 + 质量红线 + 最终输出 | 所有 member 产出 | `strategy_governance_result.json` + `strategy_governance_report.md` |

> **为何差异化逻辑与反事实模拟必须由 main 执行**：这两步需要同时持有 5 家银行的叙事矩阵、决策情景、董事会活动与股权变化数据，且要做"反事实推演"这种全局推理。
>
> **为何韧性评分必须由 main 执行**：评分规则中"政策适配度"直接依赖第三阶段结论，"言行一致度"直接依赖第二阶段 2.2 结果，汇总打分属于全局推理。

### 单任务场景

如果用户只要求分析 1 家银行或 1 个阶段，退化为顺序执行，不创建 team。

## 2. 配置文件示例

### `config/banks.yaml`

```yaml
base_bank:
  name: 基准行银行
  short_name: 基准行
peer_banks:
  - {name: A银行银行, short_name: A银行, role: "战略定力正面范本"}
  - {name: B银行银行, short_name: B银行, role: "同业+投行转型对照"}
  - {name: C银行银行, short_name: C银行, role: "战略摇摆案例"}
  - {name: D银行银行, short_name: D银行, role: "换届式创新对照"}
```

### `config/cycles.yaml`

```yaml
cycles:
  - {id: cycle1, name: 经济过热, start: "2004", end: "2008", macro: "高增长高投资"}
  - {id: cycle2, name: 四万亿, start: "2009", end: "2012", macro: "信贷扩张+影子银行"}
  - {id: cycle3, name: 新常态, start: "2013", end: "2016", macro: "去杠杆+金融创新"}
  - {id: cycle4, name: 严监管, start: "2017", end: "2020", macro: "资管新规+三三四十"}
  - {id: cycle5, name: 高质量发展, start: "2021", end: "至今", macro: "房地产调整+零售深化"}
```

### `config/leaders_template.yaml`（首次执行需人工填充，后续增量维护）

```yaml
# 领导者画像模板
# background 枚举：internal / system / regulator / external
# cross_cycle：任期是否跨越 2+ 个 cycles.yaml 中定义的周期
leaders:
  基准行银行:
    - {role: 董事长, name: <待填>, tenure_start: "YYYY-MM", tenure_end: "YYYY-MM", background: system, cross_cycle: true, note: "<关键背景>"}
    - {role: 行长,   name: <待填>, tenure_start: "YYYY-MM", tenure_end: "YYYY-MM", background: internal, cross_cycle: false}
  A银行银行:
    - {role: 董事长, name: <待填>, ...}
    - ...
  # B银行 / C银行 / D银行 同构
```

### `config/key_nodes.yaml`

```yaml
key_nodes:
  - id: 2013_qianhuang
    name: 2013 钱荒
    date: "2013-06"
    shock_type: 流动性
    expected_divergence: "招行压降非标 vs B银行守势"
    resource_indicators: [同业资产占比, 非标占比, 流动性覆盖率]
  - id: 2016_mpa
    name: 2016 MPA
    date: "2016-Q1"
    shock_type: 监管
    expected_divergence: "广义信贷口径差异"
    resource_indicators: [广义信贷增速, 同业负债占比]
  - id: 2018_asset_new_rules
    name: 2018 资管新规
    date: "2018-04"
    shock_type: 监管
    expected_divergence: "非标回表节奏"
    resource_indicators: [理财净值化率, 非标余额, 表外回表规模]
  - id: 2020_covid
    name: 2020 疫情
    date: "2020-02"
    shock_type: 宏观+信用
    expected_divergence: "信用卡敞口结构"
    resource_indicators: [信用卡不良率, 消费贷不良率, 拨备覆盖率]
  - id: 2022_real_estate
    name: 2022 房地产
    date: "2022-Q2"
    shock_type: 行业
    expected_divergence: "房企敞口与按揭质量"
    resource_indicators: [按揭贷款不良率, 对公房地产不良率, 房地产相关拨备]
```

### `config/governance_scoring.yaml`

```yaml
# 战略韧性评分（满分 100）
dimensions:
  leader_stability:
    weight: 30
    rules:
      - {metric: 董事长平均任期年数, scale: {3: 10, 5: 20, 8: 30}}
      - {metric: 跨周期覆盖率, scale: {0.3: 0, 0.5: 10, 0.7: 20, 1.0: 30}}
    merge: avg
  org_inertia:
    weight: 30
    rules:
      - {metric: 一级部室平均存续年限, scale: {3: 10, 6: 20, 10: 30}}
      - {metric: 零售条线稳定性(近5年变动次数), scale: {0: 30, 1: 20, 2: 10, 3: 0}}
      - {metric: 科技条线稳定性, scale: {0: 30, 1: 20, 2: 10}}
    merge: avg
  policy_fit:
    weight: 20
    source: phase3.decision_logic
    rules:
      - {verdict: 领先, score: 20}
      - {verdict: 跟随, score: 12}
      - {verdict: 滞后, score: 5}
  narrative_consistency:
    weight: 20
    source: phase2.consistency_matrix
    rules:
      - {avg_rho_gte: 0.6, score: 20}
      - {avg_rho_gte: 0.3, score: 12}
      - {avg_rho_gte: 0.0, score: 6}
      - {avg_rho_lt:  0.0, score: 0}
```

### `config/narrative_keywords.yaml`（节选）

```yaml
keyword_groups:
  零售优先:
    keywords: [零售优先, 零售转型, 大零售, 大财富, 零售立行]
    pair_resource: [零售贷款占比, 零售人员费用占比, 财富管理AUM]
  科技驱动:
    keywords: [科技引领, 数字化转型, 金融科技, 科技赋能]
    pair_resource: [科技投入, 科技人员占比]
  风险优先:
    keywords: [风险优先, 守住底线, 稳健经营, 以质取胜]
    pair_resource: [拨备覆盖率, 信用成本, 不良新生成率]
  综合金融:
    keywords: [综合金融, 协同经营, 集团协同, 商投一体]
    pair_resource: [对公FPA, 投行发行规模]
  绿色金融:
    keywords: [绿色金融, 双碳, ESG, 可持续]
    pair_resource: [绿色信贷余额, ESG披露完整度]
```

## 3. 首次使用流程

1. 确认 `~/RetailAnalysis/data/standard/<bank>.json`、`text/<bank>.json`、`benchmark_database.json` 已就绪（skill1 / skill2 / skill3 已跑过）
2. 在仓库维护期，打开 `shared/config-sources/strategy-governance/leaders_template.yaml`，**根据最新年报的"董事会成员简历"章节**填写 5 家行历任董事长/行长（至少覆盖 2015 起）
3. 触发本 Skill：
   - "分析基准行银行 vs 招行/B银行/C银行/D银行的战略延续性与治理韧性"
   - "生成战略与治理分析报告"
   - "识别基准行在历次领导更替中的战略摇摆点"
4. Agent 将按四阶段并行执行，最终输出 JSON + MD + PDF

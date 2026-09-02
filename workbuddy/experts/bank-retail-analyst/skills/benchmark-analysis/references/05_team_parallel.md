# Skill 3 · 附录 05：Team 并行模式（策略 A / 策略 B）

> **触发阅读条件**：执行完整分析、多维度并行、配置 team 时。

## 1. Team 并行模式（默认执行方式）

**触发条件**：本 Skill **默认使用 Team 并行模式**。两种并行策略视场景二选一（推荐使用**策略 B**）。

## 2. 策略 A：按银行并行（适合"派生指标计算"阶段）

当需要对 7 家银行都计算派生指标（Step 3）时：

```
Step 0: main 加载数据库、锁定 7 家银行范围
  │
  ├─ Step 1: team_create("skill3-bank")
  ├─ Step 2: 同一批次并行 spawn 7 个 task（每家银行一个 member）
  │    member 名称："s3-bank-{简称}"，如 s3-bank-基准行、s3-bank-A银行
  │    每个 member 按维度一~四的公式为该银行计算所有派生指标（多年份时间序列）
  │    输出 ~/RetailAnalysis/data/partial/benchmark_{bank}.json
  │
  ├─ Step 3: main 等待 7 个 member 完成
  ├─ Step 4: main 汇集 7 份数据，计算排名、差距变化（需要跨行视角）
  └─ Step 5: main shutdown + team_delete + 输出
```

## 3. 策略 B：按分析维度并行（**推荐，适合一次性完整分析**）

将 4 个分析维度 + 1 个排名维度拆成 5 个独立任务：

```
Step 0: main 加载 ~/RetailAnalysis/data/standard/<bank>.json + ~/RetailAnalysis/data/text/<bank>.json
        加载 ~/RetailAnalysis/data/benchmark_database.json（如存在）并执行 Step 2（更新数据库）
  │
  ├─ Step 1: team_create("skill3-dim")
  ├─ Step 2: 同一批次并行 spawn 4 个 task（每个分析维度一个 member）
  │    ├─ s3-dim-revenue   → 维度一：零售营收分析（7家银行全年份）
  │    │     计算营收、营收占比、利息/非息收入结构、非息占比
  │    │     输出 ~/RetailAnalysis/data/partial/bench_dim_revenue.json
  │    ├─ s3-dim-credit    → 维度二：零售信用减值损失分析
  │    │     计算减值损失、减值在零售营收/全行减值中占比
  │    │     输出 ~/RetailAnalysis/data/partial/bench_dim_credit.json
  │    ├─ s3-dim-opex      → 维度三：零售营业支出分析
  │    │     计算营业支出、减值外支出、减值外支出在营收占比
  │    │     输出 ~/RetailAnalysis/data/partial/bench_dim_opex.json
  │    └─ s3-dim-spread    → 维度四：零售存贷利差分析
  │          计算存款成本率、贷款收益率、存贷利差
  │          输出 ~/RetailAnalysis/data/partial/bench_dim_spread.json
  │    每个 member 产出：各年度 × 各银行的指标矩阵
  │
  ├─ Step 3: main 等待 4 个 member 完成
  ├─ Step 4: main 执行维度五：同业排名与变化追踪
  │    遍历 4 个 partial 文件中的所有指标
  │    为每个指标-年度计算 7 家银行排名、与前后名差距、排名变化
  │    特别标注：差距缩小/扩大、领先扩大/收窄
  ├─ Step 5: main 生成 ~/RetailAnalysis/output/<bank_short>/benchmark_analysis.md（Step 5）
  │         生成 ~/RetailAnalysis/output/<bank_short>/benchmark_analysis_result.json（Step 6）
  ├─ Step 6: main shutdown 所有 member + team_delete
  └─ Step 7: 向用户汇报
```

## 4. Member 职责边界

| 归属 | 工作内容 |
|------|---------|
| **Member（策略 B）** | 单个分析维度下所有银行×所有年份的派生指标计算 |
| **Main** | 数据库更新（Step 2）、排名计算（维度五，需跨维度和跨行视角）、报告生成、质量把关 |

> **为何排名计算必须由 main 执行**：排名需要同时持有 4 个维度 × 7 家银行的完整数据，且需判断排名变化、差距变化等"全局比较"关系，不适合拆分到单维度 member。
>
> **为何优先推荐策略 B**：4 个维度计算公式差异大，按维度拆分可以让每个 member 聚焦单一指标族，Prompt 更精准；同时并发度 4 也更易管控。

## 5. 单任务场景

如果用户只要求分析 1 个维度或 1 家银行，退化为顺序执行，不创建 team。

## 6. PDF 生成执行模式

- **默认串行**：主流程完成后由 main 串行调用当前 Skill 内 vendored 的共享 PDF Runtime，不新建 team
- **默认产物**：除 `benchmark_analysis.md` / `benchmark_analysis_result.json` 外，默认继续生成 `~/RetailAnalysis/output/<bank>/同业财报数据分析.pdf`

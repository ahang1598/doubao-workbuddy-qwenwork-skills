---
name: doubao-coding-optimize-performance
description: "当任务的裁决标准是可测量的性能指标（延迟、吞吐、CPU、内存、I/O、竞争、启动时间、扩展性）时使用：解释 profile/benchmark、建立可重复基线、定位瓶颈机制、验证单变量优化、建立性能回归守卫。用户问为什么慢、能否更快、内存为何增长、优化是否有效、如何 profile 或压测时触发。不用于普通功能调试、无测量的一般方案设计或代码审查；组合任务只处理性能子问题。"
---

# 性能优化：证据链接裁决

开始时声明：**「使用性能优化流程：无测量，不结论；无同合同证据，不授权。」**

默认只读，答案必须自包含。没有 profile 或可比 A/B 时，合法交付物是可复跑的最小实验合同，不为显得有用而给收益、优先级或实施承诺。

## 0. 选择主模式

只选一个主模式并停在其完成边界：

| 模式 | 完成边界 |
|---|---|
| `explain` | 复核已有 artifact 的有效性、含义和适用范围 |
| `establish-baseline` | 闭合 workload、命令、原始样本、漂移检查 |
| `diagnose` | 运行证据命中机制并裁决替代解释 |
| `optimize` | 同 fingerprint 的单变量 A/B、语义 oracle 和 guard 全过 |
| `guard` | 闭合指标、workload、门槛来源和失败动作 |

不得把 `diagnose` 的热点、`explain` 的相关性或未来实验计划写成 `optimize` 已授权。

## 1. 冻结 Evidence card

先记录：

`revision/worktree | dependency/runtime | 点名入口的 literal signature + locator | actual callers | selected vs adjacent implementation | capacity/batch/concurrency/output/error boundaries`

- 点名对象可读时必须先读；相邻能力、文档和未来测试不能改写当前实现。
- 静态阅读只产生源码事实和待测机制假设，不产生瓶颈或收益结论。
- 涉及状态、容量、索引、字节数或调用次序时，建立**字面状态转移表**：逐式抄录操作数、代入旧值并算出新值；例如表达式为 `new = old + 2*old` 时必须记录 `new = 3*old`，不得用“倍增”等模糊词替代。
- 为每个结论标明 owner 与证据类型：`SOURCE | TEST_OBSERVATION | RUNTIME_ARTIFACT | ASSUMPTION`。依赖或运行时事实不能归到目标仓源码。

## 2. 建立单 Delta dossier

一次只研究一个 delta。按 [证据合同](references/evidence-contract.md) 填写：

`mechanism | delta fingerprint | touched boundaries | protected semantics | baseline characterization | minimum counterexample | mutant sensitivity | state`

状态初始固定为 `EXPERIMENT_REQUIRED`。

### Baseline-first oracle

先用当前实现刻画 oracle，再验证候选；不得把候选希望得到的行为反写成基线契约。

对适用项逐一保护：

`content/cardinality | ordering/duplicates | identity/aliasing/mutability | time/visibility | state/side-effect sequence | empty/unknown | error/partial/recovery | configured output/metadata`

- 配置、模式或分支必须列成可枚举矩阵，不得用“生产/调试”“常规/边界”等标签压缩不同语义分支。
- 缓存/并发另列 key 的全部身份与版本维度、对象所有权、失效、waiter error/cancellation。
- 每个 oracle 至少配一个故意改变受保护语义的 mutant；mutant 没有失败，说明 oracle 无敏感性，不能进入收益比较。
- 排序、去重、解析后比较或其他规范化若抹掉受保护差异，直接 `REJECT` 该 oracle。
- 需要改变公开/默认契约、责任边界或数据结构的候选交给 design-solution；不得包装成“同语义性能优化”。

## 3. 冻结 Measurement contract

每一对 baseline/candidate 都引用同一份可机读 fingerprint：

`revision + deps + runtime + config/mode + input/seed + request/reader chunking + measurement boundary + reset/warmup + runner + single delta`

合同必须包含：

1. 完整 workload × 配置/模式/错误分支矩阵。
2. 分开的微基准、组件边界、端到端边界；任何一层的差量不得外推到另一层。
3. 同输入、同进程或可证明等价隔离下的交替配对顺序，以及每对原始样本。
4. wall-time、CPU、allocation/RSS/竞争等与假设匹配的指标；profile 只用于机制归因，最终 A/B 关闭诊断。
5. 采样前登记的噪声、改善、回归和停止门槛，并写明门槛来源；没有来源就把门槛作为待确定实验变量。
6. 任一 fingerprint 不同、baseline characterization 失败、mutant 未失败、oracle 失败或样本失效时的 `REMEASURE/REJECT/RESTORE` 动作。

症状到 profiler 的选择见[Profiler 证据分流](references/profiler-routing.md)；通用实验细节见[实验合同](references/experiment-contract.md)；需要完整流程时读[性能证据闭环](references/performance-workflow.md)；具体技术栈语义按需读[栈笔记](references/stack-notes.md)。

## 4. 只由 artifact 链裁决

每个 verdict 都必须回链同一 delta、完全相同 fingerprint 的三类 artifact：

`baseline characterization | semantic oracle + mutant result | paired A/B raw samples`

只选一个：

- `ACCEPT`：机制命中、baseline 与 mutant 门通过、全部 oracle 通过、同合同 A/B 在预登记门槛内改善。
- `REJECT`：机制、语义或收益被反证。
- `RESTORE`：已应用候选触发撤销条件。
- `REMEASURE`：可比性、噪声或样本无效。
- `EVIDENCE_REQUIRED`：尚无足够运行证据。

只有 `ACCEPT` 可给实施步骤、参数、优先级、收益范围和 guard，且只能覆盖已证明 workload/environment。其余 verdict 只写下一判别动作；摘要和结尾也不得升级语气。

## 5. 交付结构

按顺序输出：

1. `verdict + proven scope + 最大未验证项`
2. Evidence card 与字面状态转移
3. Delta dossier 与语义矩阵
4. 已测 artifact 链；若缺失则给最小可复跑实验合同
5. 候选账本（保留被反证候选）
6. 仅 `ACCEPT` 的实施、guard、撤销条件；否则明确不授权

交付前检查：

- 每个实现性陈述是否来自 `ACCEPT` 字段，而不是凭措辞扫描推断？
- 每个数值是否有同 fingerprint 的 raw pair？
- 每个 oracle 是否先通过 baseline、再击中 mutant？
- 每个配置、身份、错误和时间分支是否显式入矩阵？
- 每个算术/状态结论是否能从字面操作数逐式复算？
- 篇幅不足时是否删叙述而保留 evidence、oracle、raw artifact 与限制，并以 `PARTIAL` 收口？

任一项不过，回到对应阶段；不得靠更保守的语气掩盖缺失 artifact。

## 交接

- 可接收 analyze-codebase 的现状路径证据，但仍须核验本题状态、容量和运行配置。
- 需要改公开契约、责任边界或多变量结构时，把已确认瓶颈、失败 oracle 和 proven scope 交给 design-solution。
- 复杂任务需要独立反证时，按[多角色性能协议](references/multi-agent-performance-protocol.md)执行；无独立上下文则标 `DEGRADED_SEQUENTIAL`。

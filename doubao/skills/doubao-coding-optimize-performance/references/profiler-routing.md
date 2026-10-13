# Profiler 证据分流

> **何时读本文件**：MEASURE 阶段需要根据症状选择定位 artifact，或用户只要求解释单个已有 profile/trace 时加载。

本文件负责为当前症状选择能区分竞争机制、覆盖关键混淆因素的证据组合。实验可比性和最终判定使用[实验合同](experiment-contract.md)。

## 轻量解释边界

只有「选择或解释单个**已存在且可读**的 artifact，且已判为简单任务」时，才可直接使用本文件与命中的一个技术栈参考。轻量任务的边界：

1. 采集 profile/trace、运行 benchmark、安装工具、访问共享环境都**不是**轻量任务，即使用户只写了「profile」。
2. 轻量任务只冻结 artifact 来源、revision、环境、workload、采集参数和问题边界，交付 `EXPLAINED` 或 `EVIDENCE_REQUIRED`。
3. 需要端到端因果归因、跨 artifact 综合、baseline/candidate、guard 或实现变更时，升级到[性能证据闭环](performance-workflow.md)；不得用轻量路由跳过必要证据。

## 症状到证据

服务路径先看 RED：Rate、Errors、Duration；资源路径先看 USE：Utilization、Saturation、Errors。利用率只有在连接到等待、排队或目标指标时才构成瓶颈证据。

| 症状 | 首轮指标 | 定位 artifact | 主要混淆因素 |
|---|---|---|---|
| CPU 高、吞吐受限 | CPU、run queue、每请求 CPU | 采样 CPU profile、调用树 | 频率缩放、JIT、采样开销 |
| CPU 不高、延迟高 | off-CPU、锁、队列、I/O | block/mutex/async/syscall trace | 限流、连接池、空闲请求 |
| 内存或 GC 压力 | RSS、堆、分配率、pause | heap/allocation/lifetime artifact | 页缓存、allocator 保留、正常缓存 |
| 磁盘或网络 | 吞吐、队列、等待、错误 | I/O trace、系统调用、连接指标 | 压缩 CPU、远端依赖、重试 |
| 数据库 | query 次数/时长、锁、扫描行 | 脱敏 query log、plan、span | 缓存、统计信息、数据规模 |
| 分布式尾延迟 | endpoint 分位、fan-out、重试 | 代表性 trace、依赖分解 | 采样偏差、时钟、遗漏排队 |
| 浏览器交互 | LCP/INP/CLS、long task | performance trace、waterfall | lab/RUM 人群、扩展、网络 |

没有适用 profiler 时：用已有 metrics/logs 缩小范围并把结论保持为假设；证据仍不能区分机制时保留 `unknown`；工具安装需要单独权限。

## 假设卡

每个定位候选记录：

```text
触发条件 → 耗时/等待/受限资源 → 目标指标 → 端到端上限
证据 artifact + selector：
最强替代解释：
互斥预测与判别性证伪观测：
混淆因素：
```

两条纪律：Profiler 运行只定位，统计比较运行关闭 profiler 和额外诊断；热点占比决定调查优先级，不直接换算端到端加速。

> 坏例：「profile 显示该函数占 35% CPU，优化后端到端可提速 35%。」
> 好例：「该函数占 35% CPU（profile artifact 见上），端到端上限待同合同 A/B 测量。」
> 点评：热点占比是调查优先级信号，不是收益预测。

生产观测需预先固定窗口、采样率、资源上限、敏感字段、保留/删除、值班联系人和停止条件；授权不足时使用测试或回放环境方案。

**完成判据：** 首要候选与最强替代解释有互斥预测，证据组合能区分它们，观测影响和权限边界均已记录。

# 各技术栈性能证据

> **何时读本文件**：MEASURE 阶段涉及具体技术栈（Go/Python/Node/浏览器/DB/分布式）的运行语义、artifact 选择或反例核对时，加载命中的栈小节。

本文件按技术栈补充运行语义、定位 artifact 和常见反例。通用闭环与判定仍以[性能证据闭环](performance-workflow.md)和[实验合同](experiment-contract.md)为准。反例只用来提示「这只是分配/成本候选」，仍需运行 artifact 证实。

## Go

### 冻结运行语义

- 记录 Go 版本、build tags、`GOMAXPROCS`、CPU 配额、`-benchtime`、`-count` 和 `RunParallel`。
- 明确 `ResetTimer` / `StopTimer` 的边界，保证 setup 与被测工作位于约定区域。
- 保留原始 `go test -bench` 输出以及 `ns/op`、`B/op`、`allocs/op`。
- 仓库已有 `benchstat` 时可作为栈专属比较器；不自动安装。
- 编译器消除防护应保持真实数据流，不引入全局共享瓶颈。

稳态与冷启动是不同合同：

| 场景 | 合同要点 |
| --- | --- |
| 稳态 | 同进程 `testing.B`，用于预热后的稳态成本 |
| 冷启动 | 预先编译的 helper 或目标 binary；每个样本 fresh process；固定 revision、Go/OS/arch、`GOMAXPROCS`、配置/缓存/远端 fixture 和 OS page-cache 口径；不要 reset 私有 `sync.Once` 冒充新进程 |

冷样本至少保留：wall、user/sys、peak RSS，以及进程内被测边界前后的 `TotalAlloc`/`Mallocs` 或等价 artifact。

### 定位 artifact

| 症状 | Go 证据 |
|---|---|
| CPU | CPU pprof、调用树、热点源码 |
| 分配/GC | alloc-space/alloc-objects pprof、`B/op`、`allocs/op`、retained heap、RSS、GC 指标 |
| 锁竞争 | mutex profile 与采样率 |
| 阻塞 | block profile、goroutine dump |
| 调度/网络 | execution trace 与 goroutine/GC/network 关联 |

pprof 与 trace 的运行不进入最终无诊断比较。

### 反例

- 切片扩容、string/byte 转换、接口装箱、反射、临时 map 与逃逸只形成分配候选，需 allocation artifact 证实；同时核对无匹配/已小写/容量足够等 fast path，避免把源码构造语句直接计为分配。
- 三种内存口径不可互换：allocation profile 解释总分配；N 次 GC 后 heap profile 解释留存；进程 peak RSS 还包含 runtime 与映射页。
- goroutine 数、channel/锁竞争、false sharing 和下游容量可能限制局部 CPU 收益。
- `sync.Pool` 受 GC 与调度影响，池化需验证生命周期、内存上界与跨 P 行为。
- goroutine 泄漏需用 goroutine dump 随时间变化证实，而非仅看创建点。

## Python

### 冻结运行语义

- 记录解释器实现/版本、优化 flags、依赖锁、进程/线程数、GC 策略与 hash/random seed；按目标路径决定导入和初始化是否计时。
- `pyperf` 已存在时保留 worker、warmup、value 与 metadata；profile 模式不作为无插桩计时。
- 原生扩展分别记录 Python frames、native frames、数据转换和复制。

### 定位 artifact

| 症状 | Python 证据 |
|---|---|
| Python CPU | cProfile/采样 profile、调用次数、自身/累计时间 |
| 原生 CPU | 含 native frames 的系统采样 profile |
| 分配/泄漏 | tracemalloc 差分快照、对象保留、RSS/heap 分解 |
| async/I/O | task/async trace、系统调用、连接池与下游 span |
| 并行异常 | worker 利用率、GIL、IPC/序列化、启动成本 |

cProfile 只用于定位。内存增长区分 Python heap、原生分配、allocator 保留与页缓存。

### 反例

- 向量化和原生库的启动、转换与复制可让小输入退化（小输入下开销可能超过收益）。
- CPU-bound 与 I/O-bound 使用不同并发假设；受 GIL 影响，纯 Python CPU-bound 多线程未必并行；进程方案要计入 IPC、序列化和 worker 生命周期。
- 缓存记录 key、失效、隔离、命中分布与内存上界；解释器全局状态进入样本重置合同。
- 单一 `timeit` 结果不能外推为服务尾延迟或吞吐。

## Node 与浏览器

### Node / V8

冻结运行语义：

- 固定 Node/V8 版本、启动 flags、package lock、build mode、worker 数与 event-loop 并发；
- 开发模式与 production build 是不同 workload；
- JIT 稳态与冷启动使用不同合同；记录 optimization/deoptimization、inline cache 与 code cache；
- CPU profile、heap snapshot 和 `--trace-*` 只用于定位，关闭后再比较；
- `--expose-gc` 或强制 GC 属于实验条件，不代表默认运行语义。

| 症状 | Node 证据 |
|---|---|
| CPU/JIT | V8 CPU profile、优化/去优化证据 |
| event loop | event-loop delay、long synchronous task、async trace |
| heap/GC | heap snapshot、allocation profile、retainer、GC pause |
| I/O | async trace、DNS/TLS、连接池、重试和超时 |

反例：

- module/global cache、worker reuse 和连接池会跨样本泄漏状态；重置或把稳态明确写入合同。
- 同步长任务阻塞 event loop，需用 event-loop delay 或 long task 证据定位，而非只看单函数 CPU。

### 浏览器

冻结口径：

- Lab 固定浏览器、production build、viewport、CPU/network throttling、cache policy、登录状态与第三方内容；
- RUM 记录真实人群、采样和产品分位口径。

指标分解：

- LCP 分解资源发现、TTFB、加载和渲染；
- INP 分解输入延迟、处理和呈现；
- CLS 追踪具体布局变更来源；
- coverage、bundle size 与 Lighthouse 只形成候选，目标页面用户指标负责裁决。

外推边界：Lab 结论只覆盖实验配置；真实人群结论需要 RUM 或等价线上观测。冷启动/稳态、开发/生产、Lab/RUM 分别建模，定位工具关闭后的同合同测量负责最终比较。

## 数据库与分布式

### 数据库

把目标 workload 关联到可观察的数据库机制：

- 调用次数、总数据库时间和单次分布；
- 返回/扫描数据量、规划与执行差异；
- 锁、事务、连接池、排队、重试和取消；
- schema、索引、统计信息、参数分布、缓存状态和数据规模。

证据强度：

1. 重复查询、全表扫描或某个 plan 只能形成假设。
2. 确认限制机制需要它随真实 workload 变化，并在端到端分解中占有足以解释症状的等待或资源。
3. N+1 需用随 workload 变化的调用次数证实，而非只看代码里的循环查询。

候选测量：索引、批量、并发或缓存候选必须在同一合同下测量，同时观察读取收益、写放大、存储、锁、迁移、恢复和应用侧资源。不要将测试数据库上的绝对容量外推到不同数据与执行单元。

### 有状态中间层

缓存、批处理、合并请求和跨请求共享会改变状态与失败表面。先从当前实现和调用者冻结：

- key、身份与隔离边界；
- hit、miss、partial result 与错误传播；
- 数据新鲜度、失效、版本和发布顺序；
- 所有权、可变性、并发接管与故障恢复；
- 下游调用集合、顺序和持久副作用。

候选要求：

- 用 oracle 证明这些行为没有意外改变；
- 用 profile/trace 证明它作用于已观测机制；
- 命中率、批大小、并发窗口和重试策略来自当前 workload、下游容量及交叉点实验，不使用通用默认值。

### 分布式链路

- 将 trace 分解为排队、本地执行、远端依赖、重试、fan-out 和取消；
- 通过同一 workload 类别和时间窗关联 metrics、traces 与 logs；
- 记录 sampling、时钟、deadline、负载到达模型与丢弃；
- 检查生成器饱和、autoscaling、限流、连接池和下游配额等混淆因素；
- 对队列同时观察到达、服务、积压、最老等待、重试和失败；
- 对尾延迟保留完整 fan-out，而不是只比较平均 span。

外推边界：负载发生器自身饱和或遗漏排队时间时，实验不能裁决服务容量。测试环境结论只覆盖已校准执行单元与 workload，不直接外推生产。

### 正确性与守卫

- Oracle 至少覆盖适用的：结果值和顺序、事务/隔离、错误与 partial result、超时且结果未知、取消、重试、依赖调用、持久副作用。
- Guard 同时观察下游资源、放大、热点、公平性和恢复。
- 保存 artifact 前移除凭据、认证头、请求正文中的敏感数据、用户标识与 trace baggage；脱敏不能破坏用于关联机制的稳定 selector。

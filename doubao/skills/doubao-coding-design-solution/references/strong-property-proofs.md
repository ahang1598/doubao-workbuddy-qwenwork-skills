# 强性质的构造性证明卡

强性质不能由名称、局部技巧、伪代码或未来测试计划签发。先定义性质的作用域、观察者、可见状态和反例，再填写对应证明卡；任何必填项为 `unknown`、只有推测来源或 oracle 尚未执行时，相关 gate 保持 `UNKNOWN`，候选不能借此成为 `ADOPTED`。

## 用户可见契约基线

在设计新增机制前，逐项记录 `surface / current observable behavior / reader or writer / exact evidence / proposed change / migration / consumer oracle`。surface 至少覆盖任务命中的退出状态、错误类别与 envelope、wire/schema、字段与形状、顺序、版本选择和失败行为。不得把新增字段、错误、状态或版本语义称为向后兼容，除非旧消费者行为已有源码、权威契约或实际 oracle 证据。

## Reproducible

填写：

- `output identity and equality`：定义比较的输出范围，以及相同是逐字节还是语义等价。
- `complete input inventory`：列出该范围内所有源码、配置、数据、工具及依赖版本、平台与运行参数；每项绑定不可变身份或明确规范化规则。
- `complete nondeterminism inventory`：逐项处理时间、时区、locale、环境、遍历/排序、随机源、并发调度、网络、外部状态、生成标识和实现相关序列化；标明固定、消除、规范化或显式纳入输入。
- `construction and oracle`：从同一冻结输入在隔离环境重复构造，直接比较定义的输出；任一未列输入、未控非确定性或差异都使性质失败。

证明的是“相同完整输入产生同一已定义输出”，不是“使用稳定排序”或“记录部分哈希”。

## Atomic

填写：

- `observer and visible set`：定义谁读取，以及必须作为一个整体出现的完整对象集合。
- `single observer-visible commit point`：标出唯一使新集合可见的动作；提交前只能读到完整旧集合，提交后只能读到完整新集合。
- `construction`：新集合在不可见位置完成、校验并冻结，再由提交点切换；列出提交前后可达集合和读取规则。
- `crash windows and oracle`：枚举准备、校验、提交以及提交确认未知窗口的崩溃，逐窗验证观察者只得到允许的旧/新集合，并定义遗留状态的恢复。

多个对象各自原子写入或 rename 只证明单对象原子性，不能证明集合原子性。若不存在一个观察者可见提交点，就降低声明并明确可能出现的混合状态。

## Backward compatible

填写：

- `frozen contract`：从 BASELINE 引用当前 exit、error、wire、shape、version 和失败语义及实际消费者。
- `old reader oracle`：旧 reader 读取新 writer 输出时的具体结果。
- `old writer oracle`：新 reader 读取旧 writer 输出时的具体结果。
- `evolution evidence`：分别验证未知/新增字段、缺失字段、形状或类型变化、枚举扩展和版本选择/拒绝行为；只填写任务实际触及的面，但不得把未读实现假定为容忍。
- `migration`：任何既有行为变化都列消费者升级顺序、共存窗口、停止条件与可观察 oracle。

框架惯例、“通常会忽略”或新 reader 的测试不能证明旧 reader 兼容；旧实现或权威契约不可读时，兼容性保持 `UNKNOWN`。

## Rollback

填写：

- `immutable prior state`：回滚目标有不可变身份并已验证完整、可读、仍受支持。
- `switch point and scope`：说明一个可验证动作如何把全部目标观察者切回该状态，并列出代码、数据、schema、配置和在途工作的适用边界。
- `preconditions and windows`：列出新状态是否已产生不可逆写入、旧 reader/writer 是否仍兼容，以及切换失败或结果未知时的检测与恢复。
- `oracle`：切换后从消费者视角验证目标身份、可见集合和关键行为，而不只验证命令成功。

重新生成旧内容、回退代码或逐个覆盖可变文件不等于可回滚；无法恢复的状态必须改为前向修复或 `PARTIAL/BLOCKED`。

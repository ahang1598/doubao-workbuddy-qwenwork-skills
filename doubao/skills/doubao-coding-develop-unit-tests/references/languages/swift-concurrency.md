# Swift 并发

- Fake 与闭包保持真实 callable 的 `async`、`throws`、`@Sendable`、actor/MainActor 和返回类型。
- 用 continuation、gate、clock 或项目设施驱动时序：等待阶段进入，断言外层 pending，释放后 await 外层。
- 每个并发不变量使用一个 gate；其余顺序写入同一条 trace。
- `@Sendable` 闭包的可变状态放入 actor 或项目已有同步容器；`@unchecked Sendable` 只包装由同一机制保护的访问。
- 保存并最终 await 创建的 Task；teardown 取消并等待遗留任务。
- Combine/AsyncSequence 注入并读取同一个计数器或 trace，断言事件顺序和完成条件；持有并释放订阅与 iterator 资源。

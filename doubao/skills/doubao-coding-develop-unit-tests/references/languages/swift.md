# Swift 适配

- 从邻近测试、Package/project/workspace 与 target 配置确认测试运行器和框架；Swift 版本本身不是框架证据。
- 空 test target 或证据仍不足时，测试文件只能包含候选框架 import、目标 import 和一个不调用生产代码的冒烟测试。项目原生命令退出码为 0 且发现该测试后，才将它替换为探针并扩展。
- 候选框架冒烟失败时停留在门禁，删除或替换该冒烟后验证下一个项目可用候选；不保留整套不可编译测试，不搜索或安装 Xcode、框架、依赖，也不修改 Package/target，除非用户授权。
- 测试放入对应 test target，沿用项目的 import、属性和 `@testable` 惯例；私有实现通过公开行为验证。
- 写 Fake 前抄录真实 callable 的同步/异步、throws、actor 隔离和返回类型，并逐项匹配。
- 用协议注入和最小 Fake 隔离外部边界；Fake 或探针编译失败时停在该层修正。
- Optional、throwing、Result、值/引用语义按契约断言。契约写“同一错误对象”时，测试错误必须为引用类型，捕获后以 `===` 比较；只断言抛错、类型或消息不算完成。
- 元组按字段比较；整体 `==` 只用于明确遵循 `Equatable` 的类型。
- 涉及 async/actor/MainActor/Sendable/取消/Combine/AsyncSequence 时，读取 [Swift 并发](swift-concurrency.md)。
- 遇到宏、availability、deployment target 或工具链诊断时，读取 [Swift 工具链](swift-toolchain.md)。
- SwiftPM 运行 test filter；Xcode 确认共享 scheme、destination 和 test target，并将 DerivedData 放到仓库外。

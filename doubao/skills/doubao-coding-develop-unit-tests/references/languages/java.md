# Java 适配

- 从 Maven/Gradle wrapper、Java 版本、模块和邻近测试确认 JUnit、断言库、Mock 体系及 source set。
- 测试放入目标模块和对应包，沿用既有 runner/extension 和 wrapper。
- 只替换注入的外部边界；通过公开入口验证被测类、值对象和私有实现。
- 异常断言类型、cause、错误码和状态；完整消息只用于明确的文本契约。
- 每个测试独立构造状态；参数化只合并同一反例。
- 用可控时钟、executor 或 future 驱动异步，并在 teardown 恢复全局配置、关闭资源、等待任务完成。
- 目标契约属于 Spring/应用上下文且项目已有惯例时才加载它；否则保持纯单元边界。先运行方法/类级命令，再运行模块相关测试。

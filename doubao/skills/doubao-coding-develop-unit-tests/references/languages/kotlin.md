# Kotlin 适配

- 先判断 JVM、Android 或 Multiplatform；从构建配置、target、source set 和邻近测试确认框架与 Mock 体系。
- 测试放入目标 source set，沿用项目已有的一种 Mock 方案，通过公开行为验证实现。
- `suspend`、Flow 和 channel 使用现有协程测试库、dispatcher 与虚拟时间；等待或取消子协程并恢复 dispatcher。
- 按契约区分 null、空值、默认参数、sealed 分支、Result 和异常语义。
- 扩展函数、object、inline/value class 通过调用者可观察结果验证。
- Android 生命周期属于契约时使用项目已有 Robolectric/仪器边界；纯 JVM 逻辑保持轻量。
- 运行目标 module/source-set 的聚焦 wrapper 任务和相关回归；多平台只报告实际执行的 target。

# Swift 工具链

- 原样运行项目命令，并记录 Swift 可执行文件、版本、工作目录和构建缓存；从第一条因果诊断定位问题。
- 已有测试或项目配置确定框架时保持不变。框架只是本轮猜测且出现 `no such module` 时，回到最小框架探针；不要改 Package、依赖或目标来迁就猜测。
- `module compiled with Swift X cannot be imported by Swift Y` 表示工具链或缓存不一致：统一可执行文件，将缓存隔离到仓库外并重建，再原样重跑。
- 宏、属性作用域、Sendable、Task 类型和辅助 API 错误归类为 `test_failure`；scheme、destination、编译器或目标平台不可用归类为 `environment_block`。
- test-only import 或辅助 API 抬高 deployment target 时，先移除非必要 import，或改用目标兼容的设施。
- 诊断明确给出平台和最低版本时，把由诊断得出的 availability 应用于每个受影响的测试、suite 和辅助声明；版本和平台来自诊断，不从宿主机预设。
- 保持已有 Package 和构建参数不变；附加命令只用于诊断。
- 修正后原样重跑，确认命令退出码为 0 且目标测试被发现。

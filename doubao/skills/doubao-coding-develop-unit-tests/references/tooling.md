# 工具与测试发现

测试入口、发现规则或模块边界不明确时读取本文件。

## 发现

1. 读取仓库和目标目录规则。
2. 检查构建清单、lockfile、测试配置、wrapper、任务脚本和 CI。
3. 从一至两个邻近测试确认框架、目录、命名和 fixture。
4. 记录工作目录、必要环境，以及目标 case 和相关回归的项目原生命令。

常见入口仅用于定位：Go `go test`；Python pytest/unittest；JS/TS 项目 test script；Java/Kotlin Maven/Gradle wrapper；Rust `cargo test`；C/C++ 构建 target 后运行测试二进制或 `ctest`；Swift `swift test` 或项目 `xcodebuild test`。仓库证据优先。

## 执行证据

- 目标测试名出现在输出、报告包含该 case，或框架报告非零执行数量，才算已发现。
- 退出码为零但执行数量为零，归类为 `not_discovered`。
- 从 `目标 case → 文件 → 包/模块 → 受影响工作区` 扩大；全仓测试服从项目规则或用户要求。
- TDD/回归的有效 RED 必须由目标行为断言触发；编译、fixture、收集和环境错误按实际类别处理。
- 从第一条因果错误修正；每轮保持命令和环境可比。

缓存、报告、临时副本和构建产物使用仓库外目录。采用项目已有环境和依赖；需要改配置、lockfile、CI 或下载工具时先取得授权。

**完成：** 原生命令、工作目录、退出状态、发现证据和失败类别均可复核。

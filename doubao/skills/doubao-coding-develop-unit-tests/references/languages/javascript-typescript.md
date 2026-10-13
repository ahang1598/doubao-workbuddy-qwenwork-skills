# JavaScript / TypeScript 适配

- 从 `package.json`、lockfile、测试/模块配置和邻近测试确认包管理器、runner、工作区与转换链。
- 使用锁定的包管理器和现有 test script，从拥有目标代码的 package 运行。
- 按 ESM/CJS 及被测代码的实际查找位置设置 mock；需要 import 前生效时先注册，随后恢复模块、全局和环境。
- 异步等待使用受控 deferred/gate：确认阶段已进入且外层 pending，释放后 await 结果。
- 时间使用项目 fake timer；推进时钟后清空 pending timer，并在 teardown 恢复。
- 按契约分别覆盖同步 throw、Promise rejection 和 callback error。
- 先运行文件/名称过滤，再运行 package 回归，并报告 runner 的真实发现数量。

# Python 适配

- 从 `pyproject.toml`、pytest/tox 配置、锁文件、环境说明和邻近测试确认 runner、fixture 与命令。
- patch 被测代码实际查找名称的位置，并用 fixture、`mock.patch` 或 cleanup 自动恢复。
- 对 async 函数、生成器和 context manager 驱动完整生命周期，验证结果、异常和资源释放。
- 参数化只合并同一反例；断言完整返回结构和关键状态。
- 用 `tmp_path`、`tempfile`、`monkeypatch` 或 `addCleanup` 隔离文件、环境与全局状态。
- 使用项目环境运行聚焦测试和文件/模块回归，确认收集数非零。
- 禁用或外置 bytecode、pytest、coverage 和报告缓存；只清理本任务生成的临时产物。

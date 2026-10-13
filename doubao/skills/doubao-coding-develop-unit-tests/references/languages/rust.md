# Rust 适配

- 从 `Cargo.toml`、workspace、package、edition、feature、target、runtime 和邻近测试确认入口。
- 按契约选择模块内 `#[cfg(test)]` 或 `tests/` 集成测试，通过现有可见性验证公开行为。
- 用 trait、轻量 Fake 或项目已有 Mock 隔离外部边界，保持所有权、借用和核心领域逻辑真实。
- 分别断言 `Ok`、`Err`、Option、状态和副作用；panic 属于契约时才使用 panic 断言。
- 异步沿用现有 runtime，并用 channel、barrier 或虚拟时间观察 pending/完成和任务退出。
- feature 与平台条件来自项目；toolchain、linker 或 SDK 缺失归类为环境问题。
- 将 `CARGO_TARGET_DIR` 放到仓库外，运行 package/feature/名称级聚焦测试和 crate 回归。

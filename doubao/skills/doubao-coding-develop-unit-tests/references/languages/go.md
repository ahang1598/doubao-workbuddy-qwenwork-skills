# Go 适配

- 从 `go.mod`、`go.work`、构建标签、wrapper 和邻近 `*_test.go` 确认包边界与命令。
- 按邻近惯例选择同包或外部包；私有字段仍通过后续公开行为验证。
- 用小 Fake 实现接口，记录契约需要的 context、参数和 trace；API 接收 context 时验证代表值原样透传。
- 依赖返回 `(value, error)` 时套用测试边界的脏结果与失败 trace，验证结果和下游状态。
- 契约要求同一 sentinel 时用 `got == sentinel`；允许包装时用 `errors.Is`。错误文本只锁定有依据的稳定语义。
- 仅在契约区分时测试 nil/空 slice、nil interface/typed nil、零值/缺省。
- 表驱动只合并同一反例；执行 `gofmt` 后运行聚焦和包级测试，并将 Go 缓存、临时目录和报告放到仓库外。

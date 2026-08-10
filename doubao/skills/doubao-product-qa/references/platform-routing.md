# 平台专项路由

先完成目标与宿主检测，只读取命中的一条路径。平台资料是统一 QA 主流程的执行适配器，不是另一套方法论。

## 路由表

| 条件 | 必读 | 第一个动作 | 成功标志 |
|---|---|---|---|
| 本地 Web 工程或网页 | [web-runtime.md](../references/web-runtime.md) + [web-automation.md](../references/web-automation.md) | 运行 `scripts/qa_flow.py inspect-web <qa-run> --project <path>` | 上下文卡已复用，启动方式、URL、端口、登录态和 runner 已确定 |
| Web 性能/a11y/视觉/负载 | 在 Web 路径上追加 [web-quality.md](../references/web-quality.md) | 先确认专项风险、阈值来源和流量预算 | 专项结论有阈值来源与原始结果 |
| OpenAPI/API 工程 | [api-automation.md](../references/api-automation.md) | 运行 `scripts/inspect_api_project.py`；有 OpenAPI 时再运行 `scripts/generate_api_manifest.py` | 技术栈、operation 清单、写入授权和唯一框架已确定 |
| iOS/Android/HarmonyOS | [mobile-automation.md](../references/mobile-automation.md) + [device-lab.md](../references/device-lab.md) | 运行 `scripts/detect_test_targets.py` | 包/工程、设备、系统、driver 和阻塞项已登记 |
| 微信小程序 | [miniprogram-automation.md](../references/miniprogram-automation.md) + [device-lab.md](../references/device-lab.md) | 检查工程目录或已授权 automator endpoint | 标准入口可用，或已生成真机人工交接 |
| Windows/macOS/Linux 能力差异 | [platform-compatibility.md](../references/platform-compatibility.md) | 运行 `scripts/detect_host_environment.py` | 命令方言与平台 blocker 明确 |
| 用户明确不会配置且存在真实环境缺口 | [beginner-onboarding.md](../references/beginner-onboarding.md) | 一次只给一个必须由人完成的动作 | 用户完成后重新检测成功 |

## 路由纪律

- 同一任务可命中多个目标，但每个平台保持独立执行记录；一个平台通过不能推导另一个平台通过。
- Web + API 组合先共享需求与风险机制，再分别建立执行记录，不复制两套需求。
- 需要兼容矩阵时使用 `scripts/run_device_matrix.py` 聚合；每个目标必须有明确状态。
- 需要移动端证据时使用 `scripts/collect_mobile_evidence.py`；截图仍受用户策略约束。
- 本地 Web 长进程使用 `scripts/run_web_session.py`，只清理本次启动的进程。
- 新建 API starter 仅在项目没有既有框架时使用 `scripts/scaffold_api_tests.py`，且只选一套。
- 回归影响存在显式映射时使用 `scripts/analyze_change_impact.py`；未映射变更保留为风险。
- `scripts/platform_process.py` 是其他脚本的进程适配器，不由 Agent 直接调用。
- `scripts/qa_run_common.py`、`scripts/qa_gate.py`、`scripts/gate_policy.py`、renderer 和 validator 由 `scripts/qa_flow.py` 统一编排；交付一律走 `scripts/qa_deliver.py`。不要分别猜运行顺序，也不要绕过交付口直接调上屏工具。

## 失败路径

1. 标准 runner 可用 → 正式自动化。
2. 标准 runner 不可用但结构化 UI 工具可用 → 只做 `exploratory`，同时保留恢复正式自动化的动作。
3. 只能验证 API、安装、启动、日志或静态代码 → `partial_validation`。
4. 无可用入口 → `blocked + manual_handoff`，仍完成测试设计。

不得把后一级结果升级成前一级通过。

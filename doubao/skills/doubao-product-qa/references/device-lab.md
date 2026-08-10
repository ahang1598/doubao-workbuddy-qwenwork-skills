# 设备实验室与兼容矩阵

## 目录

- [设备发现](#设备发现)
- [矩阵设计](#矩阵设计)
- [矩阵清单](#矩阵清单)
- [并发与隔离](#并发与隔离)
- [结果分类与聚合](#结果分类与聚合)
- [停止规则](#停止规则)

## 设备发现

运行：

```bash
python3 scripts/detect_test_targets.py --project <项目目录> --json > target-inventory.json
```

检测输出必须记录：

- host OS 与架构；
- Node/npm/Appium、driver、adb、Xcode、微信开发者工具；
- Android serial、状态、机型、API/OS；
- iOS Simulator/真机 identifier、名称、OS、可用性；
- 小程序工程和 `miniprogram-automator` 可解析性；
- blocker 与降级建议。

设备标识在外部报告中脱敏，但本地执行清单需保留精确 ID。

## 矩阵设计

从用户分布和风险出发选择代表组合：

1. 当前主流 OS + 主流机型；
2. 最低支持 OS；
3. 最近升级或缺陷高发组合；
4. 不同屏幕/内存/厂商定制系统；
5. iOS 与 Android 各一个真实设备；
6. 涉及硬件/宿主能力时增加对应真机；
7. 小程序增加 iOS/Android 微信版本与基础库组合。

优先 P0 全矩阵冒烟，再对主设备执行完整 P1/P2。不要在所有设备重复低价值组合。

## 矩阵清单

复制 `assets/device-matrix-template.json` 并填入真实命令。每项：

```json
{
  "id": "android-pixel-api35-smoke",
  "platform": "android",
  "target": "emulator-5554",
  "command": ["npm", "run", "test:appium", "--", "--suite", "smoke"],
  "env": {
    "QA_PLATFORM": "android",
    "QA_TARGET_ID": "emulator-5554"
  },
  "timeout_seconds": 1200
}
```

`command` 必须是参数数组，不写 shell 管道、重定向或 secret。secret 由执行环境注入。

先 dry-run：

```bash
python3 scripts/run_device_matrix.py matrix.json --dry-run
```

空矩阵不是成功：原始 `runs=[]` 返回配置错误和退出码 `2`；`--only-platform` 筛选后无目标返回 `blocked/no_matching_target` 和退出码 `3`。只有明确用于模板或上游可选阶段时才传 `--allow-empty`，此时返回 `empty_allowed`。不要把 `run_count=0` 记为兼容矩阵通过。

再运行：

```bash
python3 scripts/run_device_matrix.py matrix.json \
  --out qa-results/feature/device-runs \
  --max-workers 2
```

## 并发与隔离

- 每个物理/虚拟设备同一时间只分配一个会改变状态的 run。
- Appium server port、systemPort、wdaLocalPort、Chromedriver port 按 worker 唯一。
- 每个 run 使用独立账号、数据前缀、artifact 目录和日志。
- iOS Simulator 可 clone/erase 后运行；真机不要在未授权时清除内容。
- Android emulator 使用稳定 snapshot；真机清理范围只限测试应用。
- 小程序开发者工具项目实例和 automation port 独占。
- 设备断开后不要立刻把所有用例算失败；将 run 分类为基础设施阻塞。

## 结果分类与聚合

矩阵 runner 输出：

- `matrix-summary.json`：每个 run 的状态、退出码、时长、日志路径；
- `<run-id>/stdout.log`、`stderr.log`；
- 框架自身的 JUnit/HTML/xcresult/截图等产物。

run 状态：

- `passed`：命令正常退出且框架报告无失败；
- `failed`：测试断言或产品行为失败；
- `timeout`：超过指定时限；
- `infra_error`：命令缺失、设备离线、安装/签名/runner 启动失败；
- `skipped`：由范围或依赖明确跳过。

命令退出码只能判断 run，不足以区分产品失败和基础设施错误；解析框架报告和日志后再映射到 QA 用例状态。

报告分别统计平台、OS、设备类型、框架和测试集。模拟器与真机、开发者工具与微信真机不可合并为单一“端通过”。

## 停止规则

暂停整个矩阵并先修基础设施，当：

- P0 冒烟在主目标阻塞；
- 同一基础设施错误影响多个 run；
- 设备离线/磁盘不足/系统弹窗造成连续失败；
- 测试数据服务不可用；
- 签名、WDA、instrumentation 或开发者工具连接无法建立。

只有独立设备失败且其他目标健康时继续剩余矩阵，同时隔离故障设备。

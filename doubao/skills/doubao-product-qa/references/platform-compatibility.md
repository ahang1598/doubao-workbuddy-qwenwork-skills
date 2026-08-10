# 宿主平台与命令适配

## 先检测再生成命令

在任何安装、启动或自动化命令前运行：

```bash
python3 scripts/detect_host_environment.py --json
```

Windows 上若 `python` 不可用但 `py` 可用，使用：

```powershell
py -3 scripts/detect_host_environment.py --json
```

把 `host_os`、`architecture`、`shell.dialect` 和相关 `platform_blockers` 写入 `qa-run.json.environment`。只向用户展示当前已检测 Shell 可直接复制执行的命令；不要同时倾倒 Bash、PowerShell 和 cmd 三套命令。

## 能力矩阵

| 能力 | Windows | macOS | Linux |
|---|---|---|---|
| PRD/产物生成、Web、API | 支持 | 支持 | 支持 |
| Android/ADB/Appium | 支持 | 支持 | 支持 |
| iOS/Xcode/XCUITest 本机执行 | 自动化阻塞；生成 iOS 人工方案，可选远程 Mac/设备云 | 支持 | 自动化阻塞；生成 iOS 人工方案，可选远程 Mac/设备云 |
| 微信开发者工具本地自动化 | 支持 | 支持 | 默认阻塞；使用 endpoint 或 Windows/macOS 主机 |

平台不支持不是 Shell 语法问题。不得把 `xcodebuild` 或 `xcrun simctl`“翻译”为 PowerShell/Bash；应把自动化记为 `blocked`，保留最小补齐动作，同时生成可直接执行的人工测试方案。

## 命令方言

| 操作 | Bash/zsh | PowerShell |
|---|---|---|
| 设置变量 | `export QA_BASE_URL="..."` | `$env:QA_BASE_URL = "..."` |
| 当前目录子路径 | `"$PWD/.appium-home"` | `Join-Path $PWD ".appium-home"` |
| 删除目录 | `rm -rf <path>` | `Remove-Item -Recurse -Force <path>` |
| 查找命令 | `command -v adb` | `Get-Command adb` |
| Python | `python3 script.py` | 优先 `python script.py`，不可用时 `py -3 script.py` |

尽量避免依赖这些差异：

- 使用 Python `pathlib` 处理路径；
- runner 命令保存为 JSON 参数数组，不写 shell 管道和内联环境变量；
- 使用 `npm run ...` 和跨平台 Node/Python 脚本；
- Windows 默认 PowerShell，不主动使用 cmd；只有执行 `.cmd/.bat` 时由 runner 通过 `%COMSPEC%` 适配；
- 不把 WSL 当成 Windows 默认环境，用户明确选择 WSL 后才使用 Linux 方言。

## Windows 平台规则

- 路径必须允许盘符、反斜杠、空格和中文；不要手工用 `/` 拼接用户路径。
- 查找可执行文件时接受 `.exe/.cmd/.bat` 和 `PATHEXT`。
- 启动长期服务时使用 `CREATE_NEW_PROCESS_GROUP`；清理时先尝试 `CTRL_BREAK_EVENT`，再用 `taskkill /PID <pid> /T /F`，且只清理本次启动的 PID 树。
- 微信开发者工具 CLI 优先读取 `WECHAT_DEVTOOLS_CLI`，再检测 `ProgramFiles`、`ProgramFiles(x86)` 和 `LOCALAPPDATA` 下的腾讯/微信开发者工具目录。
- Windows 本机 iOS 测试统一写入 `qa-run.json.blockers`：

```json
{
  "platform": "ios",
  "code": "IOS_REQUIRES_MACOS",
  "execution_level": "blocked",
  "fallback_path": "manual_handoff",
  "manual_handoff_required": true,
  "reason": "Windows 本机不能运行 Xcode、iOS Simulator 或 XCUITest",
  "minimal_unblock_actions": [
    "连接可访问的 macOS 测试主机",
    "或配置远程 Appium + XCUITest",
    "或使用 iOS 设备云"
  ]
}
```

## 报告要求

平台适配或降级必须记录：`host_os`、`shell_dialect`、`selected_path`、`unavailable_capabilities`、`coverage_loss` 和 `minimal_unblock_actions`。命令在某个平台未运行时，不得根据另一平台结果推导通过。

## 自动化不可用时的人工交接协议

发现宿主、设备、签名、工具或权限不能支持目标平台自动化后：

1. 停止生成当前宿主无法运行的命令，不把命令语法适配误当成平台能力适配。
2. 自动化层保持 `execution_level=blocked`，`selected_path` 设置为 `manual_handoff`。
3. 继续完成测试计划、需求追踪、测试用例、验收清单和风险，不因自动化失败而停止测试设计。
4. 在 `manual_handoff` 中记录原因、状态、操作人、执行前准备、人工用例 ID、证据要求和结果回传方式。
5. 每个转人工用例标记 `execution_mode=manual` 或 `hybrid`，并填写 `manual_reason` 与 `evidence_expected`。
6. 生成 `10-manual-test-guide.md` 和 `manual-handoff/` 人工执行包。人工指南至少包含：
   - 自动化不可用原因和受损覆盖；
   - 设备、版本、安装入口、账号、网络与测试数据准备；
   - 每条用例的“【人工操作】”标记、前置条件、编号步骤和逐项预期；
   - 应记录的截图、录屏、日志、版本号、时间点或错误文案；
   - 通过/失败/阻塞/不适用填写方式与回传方法；
   - 人工未完成前发布结论保持 `undetermined`。
7. 人工 QA 填写执行包中的 `02-manual-test-cases.csv` 后，用 `scripts/import_manual_results.py` 导回；执行结果、证据和复测记录追加到 `qa-run.json`，不得覆盖历史执行。

### Linux/Windows 测试 iOS

- 本机不能运行 Xcode、iOS Simulator、XCUITest 或本地 Appium XCUITest driver，不输出这些命令。
- 若有已安装待测版本的 iPhone/iPad，或有 TestFlight、App Store、企业分发、MDM、Ad Hoc 安装入口，按真实设备生成完整人工业务流程。
- 人工前置条件明确记录：设备型号、iOS 版本、构建版本、安装方式、网络、权限初始状态和账号/测试数据。
- 需要安装但没有安装入口时，把“获得可安装构建”标为人工前置阻塞；测试用例仍完整输出，便于条件满足后直接执行。
- 远程 Mac、远程 Appium 或设备云属于恢复自动化的可选方案，不得成为用户获得人工测试方案的前置条件。
- 用户回传人工结果后，执行记录使用 `execution_method=manual` 并记录操作人和证据；不得标记为 `full_automation`。

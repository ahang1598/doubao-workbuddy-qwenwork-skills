# 检查与按需安装 CLI

普通任务开始时运行与本文同目录的脚本：

```bash
node "{baseDir}/scripts/ensure-cli.js"
```

`{baseDir}` 是当前 Skill 的根目录。运行环境需 Node.js 16+，并允许执行本地程序。首次安装或自动升级还需要 npm、可写的用户缓存目录、访问 npm 源和 GitHub Release 的网络、`curl` 与解压工具（macOS/Linux 的 `tar`，Windows 的 PowerShell）。复用已有 CLI 不需要下载网络或 npm。

## 查找与复用

脚本依次检查 PATH 中的 CLI 和自身缓存，验证版本及本 Skill 使用命令的 `--help`；命令集合维护在脚本的 `REQUIRED_COMMANDS`，包含 `model list` 和 `model describe`。帮助检查不调用生成服务，也不需要凭据，不证明账号权限或服务端运行状态。

命令齐全则直接复用，不检查最新版本；不存在或缺少必需命令时，获取 `@pippit-dev/cli@latest`。PATH 旧版本缺少命令但缓存完整时复用缓存，避免每次升级。版本命令不能运行或检查超时则报告运行错误。

需要安装时，脚本跳过 npm 生命周期脚本获取包，调用包内 `scripts/install-cli.js` 只安装 CLI。成功后缓存到 `~/.cache/pippit-tool-cli/xyq-skill/<平台>-<架构>/current`。不要求全局 npm 写入权限，也不安装或清理全局 Skill。

## 返回与使用

日志写入 stderr，成功时 stdout 为 JSON：

```json
{"cli_path":"/absolute/path/to/pippit-tool-cli","version":"实际版本"}
```

后续所有命令使用返回的 `cli_path`，路径加引号；Windows PowerShell 使用 `& "绝对路径" 参数`。不要依赖前一次 shell 中的临时变量，同一任务复用返回路径，路径被清理后再运行脚本。

每次最多安装一次，升级成功前保留旧缓存。下载失败、最新包缺少安装入口或仍缺必需命令时停止并报告，不重复升级、不输出可用路径。仅将升级到可用版本作为恢复方式，不绕过缺失命令的检查。

独立 ZIP 必须包含整个 Skill 的命令文档、共用流程、示例和本脚本，保持相对路径；安装入口来自下载的 npm 包，不依赖本机源码仓库。

## Canvas 运行时检查

画布任务改用 `node "{baseDir}/scripts/ensure-cli.js" --canvas`。除原有检查外，再验证五个原生资产子命令的帮助，并通过同一个 npm 包的 Node 入口真实执行离线 `canvas command list`，确认运行时可加载且含基本查询与节点创建能力。该检查不登录、不访问画布、不写入远端。

成功额外返回 `canvas_entry`，供 `node "CANVAS_ENTRY" canvas command ...` 使用；`cli_path` 仍用于原生命令。语义操作的实际支持范围以当前目录为准，检查通过不代表所有业务操作或服务端权限都可用。

独立 Go 二进制没有 npm 入口，或包内运行时缺失/损坏时，Canvas 模式按原有规则检查缓存并至多安装一次最新完整 npm 包，保留旧安装直到新版本通过。普通媒体任务不要求 Canvas 运行时，也不会因为缺少它而升级。不要把缓存内的 `run.js` 单独复制出来，它依赖相邻模块与 `dist` 运行时。

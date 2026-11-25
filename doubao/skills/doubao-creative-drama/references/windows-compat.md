# Windows 兼容性

适用于 Windows 上的本地制作和只读素材查询。

## 硬规则

1. **确认终端工具与实际 Shell**：使用当前环境提供的 PowerShell、Terminal、RunCommand、exec_command 等终端工具；工具名不等于 Shell，不要求存在 Bash 工具。确认 Windows 使用的是 PowerShell、cmd 还是 Bash，不能直接复制另一种 Shell 的示例。
2. **每次终端调用只启动一条外部命令**：不使用 `&&` / `||` 拼接命令，不使用 Bash 的 `\` 续行、heredoc、`<<<` 或命令替换。组合逻辑写入任务专属 `.py`，终端只执行 `python "./任务脚本.py"`。
3. **不假设 Unix 工具存在**：`jq` / `wget` / `unzip` / `sed` / `awk` / `pdftotext` / `base64` / `head` / `tail` / `grep` / `which` / `rg` 均须确认是否可用。目录枚举、筛选、复制、JSON/XML 处理优先用 Python；PowerShell 中 `curl`、`ls` 等可能是别名，不能照搬 Unix 参数。
4. **确认 Python 入口**：先用单独的只读命令确认可用 Python 3；Windows 默认尝试 `python`，不存在时再确认 `py -3` 或 `python3`。安装依赖使用已确认解释器的 `-m pip`，Python 子进程使用 `sys.executable`。
5. **脚本与任务文件路径分开**：每次显式设置工作目录，不依赖上一次调用的 `cd`。脚本路径相对 Skill 根目录，XML、分镜和 Prompt 路径相对本次任务目录，必要时使用加引号的绝对脚本路径。Python 用 `pathlib` 组合本地路径。
6. 中文、Markdown 和 Prompt 文件使用 UTF-8 编码。
7. 使用 Python 捕获输出和真实退出码，按工具契约解析响应。
8. **不使用 PowerShell 自动变量作为赋值目标**：避开 `$PID / $HOME / $PWD / $args / $input / $error / $host / $true / $false / $null`；使用任务专属变量名。

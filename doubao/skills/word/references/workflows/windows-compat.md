# Windows 兼容性

适用于 Windows 上的全部 Word 工作流。平台按顶层 `SKILL.md` 判断；本页仅补充执行约束，路由、编辑、恢复和验收沿用原流程。

执行前确认实际设备、shell、Python 和 CLI 入口，勿将用户目标设备当作执行设备。Windows 可使用 PowerShell、cmd 或 Bash，不可凭工具名判断 shell。

## Windows 命令约束

以下约束适用于 Windows 上的所有 shell，包括 Bash。

- 不得使用 `&&` 作为多指令串联操作
- 不得使用 `2>&1` `<<` 等指令作为输出重定向
- 不得使用 `head` `tail` `grep` `ls -la` `cat -n`等典型的与 `PowerShell` 不兼容的 `Bash` 指令
- 不得使用 `python3` 作为 `Python` 执行的默认指令

## 执行与路径

- 先确认可用 Python 3.10+ 及依赖；Python 子进程优先用 `sys.executable`。
- 编排逻辑写入任务专属 `.py`，每次 shell 调用只启动一条外部命令。避免混用 Bash heredoc、`$(...)`、`<<<` 与 PowerShell 语法，也不假设 Unix 工具或 `curl` 的含义跨 shell 一致。
- 文件读取、文本筛选、行号和目录枚举优先用 Python 标准库；复杂逻辑、复制和 JSON 处理用标准库，DOCX/XML 用 `python-docx` / `lxml`。
- CLI 用 `subprocess.run(argv, shell=False, cwd=workdir, capture_output=True, encoding="utf-8", errors="strict", timeout=...)`。`argv` 使用参数数组，不用 `eval`、shell 命令字符串或插值转义。
- 每次显式设置工作目录，不依赖上次调用的 `cd`。路径遵循命令契约；要求 CWD 内相对路径时使用 `./...`，不改成盘符绝对路径。
- 路径用 `pathlib` 组合，不硬编码分隔符；不将 `$HOME`、`$PID` 等系统变量用作任务变量。

## 内容与编码

- XML、中文、多行文本和复杂 JSON 先写 UTF-8 无 BOM 文件。仅在参数明确支持时使用 `@文件`，PowerShell 中写为 `"@文件"`；不假设所有参数都支持 `@file`。
- 不支持文件引用的参数用 Python 参数数组直接传递，不将 JSON、XML 或复杂文字嵌入 PowerShell 命令字符串。
- 不用 shell 管道或重定向保存、转传 CLI JSON/XML。PowerShell 5.1 与 7 的文件和管道编码不同，Python 的 `text=True` 也不保证 UTF-8；须显式指定编码，不用 `errors="ignore"` 隐藏中文损坏。
- 完整捕获结构化输出，再按命令返回契约解析，不先截断。JSON 输出用 `json.dump(..., ensure_ascii=False)`，文件指定 `encoding="utf-8"`。

## 结果确认与失败处理

- 保留 stdout、stderr 与真实退出码；退出码和响应信封均成功后，按原流程逐目标回读验收。stderr 有内容不等于失败，`NativeCommandError` 也不能作为忽略非零退出码的理由。
- 失败或结果未知（超时、解码失败、响应不完整）时，按原流程只读恢复并确认状态，不盲目重放写入。
- 缺失渲染器或必要依赖时说明缺口。已安装的 PyMuPDF 可替代 PDF 文本工具；文本检查或截图不能替代所需渲染与视觉验收。

===== 全文完 =====

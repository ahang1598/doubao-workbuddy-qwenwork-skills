# Windows 兼容性

适用于实际执行设备为 Windows 的短剧/剧情视频工作流。平台按顶层 `SKILL.md` 判断；本页补充命令与文件执行约束，素材路由、生成确认、Workspace 绑定、回读和交付沿用原流程。Mobile 路由优先，不因此启用被禁止的 Canvas 操作。macOS / Linux 不受本文件的 PowerShell 语法约束。

## 硬规则

1. **确认终端工具与实际 Shell**：使用当前环境提供的 PowerShell、Terminal、RunCommand、exec_command 等终端工具；工具名不等于 Shell，不要求存在 Bash 工具。确认 Windows 使用的是 PowerShell、cmd 还是 Bash，不能直接复制另一种 Shell 的示例。
2. **每次终端调用只启动一条外部命令**：不使用 `&&` / `||` 拼接命令，不使用 Bash 的 `\` 续行、heredoc、`<<<` 或命令替换。组合逻辑写入任务专属 `.py`，终端只执行 `python "./任务脚本.py"`。
3. **不假设 Unix 工具存在**：`jq` / `wget` / `unzip` / `sed` / `awk` / `pdftotext` / `base64` / `head` / `tail` / `grep` / `which` / `rg` 均须确认是否可用。目录枚举、筛选、复制、JSON/XML 处理优先用 Python；PowerShell 中 `curl`、`ls` 等可能是别名，不能照搬 Unix 参数。
4. **确认 Python 与 CLI 入口**：先用单独的只读命令确认可用 Python 3；Windows 默认尝试 `python`，不存在时再确认 `py -3` 或 `python3`。安装依赖使用已确认解释器的 `-m pip`，Python 子进程使用 `sys.executable`。确认 `design-cli` 可用及真实入口，不将找不到命令解释成业务失败，不打印认证环境变量。
5. **脚本与任务文件路径分开**：每次显式设置工作目录，不依赖上一次调用的 `cd`。脚本路径相对 Skill 根目录（`scripts/drama_lint.py`、`scripts/drama_rollback.py`），剧本、分镜和 Prompt 路径相对本次任务目录，必要时使用加引号的绝对脚本路径。Python 用 `pathlib` 组合本地路径。CLI 的 `--path "/deliverables/..."` 是画布逻辑路径，必须保留 `/`，不能改成盘符或反斜杠；不套用其他 CLI 的本地相对路径限制。
6. **四个写命令必须通过 stdin 提交 XML**：`+create` / `+create-batch` / `+update` / `+update-batch` 的 `--input` 只接受 `-`。Windows 使用 Python 子进程提供 stdin；禁止 `< item.xml`、`Get-Content ... | design-cli ...`，也禁止改成 `--input "@item.xml"` 或 `--input item.xml`。
7. **中文、XML、Markdown 和复杂文本先落文件**：写 UTF-8 无 BOM 文件；不把多行 XML、Prompt 或复杂 JSON 嵌进 PowerShell 命令字符串，不使用包含复杂双引号转义的 `python -c`。仅在当前命令明确支持时才使用 `@文件`，PowerShell 中加双引号；本 CLI 的 `--input` 不支持此写法。
8. **文件读写与输出捕获走 Python**：不用 `>` / `Out-File` / Shell 管道保存或转传 CLI 输出，避免 PowerShell 版本间编码差异。XML stdin 明确为 UTF-8 字节，完整捕获 stdout、stderr 和真实退出码；JSON/XML 按 UTF-8 严格解码，不用 `errors="ignore"` 掩盖损坏。
9. **不使用 PowerShell 自动变量作为赋值目标**：避开 `$PID / $HOME / $PWD / $args / $input / $error / $host / $true / $false / $null`；使用任务专属变量名。
10. **成功必须同时核对退出码、响应和目标状态**：退出码为 `0` 且响应 `code == 0` 后，按原流程解析 `xml_data` 并回读目标。stderr 有内容或 PowerShell 显示 `NativeCommandError` 均不足以单独判断失败；也不能因此忽略真实非零退出码。参数错误先修正；写入超时、响应不完整或解码失败时先只读恢复确认，不盲目重放创建。输出包含的内部 ID、日志不直接交付用户。

## 禁用命令 → 兼容替代

| 原写法或错误做法 | 问题 | 兼容替代 |
|---|---|---|
| `design-cli ... \` 后接多行参数 | `\` 不是 PowerShell 续行符 | 单行命令；复杂调用写入 `.py` |
| `design-cli ... --input - < item.xml` | PowerShell 不支持 Bash 的输入重定向写法 | Python 读取 XML，通过子进程 stdin 提交 |
| `Get-Content item.xml -Raw \| design-cli ... --input -` | 管道可能改变中文与编码 | 提交显式 UTF-8 字节，不经过 Shell 管道 |
| `--input "@item.xml"` / `--input item.xml` | 本 CLI 只接受 `--input -` | 文件由 Python 读取，CLI 参数仍为 `--input -` |
| `python3 scripts/drama_lint.py ... \` | 解释器名称、续行和工作目录不一定适用 | 已确认解释器 + 实际脚本路径 + 单行参数 |
| `python3 scripts/drama_rollback.py ... \` | 同上 | 已确认解释器 + 实际脚本路径 + 单行参数 |
| `python -c "..."` 中内嵌 XML、JSON 或复杂引号 | Shell 可能改变参数边界 | 先写任务专属 `.py` 后执行 |
| `--item-ids 123,188` 直接复制进 Shell | 逗号参数可能被 Shell 解释 | 重复传 `--item-ids "123" --item-ids "188"`，或用 Python 参数数组 |
| `--path "C:\deliverables\drama"` | 把画布逻辑路径误当成本地路径 | `--path "/deliverables/drama"` |
| `> result.json` / `Out-File` 保存响应 | 不同 PowerShell 版本的编码行为不同 | Python 保存原始响应字节，再显式解析 |
| 只看 `NativeCommandError` 或 stderr 是否为空 | 不能代表 CLI 的真实业务结果 | 捕获真实退出码并检查响应 `code`，成功后回读 |

## XML stdin 的 Python 模板

先使用文件编辑工具在任务目录写好 `item.xml` 与任务专属 `submit_item.py`，再在该目录用已确认的解释器执行 `python "./submit_item.py"`。模板中的 Workspace ID 必须取自当前对话或真实创建响应，XML 必须按对应命令页准备；批量或更新时替换命令名与 XML 文件名。

`cli_entry` 使用已经确认可直接启动的 CLI 入口参数数组，如原生可执行文件路径，或已确认解释器与 CLI 脚本路径。若发现入口只是 `.cmd` / `.bat` / PowerShell 包装器，先确认它实际启动的可执行程序或解释器，不把包装器当作原生程序，也不临时拼接 `shell=True` 命令绕过。

```python
import json
import subprocess
from pathlib import Path

workdir = Path(__file__).resolve().parent
cli_entry = ["design-cli"]  # 替换为当前设备已经确认的可直接启动入口
workspace_id = "替换为真实的canvas_workspace_id"
xml_file = workdir / "item.xml"
xml_text = xml_file.read_text(encoding="utf-8-sig")
payload = xml_text.encode("utf-8")
if not xml_text.strip() or len(payload) > 1024 * 1024:
    raise SystemExit("XML 为空或超过单次 1MB 上限，未提交。")

argv = cli_entry + [
    "design-workspace", "+create",
    "--canvas-workspace-id", workspace_id,
    "--input", "-",
]
try:
    result = subprocess.run(
        argv, input=payload, shell=False, cwd=workdir,
        capture_output=True, timeout=120,
    )
except subprocess.TimeoutExpired as exc:
    # 保留已有输出，停止后续写入；回到原流程只读确认上一次是否成功。
    (workdir / "submit-timeout.stdout.bin").write_bytes(exc.stdout or b"")
    (workdir / "submit-timeout.stderr.bin").write_bytes(exc.stderr or b"")
    raise SystemExit("写入超时，结果未知；先恢复查询，禁止直接重试。")

# 每次调用使用新的任务脚本名或目录，避免覆盖已有请求证据。
(workdir / "submit.stdout.bin").write_bytes(result.stdout)
(workdir / "submit.stderr.bin").write_bytes(result.stderr)
(workdir / "submit.exitcode.txt").write_text(str(result.returncode), encoding="utf-8")
if result.returncode != 0:
    raise SystemExit(f"CLI 退出码 {result.returncode}；读取已保存响应并按原流程确认状态。")

response = json.loads(result.stdout.decode("utf-8", errors="strict"))
if not isinstance(response, dict) or response.get("code") != 0:
    raise SystemExit("CLI 响应未确认成功，停止后续写入并确认状态。")
xml_data = response.get("xml_data")
if not isinstance(xml_data, str) or not xml_data.strip():
    raise SystemExit("CLI 响应不完整，结果未知；先恢复查询。")
# 从 xml_data 解析真实对象 ID，再按对应命令页 +get 回读与交付。
```

无法启动 CLI 属于环境阻塞；JSON 解码、响应解析失败属于结果未知。保留证据并按原流程恢复，不因模板未执行到末尾就判断服务器没有写入。只读命令同样可用参数数组调用，但不传 XML stdin；不把本模板改成自动重试器。

## 分镜校验与留档

- 按 `references/storyboard.md` 选择真实时长、镜头上下限和尾帧参数，不因平台适配更改创意或校验规则。
- Windows 单行示例（示例目录为 Skill 根目录，替换为本次路径与参数）：

```powershell
python "./scripts/drama_lint.py" "./task/storyboard.md" --check-ids --check-media-refs
```

```powershell
python "./scripts/drama_rollback.py" "./task/drama_plan.json" --stage video --ep 1
```

- 从其他工作目录执行时，传实际 Skill 脚本路径与实际分镜/规划路径；`<占位符>` 和 `[可选参数]` 是文档说明，不能原样执行。Python 编排校验时使用 `sys.executable`，必要时加 `-X utf8`，并显式按 UTF-8 捕获输出。
- 分镜与 Prompt 用 `Path.write_text(..., encoding="utf-8")` 留档。渲染、媒体生成、上传和 `present_files` 仍按原工具契约执行；不替换成终端文字输出。

===== 全文完 =====
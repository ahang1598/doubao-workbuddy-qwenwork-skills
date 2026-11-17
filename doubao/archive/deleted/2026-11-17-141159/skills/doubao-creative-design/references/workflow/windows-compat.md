# Windows 兼容性

适用于实际执行设备为 Windows 的设计工作流。平台按顶层 `SKILL.md` 判断，本页补充执行约束；Brief、素材清单、生产轨道、固定画布、验证与交付沿用原流程。Mobile 路由优先，不因此启用 Canvas。macOS / Linux 不受本文件的 PowerShell 语法约束。

## 硬规则

1. **Windows 首次终端调用即走 PowerShell**：确认宿主提供的 PowerShell、Terminal、RunCommand、exec_command 等入口及其实际 Shell；不先调用 Bash 试错，也不要求存在 Bash 工具。工具名不等于 Shell；PowerShell、cmd、Bash 写法不能混用。
2. **每次终端调用只启动一条外部命令**：不使用 `&&` / `||` 拼接命令，不复制 Bash 的 `\` 续行、heredoc、`<<<` 或命令替换。组合逻辑写入任务专属 `.py`，终端只执行已确认解释器与脚本路径。
3. **不假设 Unix 工具存在**：`jq` / `wget` / `unzip` / `sed` / `awk` / `pdftotext` / `base64` / `head` / `tail` / `grep` / `which` / `rg` 先确认可用性。读取、筛选、复制、目录枚举和 JSON/XML 处理优先使用 Python 标准库；PowerShell 中 `curl`、`ls` 等可能是别名，不能照搬 Unix 参数。
4. **确认 Python 与 CLI 入口**：Windows 默认尝试 `python`，不存在时确认 `py -3` 或 `python3` 是否可用；正文 `python3` 示例替换为已确认的 Python 3 入口，路径与业务参数保持不变。安装必要依赖使用该解释器的 `-m pip`；Python 子进程用 `sys.executable`。确认 `design-cli` 的真实入口，缺少命令属于环境缺口，不打印认证环境变量。
5. **脚本与任务文件路径分开**：每次显式设置工作目录，不依赖上一次 `cd`。`scripts/...` 相对 Skill 根目录，Brief、素材清单、HTML、XML 和截图相对任务目录；从其他目录运行时传实际脚本路径，含空格和中文的路径加引号。Python 用 `pathlib` 组合本地路径；HTML 本地导航使用 `Path.resolve().as_uri()`，不手工拼 `file://`。
6. **画布路径与本地路径分开**：CLI 的 `--path "/deliverables/..."` 和 XML 的 `path` 是画布逻辑路径，必须保留 `/` 开头，不改成 `C:\...`。本地图片、字体和 HTML 不能以盘符路径冒充 CDN URL；已有短链和上传仍按原门禁。不套用其他 CLI 的本地相对路径限制。
7. **四个写命令只通过 stdin 提交 XML**：`+create` / `+create-batch` / `+update` / `+update-batch` 的 `--input` 只接受 `-`。XML 写文件后由 Python 子进程提供 UTF-8 stdin；不用 `< item.xml`、`Get-Content ... | design-cli ...`，不改成 `--input "@item.xml"` 或 `--input item.xml`。
8. **Windows 不用内联 `python -c` 写诊断逻辑**：PowerShell 会先解析命令；Python 字典、正则、URL、JSON/XML 与内层引号即使在 Python 中合法，也可能在启动前被 PowerShell 拆坏。把这类逻辑及多行 HTML/XML 写成任务专属 UTF-8 无 BOM `.py` 文件，终端只运行已确认的解释器和带引号的脚本路径。字体异常先读 `shot.py` 的 `fontFaces`、`resourceErrors`、`webFontErrors`；确需额外 HEAD/CORS 探测也写 `.py` 文件。仅在当前参数明确支持时用 `@文件`；本 CLI 的 `--input` 不支持此写法。
9. **响应和编码显式处理**：不用 `>` / `Out-File` / Shell 管道保存或转传 CLI JSON、XML、字体契约和截图报告。Python 捕获 stdout、stderr 原始字节及真实退出码，再严格按 UTF-8 解码；不得用 `errors="ignore"` 隐藏中文损坏。Python JSON 输出有中文时可使用 `-X utf8`，子进程捕获显式指定 UTF-8。
10. **不使用 PowerShell 自动变量作为赋值目标**：避开 `$PID / $HOME / $PWD / $args / $input / $error / $host / $true / $false / $null`，使用任务专属名称。环境变量读取方式按实际 Shell，不复制 Bash 的 `$VAR` 写法。
11. **成功核对真实退出码和响应**：CLI 退出码 `0` 且响应 `code == 0` 后解析 `xml_data`，按原流程逐目标回读。stderr 有内容或 `NativeCommandError` 不足以单独判失败，也不能据此忽略真实非零退出码。写入超时、响应不完整或解码失败先只读恢复确认，不盲目重放创建。
12. **HTML 生产前预检，正式自检仍只运行 shot.py**：选定 HTML 路线后、生成素材或编写 HTML 前，先运行 `shot.py --check-runtime`；它只检查 Playwright、Pillow 和预装的 Chromium 能否启动，不读取 HTML 或截图。Windows 自动查找 `%LOCALAPPDATA%\ms-playwright` 下的预装 Chromium；非标准安装可用 `PLAYWRIGHT_BROWSERS_PATH` 或 `--exec-path` 指向该浏览器。预检失败立即记录环境缺口，按原退出码 `3` 规则处理后续可完成的交付；不得为赶进度搜索并切换到其他 Chromium 版本、系统 Edge/Chrome、其他预览工具或下载浏览器，也不得声称预览已验证。正式 HTML 自检仍运行同一个 `shot.py <html_path>`，不以预检结果代替截图与视觉验收。

## 禁用命令 → 兼容替代

| 原写法或错误做法 | 问题 | 兼容替代 |
|---|---|---|
| `design-cli ... \` 多行参数 | `\` 不是 PowerShell 续行符 | 单行命令，复杂调用写任务专属 `.py` |
| `design-cli ... --input - < item.xml` | PowerShell 不支持 Bash 的输入重定向写法 | Python 将 UTF-8 XML 字节送入 stdin |
| `Get-Content item.xml -Raw \| design-cli ...` | 管道可能改变中文与编码 | Python 参数数组和字节 stdin |
| `--input "@item.xml"` / `--input item.xml` | 本 CLI 只接受 `-` | 文件由 Python 读取，CLI 仍传 `--input -` |
| `--item-ids 123,188` 直接复制进 Shell | 逗号参数可能被 Shell 解释 | 重复传 `--item-ids "123" --item-ids "188"` 或 Python 参数数组 |
| `python3 scripts/runtime/shot.py ...` | 解释器名字或当前目录不适用 | 已确认 Python 3 入口和实际 Skill 脚本路径 |
| `python -c "...正则、字典或嵌套引号..."` | PowerShell 会在 Python 启动前解析并截断引号 | 用文件工具写任务专属 UTF-8 `.py`，运行 `python -X utf8 "<脚本路径>"` |
| Shell 重定向保存字体 JSON／shot 报告 | 不同 PowerShell 版本编码行为不同 | Python 保存原始字节，再显式解析 |
| `/absolute/segment-01.png` | 示例路径不是 Windows 实际文件位置 | 使用真实本地文件路径，含空格时加引号 |
| `--path "C:\deliverables\poster"` | 把画布路径误当本地目录 | `--path "/deliverables/poster"` |
| 手工拼 `file://C:\...\作品.html` | URL 与文件路径格式不同 | `Path(...).resolve().as_uri()`；shot.py 已处理 |
| 找不到浏览器就执行 `playwright install` 或改用其他版本 | 违反自检入口要求，应使用部署端预装 Chromium | 在生产前运行 `shot.py --check-runtime`；部署端预装 Chromium，缺失则报告缺口 |

## XML stdin 的 Python 模板

先在任务目录写好 `item.xml` 和任务专属 `submit_item.py`，再用已确认解释器执行 `python "./submit_item.py"`。模板 ID 必须替换成真实 Workspace ID；XML 根节点、字段、来源、大小和对象数量沿用对应 CLI 契约。批量／更新时替换命令名与文件名。

`cli_entry` 使用已确认可直接启动的原生程序，或已确认解释器与 CLI 脚本的参数数组。若入口仅为 `.cmd` / `.bat` / PowerShell 包装器，先确认它实际启动的程序或解释器，不临时拼接 `shell=True` 绕过参数边界。

```python
import json
import subprocess
from pathlib import Path

workdir = Path(__file__).resolve().parent
cli_entry = ["design-cli"]  # 替换为当前设备已确认的可直接启动入口
workspace_id = "替换为真实的canvas_workspace_id"
xml_text = (workdir / "item.xml").read_text(encoding="utf-8-sig")
payload = xml_text.encode("utf-8")
if not xml_text.strip() or len(payload) > 1024 * 1024:
    raise SystemExit("XML 为空或超过单次 1MB 上限，未提交。")
argv = cli_entry + [
    "design-workspace", "+create",
    "--canvas-workspace-id", workspace_id, "--input", "-",
]
try:
    result = subprocess.run(
        argv, input=payload, shell=False, cwd=workdir,
        capture_output=True, timeout=120,
    )
except subprocess.TimeoutExpired as exc:
    (workdir / "submit-timeout.stdout.bin").write_bytes(exc.stdout or b"")
    (workdir / "submit-timeout.stderr.bin").write_bytes(exc.stderr or b"")
    raise SystemExit("写入超时，结果未知；先恢复查询，不直接重试。")

# 每次调用使用新任务目录或脚本／证据文件名，避免覆盖已有请求证据。
(workdir / "submit.stdout.bin").write_bytes(result.stdout)
(workdir / "submit.stderr.bin").write_bytes(result.stderr)
(workdir / "submit.exitcode.txt").write_text(str(result.returncode), encoding="utf-8")
if result.returncode != 0:
    raise SystemExit(f"CLI 退出码 {result.returncode}；按已保存响应确认状态。")
response = json.loads(result.stdout.decode("utf-8", errors="strict"))
if not isinstance(response, dict) or response.get("code") != 0:
    raise SystemExit("响应未确认成功，停止后续写入并确认状态。")
xml_data = response.get("xml_data")
if not isinstance(xml_data, str) or not xml_data.strip():
    raise SystemExit("响应不完整，结果未知；先恢复查询。")
# 解析真实对象 ID，按命令页 +get 回读，再由主 Agent 按原出口交付。
```

CLI 无法启动属于环境缺口；解析失败属于结果未知。保留证据，停止依赖写入，不根据模板是否执行到底推断服务器未写入。只读命令也可用参数数组与相同的输出捕获方式，但不传 XML stdin，不把模板改成自动重试器。

## HTML、字体与素材脚本

下列示例从 Skill 根目录执行；任务文件路径和业务参数替换成实际值。每次终端调用只执行一条命令。其他工作目录使用实际 Skill 脚本路径。正文 `python3` 示例只替换为可用解释器，不改变参数含义。

```powershell
python -X utf8 "./scripts/runtime/shot.py" "./task/design.html"
```

如自动查找不到，但已有指定版本的浏览器，可使用实际路径：

```powershell
python -X utf8 "./scripts/runtime/shot.py" "./task/design.html" --exec-path "C:\实际安装目录\chrome-win\chrome.exe"
```

```powershell
python -X utf8 "./scripts/runtime/resolve_font.py" "douyin-sans" --target html --weight 700 --style normal --text "让美好发生" --require-ready
```

```powershell
python -X utf8 "./scripts/runtime/validate_asset_manifest.py" --require-ready "./task/asset-manifest.json"
```

- 字体检索与 CSS 库查询、SVG 内联、纹理、弧形文字和拼图脚本同样使用已确认解释器；长文案或复杂 JSON 参数由任务 `.py` 的参数数组传递，不手工拼 Shell 字符串。
- 保留 Resolver 白名单、真实 CDN、字体回退和素材清单要求。XML 系统字体与 HTML Web 字体不能混用，不因 Windows 全局强制改为微软雅黑。
- `shot.py` 使用输入 HTML 的真实路径和 `as_uri()`，截图仍同尺寸、DPR=1、完整 PNG；字体与图片等待、自然高度、安全区、分片及报告规则不变。
- `shot.py` 退出码 `0` / `1` / `3` 及其是否阻断后续步骤，严格沿用 [`html-preview.md`](html-preview.md)；Windows 兼容说明不增加或放宽生产和交付门禁。

===== 全文完 =====

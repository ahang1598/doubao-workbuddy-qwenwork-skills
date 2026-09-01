# Windows 兼容性

用于在 SystemPrompt 里出现 `Computer OS: Windows` 的会话，表明当前所在的设备是 Windows。Windows 上 Bash 工具调用实际交给 **PowerShell** 来执行，本 Skill 默认的 bash 示例（`jq --rawfile`、`--data "$(...)"`、`&&` 组合、`--output C:\...`、`ls -la`、`$PID` 等）会直接失败，故需要替换成其他命令来执行。macOS / Linux 不受本文件约束。

## 硬规则

1. **每次 Bash 调用只跑一条外部命令**：禁止 `&&` / `||` / heredoc / `$(...)` / `<<<`；组合逻辑走多次 Bash 调用或落成 `.py`。
2. **不假设 Unix 工具存在**：`jq` / `wget` / `unzip` / `sed` / `awk` / `pdftotext` / `base64` / `file` 在 Windows 上都没有；`curl` 是 `Invoke-WebRequest` 别名，参数完全不同。
3. **lark-cli 路径只接受 CWD 内相对路径**：`--output` / `--input` / `--file` / `--pages @xxx`，传 C盘路径比如 `C:\...` 这种绝对路径会被拒。开工第一步 `cd "<chat 目录>"`，之后一律 `./xxx`。
4. **`--params` / `--data` / `--pages` / `--parts` 绝对禁止命令行内联 JSON**：无论 `'{...}'` 单引号还是 `"{\"...\":\"...\"}"` 双反斜杠，PS 里两种都会拆散引号栈。只允许两条路径 —— ① typed flags（如 `--xml-presentation-id <id> --slide-id <sid>`）；② 先 Write `params.json` / `payload.json`，再 `--params "@params.json"` / `--data "@payload.json"`（`@` 前必须加双引号）
5. **`python3 -c "..."` 里禁止出现 `\"`、`'''` 内含 `"`、`"""` 或任何双引号相关的转义**：PS 的双引号处理跟 bash 不同，会把 `\"` 拆开导致 Python 拿到不完整字符串（`SyntaxError: unterminated string literal`）。凡是脚本里要用双引号的场景，一律 Write 到 `.py` 文件后 `python3 xxx.py`。
6. **不使用 PowerShell 自动变量作赋值目标**：`$PID / $HOME / $PWD / $args / $input / $error / $host / $true / $false / $null`，改用 `$PRES_ID / $SLIDE_ID / $FILE_TOKEN` 等前缀化命名。
7. **文件读写走工具本身或 Python**：不要用 `>` / `Out-File` / `Get-Content ... | cli --xxx -`——PowerShell 5 默认非 UTF-8、加 BOM、走 stdin 时非 ASCII 字节会被重编码。让 lark-cli 用 `--output`、让 Python 用 `open(..., encoding='utf-8')`。
8. 在 Windows PowerShell 5.X 上，lark-cli 的任何 stderr 输出（进度、失败 JSON、提示）都会被包成 NativeCommandError 并让 exit code 变非 0，所以 NativeCommandError 并不一定代表了报错，需要去细看报错内容才能知道真实报错是什么

## 禁用命令 → 兼容替代

### shell 组合

| 禁用 | 症状 | ✅ 替代 |
|---|---|---|
| `cmd1 && cmd2` | `The token '&&' is not a valid statement separator` | 拆成两次 Bash 调用；或 `python3 -c "import subprocess; subprocess.check_call([...]); subprocess.check_call([...])"` |
| `<<'EOF' ... EOF` / `<<<` | PowerShell 无 heredoc / here-string | 先 Write 到文件（`.py` / `.json`）再引用 |
| `"$(cmd)"` / `` `cmd` `` | PS 的 `$(...)` 是表达式插值，非命令替换 | 让 Python 跑外部命令，shell 层只做一件事 |
| `cmd 2>&1 \| Select-Object -Last 5` | native stderr 被 PS 视为 error-record，`2>&1` 语义不同 | 直接跑命令；截断输出用 `python3 -c "print(''.join(open('out.txt').readlines()[-5:]))"` |
| `mkdir -p dir` | PS5 的 `mkdir` 不支持 `-p` | `python3 -c "import pathlib; pathlib.Path('dir').mkdir(parents=True, exist_ok=True)"` |
| `ls -la <path>` | `Get-ChildItem: A parameter cannot be found that matches parameter name 'la'` | 用 Read 工具；或 `python3 -c "import os,sys;p=sys.argv[1];print(os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)" <path>` |

### Unix-only 工具

| 禁用 | ✅ 替代 |
|---|---|
| `jq -n --rawfile c slide.xml '{slide:{content:$c}}'` | Write 一段 `build_payload.py`（`json.dump({'slide':{'content':open(sys.argv[1],encoding='utf-8').read()}}, open(sys.argv[2],'w',encoding='utf-8'), ensure_ascii=False)`），再 `--data @payload.json` |
| `wget URL -O file` | `python3 -c "import urllib.request; urllib.request.urlretrieve('URL','file')"` |
| `curl -L -o file URL` | 同上；或显式 `curl.exe -L -o file URL`（`.exe` 后缀绕过 PS 别名） |
| `unzip file.zip` | `python3 -c "import zipfile; zipfile.ZipFile('file.zip').extractall('.')"` |
| `sed -i` / `awk` | Python `re.sub` / 处理逻辑 |
| `pdftotext file.pdf -` | `python3 -c "import fitz; print(''.join(p.get_text() for p in fitz.open('file.pdf')))"` |
| `base64 -d` | `python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))"` |

### lark-cli 参数

| 禁用 | 症状 | ✅ 替代 |
|---|---|---|
| `--output "C:\Users\...\full.xml"` | `--output must be a relative path within the current directory` | 先 `cd "<chat 目录>/<sess>"`，再 `--output ./full.xml` |
| `--file "C:\Users\...\bg.jpg"` | `--file must be a relative path within the current directory` | 同上，先 `cd` 素材目录再 `--file ./bg.jpg` |
| `--pages @pages.json`（未加引号） | `The splatting operator '@' cannot be used to reference variables in an expression` | 加双引号：`--pages "@pages.json"` |
| `--params '{"xml_presentation_id":"<id>"}'` | 单引号 JSON 在 PS 里勉强能过，拼变量必然错 | 优先 typed flags（`--xml-presentation-id <id> --slide-id <sid>`）；否则 `--params @params.json` |
| `--data "$(jq ...)"` | jq 不存在 + PS 无命令替换 | Write `payload.json` 后 `--data @payload.json` |
| `--params "{\"xml_presentation_id\":\"<id>\"}"` | PS 双引号不认 `\"` 转义，lark-cli 收到坏 JSON | 同上 |

### 编码 / BOM / CRLF

| 禁用 | 症状 | ✅ 替代 |
|---|---|---|
| `Get-Content file.json -Raw \| lark-cli ... --pages -` | 中文 UTF-8 字节被 PS 管道重编码，`invalid character '\uXX'` | 改 `--pages "@file.json"` |
| `'{"k":"v"}' \| Out-File params.json` | Out-File 默认 UTF-16 LE + BOM，lark-cli 解析失败 | 用 Write 工具生成；或 `python3 -c "import json; json.dump({'k':'v'}, open('params.json','w',encoding='utf-8'), ensure_ascii=False)"` |
| shell 重定向 `> out.json` | PS5 默认 UTF-16 LE + BOM | 让工具自己写文件（`--output`），或 Python 写 |

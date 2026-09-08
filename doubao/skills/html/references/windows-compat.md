# Windows 兼容性

用于 SystemPrompt 里出现 `Computer OS: Windows` 的会话。macOS / Linux 不受本文件约束。

Windows 上 Bash 工具调用实际交给 **PowerShell** 执行，你会遇到三类问题：

- **bash 语法几乎全部失效**：`&&`、`$(...)`、heredoc、**引号转义**、`ls -la` 这类 Unix 参数，要么
  直接报错，要么静默产生错误结果。
- **编码被静默改写**：一段 UTF-8 文本经过 PowerShell 就换了编码——写文件默认 UTF-16 LE 加 BOM，
  管道和 stdout 按系统代码页（中文环境是 cp936）重编码。表现是频繁乱码、`invalid character
  '\uXX'`、文件开头多出 BOM，而且不报错。
- **Unix 工具不可靠**：`jq` / `sed` / `awk` / `unzip` / `head` / `grep` 根本不存在；`curl` /
  `wget` / `ls` / `cat` / `sort` 则是 PowerShell 命令的别名，同名但参数和语义都不同。

因此在 Windows 上：**Bash 工具里的命令写得尽可能简单，复杂逻辑一律下沉到 Python 脚本**，用标准库
替代 Unix 工具（`urllib` 换 curl、`zipfile` 换 unzip、`json` 换 jq、`re` 换 sed）。管道和重定向
不要经过 PowerShell，让 Python 直接读写文件，并且每次都显式带编码：`open(..., encoding='utf-8')`。
命令失败时**不要尝试继续改写 PowerShell 写法**。

## 怎么下沉

- **Python 代码简单小于三行、且代码中只需要使用单引号** → 直接 `python -c "<code>"`，省一次工具调用。
- **代码需要双引号，或含 `$` / 反引号，代码量多** → Write 一个 `xxx.py`，再 `python xxx.py`。这几个字符会被
  PowerShell 吃掉（`$x` 被当成 PS 变量展开），典型报错 `SyntaxError: unterminated string literal`。

撞到下面这些报错，说明你在写 shell 语法，回到上面的规则，别在 shell 里继续试参数：

| 报错 | 你违反了 |
| --- | --- |
| `The token '&&' is not a valid statement separator` | 一条命令里串了多条 |
| `A parameter cannot be found that matches parameter name 'la'` | 用了 Unix 命令的参数（`ls -la`、`wget -O`、`curl -o`） |
| `SyntaxError: unterminated string literal` | 在 `python -c "..."` 里写了引号转义 |
| 中文乱码 / `invalid character '\uXX'` / 文件开头多出 BOM | 让管道或重定向经过了 PowerShell |
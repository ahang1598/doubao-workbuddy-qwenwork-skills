---
name: verifier-hub
description: >-
  Deterministic artifact verifier CLI (file/xlsx/docx/pdf/pptx/text/archive/rubric)
  for pre-delivery artifact checks and agentic judges. 58 subcommands callable as
  `verifier {family} {subcmd} [args]`. Use before delivering or uploading a file,
  or whenever you need to check file format, sheet/section presence, cell values,
  formulas, keywords, character counts, page counts, placeholders, signatures or
  zip contents, instead of guessing from an LLM reading. Every call prints one
  JSON object with a quotable `evidence` field.
license: Proprietary — internal use only.
compatibility: >-
  Linux, macOS or Windows. Needs Python 3.10+ and the Python packages openpyxl,
  python-docx, python-pptx and PyYAML; the pdf family additionally needs one of
  pymupdf / pdfplumber / pypdf. `docx page-count --method soffice` needs a
  LibreOffice install. Everything else is pure Python. On Windows invoke the
  entry point as bin/verifier.cmd (or `python bin/verifier`): the
  extension-less POSIX script cannot be executed directly there.
metadata:
  version: "2.1"
  hub: verifier-hub
---

# verifier-hub

`verifier` CLI 对产物文件做可复现校验（xlsx / docx / pdf / pptx / md / zip 等）。
它回答的是「文件结构和数值对不对」这类有确定答案的问题，比让模型读一遍再判断可靠。

主要用在交付前自检：准备把文件交给用户之前，先用 verifier 确认格式和关键内容都符合任务要求。

## CLI 形态

优先用工作区内的相对路径调用：

```
./skills/verifier-hub/bin/verifier
```

Windows 上换成同目录的 `.cmd` 包装，或者直接把无扩展名的脚本交给 Python：

```powershell
.\skills\verifier-hub\bin\verifier.cmd docx outline .\contract.docx
python .\skills\verifier-hub\bin\verifier docx outline .\contract.docx
```

下文所有示例都写成 POSIX 形式，Windows 上按上面这两种写法替换即可。

两级子命令：

```bash
verifier --help                       # 列 family
verifier <family> --help              # 列 family 内子命令
verifier <family> <subcmd> --help     # 查看子命令参数与默认值
```

## 输出协议

每次调用在 stdout 输出**一个** JSON 对象，参数写错时也一样：

```json
{"ok": true,  "tool": "<family>.<sub>", "result": {...}, "evidence": {...}}
{"ok": false, "tool": "<family>.<sub>", "error": {"code": "...", "msg": "..."}}
```

- `ok` 表示**工具本身**是否执行成功，不表示校验结论。
- 校验结论在 `result.passed`（`true` / `false` / `null`，`null` 表示该子命令只报告事实、不做断言）。
  所以「文件格式不符合预期」这种情况是 `ok: true` + `result.passed: false`。
- `evidence.quote` 是可直接引用的一句话证据。
- `rubric` 家族在 `result` 里额外给 `passed` 和 `evidence_quote` 两个字段（注意都在 `result` 下，不在顶层）。

## 交付前校验流程

1. **定位待交付文件**：确认文件真实存在，路径和扩展名正确。
2. **格式校验**：对每个文件至少跑一次
   ```bash
   ./skills/verifier-hub/bin/verifier rubric check-file-format <path> --expected-ext <.ext>
   ```
3. **内容校验**：按文件类型补一条与任务直接相关的检查，例如
   - xlsx：`xlsx list-sheets`、`xlsx assert-value`、`xlsx eval-formula`
   - docx：`docx outline`、`docx table-list`、`docx page-count`
   - pdf：`pdf pages`、`pdf text-dump`、`pdf cjk-check`
   - pptx：`pptx list-slides`、`pptx slide-text`
   - text / md：`text must-contain`、`text placeholder-audit`
   - zip：`archive zip-list`、`archive zip-check-entries`
4. **记录证据**：交付说明里只引用真实执行过的 verifier 命令和它的输出。不要把自己用 Python 或 Bash 算出来的结果说成 verifier 证据。
5. **再交付**：所有待上传文件都通过校验后再交付。

## 工具族总览

| family    | 子命令数 | 典型用途 |
| --------- | -------- | -------- |
| `file`    | 4  | 列产物 / 校验可打开 / 抽文本 / 计数 |
| `xlsx`    | 12 | sheet、cell、公式、格式、求和、列号格式；含 `eval-formula` 跨 cell 回算 |
| `docx`    | 12 | 大纲、章节抽取、表格、修订标记、签字块、布局、页数、图片计数、页面设置 |
| `pdf`     | 4  | 页数与方向、抽文本、CJK 字体检测、图片计数 |
| `pptx`    | 4  | slide 列表、抽文本、按 regex 找 slide、图表与图片计数 |
| `text`    | 9  | 关键词、正则计数、章节字数、中文占比、引用、占位符、列表项、日期 |
| `archive` | 2  | zip 内容列表、必含条目断言 |
| `rubric`  | 11 | 高层 DSL：把常见组合一行搞定，含跨文件数值一致性校验 |

**58 个子命令的完整参数与调用示例见 [`references/subcommands.md`](references/subcommands.md)。**
也可以直接 `verifier <family> --help` 现场查，不必先读文档。

## 错误码

| code               | 含义 |
| ------------------ | ---- |
| `FILE_NOT_FOUND`   | 文件不存在 |
| `NOT_A_FILE`       | 路径存在但不是普通文件 |
| `BAD_EXT`          | 扩展名与预期不符 |
| `PARSE_ERROR`      | 文件存在但所选库打不开（损坏 / 格式不对） |
| `LOCATOR_INVALID`  | `--cell` / `--range` / `--locator` 形式错误 |
| `NOT_FOUND`        | sheet / heading / row-header / table-index 不存在 |
| `DEP_MISSING`      | 需要的 Python 包或 LibreOffice 不可用，`msg` 里带可执行的安装命令 |
| `BAD_ARGS`         | 参数缺失、类型错、family 或子命令名写错 |
| `INTERNAL`         | 不属于以上任何一类（dispatcher 兜底包装） |

## 依赖与环境

| 用途 | 需要什么 | 缺了会怎样 |
| ---- | -------- | ---------- |
| xlsx 家族 | `openpyxl` | `DEP_MISSING` |
| docx 家族 | `python-docx` | `DEP_MISSING` |
| pptx 家族 | `python-pptx` | `DEP_MISSING` |
| pdf 家族、`file extract-text`（PDF）、`docx page-count --method soffice` | `pymupdf`、`pdfplumber`、`pypdf` 三者之一，按此顺序选用 | 三个都没有才 `DEP_MISSING`；结果里的 `backend` 字段会写明实际用的是哪个 |
| `text`、`archive` 家族 | 只用标准库 | 不会缺 |
| `docx page-count --method soffice` | LibreOffice 二进制 | `DEP_MISSING`；`--method auto` 会自动退到 XML 启发式，并在 `soffice_fallback_reason` 里说明原因 |

安装缺失的 Python 包时**不要**用裸 `pip install`：沙箱里 venv 的 site-packages 不可写，
user site 又没有 sys.path 优先级，两种默认路径都会失败。用这个写法：

```bash
pip install --target "$HOME/.verifier-pylibs" pymupdf
export PYTHONPATH="$HOME/.verifier-pylibs:$PYTHONPATH"
```

Windows / PowerShell 上没有 `$HOME` 和 `export`，改用：

```powershell
python -m pip install --user pymupdf
```

`DEP_MISSING` 的 `msg` 里已经按当前平台和缺失的包把命令拼好了，照着执行再重试即可。
LibreOffice 在 Windows 上用 `winget install --id TheDocumentFoundation.LibreOffice -e` 装，
安装器不会把它加到 PATH，但 `--method soffice` 会自己去 `%ProgramFiles%\LibreOffice\program\` 找。

## 调试指南

调用失败或输出不符合预期时：

1. `verifier <family> <subcmd> --help` 看完整参数与默认值。
2. 用 **Read** 打开 `skills/verifier-hub/lib/<family>.py` 读源码，每个家族不超过 400 行。
3. `DEP_MISSING` → 按 `msg` 里给的 `pip install --target` 命令装包后重试。
4. `LOCATOR_INVALID` / `NOT_FOUND` → 先用 `xlsx list-sheets`、`docx outline`、`docx table-list`
   把结构列出来，再选 cell / heading / row-header。
5. `BAD_ARGS` → `msg` 里带了 argparse 的原文，照着补参数。

## 何时不要用 verifier

- 主观判断类的问题（图表是否美观、语气是否专业）：工具拿不到决定性证据，老老实实读内容再下判断。
- 需要看实际渲染效果的问题（HTML 显示效果、PPT 整体视觉）：verifier 只能读元素，判断不了「看起来对不对」。
  这类问题用 `artifact-preview` 渲染成图片再看。

结构、数值、关键字、格式、占位符这几类，verifier 都能给出比模型自己读一遍更可靠的判定。

## 评分员模式

如果当前工作区里存在 `questionnaire.md`、`rubric_index.yaml`、`run_verifiers.py` 这些评分文件，
说明这是 questionnaire 评分任务，工作流和上面的交付前自检不同，
见 [`references/questionnaire.md`](references/questionnaire.md)。
工作区里没有这些文件时，忽略这一节。

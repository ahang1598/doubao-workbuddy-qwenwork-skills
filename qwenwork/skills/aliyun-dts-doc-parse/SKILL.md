---
name: aliyun-dts-doc-parse
description: 通过阿里云 DTS-AI 端到端解析 PDF、DOCX、PPTX 和图片等本地文件，并将结果保存为 Markdown。用户提到 DTS-AI 文档解析，或需要把本地 PDF、Word、PowerPoint 或图片解析、转换、提取为 Markdown 时使用。
install_source: official
install_method: download
skill_id: official_Gs3nl4Um
enabled_at: 1791893791119
version: 1.0.1
name_zh: 文档解析
---

# 阿里云 DTS-AI 文档解析

## 功能与支持格式

使用 `scripts/dts_doc_parse.py` 完成文件验证、上传、解析、等待结果和原子保存，并向用户交付最终 Markdown 文件。云端任务及其恢复机制属于内部实现，正常流程中不得要求用户查询、选择或恢复任务。

可解析以下格式的可读、非空本地文件：`pdf`、`docx`、`pptx`、`png`、`jpg` 和 `jpeg`。

## 云端处理与安全边界

- 仅当用户明确要求使用 DTS-AI 或本技能解析指定的本地文件，或在获知该流程需要云端处理后明确确认时，才可启动解析。授权涵盖完成当前请求所需的文件上传和云端处理；不得单独上传文件，也不得处理用户未指定的文件。
- 不得打印、记录或暴露 API Key 或临时 OSS 凭据。
- 只能通过 `scripts/dts_doc_parse.py` 读取凭据。API Key 缺失、需要设置或认证失败时，阅读 [DTS-AI 认证](references/dts-ai-authentication.md)。
- 必须原样保存 DTS-AI 返回的 Markdown。结果完整性和内部恢复规则以[解析任务执行与结果处理](references/parser-job-execution.md)为准。

## 运行环境与认证配置

支持 Windows、macOS 和 Linux，需要 Python 3。命令路径均相对于本 `SKILL.md` 所在目录解析；命令中的 `python3` 表示 Python 3 解释器，Windows 可使用 `py -3`。

在不显示密钥、不发送网络请求的情况下检查本地配置：

```bash
python3 scripts/dts_doc_parse.py check
```

如果 API Key 不存在，先阅读 [DTS-AI 认证](references/dts-ai-authentication.md)，再引导用户运行：

```bash
python3 scripts/dts_doc_parse.py setup --language <en|zh-CN>
```

## 输出文件与内部恢复

持久输出和恢复记录默认保存至当前用户主目录下的 `.aliyun-dts/doc-parse/`。省略 `--output` 时，默认输出名保留输入文件的完整名称和源扩展名，例如 `report.pdf.md`、`report.docx.md`。如果该名称已被不同内容占用，命令使用输入内容 SHA-256 的前 8 位生成稳定名称，例如 `report.pdf-a1b2c3d4.md`。该命令只会创建默认目录；其他输出目录必须已存在且由用户明确指定。

除非用户明确要求使用 `--force`，否则不得覆盖现有输出。命令会先根据输入内容 SHA-256 检测此前保存的相同内容；检测到时直接复用已有结果，不得重新上传。用户指定新的 `--output` 时，命令将已有结果原子复制到该路径；目标已存在时仍须停止，不得自动改名或覆盖。除非用户明确要求重新解析，否则不得使用 `--force`。完整规则见[解析任务执行与结果处理](references/parser-job-execution.md)。

在无法写入默认主目录路径的沙箱中，请用户指定一个可写目标，或在具备写权限的环境中重新执行。

## 文档解析流程

### 解析单个文件

除非用户选择了目标位置，否则省略 `--output`：

```bash
python3 scripts/dts_doc_parse.py parse "/absolute/path/to/<input-file>"
```

对于用户选择的现有目录：

```bash
python3 scripts/dts_doc_parse.py parse \
  "/absolute/path/to/<input-file>" \
  --output "/absolute/existing-dir/<output-file>.md"
```

命令会端到端等待解析完成并保存结果。正常完成后，只向用户说明 Markdown 输出路径和必要的结果说明，不得展示 JobId、任务状态、恢复命令或恢复记录。结果供其他程序处理时，优先使用 `--json`；此时标准输出仅包含一个最终对象，字段为 `status`、`job_id`、`output` 和 `bytes`，其中 `status` 恒为 `success`。失败时进程以非零退出码退出，且不输出该对象。

### 异常后的内部恢复

仅在超时、中断、保存失败或结果状态不明确时，保留命令输出的 JobId 并在同一请求中恢复，不得重新上传：

```bash
python3 scripts/dts_doc_parse.py resume "<JobId>"
```

省略 `--output` 时，命令使用记录中的路径；如果找不到匹配且有效的 v1 记录，则停止执行。需要定位可恢复解析时，可在不发送网络请求的情况下列出不含密钥的本地恢复记录：

```bash
python3 scripts/dts_doc_parse.py jobs
```

如需结构化输出，使用 `jobs --json`。核对 API 响应、检查恢复记录、处理异常状态或遇到超时、中断和保存失败时，阅读[解析任务执行与结果处理](references/parser-job-execution.md)，并优先自行完成恢复。只有无法在当前请求中交付最终文件时，才向用户说明解析未完成及可采取的下一步；除非排障确有必要，不得要求用户理解或操作 JobId、`jobs` 或 `resume`。

### 处理多个文件和多页文档

将多页文档视为一个文件、一个任务和一个输出。不得自动拆分。解析器用 `---` 分隔 PDF 页面；不会跨页重新拼接句子。

逐个解析多个独立文件，每个文件对应一个任务和一个输出。单个文件失败不得影响此前生成的输出。省略 `--output` 时，由脚本按上述规则生成互不覆盖的稳定名称；用户指定的输出路径发生冲突时必须停止，不得使用 `--force` 绕过。仅当用户明确要求时，才可合并输出。

## 官方 API 文档

- [使用 DTS-AI API 解析文档](https://help.aliyun.com/zh/dts/use-cases/use-dtsai-api-to-parse-documents)
- [CreateDocParserJob](https://help.aliyun.com/zh/dts/developer-reference/api-dtsai-2026-04-01-createdocparserjob)
- [DescribeDocParserJobStatus](https://help.aliyun.com/zh/dts/developer-reference/api-dtsai-2026-04-01-describedocparserjobstatus)
- [DescribeDocParserJobResult](https://help.aliyun.com/zh/dts/developer-reference/api-dtsai-2026-04-01-describedocparserjobresult)

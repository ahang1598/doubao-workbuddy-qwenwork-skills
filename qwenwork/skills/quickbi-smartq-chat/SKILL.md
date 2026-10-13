---
name: quickbi-smartq-chat
description: |
  Quick BI-智能分析 技能，具备多种数据分析能力:
  1. **数据集问数**：自然语言查询 Quick BI 平台数据集，自动智能选表匹配
  2. **文件问数**：上传 Excel/CSV 文件，通过 Quick BI API 进行智能分析
  3. **文档解析**：解析 PDF/Word/Excel/CSV/图片等文档，提取文本，并支持提取关键字段并生成结构化 Excel
  4. **仪表板技能生成**：将 QuickBI 仪表板自动转化为数据查询技能
  5. **数据解读**：对 Quick BI 数据集进行深度数据洞察分析
  6. **数据报告**：基于数据分析结果自动生成专业数据报告
  当用户提到数据分析、问数、智能问数、查数据、分析文件、文档解析、仪表板技能、数据解读、数据报告等场景时使用此技能。
compatibility:
  tools:
    - python3
    - pip
    - browser
  runtime:
    - requests
    - pyyaml
    - matplotlib
    - numpy
metadata:
  label: Quick BI-智能分析
install_source: official
install_method: download
skill_id: official24681357
enabled_at: 1791893724942
version: 1.0.1
name_zh: 数据分析
---

# Quick BI-智能分析 — QuickBI 数据分析助手

一个入口，覆盖 QuickBI 全场景数据分析能力。根据用户意图自动路由到对应模块，无需手动选择。

## Scope

**Does:**
- 自动识别用户意图并路由到对应数据分析模块
- 对 Quick BI 平台数据集进行自然语言查询分析（数据集问数）
- 对用户上传的 Excel/CSV 文件通过 Quick BI API 进行自然语言分析（文件问数）
- 解析 PDF/Word/Excel/CSV/图片等文档，提取文本，支持提取关键字段并生成结构化 Excel（文档解析）
- 将 QuickBI 仪表板自动转化为数据查询技能（仪表板技能生成）
- 对数据集进行深度洞察分析（数据解读）
- 基于分析结果自动生成专业数据报告（数据报告）

**Does NOT:**
- 在问数场景下使用 pandas/openpyxl/csv 等库直接读取文件进行本地分析
- 要求用户手动选择模块或提供 cubeId 等内部参数
- 执行与 QuickBI 数据分析无关的任务

## 任务路由

根据用户输入自动判断意图，路由到对应模块执行。

### 路由决策表

| 用户意图特征                                                     | 路由模块        | 参考文档                                                                                                                                              |
|------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| 未上传文件，要查询/分析平台数据集中的具体指标                                    | 数据集问数       | [module-chat.md](references/chat/module-chat.md)                                                                                                  |
| 上传了 Excel/CSV 文件，要查询具体指标或回答具体数据问题（如 TOP N、对比、筛选）           | 文件问数        | [module-chat.md](references/chat/module-chat.md)                                                                                                  |
| 上传了多个文件(PDF/word/图片等), 或者选择文件夹，要查询具体数据问题（如 TOP N、对比、筛选）    | 文档解析 → 文件问数 | [module-document-parser.md](references/document/module-document-parser.md) → [module-chat.md](references/chat/module-chat.md)                     |
| 上传了 PDF/Word/图片等非结构化文档，, 或者选择文件夹，要解析所有文件内容或提取字段            | 文档解析        | [module-document-parser.md](references/document/module-document-parser.md)                                                                        |
| 提供了 QuickBI 仪表板 URL，要生成查询技能                                | 仪表板技能生成     | [module-dashboard.md](references/dashboard/module-dashboard.md)                                                                                   |
| 上传了 Excel 文件，要对数据进行深度解读/洞察/趋势分析（不生成报告文档）                   | 数据解读        | [module-data-insight.md](references/insight/module-data-insight.md)                                                                               |
| 上传了多个文件(PDF/word/图片等), 或者选择文件夹，要对数据进行深度解读/洞察/趋势分析（不生成报告文档） | 文档解析 → 数据解读 | [module-document-parser.md](references/document/module-document-parser.md) -> [module-data-insight.md](references/insight/module-data-insight.md) |
| 要生成报告/分析报告/复盘报告，无论是否上传文件                                   | 数据报告        | [module-data-report.md](references/report/module-data-report.md)                                                                                  |

### 路由优先级规则

当用户意图可能匹配多个模块时，按以下优先级判断：

1. **「报告」关键词优先**：用户意图中包含「报告」「复盘」「总结报告」「分析报告」等生成报告类关键词时，**始终路由到数据报告模块**，无论是否上传了文件。数据报告模块的优先级高于文件问数和数据解读
2. **「解读」「洞察」「趋势」关键词**：用户要求理解数据含义、发现趋势或洞察规律，路由到数据解读模块
3. **具体数据查询**：用户要查询具体指标（TOP N、求和、对比等），路由到问数模块（根据是否有文件选择数据集问数或文件问数）
4. **仪表板 URL**：用户提供了仪表板链接，路由到仪表板技能生成

### 路由示例

| 用户输入                                | 路由结果                                                         | 判断依据              |
|-------------------------------------|--------------------------------------------------------------|-------------------|
| "销量最高的地区TOP3"                       | → 数据集问数 (module-chat)                                        | 查具体指标，无文件         |
| "帮我查一下这份数据中销售额最高的产品" + 上传文件         | → 文件问数 (module-chat)                                         | 查具体指标，有文件         |
| "帮我分析这份Excel数据，各部门人数分布TOP10" + 上传文件 | → 文件问数 (module-chat)                                         | 查具体指标（TOP N），有文件  |
| "解析这些合同并汇总信息" + 文件夹                 | → 文档解析 (module-document-parser)                              |                   |
| "把这个仪表板转化为查询技能" + URL               | → 仪表板技能生成 (module-dashboard)                                 | 提供了仪表板 URL        |
| "帮我解读一下销售数据的趋势" + 上传文件              | → 数据解读 (module-data-insight)                                 | 要求解读/洞察，非报告       |
| "这份数据有什么规律和洞察" + 上传文件               | → 数据解读 (module-data-insight)                                 | 要求洞察分析            |
| "生成一份本月销售数据报告"                      | → 数据报告 (module-data-report)                                  | 含「报告」关键词          |
| "帮我基于这份Excel生成一份分析报告" + 上传文件        | → 数据报告 (module-data-report)                                  | 含「报告」关键词，文件作为参考资料 |
| "汇总这几份数据，写一份复盘报告" + 上传文件            | → 数据报告 (module-data-report)                                  | 含「复盘报告」关键词        |
| "结合这些文件生成数据分析报告" + 上传文件             | → 数据报告 (module-data-report)                                  | 含「报告」关键词          |
| "解析这10个发票PDF，提取字段生成Excel" + 多文件     | → 文档解析 (module-document-parser)                              | 含"提取字段"等相关关键字     |
| "帮我查一下这份数据中销售额最高的产品" + 多个文件或者文件夹    | → 文档解析 (module-document-parser) → 文件问数 (module-chat)         | 查具体指标，有多个文件       |
| "这些文件中的数据有什么规律和洞察" + 多个文件或者文件夹      | → 文档解析 (module-document-parser) → 数据解读 (module-data-insight) | 要求洞察分析      
| "汇总这几份数据，写一份复盘报告" + 5个以内文件          | → 数据报告 (module-data-report)                                  | 含「复盘报告」关键词        |
| "汇总这几份数据，写一份复盘报告" + >5个文件             | → 文档解析 (module-document-parser) → 数据报告 (module-data-report)  | 含「复盘报告」关键词        |

### 兜底规则
- 当意图不明确时，**默认路由到数据集问数**（module-chat）
- 如果用户同时涉及多个模块（如"分析数据并生成报告"），按顺序依次执行
- **特殊场景 - 多文件问数前置处理**：
  - 当用户上传 ≥5 个非结构化文档（PDF/Word/图片等）并要求分析时
  - **必须先执行文档解析**（生成结构化 Excel）
  - **再根据问题意图，路由对应的功能模块**（对生成的 Excel 进行智能分析）
  - 示例："分析这些发票数据" + 10个PDF → 文档解析(生成Excel) → 文件问数(分析Excel)
- 路由错误时允许用户手动指定模块

## 配置

本技能采用 **配置分层** 架构，用户配置与技能包分离，**技能包更新不会覆盖用户配置**。

> **`<工作目录>` 约定**：本文档中 `<工作目录>` 指用户当前在 IDE / 文件管理器中打开的文件夹的绝对路径。Agent 需在首次操作前确认该路径，应该通过运行python脚本 os.getenv('CODE_AGENT_CURRENT_SESSION_WORK_DIR') 来获取。如果脚本获取不到或为空，应该使用用户选择的文件夹的绝对路径。禁止使用 `$PWD` 或 `$CWD` 或 `Path.cwd()` 等运行时变量推断。
>
> **`<技能包目录>` 约定**：本文档中 `<技能包目录>` 指本 skill 安装后的根目录（即包含本 `SKILL.md` 文件的目录）。Agent 可通过本文件所在路径推断获得。

### 配置加载优先级（高覆盖低）

1. **环境变量** `ACCESS_TOKEN`（最高优先级，适合容器部署）
2. **工作目录级配置** `<工作目录>/.qbi/smartq-chat/config.yaml`
3. **QBI 全局配置** `~/.qbi/config.yaml`（所有 skill 共享）
4. **默认配置** 技能包内 `default_config.yaml`（包内默认值，随包更新）

`server_domain`、`api_key`、`api_secret`、`user_token` 可以放在工作目录级配置或全局配置中。当两者都存在时，工作目录级配置优先。

### 配置项说明

- **`server_domain`**：Quick BI 服务域名
- **`api_key`** / **`api_secret`**：OpenAPI 认证密钥对（未配置时使用内置默认值进入试用）
- **`user_token`**：Quick BI 平台用户 ID，问数接口需传 `userId`（未配置时自动注册并回填）

若启用 `use_env_property: true`，可通过环境变量 `ACCESS_TOKEN` JSON 中的 `qbi_api_key`、`qbi_api_secret`、`qbi_server_domain`、`qbi_user_token` 字段覆盖配置。

### 试用凭证自动注册

当 `api_key`、`api_secret` 均未配置时（无论 `user_token` 是否存在），脚本会：
1. 若 `user_token` 也未配置，输出温馨提示，告知用户将自动注册试用凭证并进入试用期
2. 使用内置默认凭证填充 `api_key` 和 `api_secret`
3. 自动基于设备唯一标识注册用户，将 userId 写入全局配置 `~/.qbi/config.yaml`（不受技能包更新影响）

> 注意：`user_token` 单独存在于全局配置中（来自试用自动注册）不会阻止试用凭证填充。只有当外部配置中存在 `api_key` 或 `api_secret` 时，才会跳过试用链路。

试用到期由服务端接口通过错误码 `AE0579100004` 进行控制，无需本地追踪。

### 自定义配置指导

当用户希望使用自己的 Quick BI 账号凭证（而非试用凭证）时，请登录 Quick BI 控制台后，点击头像「**一键复制 skill 配置**」，如图所示：

![一键复制 skill 配置](references/common/copy_skill_config.png)

复制后将配置粘贴给 Agent，Agent 会自动将 `server_domain`、`api_key`、`api_secret`、`user_token` 写入工作目录级配置 `<工作目录>/.qbi/smartq-chat/config.yaml`（并根据 `save_global_property` 开关决定是否同步到全局配置）。

## Agent 配置更新操作规范（必读）

**新用户零配置初始化**：如果用户说"初始化配置"、"我是新用户"等，但**未提供任何具体配置值**，则无需手动写入任何配置文件。告知用户直接运行问数即可，系统会自动完成试用注册（详见上方「试用凭证自动注册」章节）。

只有当用户**明确提供了**具体配置值时，才执行以下写入规则。

**已有配置保护规则**：在写入前，Agent **必须**先检查工作目录级配置文件 `<工作目录>/.qbi/smartq-chat/config.yaml` 是否已存在且包含有效配置。若该文件已存在且非空，Agent **禁止自行修改或覆盖**其中的任何配置项，除非用户**明确表达了更新配置的意图**（如「更新我的配置」「替换为这个配置」「把 api_key 改成 xxx」等）。遇到已有配置时，应告知用户当前配置已存在，并询问是否确认覆盖。

当用户提供了 `api_key`、`api_secret`、`user_token`、`server_domain` 中的任意一项或多项配置值，且满足上述保护规则时，Agent **必须**使用文件编辑工具直接修改对应的用户配置文件，将用户提供的值写入对应字段。

**写入位置规则**：
- `server_domain`、`api_key`、`api_secret`、`user_token` → **始终**写入 **工作目录级配置** `<工作目录>/.qbi/smartq-chat/config.yaml`
- 全局配置读写受 `save_global_property` 开关控制（默认 `true`）：
  - 开关为 `false` → **不论何种情况都不读取也不写入全局配置**，跳过下述全局配置相关步骤
  - 开关为 `true` 且 **全局配置** `~/.qbi/config.yaml` 为空或不存在 → 同时写入全局配置
  - 开关为 `true` 且全局配置已有内容 → 仅写入工作目录级配置，并询问用户是否同步更新全局配置

**操作步骤**：
1. 从用户消息中提取配置键值对（支持 `key: value`、`key：value`、`key=value` 等常见格式）
2. 使用文件编辑工具（如 search_replace）将配置写入工作目录级配置文件
3. 读取配置中的 `save_global_property` 值，若为 `false` 则跳至步骤 5
4. 检查全局配置 `~/.qbi/config.yaml` 是否存在且非空：
   - 若为空或不存在 → 同时写入全局配置
   - 若已有内容 → 询问用户「全局配置已存在，是否同步更新？」，根据用户回复决定是否写入
5. 更新完成后，向用户确认已写入的配置项及写入位置

**禁止行为**：
- ❌ 禁止以「权限受限」「无法修改技能包内文件」等理由拒绝修改
- ❌ 禁止建议用户通过环境变量、手动复制文件等替代方案绕行
- ❌ 禁止仅输出配置内容让用户自行修改

## 前置条件

- 需安装 Python 依赖：`pip install requests pyyaml matplotlib numpy`
- 需要浏览器自动化能力（仅表盘技能生成模块）
- 数据集问数：用户需要有目标数据集的**问数权限**
- 文件问数：文件格式限 `xls`、`xlsx`、`csv`，单文件大小 ≤ 10MB
- **文档解析**：
  - 系统依赖：`brew install tesseract tesseract-lang`（仅本地解析需要）
  - 支持格式：PDF、Word(.doc/.docx)、Excel(.xls/.xlsx)、CSV、图片(.png/.jpg/.jpeg)
  - 单文件大小 ≤ 10MB（远程 OCR 限制）
  - **错误处理**：
    - 本地解析失败 → 自动降级到远程 OCR
    - 远程 OCR 仍失败 → 归类为"解析失败"，保留原始文件名和错误信息
    - 未知文档类型 → 提取 5+ 通用字段，需用户确认后方可生成 Excel
  - 详细文档：[module-document-parser.md](references/document/module-document-parser.md)

## 脚本调用规范（必读）

所有 Python 脚本调用时：
1. 脚本路径必须使用**技能包安装目录的绝对路径**（即 `<技能包目录>/scripts/...`），禁止使用相对路径
2. **必须**通过 `--workspace-dir` 参数传入 `<工作目录>` 的绝对路径（获取方式见上方「配置」章节约定）
3. 路径参数值用引号包裹（防止中文、空格等特殊字符导致 shell 拆词）

**调用示例**：
```bash
# 数据集问数
python3 '<技能包目录>/scripts/chat/smartq_stream_query.py' "销量最高的地区TOP3" --workspace-dir '<工作目录>'

# 文件上传
python3 '<技能包目录>/scripts/chat/upload_file.py' '/path/to/data.xlsx' --workspace-dir '<工作目录>'

# 文件问数
python3 '<技能包目录>/scripts/chat/file_stream_query.py' <fileId> "各部门人数分布" --workspace-dir '<工作目录>'

# 文档解析 - 本地解析
python3 '<技能包目录>/scripts/document/document_local_parse.py' '/path/to/folder/' --json --workspace-dir '<工作目录>'

# 文档解析 - 远程 OCR
python3 '<技能包目录>/scripts/document/document_remote_ocr.py' '/path/to/folder/' --workspace-dir '<工作目录>'

# Excel 生成
python3 '<技能包目录>/scripts/document/generate_excel.py' '<JSON路径>' --workspace-dir '<工作目录>'

# 报告生成
python3 '<技能包目录>/scripts/report/generate_report.py' "本月销售分析" --workspace-dir '<工作目录>'
```

**禁止行为**：
- ❌ 禁止调用脚本时省略 `--workspace-dir` 参数
- ❌ 禁止使用相对路径调用脚本（如 `python3 scripts/chat/...`）
- ❌ 禁止使用硬编码路径或猜测路径

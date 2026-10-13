---
name: ai-table-datasource-plugin-generator
displayName: AI表格数据源插件生成器
name_en: ai-table-datasource-plugin-generator
version: 1.0.0
description: |
  快速生成、修改和调试钉钉 AI 表格数据源连接器插件，覆盖前后端项目初始化、 MySQL/PostgreSQL/SQL Server/Oracle 数据源代码生成、本地环境配置、账号代管接入和发布指导。 当用户提出创建数据源插件、生成 AI 表格连接器代码、改造或排查已有数据源插件、配置本地调试环境、 接入三方账号代管或了解插件发布流程时使用。
description_en: |
  Generate, modify, and troubleshoot DingTalk AI Table datasource connector plugins, including frontend and backend scaffolding, database-specific code generation, local development setup, managed third-party accounts, and publishing guidance.
argument-hint: 数据源类型、插件英文标识，以及新建、修改、调试或发布需求
install_source: official
install_method: download
skill_id: official_EDKQsvZt
enabled_at: 1791893828595
name_zh: AI表格数据源插件生成器
---

# AI表格数据源连接器插件生成器

## ⚡ 最新版本变更（v1.0）

> **升级检测规则**：在帮助用户修改或调试现有插件时，**必须先检查**以下升级点是否已适配。若未适配，应主动告知用户并建议升级。

| 检测项 | 检查方式 | 未适配时的表现 |
|--------|---------|--------------|
| context.fields 适配 | RecordsRequest 的 Context 类中是否有 `fields` 字段 | 每次同步都查询全量字段，浪费带宽 |
| errorMessages 国际化 | manifest.json 中是否有 `errorMessages` + `i18nMap` 配置 | 错误弹窗只展示后端原始 msg，无多语言 |
| i18nMap key 格式 | manifest.json 中 i18nMap 的 key 是否使用下划线 `_` | 使用 `-` 会导致前端展示 `NaN`（nunjucks bug） |

当检测到未适配时，引导用户阅读：`references/upgrade-guide.md`

---

## Introduction

一键生成钉钉AI表格数据源连接器插件的完整项目代码，提供从初始化到部署的全流程自动化工具链。

数据源同步是钉钉 AI 表格提供的数据集成能力，将分散在不同系统的数据自动汇聚到 AI 表格中，实现统一管理和分析。

**核心价值**：数据集中化管理、自动化数据流转、跨系统数据协作

**已支持的开箱即用数据源**：钉钉生态（AI表格、OA审批、考勤等）、主流数据库（MySQL、PostgreSQL、SQLServer）、电商平台（淘宝生意参谋、拼多多等）、企业管理系统等。

### 支持的任务

当你需要：
- 创建新的 AI 表格数据源连接器插件
- 改进现有的钉钉 AI 表格数据源连接器插件
- 为现有数据源（MySQL、PostgreSQL 等）快速生成标准数据源连接器插件代码
- 搭建本地开发调试环境
- 了解插件发布流程和配置

---

## 使用流程

### Step 0：定位技能目录并检查环境

1. 先定位本文件 `SKILL.md` 所在目录，并将该目录作为执行技能脚本时的工作目录。下文所有 `scripts/`、`references/`、`templates/` 和 `docs/` 路径均相对于技能目录。
2. 优先执行 `python3 --version`。如果缺少 Python 3，允许 Agent 在当前环境权限范围内安装；无法自动安装时，明确提示用户安装 Python 3 后继续。
3. 新建项目前先向用户确认输出目录。重新生成已有项目时，必须说明会覆盖哪些目录，并获得用户确认后才使用 `--force`。
4. 安装 Node.js、pnpm、Java 或 Maven，以及启动内网穿透前，先说明会发生的系统修改或公网暴露行为。

### Step 1：判断用户意图

明确用户是要：
- **新建插件**：走完整初始化流程（Step 2 → Step 6）
- **修改/调试现有插件**：直接跳到对应步骤
- **了解接口规范**：读取参考文档后回答

### Step 2：读取参考文档

在生成任何代码前，**必须先读取**以下文档，确保生成的代码符合最新规范。

| 文档路径 | 内容 |
|------|------|
| `references/backend-developer-guide.md` | 后端接口规范（`/api/sheet_meta`、`/api/records`）、签名算法、错误码、`context.credentials` 注入规则 |
| `references/frontend-developer-guide.md` | 前端 `dataSource.saveConfigAndGoNext` / `dataSource.getSyncConfig` / `account.*` API 规范 |

### Step 3：初始化插件项目

`init_plugin.py` 会**一步完成**：创建目录结构 + 生成前后端代码 + 写入配置文件 + 创建启动脚本。

```bash
python3 scripts/init_plugin.py --name "my-datasource" --type mysql
```

初始化完成后，项目结构如下：

```
{name}-plugin/
├── .gitignore        # 排除密钥、依赖和构建产物
├── frontend/          # 前端项目 (React + TypeScript + Vite)
├── backend/           # 后端项目 (Java 8 + Spring Boot 2.7)
├── manifest.json      # 插件 Manifest（含错误码国际化模板）
├── scripts/           # 项目内启动脚本
│   ├── start-frontend.sh
│   ├── start-backend.sh
│   └── build.sh
└── config/
    ├── plugin.json    # 插件配置（前后端地址、密钥）
    └── tunnel-guide.txt  # 内网穿透说明（Cloudflare Tunnel）
```

默认模板使用 React 19、pnpm 和数据源注册表架构；`RecordsRequest.Context.fields`
已内置，记录服务会按平台请求过滤返回字段。前端统一调用
`Dingdocs.base.host.dataSource.*` API。

### Step 4：配置插件信息

初始化后需编辑以下三个文件。其中两处签名密钥必须保持一致：

**`config/plugin.json`**：
```json
{
  "pluginName": "插件名称",
  "frontendUrl": "http://localhost:3000",
  "secretKey": "your-secret-key-here",
  "backend": {
    "host": "http://example.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records"
  }
}
```

**`backend/src/main/resources/application.yml`**：
```yaml
plugin:
  secret-key: your-secret-key-here   # 必须与 plugin.json 中的 secretKey 一致
  enable-signature-verification: true
```

> ⚠️ 两处密钥不一致会导致签名验证失败，AI 表格服务端调用接口时将返回 `10004` 错误。

**`manifest.json`**：

- 替换 `icon.light` 中的图标占位地址。
- 将 `manifest.base.dataSource.dataSourceConfig.uri` 改成真实前端地址。
- 将 `manifest.base.dataSource.serverConfig.baseUrl` 改成真实后端地址。
- 校对 `i18nName`、`i18nDesc`、隐私协议和服务协议内容。
- 发布前搜索 `your-`、`example.com` 和 `__PLUGIN_SLUG__`，确保没有遗留占位值。

### Step 5：配置本地开发环境

`setup_dev.py` 会检查环境依赖；仅在明确提供 `--install` 时安装前后端依赖，并打印 Cloudflare Tunnel 启动指引。

```bash
python3 scripts/setup_dev.py --name "my-datasource" --install
```

不希望自动安装依赖时省略 `--install`；脚本只检查环境并给出下一步提示。

### Step 6：启动服务并调试

```bash
cd {name}-plugin

# 启动后端（运行在 http://localhost:8080）
./scripts/start-backend.sh

# 启动前端（新终端，运行在 http://localhost:3000）
./scripts/start-frontend.sh

# 配置后端内网穿透（新终端，推荐 Cloudflare Tunnel）
cloudflared tunnel --url http://localhost:8080
```

> ⚠️ AI 表格服务端需要通过公网调用**后端**接口，因此只需对后端进行内网穿透。前端由用户浏览器直接访问 localhost，无需穿透。

获取公网地址后，更新 `config/plugin.json` 中的 `backend.host`：
```json
{
  "backend": {
    "host": "https://xxxx.trycloudflare.com"
  }
}
```

详细调试步骤见 `docs/debug-guide.md`。

---

## 三方账号代管（可选能力）

当数据源场景涉及三方平台账号关联（如需要外部平台账号/令牌/AK-SK 进行数据拉取），可使用**官方提供的三方账号代管能力**，由钉钉一方安全存储账号凭证，插件通过标准接口获取使用。

完整接入说明：
- 前端：`references/frontend-developer-guide.md` — 「三方账号代管」章节
- 后端：`references/backend-developer-guide.md` — 「三方账号代管」与「动态查询凭证 Token 解密」章节

---

## 工具速查

### `init_plugin` — 初始化插件项目（含代码生成）

脚本路径：`scripts/init_plugin.py`

> **注意**：`init_plugin` 内部已自动调用 `generate_code`，无需单独运行 `generate_code.py`。

| 参数 | 必需 | 说明 |
|------|------|------|
| `--name` | ✅ | 插件英文标识，如 `mysql-datasource`，项目目录命名为 `{name}-plugin` |
| `--type` | 可选 | 数据源类型：`mysql` / `postgresql` / `sqlserver` / `oracle` / `custom`（默认 `custom`） |
| `--output-dir` | 可选 | 输出目录路径，默认在当前目录下创建 `{name}-plugin` |

**示例：**
```bash
python3 scripts/init_plugin.py --name "custom-datasource" --type mysql
python3 scripts/init_plugin.py --name "my-datasource" --output-dir /Users/xxx/workspace/my-datasource-plugin
```

---

### `generate_code` — 单独重新生成前后端代码

脚本路径：`scripts/generate_code.py`

仅在需要**重新生成**代码时使用（如更换数据源类型、覆盖已有代码）。

| 参数 | 必需 | 说明 |
|------|------|------|
| `--name` | ✅ | 插件英文标识 |
| `--project-dir` | 可选 | 项目目录路径，默认为 `{name}-plugin` |
| `--datasource-type` | 可选 | 指定数据源类型并写入 `plugin.json`（`mysql` / `postgresql` / `custom` 等） |
| `--backend-only` | 可选 | 仅重新生成后端代码（flag，无需赋値） |
| `--frontend-only` | 可选 | 仅重新生成前端代码（flag，无需赋値） |
| `--with-account-hosting` | 可选 | 启用三方账号代管：注入 `AccountSelector.tsx` 前端组件和 `CredentialService.java` 后端服务，并将 accountId 绑定到 `saveConfigAndGoNext`（与完整代码生成一起使用） |
| `--account-hosting-only` | 可选 | **仅**注入三方账号代管代码，不重新生成前后端。适用于已在开发中的项目增量开启此能力 |
| `--force` | 覆盖时必需 | 允许覆盖已有 `frontend/` 或 `backend/`；必须先获得用户确认 |

**示例：**
```bash
# 重新生成全部代码（切换为 mysql 类型）
python3 scripts/generate_code.py --name "my-datasource" --datasource-type mysql --force

# 仅重新生成后端代码
python3 scripts/generate_code.py --name "my-datasource" --backend-only --force

# 初始化时开启三方账号代管能力
python3 scripts/generate_code.py --name "my-datasource" --with-account-hosting --force

# 在开发中的项目里增量开启三方账号代管能力（不会覆盖已有代码）
python3 scripts/generate_code.py --name "my-datasource" --account-hosting-only
```

---

### `setup_dev` — 配置本地开发环境

脚本路径：`scripts/setup_dev.py`

检查前置依赖（Node.js、Java、Maven）、安装前后端依赖、打印 Cloudflare Tunnel 启动指引。

| 参数 | 必需 | 说明 |
|------|------|------|
| `--name` | ✅ | 插件英文标识 |
| `--project-dir` | 可选 | 项目目录路径，默认为 `{name}-plugin` |
| `--install` | 可选 | 明确允许安装前后端依赖；未提供时只检查环境 |

**示例：**
```bash
python3 scripts/setup_dev.py --name "my-datasource" --install
python3 scripts/setup_dev.py --name "my-datasource"
```

---
## 数据源模板说明

`scripts/datasource_templates.py` 提供了常见数据库的参考实现，`init_plugin` 指定 `--type` 时会自动注入对应代码：

| 数据源类型 | 自动注入内容 |
|-----------|------------|
| `mysql` | MySQL JDBC 驱动依赖 + `SheetMetaService` + `RecordService`（含主键自动检测、MD5 行 ID） |
| `postgresql` | PostgreSQL JDBC 驱动依赖 + `SheetMetaService` + `RecordService` |
| `sqlserver` | SQL Server JDBC 驱动依赖 |
| `oracle` | Oracle JDBC 驱动依赖 |
| `custom` | 保留模板中的示例实现，由开发者自行修改 |

> 模板代码仅供参考，需根据实际数据源结构和业务逻辑调整。

数据库连接安全默认值：MySQL 使用 `sslMode=PREFERRED` 兼容本地环境，生产环境应改为 `VERIFY_IDENTITY` 并配置受信任证书；SQL Server 默认 `trustServerCertificate=false`。不要为绕过证书错误而关闭验证。

---

## 参考文档索引

| 文档 | 内容 |
|------|------|
| `references/backend-developer-guide.md` | 后端接口规范、签名算法、错误码、调试指南 |
| `references/interface/data-rules.md` | 字段 ID / 行 ID / 数据类型规范，含正确/错误示例代码 |
| `references/interface/field-types.md` | 支持的字段类型枚举及 `property` 配置详情、数据库类型映射建议 |
| `references/frontend-developer-guide.md` | 前端 API 规范及完整示例 |
| `references/publish-guide.md` | 企业内插件和三方插件发布完整流程 |
| `docs/quickstart.md` | 7 步快速上手指南 |
| `docs/faq.md` | 开发期间高频问题汇总（端口冲突、签名验证、数据异常、前端初始化等） |
| `docs/debug-guide.md` | 本地调试、内网穿透、接口测试、常见问题排查 |
| `docs/deploy.md` | 生产环境部署指南（Nginx、Docker、systemd） |
| `docs/examples.md` | MySQL / PostgreSQL / 自定义 API 等完整使用示例 |
| `docs/publish-guide.md` | 发布前检查清单、生产部署、常见审核问题 |

---

## 输出格式

每次执行完成后，至少输出：

1. 创建或修改的项目绝对路径。
2. 已生成、覆盖或跳过的关键文件摘要。
3. 尚未替换的配置占位项和需要用户提供的密钥、URL、图标或协议。
4. 已执行的验证及结果；未执行构建或联调时明确说明。
5. 下一条可直接执行的命令。

## 失败恢复

- Python 3 不可用：在权限允许时安装 Python 3；否则给出安装提示并暂停脚本执行。
- Node.js、pnpm、Java 或 Maven 缺失：列出缺失项，不继续安装依赖或启动服务。
- `@ali/we-design-3` 无法下载：说明该依赖不在公共 npm registry，检查当前环境是否配置了有权限的依赖源；未经用户确认不要擅自切换 registry 或替换组件库。
- 目标目录已存在：保留用户文件，改用新目录；确需覆盖时先确认，再使用 `--force`。
- 依赖安装失败：保留已生成源码，报告失败命令和日志摘要，并提供 `--install` 重试命令。
- 内网穿透不可用：继续完成本地代码生成，改用用户已有的 HTTPS 测试地址或提示稍后配置。
- 发布配置不完整：列出 `manifest.json` 和 `config/plugin.json` 中的剩余占位值，不宣称项目已可发布。

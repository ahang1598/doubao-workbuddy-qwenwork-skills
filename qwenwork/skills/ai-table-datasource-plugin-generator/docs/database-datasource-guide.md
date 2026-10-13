# 数据库数据源插件开发指南

本文档介绍如何使用内置的 MySQL / PostgreSQL 数据源模板，快速生成一个**开箱即用**的数据库数据源连接器插件。

---

## 适用场景

- 需要将 **MySQL** 或 **PostgreSQL** 数据库中的表数据同步到钉钉 AI 表格
- 希望跳过手动编写 JDBC 查询、字段映射、分页逻辑，直接得到一个可运行的后端服务

---

## 整体架构

```
init_plugin --type mysql
    │
    ├── 复制 templates/backend/java → backend/
    ├── 注入 MySQL JDBC 驱动依赖到 pom.xml
    ├── 替换 SheetMetaService.java（自动查询表结构 + 字段类型映射）
    ├── 替换 RecordService.java（分页查询 + 自动检测主键 + 行 ID 生成）
    └── 生成 backend/.env（数据库连接配置示例）
```

**配置读取链路：**

```
backend/.env
    └─→ Spring Boot（spring.config.import）
            └─→ @Value("${datasource.xxx}")
                    └─→ SheetMetaService / RecordService
```

---

## 快速开始

### 第一步：初始化插件项目

```bash
python3 scripts/init_plugin.py --name "mysql-datasource" --type mysql
```

支持的 `--type` 值：

| 值 | 说明 |
|----|------|
| `mysql` | 生成 MySQL 实现，注入 MySQL JDBC 驱动 |
| `postgresql` | 生成 PostgreSQL 实现，注入 PostgreSQL JDBC 驱动 |
| `sqlserver` | 注入 SQL Server JDBC 驱动（Service 保留模板示例，需自行实现） |
| `oracle` | 注入 Oracle JDBC 驱动（Service 保留模板示例，需自行实现） |
| `custom` | 不替换任何内容，保留模板示例实现，由开发者自行修改 |

### 第二步：填写数据库连接信息

初始化完成后，进入项目目录，编辑 `backend/.env` 文件：

```bash
cd 我的MySQL数据源-plugin
```

打开 `backend/.env`，将示例值替换为真实的数据库连接信息：

```properties
# MySQL 数据库连接配置
# 请将以下示例值替换为真实的数据库连接信息，然后启动后端服务
# 注意：.env 文件包含敏感信息，请勿提交到版本控制系统

datasource.host=your-db-host
datasource.port=3306
datasource.database=your_database_name
datasource.username=your_username
datasource.password=your_password
datasource.sslMode=PREFERRED
```

> ⚠️ `.env` 文件包含数据库密码等敏感信息，**请勿提交到 Git 仓库**。项目已在 `.gitignore` 中排除该文件。
> 生产环境应将 MySQL `datasource.sslMode` 改为 `VERIFY_IDENTITY`，并配置可信 CA 证书。

### 第三步：配置 secretKey

编辑 `backend/src/main/resources/application.yml`，填写与 AI 表格平台约定的签名密钥：

```yaml
plugin:
  secret-key: your-secret-key-here   # 替换为真实密钥
  enable-signature-verification: false  # 开发阶段可设为 false
```

### 第四步：启动后端服务

```bash
./scripts/start-backend.sh
```

服务启动后监听 `http://localhost:8080`，可通过以下命令验证：

```bash
curl -X POST http://localhost:8080/api/sheet_meta \
  -H "Content-Type: application/json" \
  -d '{"params": "{\"tableName\": \"your_table_name\"}"}'
```

### 第五步：配置内网穿透

AI 表格服务端需要通过公网调用后端接口，推荐使用 Cloudflare Tunnel（无需注册账号）：

```bash
cloudflared tunnel --url http://localhost:8080
```

获取公网地址后，更新 `config/plugin.json` 中的 `backend.host`：

```json
{
  "backend": {
    "host": "https://xxxx.trycloudflare.com"
  }
}
```

---

## .env 文件说明

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `datasource.host` | 数据库主机地址 | `localhost` 或 `192.168.1.100` |
| `datasource.port` | 数据库端口 | MySQL: `3306`，PostgreSQL: `5432` |
| `datasource.database` | 数据库名称 | `mydb` |
| `datasource.username` | 数据库用户名 | `root` |
| `datasource.password` | 数据库密码 | `your_password` |

`.env` 文件通过 Spring Boot 的 `spring.config.import` 机制加载（`application.yml` 中已预配置），无需额外代码，Service 层直接通过 `@Value` 注入：

```java
@Value("${datasource.host}")
private String host;

@Value("${datasource.password}")
private String password;
```

---

## tableName 的传递方式

`tableName`（要查询的数据库表名）**不在 `.env` 中配置**，而是由前端配置页面在用户完成配置后传入。

**前端配置页面**调用 `saveConfigAndGoNext` 时传入 `tableName`：

```typescript
await Dingdocs.base.host.dataSource.saveConfigAndGoNext({
  tableName: 'users'   // 用户在配置页面填写的表名
});
```

**后端 Service** 从请求的 `params` 字段中解析：

```java
// SheetMetaService / RecordService 内部
String tableName = parseParam(request.getParams(), "tableName");
```

这样设计的好处是：同一套后端服务可以通过不同的前端配置支持多张表，无需重启服务。

---

## 字段类型映射规则

MySQL / PostgreSQL 的列类型会自动映射为 AI 表格支持的字段类型：

| 数据库类型 | AI 表格字段类型 | 备注 |
|-----------|----------------|------|
| `INT` / `BIGINT` / `SMALLINT` | `number` (formatter: INT) | |
| `DECIMAL` / `DOUBLE` / `FLOAT` | `number` (formatter: FLOAT_2) | 保留 2 位小数 |
| `DATE` | `date` (formatter: YYYY-MM-DD) | |
| `TIMESTAMP` / `DATETIME` | `date` (formatter: YYYY-MM-DD HH:mm) | 返回毫秒时间戳 |
| `BOOLEAN` / `BIT` | `singleSelect` (choices: true/false) | |
| 其他（VARCHAR、TEXT 等） | `text` | |

---

## 行 ID 生成规则

行 ID 必须稳定唯一，Service 按以下优先级生成：

1. **有主键**：直接使用主键列的值（通过 `DatabaseMetaData.getPrimaryKeys` 自动检测）
2. **无主键**：对所有字段的 `key=value` 按字段名排序后拼接，取 MD5 哈希

---

## 分页机制

`RecordService` 使用 `nextToken` 传递分页游标（当前 offset 的字符串表示）：

- 首次请求：`nextToken` 为 `null` 或空字符串，从第 0 条开始
- 后续请求：`nextToken` 为上次返回的值（如 `"300"`），从该 offset 继续查询
- 每次实际查询 `pageSize + 1` 条，多出的一条用于判断是否还有更多数据

---

## 重新生成代码

如果需要切换数据源类型或覆盖已有的 Service 实现：

```bash
# 切换为 PostgreSQL 并重新生成后端代码
python3 scripts/generate_code.py --name "my-datasource" --datasource-type postgresql --backend-only --force
```

> ⚠️ 重新生成会**覆盖** `backend/` 目录下的所有文件（包括 `.env`），请提前备份已修改的配置。

---

## 常见问题

### 启动时报 `Could not resolve placeholder 'datasource.host'`

**原因**：`backend/.env` 文件不存在或未填写对应配置项。

**解决**：确认 `backend/.env` 文件存在且包含所有必要的 `datasource.*` 配置项，然后重启服务。

### 连接数据库失败（`Communications link failure`）

**原因**：数据库地址、端口、用户名或密码错误，或数据库服务未启动。

**解决**：
1. 检查 `backend/.env` 中的连接信息是否正确
2. 确认数据库服务正在运行
3. 确认数据库允许来自当前机器的连接（检查防火墙和数据库用户权限）

### `sheet_meta` 接口返回字段列表为空

**原因**：`tableName` 不存在，或数据库用户没有查询该表元数据的权限。

**解决**：
1. 确认前端传入的 `tableName` 与数据库中的表名完全一致（区分大小写）
2. 确认数据库用户有 `SELECT` 权限

### 签名验证失败（错误码 10004）

**原因**：`application.yml` 中的 `plugin.secret-key` 与 AI 表格平台配置的密钥不一致。

**解决**：开发阶段可将 `enable-signature-verification` 设为 `false` 跳过验证，生产环境必须填写正确的密钥。

---

## 参考文档

- 后端接口规范：`references/backend-developer-guide.md`
- 字段类型枚举：`references/interface/field-types.md`
- 数据规范（行 ID / 字段 ID）：`references/interface/data-rules.md`
- 前端开发规范：`references/frontend-developer-guide.md`
- 调试指南：`docs/debug-guide.md`

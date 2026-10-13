# 快速开始指南

本指南将帮助你快速创建并运行一个 AI 表格数据源连接器插件。

## 前置要求

确保你的开发环境已安装：
- Node.js 18+ 和 npm
- Java 8+ 和 Maven
- Git

## 步骤 1：初始化项目

`init_plugin.py` 会创建完整的项目目录结构，并生成前后端代码、启动脚本和配置文件模板。

```bash
python3 scripts/init_plugin.py --name "my-datasource" --type mysql
```

参数说明：
- `--name`：插件英文标识，只能使用小写字母、数字和连字符，项目目录命名为 `{name}-plugin`
- `--type`：数据源类型，可选 `mysql` / `postgresql` / `sqlserver` / `oracle` / `custom`（默认 `custom`）

初始化完成后，项目结构如下：

```
我的数据源-plugin/
├── frontend/          # 前端项目 (React + TypeScript + Vite)
├── backend/           # 后端项目 (Java 8 + Spring Boot 2.7)
├── scripts/           # 项目内启动脚本（start-backend.sh / start-frontend.sh / build.sh）
└── config/
    ├── plugin.json    # 插件配置（前后端地址、密钥）
    └── tunnel-guide.txt  # 内网穿透说明（Cloudflare Tunnel）
```

## 步骤 2：配置插件信息

需要编辑以下两个文件，且两处的密钥必须保持一致。

### 2.1 编辑 `config/plugin.json`

填写插件名称、密钥，以及前后端地址（本地调试阶段保持默认即可）：

```json
{
  "pluginName": "my-datasource",
  "frontendUrl": "http://localhost:3000",
  "secretKey": "your-secret-key-here",
  "backend": {
    "host": "http://example.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records"
  }
}
```

### 2.2 编辑 `backend/src/main/resources/application.yml`

将 `plugin.secret-key` 设置为与 `plugin.json` 中 `secretKey` 相同的值：

```yaml
plugin:
  secret-key: your-secret-key-here   # 必须与 config/plugin.json 中的 secretKey 一致
  enable-signature-verification: true
```

> ⚠️ 两处密钥不一致会导致签名验证失败，AI 表格服务端调用接口时将返回 `10004` 错误。

## 步骤 3：配置开发环境

`setup_dev.py` 会检查环境；添加 `--install` 后才会安装前后端依赖：

```bash
python3 scripts/setup_dev.py --name "my-datasource" --install
```

可选参数：
- `--project-dir`：指定项目目录（默认为 `{name}-plugin`）
- 省略 `--install`：只检查环境，不安装依赖

## 步骤 4：启动前后端服务

在项目目录下执行（脚本从项目根目录运行）：

```bash
cd 我的数据源-plugin

# 启动后端（运行在 http://localhost:8080）
./scripts/start-backend.sh

# 启动前端（新终端，运行在 http://localhost:3000）
./scripts/start-frontend.sh
```

## 步骤 5：对后端启动内网穿透

AI 表格服务端需要通过公网调用后端接口，因此只需对后端进行内网穿透。前端由用户浏览器直接访问 localhost，无需穿透。

```bash
# 新终端执行（推荐 Cloudflare Tunnel，无需注册账号）
cloudflared tunnel --url http://localhost:8080
```

启动后终端输出一个临时公网地址，例如：`https://xxxx.trycloudflare.com`

然后将 `config/plugin.json` 中的 `backend.host` 更新为该公网地址：

```json
{
  "pluginName": "my-datasource",
  "frontendUrl": "http://localhost:3000",
  "secretKey": "your-secret-key-here",
  "backend": {
    "host": "https://xxxx.trycloudflare.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records"
  }
}
```

ngrok 和其他内网穿透方案详见 `docs/debug-guide.md`。

## 步骤 6：在 AI 表格中添加插件

1. 打开钉钉 AI 表格 → 「添加/导入」→「从其他数据源同步」
2. 选择「自定义插件」（企业内）或「三方插件」
3. 填写配置：
   - **前端页面地址**：`http://localhost:3000`（即 `plugin.json` 中的 `frontendUrl`）
   - **服务端接口地址**：内网穿透公网地址（即 `plugin.json` 中的 `backend.host`）
   - **密钥**：与 `plugin.json` 中的 `secretKey` 一致
4. 点击「下一步」进入插件配置页面

## 步骤 7：实现数据源逻辑

### 后端

后端需实现两个接口：
- `POST /api/sheet_meta`：返回数据源的字段结构
- `POST /api/records`：分页返回数据记录

如果使用 MySQL / PostgreSQL 等常见数据库，可参考 `scripts/datasource_templates.py` 中的实现思路：

| 函数 | 参考内容 |
|------|------|
| `get_mysql_service_impl()` | MySQL `SheetMetaService` 参考实现 |
| `get_mysql_record_service()` | MySQL `RecordService` 参考实现（分页、主键检测、MD5 行 ID） |
| `get_postgresql_service_impl()` | PostgreSQL `SheetMetaService` 参考实现 |
| `get_pom_dependency(type)` | 各数据库的 Maven 依赖配置 |

> 模板代码仅供参考，需根据实际数据源结构和业务逻辑调整，不建议直接照搬。

接口规范详见 `references/backend-developer-guide.md`。

### 前端

前端需在页面挂载时调用 `initView` 初始化插件环境；`onReady` 回调中调用 `getSyncConfig` 获取已保存的配置（编辑已有同步表时用于回显）；用户完成配置后调用 `saveConfigAndGoNext` 保存配置并跳转：

```typescript
import { initView } from 'dingtalk-docs-cool-app';

useEffect(() => {
  initView({
    onReady: async () => {
      // 编辑已有同步表时回显已保存配置
      try {
        const saved = await Dingdocs.base.host.dataSource.getSyncConfig();
        if (saved) { /* 用 saved 初始化表单 */ }
      } catch { /* 首次创建时正常 */ }
    },
    onError: (e) => console.error(e)
  });
}, []);

// 用户点击「下一步」时
await Dingdocs.base.host.dataSource.saveConfigAndGoNext({ tableName });
```

前端开发规范详见 `references/frontend-developer-guide.md`。

## 下一步

- 📖 调试指南 `docs/debug-guide.md`：接口测试、签名验证、常见问题排查
- 🚀 部署指南 `docs/deploy.md`：生产环境部署（Nginx、Docker、systemd）
- ❓ 常见问题 `docs/faq.md`：端口冲突、签名验证、数据异常等高频问题汇总

## 获取帮助

通过千问市场技能详情页提供的发布方联系方式获取支持。

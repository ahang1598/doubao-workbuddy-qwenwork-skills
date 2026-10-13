# 插件调试&部署指南

本文档描述插件在两种场景下的部署流程和关键配置。

## 场景一：本地调试

### 原理说明

- 前端（`localhost:3000`）由用户浏览器直接访问，**不需要**内网穿透
- 后端（`localhost:8080`）需要被 AI 表格服务端通过公网调用，**必须**通过内网穿透工具暴露到公网

### 部署步骤

**第一步：安装依赖**

> 注意：`scripts/` 下的脚本适用于标准项目结构（`frontend/` + `backend/` 双目录）。如果是自行开发的项目，请参考这些脚本的逻辑，根据实际项目结构自行安装依赖。

执行 `python3 scripts/setup_dev.py --name "my-datasource" --install`，脚本会检查 Node.js / Java / Maven 环境，并在显式授权后安装前后端依赖。

**第二步：启动前端和后端**

- 前端：在项目根目录执行 `./scripts/start-frontend.sh`，运行在 `http://localhost:3000`
- 后端：在项目根目录执行 `./scripts/start-backend.sh`，运行在 `http://localhost:8080`
- 如果是用户自行开发的项目，参考上述脚本逻辑，根据实际情况启动前后端服务

**第三步：对后端启动内网穿透**

推荐使用 Cloudflare Tunnel（无需账号，一行命令）：
```bash
# 安装 cloudflared（macOS）
brew install cloudflare/cloudflare/cloudflared

# 启动内网穿透
cloudflared tunnel --url http://localhost:8080
```

或使用 ngrok（备选）：
```bash
ngrok http 8080
```

记录工具提供的后端公网地址，例如 `https://xxx.trycloudflare.com` 或 `https://xxxx.ngrok.io`。
将 `config/plugin.json` 中的 `backend.host` 填写为该地址。

内网穿透安装和配置详见 `docs/debug-guide.md`。

**第四步：更新 `config/plugin.json`**

如果是用户开发的项目，需要额外在项目目录下新增一个 `config/plugin.json` 文件，内容如下：
```json
{
  "pluginName": "我的数据源插件",
  "frontendUrl": "http://localhost:3000",
  "secretKey": "your-secret-key-here",
  "backend": {
    "host": "https://xxxx.trycloudflare.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records"
  }
}
```

字段说明：
- `frontendUrl`：本地调试时填 `http://localhost:3000`，AI 表格在用户浏览器中加载，可直接访问 localhost
- `backend.host`：填内网穿透工具提供的后端公网地址，AI 表格服务端通过此地址调用接口
- `secretKey`：签名密钥，必须与 `backend/src/main/resources/application.yml` 中的 `plugin.secret-key` 保持一致
- `backend.sheetEndpoint` / `backend.recordEndpoint`：接口路径，通常无需修改

**第五步：在 AI 表格中添加插件**

1. 打开 AI 表格 → 「添加/导入」→「从其他数据源同步」
2. 选择「自定义插件」（企业内）或「三方插件」
3. 填写：前端页面地址（`frontendUrl`）、服务端接口地址（`backend.host`）、密钥（`secretKey`）
4. 点击「下一步」进入插件配置页面

完整调试流程、接口测试、常见问题排查详见 `docs/debug-guide.md`。

## 场景二：生产环境部署

### 原理说明

生产环境将前后端部署到公网服务器，使用正式域名替换本地地址和内网穿透地址。后端必须开启签名验证。

### 部署步骤

**第一步：构建产物**

- 前端：在 `frontend/` 目录执行 `pnpm run build`，产物在 `frontend/build/`
- 后端：在 `backend/` 目录执行 `mvn clean package -DskipTests`，产物在 `backend/target/*.jar`

**第二步：部署服务**

- 前端：将 `frontend/build/` 部署到 Nginx 静态文件目录
- 后端：将 JAR 包部署到服务器，通过 systemd 或 Docker 管理进程

生产环境 `application.yml` 关键配置：

```yaml
plugin:
  secret-key: ${PLUGIN_SECRET_KEY}           # 从环境变量读取，禁止硬编码
  enable-signature-verification: true        # 生产环境必须为 true
  encryption-key: ${PLUGIN_ENCRYPTION_KEY:}  # 三方账号代管时必填，未设置时 credentialToken 为Base64Url编码明文
```

Nginx 配置、systemd 服务、Docker 部署方式详见 `docs/deploy.md`。

**第三步：更新 `config/plugin.json`**

将 `frontendUrl` 和 `backend.host` 替换为生产环境正式域名：

```json
{
  "pluginName": "我的数据源插件",
  "frontendUrl": "https://your-domain.com",
  "secretKey": "your-production-secret-key",
  "encryptionKey": "",
  "backend": {
    "host": "https://your-domain.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records",
    "verifyEndpoint": ""
  }
}
```

字段说明：
- `encryptionKey`：开放平台酷应用配置页中配置的加密密鑰，三方账号代管时必填
- `backend.verifyEndpoint`：账号校验接口路径，可选；如已实现 `/api/verify`，在此填写

**第四步：注册/发布插件**

- 企业内插件：在钉钉开放平台创建企业内部应用，填写前端页面地址和后端接口地址
- 三方插件：提交审核，通过后在 AI 表格插件市场上架

具体发布步骤详见 `docs/publish-guide.md`，插件类型说明详见 `references/publish-guide.md`。

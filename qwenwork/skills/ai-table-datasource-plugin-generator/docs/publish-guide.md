# 数据源插件发布详细指南

> 发布流程概述请参考 `references/publish-guide.md`，本文档聚焦于发布前准备、生产环境部署和常见问题排查。

## 发布前检查清单

在发布到生产环境前，请逐项确认：

**功能完整性**
- [ ] `sheet_meta` 接口返回正确的表结构（字段名、字段类型）
- [ ] `records` 接口支持分页（`nextToken` 机制正确实现）
- [ ] 前端配置页面能正确收集用户输入并传递给后端
- [ ] 签名验证已开启（`plugin.enable-signature-verification=true`）
- [ ] `plugin.secret-key` 已替换为平台分配的正式密钥

**稳定性**
- [ ] 数据源连接异常时有友好的错误提示（不暴露内部堆栈）
- [ ] 大数据量场景下分页正常，不会超时或 OOM
- [ ] 后端服务使用进程管理工具（systemd / Docker）保证自动重启

**安全性**
- [ ] 生产环境使用 HTTPS（前端和后端均需）
- [ ] `secret-key` 未提交到代码仓库（已加入 `.gitignore` 或通过环境变量注入）
- [ ] 数据库连接使用最小权限账号（只读权限即可）

**三方账号代管（使用了账号代管能力时必检）**
- [ ] 已在开放平台酷应用配置页填写 `encryptionKey`，并在部署时设置对应的 `PLUGIN_ENCRYPTION_KEY` 环境变量
  - 未配置时 `getCredentialToken` 返回明文 token，账号凭证存在泄露风险
- [ ] 评估是否需要实现 `/api/verify` 账号校验接口（推荐：可在账号保存前拦截无效凭证）
  - 如已实现，确认 `config/plugin.json` 中 `backend.verifyEndpoint` 已填写正确路径

## 生产环境部署

### 构建产物

```bash
# 构建前端
cd frontend
pnpm run build
# 产物在 frontend/build/

# 构建后端
cd backend
mvn clean package -DskipTests
# 产物在 backend/target/*.jar
```

### 前端部署（Nginx）

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        root /path/to/frontend/build;
        try_files $uri $uri/ /index.html;
    }
}
```

### 后端部署

**直接运行 JAR：**

```bash
java -jar backend/target/ai-table-datasource-plugin-1.0.0.jar \
  --plugin.secret-key=YOUR_SECRET_KEY \
  --plugin.enable-signature-verification=true
```

**推荐使用 Docker：**

```dockerfile
# backend/Dockerfile
FROM openjdk:8-jdk-alpine
WORKDIR /app
COPY target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  frontend:
    build: ./frontend
    ports:
      - "443:443"
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - PLUGIN_SECRET_KEY=your-secret-key
      - SPRING_PROFILES_ACTIVE=prod
```

## 版本管理

采用语义化版本号 `主版本号.次版本号.修订号`：

- **主版本号**：不兼容的接口变更
- **次版本号**：向下兼容的新功能
- **修订号**：Bug 修复

每次发布新版本，需在钉钉开放平台「版本管理与发布」中创建新版本并填写更新说明。

## 常见问题

### 签名验证失败（错误码 10004）

**可能原因：**
1. `plugin.secret-key` 与平台配置的密钥不一致
2. 请求体被中间件（如 Nginx）修改导致签名不匹配
3. 签名算法实现有误（必须使用 fastjson 序列化，且拼接顺序为 `body + timestamp`）

**排查方式：**
- 临时将 `plugin.enable-signature-verification` 设为 `false`，确认业务逻辑本身正常后再排查签名问题
- 在后端日志中打印收到的 `body` 和 `timestamp`，手动验证签名

---

### 前端配置页面在 AI 表格中无法加载

**可能原因：**
1. 前端 URL 未使用 HTTPS（AI 表格要求 HTTPS）
2. 前端服务未配置正确的 CORS 响应头
3. 前端构建产物的 `base` 路径配置有误（检查 `vite.config.ts` 中的 `base` 字段）

---

### `records` 接口返回数据不完整

**可能原因：**
1. 分页逻辑有误，`nextToken` 未正确传递导致漏数据
2. 单次返回超过 `maxResults` 限制（AI 表格默认最大 300 条）
3. 数据库查询未按固定顺序排序，导致分页时数据重复或遗漏

**建议：** 分页查询必须加 `ORDER BY` 保证结果稳定。

---

### 三方插件审核被拒

**常见原因：**
- 前端配置页面缺少必要的输入项说明或校验提示
- `sheet_meta` 返回的字段类型不在平台支持的类型列表内（参考 `references/interface/field-types.md`）
- 错误码不符合规范（参考 `references/interface/data-rules.md`）

---

### 部署后服务偶发 OOM

**可能原因：** 未分页，一次性将全量数据加载到内存后再返回。

**解决方案：** 严格实现分页查询，每次最多返回 `maxResults` 条，绝不在内存中聚合全量数据。

## 获取帮助

通过千问市场技能详情页提供的发布方联系方式获取支持。

## 部署最佳实践

### 1. 使用HTTPS

生产环境必须使用HTTPS协议：

- 申请SSL证书
- 配置Nginx或应用服务器
- 确保所有API接口都使用HTTPS

### 2. 使用Docker

推荐使用Docker进行部署：

#### Dockerfile (前端)

```dockerfile
FROM node:20-alpine as builder
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### Dockerfile (后端)

```dockerfile
FROM openjdk:8-jdk-alpine
WORKDIR /app
COPY target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

#### docker-compose.yml

```yaml
version: '3'
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
  
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
```

### 3. 使用CI/CD

配置自动化构建和部署：

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [ main ]
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Frontend
        run: |
          cd frontend
          corepack pnpm install --frozen-lockfile
          corepack pnpm run build
      - name: Build Backend
        run: |
          cd backend
          mvn clean package
      - name: Deploy
        run: |
          # 部署到服务器
```

### 4. 监控和日志

- 配置日志收集（如ELK）
- 设置监控告警
- 定期备份数据

### 5. 安全配置

- 使用环境变量存储敏感信息
- 定期更新依赖包
- 配置防火墙规则
- 实施访问控制

## 版本管理

### 版本号规范

采用语义化版本号：`主版本号.次版本号.修订号`

- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 更新流程

1. 修改版本号
2. 更新变更日志
3. 提交代码
4. 构建测试
5. 发布新版本
6. 在开放平台更新版本

## 常见问题

### 1. 审核失败

**可能原因**:
- 功能不完整
- 存在安全漏洞
- 不符合规范
- 文档不全

**解决方案**:
- 仔细检查功能实现
- 进行安全测试
- 查看审核意见并修改
- 完善文档

### 2. 部署后无法访问

**排查步骤**:
1. 检查服务器状态
2. 检查防火墙配置
3. 检查域名解析
4. 检查SSL证书
5. 查看应用日志

### 3. 性能问题

**优化建议**:
- 使用CDN加速前端资源
- 实现接口缓存
- 优化数据库查询
- 使用负载均衡

## 获取帮助

通过千问市场技能详情页提供的发布方联系方式获取支持。

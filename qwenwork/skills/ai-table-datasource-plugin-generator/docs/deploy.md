# 部署指南

本指南介绍如何将 AI 表格数据源连接器插件部署到生产环境。

## 部署方式

支持两种部署方式：
1. **本地部署**：部署到自己的服务器
2. **云平台部署**：部署到阿里云、腾讯云等云平台

## 前置准备

### 1. 域名和 SSL 证书

生产环境必须使用 HTTPS，需要准备：
- 已备案的域名
- SSL 证书（可使用 Let's Encrypt 免费证书）

### 2. 服务器要求

**最低配置**：
- CPU: 2核
- 内存: 4GB
- 磁盘: 20GB
- 带宽: 1Mbps

**推荐配置**：
- CPU: 4核
- 内存: 8GB
- 磁盘: 50GB
- 带宽: 5Mbps

### 3. 软件环境

- Java 8+
- Node.js 18+
- Nginx（用于反向代理）
- 数据库（MySQL/PostgreSQL 等）

## 本地部署

### 步骤 1：构建项目

```bash
# 进入项目目录
cd your-plugin-project

# 构建前端
cd frontend
pnpm install --frozen-lockfile
pnpm run build

# 构建后端
cd ../backend
mvn clean package -DskipTests
```

构建产物：
- 前端：`frontend/build/`
- 后端：`backend/target/*.jar`

### 步骤 2：配置 Nginx

创建 Nginx 配置文件 `/etc/nginx/sites-available/your-plugin`：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 证书配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 前端静态文件
    location / {
        root /var/www/your-plugin/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # 后端 API 代理
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 日志
    access_log /var/log/nginx/your-plugin-access.log;
    error_log /var/log/nginx/your-plugin-error.log;
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/your-plugin /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 3：部署前端

```bash
# 创建部署目录
sudo mkdir -p /var/www/your-plugin/frontend

# 复制前端文件
sudo cp -r frontend/build/* /var/www/your-plugin/frontend/

# 设置权限
sudo chown -R www-data:www-data /var/www/your-plugin
```

### 步骤 4：部署后端

创建 systemd 服务文件 `/etc/systemd/system/your-plugin.service`：

```ini
[Unit]
Description=Your Plugin Backend Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/your-plugin
ExecStart=/usr/bin/java -jar /opt/your-plugin/backend.jar
Restart=on-failure
RestartSec=10

# 环境变量
Environment="SPRING_PROFILES_ACTIVE=prod"
Environment="SERVER_PORT=8080"
Environment="PLUGIN_SECRET_KEY=your-production-secret-key"
# 三方账号代管时必设，未设置时 getCredentialToken 返回明文 token
# Environment="PLUGIN_ENCRYPTION_KEY=your-encryption-key"

# 日志
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

部署步骤：
```bash
# 创建部署目录
sudo mkdir -p /opt/your-plugin

# 复制 JAR 文件
sudo cp backend/target/*.jar /opt/your-plugin/backend.jar

# 复制配置文件
sudo cp backend/src/main/resources/application-prod.yml /opt/your-plugin/

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable your-plugin
sudo systemctl start your-plugin

# 查看状态
sudo systemctl status your-plugin

# 查看日志
sudo journalctl -u your-plugin -f
```

### 步骤 5：配置生产环境参数

`application-prod.yml` 使用项目模板自带的配置，密鑰通过环境变量注入：

```yaml
# 生产环境配置（通过环境变量注入密鑰）
plugin:
  secret-key: ${PLUGIN_SECRET_KEY}           # 签名密鑰，必需在开放平台配置
  enable-signature-verification: true        # 生产环境必须为 true
  encryption-key: ${PLUGIN_ENCRYPTION_KEY:}  # 三方账号代管时必填，未设置时 credentialToken 为明文
```

在 systemd 服务文件中设置环境变量：
```bash
# 编辑 /etc/systemd/system/your-plugin.service
Environment="PLUGIN_SECRET_KEY=your-production-secret-key"
Environment="PLUGIN_ENCRYPTION_KEY=your-encryption-key"  # 三方账号代管时设置
```

## Docker 部署

### 步骤 1：创建 Dockerfile

**前端 Dockerfile** (`frontend/Dockerfile`)：
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
CMD ["nginx", "-g", "daemon off;"]
```

**后端 Dockerfile** (`backend/Dockerfile`)：
```dockerfile
FROM maven:3.8-openjdk-8 as builder

WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn clean package -DskipTests

FROM openjdk:8-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### 步骤 2：创建 docker-compose.yml

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - PLUGIN_SECRET_KEY=${PLUGIN_SECRET_KEY}
    restart: unless-stopped

networks:
  default:
    name: your-plugin-network
```

### 步骤 3：部署

```bash
# 设置环境变量
export PLUGIN_SECRET_KEY=your-production-secret-key

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 云平台部署

### 阿里云 ECS 部署

1. **购买 ECS 实例**
   - 选择合适的配置
   - 选择操作系统（推荐 Ubuntu 20.04）
   - 配置安全组（开放 80、443、8080 端口）

2. **配置域名解析**
   - 在阿里云 DNS 控制台添加 A 记录
   - 指向 ECS 公网 IP

3. **申请 SSL 证书**
   - 在阿里云 SSL 证书服务申请免费证书
   - 下载证书文件

4. **部署应用**
   - 按照"本地部署"步骤操作

### 阿里云容器服务部署

1. **创建容器镜像**
   ```bash
   # 登录阿里云容器镜像服务
   docker login --username=your-username registry.cn-hangzhou.aliyuncs.com
   
   # 构建镜像
   docker build -t registry.cn-hangzhou.aliyuncs.com/your-namespace/your-plugin:v1.0.0 .
   
   # 推送镜像
   docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/your-plugin:v1.0.0
   ```

2. **创建 Kubernetes 部署**
   - 在容器服务控制台创建集群
   - 创建应用部署
   - 配置负载均衡

## 监控和维护

### 1. 日志管理

**查看应用日志**：
```bash
# systemd 服务日志
sudo journalctl -u your-plugin -f

# 应用日志文件
tail -f /var/log/your-plugin/application.log

# Nginx 日志
tail -f /var/log/nginx/your-plugin-access.log
tail -f /var/log/nginx/your-plugin-error.log
```

### 2. 性能监控

推荐使用以下工具：
- **Prometheus + Grafana**：监控系统指标
- **ELK Stack**：日志分析
- **阿里云监控**：云平台监控

### 3. 备份策略

**数据库备份**：
```bash
# 每日自动备份
0 2 * * * /usr/bin/mysqldump -u root -p'password' mydb > /backup/mydb_$(date +\%Y\%m\%d).sql
```

**应用备份**：
```bash
# 备份应用文件
tar -czf /backup/your-plugin_$(date +%Y%m%d).tar.gz /opt/your-plugin
```

### 4. 更新部署

**零停机更新**：
```bash
# 1. 构建新版本
mvn clean package

# 2. 备份当前版本
sudo cp /opt/your-plugin/backend.jar /opt/your-plugin/backend.jar.bak

# 3. 部署新版本
sudo cp backend/target/*.jar /opt/your-plugin/backend.jar

# 4. 重启服务
sudo systemctl restart your-plugin

# 5. 验证
curl https://your-domain.com/api/health
```

## 安全加固

### 1. 防火墙配置

```bash
# 安装 ufw
sudo apt install ufw

# 配置规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
```

### 2. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新依赖
cd backend && mvn versions:display-dependency-updates
cd frontend && npm outdated
```

### 3. 安全审计

- 定期检查日志
- 监控异常访问
- 定期更新 SSL 证书
- 定期备份数据

## 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   # 查看日志
   sudo journalctl -u your-plugin -n 100
   
   # 检查端口占用
   sudo netstat -tlnp | grep 8080
   ```

2. **502 Bad Gateway**
   - 检查后端服务是否运行
   - 检查 Nginx 配置
   - 检查防火墙规则

3. **SSL 证书问题**
   ```bash
   # 检查证书有效期
   openssl x509 -in /path/to/cert.crt -noout -dates
   
   # 测试 SSL 配置
   openssl s_client -connect your-domain.com:443
   ```

## 性能优化

### 1. Nginx 优化

```nginx
# 启用 gzip 压缩
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# 启用缓存
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 2. JVM 优化

```bash
# 在 systemd 服务中添加 JVM 参数
ExecStart=/usr/bin/java -Xms2g -Xmx4g -XX:+UseG1GC -jar /opt/your-plugin/backend.jar
```

### 3. 数据库优化

- 添加适当的索引
- 使用连接池
- 定期优化表

## 参考资源

- [Nginx 官方文档](https://nginx.org/en/docs/)
- [Spring Boot 部署指南](https://docs.spring.io/spring-boot/docs/current/reference/html/deployment.html)
- [Docker 官方文档](https://docs.docker.com/)
- [阿里云 ECS 文档](https://help.aliyun.com/product/25365.html)

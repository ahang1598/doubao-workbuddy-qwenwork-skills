# 数据源插件调试指南

> **备注**：本文档根据实际项目中使用的语言和技术栈的不同，可以做适当调整。

## 本地调试环境搭建

### 1. 环境要求
- Node.js v18+
- Java JDK 8+
- Maven 3.6+
- Git

### 2. 初始化项目

```bash
# 1. 克隆或创建项目
git clone <your-repo-url>
cd <project-name>

# 2. 运行初始化脚本
python3 scripts/init_plugin.py --name "my-datasource" --type custom
```

### 3. 配置插件信息

编辑 `config/plugin.json`：

```json
{
  "pluginName": "我的数据源插件",
  "frontendUrl": "http://localhost:3000",
  "secretKey": "your-secret-key-here",
  "backend": {
    "host": "http://example.com",
    "sheetEndpoint": "/api/sheet_meta",
    "recordEndpoint": "/api/records"
  }
}
```

字段说明：
- `pluginName`：插件名称
- `frontendUrl`：前端页面地址（开发时为 localhost，生产时替换为实际域名）
- `secretKey`：签名密钥，需与 `backend/src/main/resources/application.yml` 中的 `plugin.secret-key` 保持一致
- `backend.host`：后端服务域名（开发时为 localhost，生产时替换为实际域名）
- `backend.sheetEndpoint`：`sheet_meta` 接口路径，根据项目实际情况更新
- `backend.recordEndpoint`：`records` 接口路径，根据项目实际情况更新

编辑 `backend/src/main/resources/application.yml`：

```yaml
plugin:
  secret-key: your-secret-key-here
```

⚠️ **重要**: 确保 `plugin.json` 中的 `secretKey` 与 `application.yml` 中的 `plugin.secret-key` 一致。

### 4. 启动开发服务器

#### 启动前端

```bash
./scripts/start-frontend.sh
```

前端将在 `http://localhost:3000` 启动。

#### 启动后端

```bash
./scripts/start-backend.sh
```

后端将在 `http://localhost:8080` 启动。

### 5. 配置内网穿透

由于 AI 表格服务端需要访问你的本地服务，需要配置内网穿透。

> ⚠️ **安全提示**：内网穿透会将本地服务暴露到公网，请确保本地环境不含敏感数据，**仅在开发调试阶段使用**，生产环境请使用正式部署方案。

#### 方案一：Cloudflare Tunnel（推荐）

Cloudflare 提供免注册的临时隧道，**无需安装账号，一行命令启动**，速度和稳定性优于 ngrok 免费版。

1. 安装 cloudflared：

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# 或直接下载二进制（Linux / macOS / Windows）
# https://developers.cloudflare.com/cloudflared/downloads/
```

2. 启动隧道（穿透后端 8080 端口）：

```bash
cloudflared tunnel --url http://localhost:8080
```

3. 启动后终端会输出一个临时公网地址，例如：

```
https://random-words-here.trycloudflare.com
```

将该地址填入 `config/plugin.json` 的 `backend.host`。

> **注意**：每次重启 cloudflared 临时地址会变更，重启后需重新更新 `backend.host`。

#### 方案二：ngrok（备选）

1. 访问 [ngrok 官网](https://dashboard.ngrok.com/signup) 注册账号，复制 Authtoken

2. 安装并配置：

```bash
# 安装 ngrok
npm install -g ngrok

# 配置 authtoken
ngrok authtoken YOUR_AUTH_TOKEN_HERE
```

3. 启动内网穿透：

```bash
ngrok http 8080
```

4. 记录 ngrok 提供的公网地址，例如：`https://abc123.ngrok.io`

#### ⚠️ 免责声明

内网穿透工具（Cloudflare Tunnel、ngrok 等）均为第三方服务，使用前请知悉：

1. **安全风险**：内网穿透会将本地服务暴露到公网，**仅在开发调试阶段使用**，生产环境请使用正式部署方案
2. **服务稳定性**：工具的可用性、性能均由其服务商负责，可能出现连接中断、速度缓慢等情况
3. **费用说明**：免费版本存在功能和时长限制，请自行了解其服务条款
4. **责任范围**：因使用上述工具导致的数据泄露、网络安全问题，以及服务故障造成的开发中断，均由用户自行承担风险

### 6. 在AI表格中配置插件

1. 打开AI表格
2. 点击左下角「添加/导入」-「从其他数据源同步」
3. 点击「自定义数据源连接器」-「新建数据源连接器」
4. 填写配置信息：
   - **数据连接器名称**: 自定义，如 `我的测试插件`
   - **服务端地址**: 内网穿透工具提供的公网地址，如 `https://xxxx.trycloudflare.com`
   - **SecretKey（选填）**: 与 `config/plugin.json` 中 `secretKey` 一致
   - **数据表结构同步接口**: 后端表结构接口路径，如 `/api/sheet_meta`
   - **行记录同步接口**: 后端行记录接口路径，如 `/api/records`
   - **前端页面地址**: `http://localhost:3000`（本地前端地址）
   - **界面高度 / 界面宽度**: 可保留默认値（450px / 300px）
5. 点击「保存」完成配置

## 调试技巧

### 1. 查看日志

#### 前端日志
- 浏览器控制台（F12）
- 查看网络请求

#### 后端日志
后端日志会输出到控制台，包含：
- 请求详情
- 签名验证结果
- 数据库查询结果
- 错误信息

### 2. 测试API接口

使用 Postman 或 curl 测试：

#### 测试表结构接口

```bash
curl -X POST http://localhost:8080/api/sheet_meta \
  -H "Content-Type: application/json" \
  -H "Ding-Docs-Timestamp: 1234567890" \
  -H "Ding-Docs-Signature: <生成的签名>" \
  -d '{
    "requestId": "test-request-id",
    "params": "{\"database\":\"test\",\"table\":\"users\"}",
    "context": {
      "unionId": "test-user-id",
      "corpId": "test-corp-id"
    }
  }'
```

#### 测试数据记录接口

```bash
curl -X POST http://localhost:8080/api/records \
  -H "Content-Type: application/json" \
  -H "Ding-Docs-Timestamp: 1234567890" \
  -H "Ding-Docs-Signature: <生成的签名>" \
  -d '{
    "requestId": "test-request-id",
    "maxResults": 300,
    "params": "{\"database\":\"test\",\"table\":\"users\"}",
    "context": {
      "unionId": "test-user-id",
      "corpId": "test-corp-id"
    }
  }'
```

### 3. 验证签名

使用在线工具或代码验证签名是否正确：

```java
String content = body + timestamp;
String signature = Base64.getEncoder().encodeToString(
    Mac.getInstance("HmacSHA256").doFinal((secretKey + content).getBytes())
);
```

### 4. 常见问题排查

#### 签名验证失败

**症状**: 后端返回 `10004: 签名验证失败`

**排查步骤**:
1. 检查 `secretKey` 是否一致
2. 检查 `timestamp` 是否正确
3. 检查 `body` 格式是否正确
4. 检查签名算法是否正确

#### CORS错误

**症状**: 前端请求被浏览器阻止

**解决方案**:
在后端添加CORS配置：

```java
@Configuration
public class CorsConfig {
    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOrigin("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        
        return new CorsFilter(source);
    }
}
```

#### 数据同步失败

**症状**: AI表格显示数据同步失败

**排查步骤**:
1. 检查数据源连接配置是否正确
2. 检查数据库权限
3. 检查表结构是否正确
4. 查看后端日志中的错误信息

#### 前端页面无法加载

**症状**: AI表格中无法打开插件配置页面

**排查步骤**:
1. 检查前端服务是否启动
2. 检查内网穿透工具（cloudflared）是否正常运行
3. 检查前端URL是否正确
4. 检查浏览器控制台的错误信息

### 5. 性能优化

#### 实现分页查询

```java
public RecordsResponse getRecords(RecordsRequest request) {
    int pageSize = request.getMaxResults() != null ? request.getMaxResults() : 300;
    int offset = calculateOffset(request.getNextToken());
    
    List<Record> records = queryRecords(offset, pageSize);
    String nextToken = records.size() >= pageSize ? generateNextToken(offset, pageSize) : null;
    
    return RecordsResponse.builder()
        .records(records)
        .nextToken(nextToken)
        .hasMore(nextToken != null)
        .build();
}
```

#### 添加缓存

```java
@Cacheable(value = "sheetMeta", key = "#request.params")
public SheetMetaResponse getSheetMeta(SheetMetaRequest request) {
    // 查询表结构
}
```

## 远程调试

如果需要远程调试，可以：

1. 使用日志收集服务（如 ELK）
2. 使用远程调试工具
3. 配置日志级别为 DEBUG

## 生产环境部署

生产环境部署请参考 `docs/publish-guide.md`。

## 获取帮助

通过千问市场技能详情页提供的发布方联系方式获取支持。

# 常见问题汇总

开发 AI 表格数据源连接器插件过程中的高频问题与解决方案。

---

## 环境与启动

### 端口被占用

**后端端口冲突**：编辑 `backend/src/main/resources/application.yml`，修改 `server.port`：

```yaml
server:
  port: 8081
```

后端地址需要公网可访问，因此需要重新对新端口启动内网穿透：

```bash
# Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8081
```

然后将 `config/plugin.json` 中的 `backend.host` 更新为新的公网地址：

```json
{
  "backend": {
    "host": "https://xxxx.trycloudflare.com"
  }
}
```

**前端端口冲突**：编辑 `frontend/vite.config.ts`，修改 `server.port`，或启动时指定：

```bash
cd frontend && pnpm run dev -- --port 3001
```

同步更新 `config/plugin.json` 中的 `frontendUrl`：

```json
{
  "frontendUrl": "http://localhost:3001"
}
```

---

### Maven 依赖下载慢

配置 Maven 使用阿里云镜像，编辑 `~/.m2/settings.xml`：

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/public</url>
  </mirror>
</mirrors>
```

---

### 内网穿透连接失败

如使用 Cloudflare Tunnel：

```bash
# macOS 安装
brew install cloudflare/cloudflare/cloudflared

# 启动
cloudflared tunnel --url http://localhost:8080
```

如使用 ngrok（备选）：

1. 注册 ngrok 账号并获取 authtoken：[ngrok 官网](https://dashboard.ngrok.com/get-started/your-authtoken)
2. 配置 authtoken：`ngrok authtoken YOUR_TOKEN`
3. 启动：`ngrok http 8080`

---

## 签名与认证

### 返回 10004 错误（身份校验失败）

原因：`config/plugin.json` 中的 `secretKey` 与 `backend/src/main/resources/application.yml` 中的 `plugin.secret-key` 不一致。

检查两处配置是否完全相同：

```json
// config/plugin.json
{
  "secretKey": "your-secret-key-here"
}
```

```yaml
# backend/src/main/resources/application.yml
plugin:
  secret-key: your-secret-key-here
```

开发阶段可临时关闭签名验证：

```yaml
plugin:
  enable-signature-verification: false
```

> ⚠️ 生产环境必须开启签名验证（`true`）。

---

### 签名验证失败但密钥一致

可能原因：
1. 请求时间戳与服务器时间差超过允许范围，检查服务器时区配置
2. 请求体在传输过程中被修改（如网关对 body 做了处理）
3. 签名算法实现有误，参考 `references/backend-developer-guide.md` 中的签名算法说明

---

## 接口返回数据

### AI 表格同步后字段为空或同步失败

常见原因：

1. **字段 ID 不稳定**：每次 `/api/sheet_meta` 返回的字段 ID 不一致，禁止使用 UUID、时间戳、随机数作为字段 ID，应直接使用字段名
2. **数据类型不匹配**：`number` 类型字段返回了字符串，`date` 类型字段返回了日期字符串而非毫秒时间戳
3. **Boolean 字段未转换**：`BOOLEAN`/`BIT` 字段映射为 `singleSelect`，但返回了 `true`/`false` 布尔值而非字符串 `"true"`/`"false"`

详见 `references/interface/data-rules.md`。

---

### 返回 10001 错误（参数错误）

检查请求体格式是否符合规范，必填字段是否缺失。参考 `references/backend-developer-guide.md` 中的接口入参说明。

---

### 返回 10002 错误（配置信息错误）

前端 `saveConfigAndGoNext` 传入的配置参数有误，检查前端传参格式是否正确。

---

### 分页数据重复或丢失

原因：行 ID 不稳定，导致 AI 表格无法正确识别同一行数据。

- 有主键：直接使用主键值（String 类型）
- 无主键：选取多个稳定字段拼接后取 MD5 哈希

禁止使用分页序号（`rowIndex`）、时间戳作为行 ID。

---

## 前端

### `initView` 未调用导致插件无法初始化

前端页面挂载时必须调用 `initView`，否则插件环境无法就绪：

```typescript
import { initView } from 'dingtalk-docs-cool-app';

useEffect(() => {
  initView({
    onReady: () => console.log('初始化完成'),
    onError: (e) => console.error('初始化失败', e),
  });
}, []);
```

---

### `saveConfigAndGoNext` 调用失败

确认 `dingtalk-docs-cool-app` 版本 >= 0.3.16：

```bash
pnpm add dingtalk-docs-cool-app@latest
```

---

### `getAuthCode` 无法获取免登码

请依次排查以下问题：

1. **插件类型确认**：确认已创建企业内插件或三方企业插件，否则参考 `references/publish-guide.md` 完成插件创建
2. **企业一致性**：
   - 企业内插件：确保插件所在钉钉应用的所属组织与 AI 表格所属组织一致
   - 三方企业插件：确保 AI 表格所属组织已授权开通使用该三方应用
3. **免登授权域名未配置**：检查开发者后台，插件所在钉钉应用是否已将插件前端地址配置到安全设置 -「重定向 URL」和「端内免登地址」中
4. **应用未发布**：检查插件所在的钉钉应用是否已完成发布
5. **应用能力缺失**：检查钉钉应用扩展的应用能力，若仅添加了「插件」能力，需额外添加「网页应用」或「小程序」能力（无需进行具体配置），更新后需要重新发布

---

## 获取帮助

通过千问市场技能详情页提供的发布方联系方式获取支持。

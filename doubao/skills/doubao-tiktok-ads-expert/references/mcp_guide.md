# TikTok Ads MCP 连接与使用指南

> ⚠️ **平台关联模式说明（2026-08 更新）**：本 Skill 已迁移至平台关联模式，授权由豆包平台统一管理。
> 下文「二、MCP 连接配置」中的本地配置文件（`~/.tiktok_ads_mcp/config.json`）和「三、OAuth 授权流程」中的手动 OAuth 步骤**已不再适用**，仅作为 MCP 协议背景知识保留。
> 实际使用时无需创建任何本地配置文件或手动管理 Token，连接器状态由 Agent 通过 `tool_search` 校准。
> 「四、MCP 工具列表」及之后章节的工具说明和最佳实践仍然有效。

## 目录

- [TikTok Ads MCP 连接与使用指南](#tiktok-ads-mcp-连接与使用指南)
  - [一、MCP 概述](#一mcp-概述)
    - [1.1 什么是 MCP](#11-什么是-mcp)
    - [1.2 TikTok 官方 Ads MCP](#12-tiktok-官方-ads-mcp)
  - [二、MCP 连接配置](#二mcp-连接配置)
    - [2.1 连接信息](#21-连接信息)
    - [2.2 本地配置文件](#22-本地配置文件)
  - [三、OAuth 授权流程](#三oauth-授权流程)
    - [3.1 授权流程说明](#31-授权流程说明)
    - [3.2 授权步骤](#32-授权步骤)
    - [3.3 授权范围（Scopes）](#33-授权范围scopes)
    - [3.4 Token 管理](#34-token-管理)
  - [四、MCP 工具列表](#四mcp-工具列表)
    - [4.1 工具发现](#41-工具发现)
    - [4.2 预期可用工具](#42-预期可用工具)
    - [4.3 工具调用示例](#43-工具调用示例)
  - [五、连接状态检查](#五连接状态检查)
    - [5.1 状态检查项](#51-状态检查项)
    - [5.2 常见连接问题](#52-常见连接问题)
  - [六、多账户管理](#六多账户管理)
    - [6.1 多账户支持](#61-多账户支持)
    - [6.2 账户信息展示](#62-账户信息展示)
  - [七、最佳实践](#七最佳实践)
    - [7.1 安全最佳实践](#71-安全最佳实践)
    - [7.2 使用最佳实践](#72-使用最佳实践)
    - [7.3 性能最佳实践](#73-性能最佳实践)
  - [八、相关资源](#八相关资源)

---


## 一、MCP 概述

### 1.1 什么是 MCP

MCP（Model Context Protocol）是由 Anthropic 推出的开放标准，用于 AI Agent 与外部工具和服务的标准化连接。类似于"USB for AI"，让 AI 可以通过统一的协议调用各种外部服务。

**核心概念：**
- **MCP Server**：提供工具的服务端（如 TikTok 官方 Ads MCP）
- **MCP Client**：调用工具的 AI 客户端（如本 Skill）
- **Tools**：MCP Server 暴露的可调用工具（如获取报表、查询广告等）

### 1.2 TikTok 官方 Ads MCP

**官方端点地址：**
```
https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat
```

**端点说明：**
- `tt-ads-mcp`：TikTok Ads MCP Server
- `flat`：工具名采用扁平命名风格（如 `report_integrated_get`）

**发布时间：** 2026年5月（TikTok World '26 大会宣布）

**传输协议：** Streamable HTTP / SSE（Server-Sent Events）

**认证方式：** OAuth 2.0 授权码流程

---

## 二、MCP 连接配置

### 2.1 连接信息

| 配置项 | 值 | 说明 |
|--------|-----|------|
| MCP 端点 | `https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat` | TikTok 官方 MCP Server 地址 |
| 传输协议 | Streamable HTTP | 基于 HTTP 的流式传输 |
| 认证方式 | OAuth 2.0 Authorization Code Flow | 授权码流程 |
| 凭证存储 | 本地安全存储 | 由 MCP 客户端管理 |

### 2.2 本地配置文件

**配置文件位置：** `~/.tiktok_ads_mcp/config.json`

**目录结构：**
```
~/.tiktok_ads_mcp/
├── config.json          # 主配置文件
├── tokens/              # OAuth Token 存储（加密）
│   └── tiktok_ads.json
├── cache/               # 数据缓存目录
│   └── report_cache/
└── logs/                # 日志目录
    └── mcp_calls.log
```

**配置文件格式：**
```json
{
  "version": "1.0",
  "mcp_endpoint": "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat",
  "default_account": "main",
  "accounts": {
    "main": {
      "name": "主账户",
      "advertiser_id": "<广告主ID，脱敏存储>",
      "currency": "USD",
      "timezone": "Asia/Shanghai"
    }
  },
  "oauth": {
    "client_id": "<OAuth Client ID>",
    "auth_endpoint": "https://business-api.tiktok.com/portal/auth",
    "token_endpoint": "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/",
    "redirect_uri": "http://localhost:8888/callback",
    "scopes": ["ads:read"]
  },
  "security": {
    "token_encryption": true,
    "enable_request_logging": false,
    "log_sensitive_data": false
  },
  "cache": {
    "enable_cache": true,
    "cache_ttl_hours": 4
  }
}
```

> ⚠️ 注意：配置文件中使用 `<占位符>` 格式，不要出现真实明文示例。
> Token 不存储在配置文件中，而是加密存储在 tokens/ 目录下。

---

## 三、OAuth 授权流程

### 3.1 授权流程说明

TikTok Ads MCP 使用 OAuth 2.0 授权码流程，用户只需用广告账户登录授权即可，**无需开发者 Token**。

```
用户 → MCP Client → TikTok OAuth 登录页 → 用户授权 → 获取授权码 → 换取Token → 存储Token
```

### 3.2 授权步骤

**步骤一：发起授权请求**
1. MCP 客户端生成授权 URL
2. 用户在浏览器中打开授权页面
3. 用户使用 TikTok 广告账户登录

**步骤二：用户授权**
1. 用户确认授权范围（如：读取广告数据）
2. TikTok 重定向到回调地址，附带授权码

**步骤三：换取 Token**
1. MCP 客户端使用授权码换取 Access Token
2. 同时获取 Refresh Token
3. Token 加密存储到本地

**步骤四：验证连接**
1. 使用 Token 调用 MCP 工具
2. 验证连接正常
3. 获取可访问的账户列表

### 3.3 授权范围（Scopes）

| 权限范围 | 说明 | 推荐 |
|---------|------|------|
| `ads:read` | 读取广告数据（报表、广告列表等） | ✅ 分析必备 |
| `ads:write` | 修改广告设置（预算、出价、状态等） | ⚠️ 按需开启 |
| `ads:manage` | 创建/删除广告 | ⚠️ 高风险 |
| `finance:read` | 读取财务数据（余额、账单等） | ⚠️ 按需开启 |

**建议：** 分析类需求只需 `ads:read` 权限，遵循最小权限原则。

### 3.4 Token 管理

**Token 有效期：**
- Access Token：通常 24 小时
- Refresh Token：通常 30 天

**自动刷新机制：**
- Access Token 过期前自动使用 Refresh Token 刷新
- Refresh Token 过期时需要用户重新授权

**安全存储：**
- Token 使用系统密钥链或加密文件存储
- 绝不明文存储或传输
- 绝不在对话中展示

---

## 四、MCP 工具列表

### 4.1 工具发现

首次连接 MCP Server 时，应调用 `tools/list` 发现所有可用工具。

**工具发现命令：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

### 4.2 预期可用工具

根据 TikTok Marketing API 的能力，MCP Server 预计提供以下工具：

| 工具名（推测） | 类别 | 说明 |
|---------------|------|------|
| **账户类** | | |
| `list_ad_accounts` | 账户 | 获取已授权的广告账户列表 |
| `get_account_info` | 账户 | 获取账户基本信息 |
| **报表类** | | |
| `report_integrated_get` | 报表 | 获取综合报表数据（最常用） |
| `report_audience_get` | 报表 | 获取受众分析报表 |
| **广告系列类** | | |
| `campaign_get` | 广告系列 | 获取广告系列列表 |
| `campaign_create` | 广告系列 | 创建广告系列（写权限） |
| `campaign_update` | 广告系列 | 更新广告系列（写权限） |
| **广告组类** | | |
| `adgroup_get` | 广告组 | 获取广告组列表 |
| `adgroup_create` | 广告组 | 创建广告组（写权限） |
| `adgroup_update` | 广告组 | 更新广告组（写权限） |
| **广告类** | | |
| `ad_get` | 广告 | 获取广告列表 |
| `ad_create` | 广告 | 创建广告（写权限） |
| `ad_update` | 广告 | 更新广告（写权限） |
| **素材类** | | |
| `creative_get` | 素材 | 获取素材列表 |
| `creative_analysis` | 素材 | 素材效果分析 |
| **受众类** | | |
| `audience_insights` | 受众 | 受众洞察分析 |
| `audience_list` | 受众 | 自定义受众列表 |

> ⚠️ 注意：具体工具名和参数以 MCP 端点实际暴露的为准。
> 首次连接时务必先调用 `tools/list` 确认可用工具。

### 4.3 工具调用示例

**调用报表查询工具：**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "report_integrated_get",
    "arguments": {
      "advertiser_id": "123456789",
      "start_date": "2024-01-01",
      "end_date": "2024-01-31",
      "data_level": "AUCTION_ADVERTISER",
      "dimensions": ["stat_time_day"],
      "metrics": ["spend", "impressions", "clicks", "ctr", "cpc"]
    }
  }
}
```

---

## 五、连接状态检查

### 5.1 状态检查项

| 检查项 | 方法 | 正常状态 |
|--------|------|---------|
| 端点可达性 | HTTP GET 请求 | 200 或 401（未授权是正常的） |
| OAuth 授权状态 | 调用简单工具（如 list_accounts） | 成功返回数据 |
| Token 有效性 | 检查 Token 过期时间 | 未过期或可自动刷新 |
| 权限范围 | 检查已授权的 scopes | 包含所需权限 |
| 账户访问 | 列出可访问的账户 | 返回账户列表 |

### 5.2 常见连接问题

**问题1：连接超时**
- 检查网络连接
- 确认端点地址正确
- 检查是否需要代理

**问题2：授权失败**
- 确认账户有广告投放权限
- 检查授权范围是否正确
- 重新发起授权流程

**问题3：Token 过期**
- 检查 Refresh Token 是否有效
- 重新授权获取新 Token
- 检查自动刷新机制

**问题4：权限不足**
- 确认已授权所需的 scopes
- 重新授权并选择正确的权限
- 联系账户管理员确认权限

---

## 六、多账户管理

### 6.1 多账户支持

MCP 授权后可以访问该用户名下的所有广告账户。

**账户切换：**
- 默认使用配置文件中的 `default_account`
- 可以通过参数指定使用的账户
- 每次操作前确认使用的账户

### 6.2 账户信息展示

**可以展示的信息：**
- 账户名称
- 账户状态（活跃/暂停）
- 账户货币
- 账户时区

**需要脱敏的信息：**
- 完整的 advertiser_id（可展示后4位：****1234）
- 账户余额（敏感财务数据）
- 账户负责人信息

---

## 七、最佳实践

### 7.1 安全最佳实践

1. **最小权限原则**：只授权分析所需的只读权限
2. **定期审查授权**：定期检查已授权的应用，移除不需要的
3. **使用独立账户**：建议使用专门的分析账户，而非管理员账户
4. **启用日志审计**：记录 MCP 调用日志，定期审查
5. **异常监控**：监控异常调用模式，及时发现安全问题

### 7.2 使用最佳实践

1. **先发现工具**：首次连接先调用 `tools/list` 了解可用工具
2. **缓存常用数据**：减少重复调用，提高效率
3. **控制调用频率**：遵守 API 限流规则
4. **错误处理**：实现重试和退避机制
5. **数据验证**：对返回数据进行基本验证，确保完整性

### 7.3 性能最佳实践

1. **合理设置时间范围**：单次查询不超过 30 天
2. **使用分页**：大数据量查询使用分页
3. **只请求需要的指标**：减少数据传输量
4. **本地缓存**：缓存不常变化的数据
5. **批量查询**：合并多个小查询

---

## 八、相关资源

- [TikTok Marketing API 官方文档](https://business-api.tiktok.com/portal/docs)
- [MCP 官方规范](https://modelcontextprotocol.io/)
- [TikTok for Business](https://www.tiktok.com/business)
- [OAuth 2.0 规范](https://oauth.net/2/)

# Amazon Store Authorization Skill

亚马逊店铺 **授权与管理** Skill，提供授权流程、令牌管理、店铺查询等能力，是所有下游业务 skill（如 `linkfox-amazon-store-report`）的前置依赖。

## 📋 目录结构

```
linkfox-amazon-store-auth/
├── SKILL.md                          # Skill 主文档
├── _meta.json                        # Skill 元数据
├── README.md                         # 本文件
├── references/
│   ├── api.md                        # API 详细说明
│   ├── authorization-flow.md         # 完整授权流程
│   └── quick-start.md                # 5 分钟快速授权
└── scripts/
    ├── README.md                     # 脚本使用指南
    ├── authorize_url.py              # 生成授权 URL
    ├── authorized_stores.py          # 列出已授权店铺
    ├── refresh_token.py              # 刷新访问令牌
    └── store_tokens.py               # 查询店铺令牌
```

## 🚀 快速开始

### 1. 授权新店铺

```bash
POST /spApi/authorizeUrl
{
  "region": "NA",
  "sellerName": "My Store"   # ⚠️ 必填：用于识别该授权店铺
}
# 在浏览器打开返回的 authorizeUrl
```

### 2. 查看已授权店铺

```bash
POST /spApi/authorizedStores
```

### 3. 获取访问令牌（供下游 skill 使用）

```bash
POST /spApi/storeTokens
{
  "sellerId": "A1234567890",
  "region": "NA"
}
```

## 🔗 关联 Skill

| Skill | 说明 |
|-------|------|
| `linkfox-amazon-store-report` | 获取亚马逊报告（依赖本 skill） |

## 🌍 支持的区域

- **NA**：美国、加拿大、墨西哥
- **EU**：英国、德国、法国、意大利、西班牙等
- **FE**：日本、澳大利亚、新加坡、印度

## 🔐 安全特性

- ✅ 用户级数据隔离
- ✅ 令牌自动刷新
- ✅ 完整错误处理
- ✅ HTTPS 加密

## 🔄 版本历史

- **v1.0.0**（2026-04-24）
  - 从早期综合亚马逊 skill 拆分而来
  - 保留所有授权、店铺管理、令牌管理能力
  - 报告相关能力已拆出至 `linkfox-amazon-store-report`

## 📄 许可

本 Skill 是 LinkFoxAgent 项目的一部分。

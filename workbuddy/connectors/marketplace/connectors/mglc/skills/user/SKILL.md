---
name: mglc-user
description: 灵创用户认证技能 - 登录、查看用户信息、退出登录
version: "1.0.0"
author: "灵创 AI"
---

# 灵创用户认证 Skill

本 Skill 提供灵创 CLI 的用户认证能力。

## 认证说明

在 WorkBuddy 中首次使用时执行 `mglc auth --source workbuddy`。该命令输出 HTTPS 授权 URL；用户在浏览器中完成确认后，下一条需要认证的 `mglc` 命令会自动兑换待授权设备码、保存 Bearer Token，并继续执行该命令。`mglc status` 也会触发兑换，但业务命令前不需要先轮询 status。

AK/SK 登录仍可用于非 WorkBuddy 环境：通过 `mglc login`，或设置 `MGLC_ACCESS_KEY` 和 `MGLC_SECRET_KEY`。

## 可用命令

### auth - WorkBuddy 设备授权

```bash
mglc auth --source workbuddy
```

stdout 只会输出授权 URL。授权等待期间，任何需要认证的命令均返回等待浏览器确认；用户拒绝或授权过期后会清理 pending 状态，但不会删除已有有效 Token。

### login - AK/SK 登录配置凭证

配置 Access Key 和 Secret Key 登录灵创平台。

**命令**：
```bash
mglc login --access-key YOUR_AK --secret-key YOUR_SK
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --access-key | string | ✓ | Access Key |
| --secret-key | string | ✓ | Secret Key |
| --endpoint | string | - | API 地址，默认 https://aigc.mgtv.com |

### user info - 查看用户信息

查看当前登录用户和企业空间信息。

**命令**：
```bash
mglc user info
```

**使用示例**：
- 检查当前登录状态
- 查看用户所属企业空间
- 获取用户基本信息

### logout - 退出登录

设备授权登录时先撤销远端 Token，再清除本地 Token；AK/SK 登录时清除本地保存的 AK/SK 配置。

**命令**：
```bash
mglc logout
```

### version - 查看版本

查看当前 CLI 版本信息。

**命令**：
```bash
mglc version
```

## 输出格式

默认输出 JSON 格式：

```json
{
  "code": 0,
  "data": { ... },
  "msg": "success"
}
```

常见错误码：
| 错误码 | 含义 |
|--------|------|
| 0 / 200 | 成功 |
| 10002 | 未登录 |
| 10003 | 无权限 |
| 10101 | 服务不可用 |

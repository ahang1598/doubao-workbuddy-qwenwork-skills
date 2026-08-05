# AK 配置指南

## 获取 AK（引导用户）

当用户没有 AK 时，Agent 输出以下引导：

> 请提供您的 AK（Access Key），用于 1688 商品运营接口的鉴权。

也可以执行 `python3 cli.py get_ak` 由浏览器自动登录获取并写入。

## Agent 配置流程（核心）

用户告知 AK 后，Agent 按以下步骤执行：

```
1. 从用户消息中提取 AK 字符串
2. 执行 python3 cli.py configure <AK>
3. 检查输出：success=true → 继续；success=false → 原样输出 markdown 错误信息
4. 配置成功后由本地存储生效（设备绑定加密）；如当前会话仍未生效，提示用户新开会话或重试 configure
5. 继续用户的原始请求（如发布商品、改标题、改主图、上下架等）；若用户仅提供了 AK 没有其他请求，告知"配置成功，您可以开始进行商品运营操作了"
```

## CLI 调用

```bash
python3 {baseDir}/cli.py configure YOUR_AK_HERE
```

无参数调用可查看当前配置状态：`python3 {baseDir}/cli.py configure`

## AK 前置检查（强制）

除 `configure` / `get_ak` / `change_ak` 这类 AK 管理命令外，执行任何业务命令前都必须先执行：

```
python3 cli.py configure --status
```

判定规则：

- `data.configured: true` 且 `data.healthy: true` → 继续执行用户目标命令。
- `data.configured: true` 但 `data.healthy: false` 或 `data.expired: true` → 不得继续执行用户目标命令，必须优先执行 `python3 cli.py get_ak` 重新获取 AK。
- `data.configured: false` 或 `markdown` 含"AK 未配置" / "AK 已失效" → 不得继续执行用户目标命令，必须优先执行 `python3 cli.py get_ak` 自动获取 AK。
- 自动获取 AK 并写入后，必须再次执行 `python3 cli.py configure --status`，确认 `data.configured: true` 且 `data.healthy: true` 后才能继续原命令。
- 不得仅依赖业务命令返回的"AK 未配置"错误作为首次判断。

## CLI 命令说明

| 命令 | 说明 |
|---|---|
| `python3 cli.py get_ak` | 通过浏览器自动登录获取 AK 并写入本地（推荐） |
| `python3 cli.py change_ak` | 通过浏览器切换账号，引导从授权页 localStorage 读取新 AK |
| `python3 cli.py configure` / `configure --status` | 查看 AK 配置状态并探活 |
| `python3 cli.py configure <AK>` | 手动设置 AK |
| `python3 cli.py configure --reset <AK>` | 重置 AK（清除旧 Token + 写入新 AK） |
| `python3 cli.py configure --clear` | 清除 AK 与关联 Token |

## 设计说明

- **AK 存储位置**：`{workspace}/.1688-AK/.ak_store.json`，文件权限 `0o600`，仅文件所有者可读写
- **加密方式**：PBKDF2-HMAC-SHA256 派生密钥 + 流加密 + HMAC 校验，使用机器 ID 设备绑定，拷贝到其他机器后无法解密
- **优先存储**：可用时优先使用 OS Keychain，不可用时降级为加密文件
- **签名方式**：HMAC-SHA256（请求头 `x-csk-*`）
- **userId 注入**：发送请求时 `api_post()` 自动从 AK 解析 AccessKeyID 作为 userId 注入请求体
- **AK 探活**：`configure --status` 通过 `/api/infra_system_health_check/1.0.0` 校验 AK 是否健康

## 异常处理

| 场景 | Agent 应对 |
|------|-----------|
| `configure` 输出 `success=false` | 原样输出 `markdown` 错误信息 |
| 配置成功但后续命令仍报 AK 未配置 | 提示用户新开会话，必要时再重试 `configure --status` |
| `configure --status` 返回 `healthy=false` 且 `expired=true` | 执行 `python3 cli.py get_ak` 重新获取 AK |
| 用户问"我的 AK 在哪" | 输出上方获取 AK 引导话术 |

### macOS Keychain 权限错误（错误码 -67674）

当 Python 首次访问 macOS Keychain 时，系统会弹出授权对话框。如果用户未授权或权限被拒绝，会出现此错误。

**解决方案**：
1. 当系统弹出「python 想要访问钥匙串」对话框时，输入密码并点击「始终允许」
2. 如果对话框未弹出，打开「钥匙串访问」应用手动添加权限

### AK 配置持续失败（开启完全授权访问模式）

若执行 `configure` 后 AK 仍无法写入或读取，可能是运行本 skill 的软件未开启完全授权访问模式，导致 skill 进程无法访问本地文件。

**解决方案**：在运行本 skill 的客户端软件的设置中，开启「自动授权访问」模式后重新执行 `configure` 命令。

## AK 格式要求

- 长度 ≥ 32
- 字符集仅含 `A-Za-z0-9_-=`
- 包含敏感信息，请勿泄露到聊天、截图、日志或版本控制

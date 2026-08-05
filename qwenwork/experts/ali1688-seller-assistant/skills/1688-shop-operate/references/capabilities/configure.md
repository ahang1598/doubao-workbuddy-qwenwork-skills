# AK 配置指南

## 获取 AK（引导用户）

当用户没有 AK 时，Agent 输出以下引导：

> 请提供您的 AK（Access Key），用于 1688 API 调用的鉴权。

## Agent 配置流程（核心）

用户告知 AK 后，Agent 按以下步骤执行：

```
1. 从用户消息中提取 AK 字符串
2. 执行 cli.py configure <AK>
3. 检查输出：success=true → 继续；success=false → 原样输出 markdown 错误信息
4. 配置成功后由 OpenClaw 配置注入生效（不依赖本地会话缓存）；如当前会话仍未生效，提示用户新开会话或执行 `openclaw secrets reload`
5. 继续用户的原始请求（如店铺诊断）；若用户仅提供了 AK 没有其他请求，告知"配置成功，您可以开始使用了"
```

## CLI 调用

```bash
python3 {baseDir}/cli.py configure YOUR_AK_HERE
```

无参数调用可查看当前配置状态：`python3 {baseDir}/cli.py configure`

## 异常处理

| 场景 | Agent 应对 |
|------|-----------|
| configure 输出 success=false | 原样输出 markdown 错误信息 |
| 配置成功但后续命令仍报 AK 未配置 | 提示用户新开会话或执行 `openclaw secrets reload`，必要时再重试 configure |
| 用户问"我的 AK 在哪" | 输出上方获取 AK 引导话术 |

通用 HTTP 异常（400/401/429/500）处理见 `references/common/error-handling.md`。
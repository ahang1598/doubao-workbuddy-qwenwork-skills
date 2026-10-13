# 登录授权：status / login / logout

适用于检查登录、首次授权、退出和切换账号。所有业务命令共享 CLI 凭据，无需为查询或媒体处理单独设置密钥。

## 调用与结果

```bash
pippit-tool-cli status
```

读取 JSON 的 `logged_in`、`source`，以及存在时的 `uid`、`expires_at`。`logged_in=true` 表示 CLI 找到了可用凭据，不保证服务端尚未撤销凭据或具有某个模型的使用权限。

未登录时执行：

```bash
pippit-tool-cli login
```

引导用户在 CLI 提供的浏览器页面完成授权，等待命令成功返回 `logged_in=true`。CLI 自动申请或复用本机凭据并保存到系统安全凭证库。无浏览器交互能力且没有可用凭据时，报告授权阻塞。

用户要求退出时执行：

```bash
pippit-tool-cli logout
```

`logged_out=true` 表示清除了本机浏览器登录凭据；`remote_credential_preserved=true` 表示远端密钥未撤销。切换账号时先退出，再重新登录，在新授权页选择目标账号；不要刷新旧授权页。

## 显式凭据覆盖与故障处理

- `XYQ_ACCESS_KEY` 是 CI、Agent 等环境的显式覆盖，优先于网页登录凭据。已设置但无效时不会自动回退；应修正该环境的配置或取消覆盖，再重试原操作。
- `logout` 不清除环境变量；返回 `environment_still_active=true` 时，显式密钥仍生效。不要把本机退出解释成所有凭据均已失效。
- 浏览器登录凭据被服务端拒绝时可使用 `pippit-tool-cli login --force` 轮换本机密钥；不要作为每次调用的例行步骤。
- 不展示、回显或把密钥写入文档和命令参数。错误信息中出现凭据时，向用户展示前须隐藏凭据。
- 带凭据的 API 请求固定发往 `https://xyq.jianying.com`，不通过修改 API 域名修复鉴权问题。

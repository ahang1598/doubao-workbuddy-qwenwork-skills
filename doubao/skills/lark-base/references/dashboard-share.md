# 仪表盘分享命令 Reference

## 命令与字段

`+dashboard-share-get` 读取状态，`+dashboard-share-update` 更新设置，均使用 `--base-token` 与 `--dashboard-id` 定位。

| 更新参数 | 字段 | 含义与取值 |
|---|---|---|
| `--enabled` | `enabled` | 分享启停，布尔值 |
| `--access-scope` | `access_scope` | 访问范围：`invite`、`tenant`、`anyone` |
| `--show-source` | `settings.show_source` | 是否显示返回源 Base 的入口，布尔值 |

## 更新语义

每次调用必须且只能提供一个更新参数；未提供或同时提供多个会被 CLI 拒绝。修改多个设置需拆成独立调用。未传字段不加入 PATCH 请求，显式 `false` 必须保留，用 `--enabled=false` 或 `--show-source=false` 表达关闭。

```bash
lark-cli base +dashboard-share-get \
  --base-token "<base_token>" --dashboard-id "<dashboard_id>"

lark-cli base +dashboard-share-update \
  --base-token "<base_token>" --dashboard-id "<dashboard_id>" --show-source=false
```

## 返回与核对

读取和更新均返回服务端分享数据，`show_source` 位于 `settings` 中；按实际返回解释状态，不把提交值当作回读值。`enabled=true` 表示分享已开启，分享 URL 使用服务端实际返回，不从普通 Base 地址推导。CLI 不开放 `enable_auto_analysis` 设置，并会从返回中移除该字段。

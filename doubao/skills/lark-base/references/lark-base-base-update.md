# base +base-update

更新已有 Base 的 Base 级设置。目前该命令用于更新 Base 时区，不用于修改表、字段或视图。

## 推荐命令

```bash
lark-cli base +base-update \
  --base-token <base_token> \
  --time-zone Asia/Shanghai \
  --as user
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--base-token <token>` | 是 | 目标 Base Token，不是 Workspace Token |
| `--time-zone <iana-time-zone>` | 是 | 新的 IANA 时区，例如 `Asia/Shanghai` |
| `--as user` | 否 | 默认优先使用当前用户身份；应用身份只有在用户明确要求时使用 |

## API 入参详情

**HTTP 方法和路径：**

```
PATCH /open-apis/base/v3/bases/:base_token
```

**请求体：**

```json
{"time_zone":"Asia/Shanghai"}
```

只提交要更新的 `time_zone` 字段，其他 Base 设置由服务端保留。时区格式由 backend 按 IANA 时区校验；参数非法时根据返回错误修正后重试，不要把任意时区缩写当作合法值。

## 工作流

1. 已有 Base Token 时直接使用；只有 Base URL 或名称时，先按 [lark-base](../SKILL.md) 的实体解析入口取得 `base_token`。
2. 低频更新无需先比较当前时区；即使新值与现值相同，也可以直接执行。
3. 写入前可用 `--dry-run` 检查请求方法、路径和请求体；确认无误后移除该参数执行更新。
4. 成功响应中的 `base.revision` 和 `base.time_zone` 用于确认服务端已接受更新。

## 注意事项

- 不要使用 `+base-create` 或 `+base-copy` 代替已有 Base 的时区更新。
- 不要把表、字段或视图的配置参数放进本次请求体；这些对象使用各自的命令。
- 权限错误沿用当前身份处理，只有用户明确要求时才切换 `--as bot`。

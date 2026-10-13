# DTS-AI 认证

## API Key 读取顺序

按以下顺序解析 API Key：

1. 当前进程的 `DTS_AI_API_KEY` 环境变量。
2. `~/.aliyun-dts/dts-ai/credentials.json`。

不得读取或修改 Shell 启动文件。不得打印、记录或另行持久化解码后的 API Key。

## 凭据文件要求

只接受以下 v1 JSON 对象：

```json
{"schema_version":1,"service":"aliyun-dts-ai","api_key":"<base64-api-key>"}
```

`api_key` 的值是 API Key 的 UTF-8 字节经标准 Base64 编码后的结果。Base64 是可逆编码，并非加密。不得增加用于描述编码方式的字段名或元数据。

出现以下任一情况时，必须拒绝凭据文件：JSON 格式错误；存在重复字段或未知字段；`schema_version` 或 `service` 的值不受支持；`api_key` 为空或不是标准 Base64；内容包含无效 UTF-8、BOM 或控制字符；文件大于 16 KiB；文件是符号链接、Windows 重解析点、非普通文件或不属于当前用户。

写入时，先写入同目录的临时文件，再以原子方式替换凭据文件。不得将 API Key 存储在技能目录、工作区、已保存结果、任务记录、URL、命令参数、页面源码、命令输出、错误信息或日志中。

## 交互式设置

`setup` 命令会在 `127.0.0.1` 的随机端口上启动临时服务器，并打开系统默认浏览器。中文会话使用 `zh-CN`，其他会话使用 `en`。

必须满足：

- 使用随机会话路径和 CSRF Token；
- 验证 Host 请求头完全匹配，并验证 Origin 或 Referer 请求头提供的同源证据；
- 强制限制表单大小和字段数量；
- 使用密码输入框；
- 禁用请求日志、缓存、嵌入框架、外部资源和不必要的浏览器权限；
- 在成功保存一次、用户取消或等待超过五分钟后，终止服务器。

成功页面只能提示配置完成，不得显示 API Key 或凭据路径。

## 智能体限制

不得执行以下操作：

- 显示或泄露会话 URL；
- 使用浏览器自动化打开或检查页面；
- 要求用户通过聊天、终端输入、命令参数或工具结果提供 API Key；
- 增加通过终端输入 API Key 的回退方式；
- 读取、写入、替换或删除 Shell 启动文件中的 API Key 赋值。

如果无法打开系统浏览器，返回 `OPEN_FAILED` 并停止配置。引导用户前往[阿里云 RAM API Key 控制台](https://ram.console.aliyun.com/profile/api-keys)，为“数据传输服务 / DTS”创建 API Key。

## 服务配置

| 配置项 | 必需值 |
| --- | --- |
| Endpoint | `dtsai.cn-beijing.aliyuncs.com` |
| API 版本 | `2026-04-01` |
| 地域 | `cn-beijing` |

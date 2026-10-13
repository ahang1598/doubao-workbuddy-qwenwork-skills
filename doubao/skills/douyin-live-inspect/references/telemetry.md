# 统一埋点接口

## 唯一事件表

所有应用层事件 Key 集中在 `runtime/telemetry-events.json`：

| 分组 | 内容 |
| --- | --- |
| skill | 新请求入口 START、版本确定 VERSION_SELECTED |
| formal | 正式版全部已有脚本命令 |
| operations | 正式版 OpenAPI 操作名到线上 command 的映射 |
| lite | START、STOP、REPORT、RECAP_REPORT 四个命令 |
| task | STARTED、RESUMED、FINISHED 三种生命周期 |

该文件是事件名称和允许上报范围的唯一来源。JS 使用 `EVENTS`，Python 使用 `TASK`；不在业务文件复制 `task.started` 等字符串。SDK 自带的 `cli_command_executed` 通道保持原样，不修改 vendor。版本继续读取主 SKILL.md。

## 如何调用

正式版业务通过已有命令包装器调用，自动处理结果、耗时、身份、安全字段和嵌套去重：

```js
import {EVENTS, runCommand} from '../runtime/telemetry.mjs';
await runCommand(EVENTS.formal.REPORT_LINK, async () => {
  // 执行业务，返回真实结果。
});
```

每次业务请求先执行无参命令 `node scripts/skill-start.mjs`，读取或生成持久化 Device ID，并尝试上报一次。子 Skill 跳转和同请求续办不重复执行。入口统计使用 SDK 的 `invocation_id`，Device ID 不作为使用次数去重键。

确定版本时调用 `node scripts/version-selected.mjs --mode lite|formal`（两值择一）。对应 command 为 `version-selected`，extra 包含 `product=douyin-live-inspect`、`record_type=skill_lifecycle`、`feature=version_selection`、`inspection_mode=lite|formal`，自动附加 Device ID 和允许的身份字段，版本读取主 Skill。统计用户回答、直接指定及自动分流，实际切换再次记录；展示选项、等待回答、查询和普通续办不计入。调用与会话去重遵循[版本确定埋点](../SKILL.md#版本确定埋点)，脚本本身不持久化去重，不传用户原话或媒体地址。

命令只接受 `--mode lite` 或 `--mode formal`，非法参数不发送；输出安全状态 `attempted`、`disabled`、`invalid_input`、`unavailable` 或 `timeout`，均以退出码 0 返回。关闭遥测不解析身份、不读取或创建设备 ID；发送失败静默降级，2.5 秒截止，不补报。`attempted` 不代表线上入库；本机观察台直接使用统一事件表中的中文说明和 `inspection_mode` 展示。

一次性入口由统一发送函数处理，自动附加 `extra.deviceId`；仅传入已验证的白名单字段，保留入口调用方的截止时间与异常降级：

```js
import {EVENTS, reportEvent} from '../runtime/telemetry-reporter.cjs';
await reportEvent(EVENTS.skill.START, {
  product: 'douyin-live-inspect', record_type: 'skill_lifecycle',
  feature: 'skill_start',
}, {toolName: 'byted-live-inspect'});
```

Lite 生命周期在现有任务事务钩子内调用统一函数。函数认领并构造事件，外层事务提交后统一发送；不能在事务内直接发网络请求：

```python
from runtime.telemetry_keys import TASK
from runtime.task_telemetry import record_event

payload = record_event(TASK.FINISHED, record, result='completed')
if payload:
    tx.events.append(payload)
# 同一事务持久化 record；现有 Store 提交钩子负责发送，回滚不发送。
```

普通业务位置不需要自己管理 SDK、Node、发送超时或去重。Store 创建/状态变更和批次钩子已经接入；不要再从每个 CLI 分支重复记录任务事件。

## 实现职责

- `runtime/telemetry-reporter.cjs`：共享 SDK 初始化、允许事件检查、统一 runEvent/reportEvent 发送。只有这里调用 SDK runScript。
- 正式版 `runtime/telemetry.mjs`：业务执行包装、账号上下文、取消、嵌套操作去重。
- Lite `scripts/telemetry.cjs`：Python 进程桥接，仅四个白名单命令创建命令事件；其他已有桥接路径仅提供生命周期上下文。
- Lite `runtime/task_telemetry.py`：生命周期统一 record_event、身份快照、轮次和去重。状态规则与事务发送沿用现有模块。

未知事件不会进入 SDK；移除的命令也不会残留基础事件。遥测失败不影响业务，不重放操作；关闭遥测不识别用户、不创建设备 ID。媒体、认证内容、请求正文和异常原文不得传入公共接口。

正式版覆盖保持原样，详见 [正式版埋点](formal-telemetry.md)。Lite 精简后的白名单及统计口径见 [Lite 埋点](../lite/references/telemetry.md)。历史数据不清理、不补发，线上报表不在本次修改范围。

## 本机埋点观察

在包含当前观察模块的 Skill 根目录启动：

```sh
node scripts/telemetry-observer.mjs
```

打开终端输出的本机网页，在豆包工作 APP 的“本地电脑”模式正常使用该 Skill。无需为每次调用增加参数；正式版、Lite 和后台任务共用发送入口。旧安装包需要先通过正常安装流程更新到包含观察模块的包，服务不会自动替换安装文件。

服务与 Skill 必须使用同一配置目录：优先 `DOUYIN_LIVE_INSPECT_CONFIG_DIR`，否则为 `${XDG_CONFIG_HOME:-$HOME/.config}/byted-live-inspect`。自定义目录时启动服务也需指定相同变量。默认监听 `127.0.0.1` 随机端口，可用 `--port` 指定端口。`Ctrl+C` 关闭并清理观察标记。异常退出的无效标记不会阻断业务；启动报 EEXIST 时请确认旧服务已停止，再移除配置目录下的 `telemetry-observer.json` 后重试。

网页区分服务连接和已捕获事件，可搜索 Key/中文说明、筛选版本并查看详情。只保留内存中最近 1000 条事件，不保存历史、不补发；服务关闭后清空。已捕获仅表示进入 SDK 发送通道，不表示线上平台已接收或入库。

观察是尽力而为的旁路：不更改线上地址或负载，不等待本地响应，不重试；150ms 超时，最多 32 个并发请求，短进程退出时允许丢弃未完成的观察请求。服务不可达或标记损坏时静默跳过，关闭遥测时也不观察。不要用观察台作为审计存档或线上入库统计。

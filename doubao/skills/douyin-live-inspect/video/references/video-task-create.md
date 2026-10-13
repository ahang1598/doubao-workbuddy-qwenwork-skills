# content/+video-task-create

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-task-create' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 项目、场景和一个待检视频来源都已确定时创建视频质检任务。

## Avoid when

- 来源缺失、来源类型冲突时停止。多视频请求在用户确认映射与顺序后，由上层编排逐项调用本单视频创建能力；一次调用仍只能传一个视频。

## Prerequisites

- 准备已选择并核验的 `ProjectName`、`ScenarioId`、`SourceType` 和仅含一个对象的 `TaskItems`；始终显式传 `project_name`，不使用内置运行时默认项目。
- 本产品固定 `SourceType=4`，提供单个 HTTP(S) `Url`。不开放 Vid 或 SourceTaskId 输入。
- 豆包 Work 的本地视频附件必须先由宿主上传并物化为质检服务可访问的 HTTP(S) URL，再按 `SourceType=4` 提交；不得提交本地路径、`file://`、对象 Key 或原始附件字段。
- 任务名可省略，由内置运行时生成带时间信息的默认名称。

## Tips

- 先通过 JSON stdin 设置 `dry_run:true` 校验；带临时鉴权参数的地址只通过同一 JSON stdin 的 `task_items` 数组传入，不得写入命令参数或临时文件，也不在对话中展示。
- 宿主物化的附件 URL 只在当前任务内存中使用，不写入日志或最终结果；Skill 不自行实现附件上传。

## Examples

从视频子目录执行以下 JavaScript 函数。`sourceUrl` 由宿主在受控内存中提供，不把实际 URL 粘进脚本、命令文本、临时文件或调试输出。示例按当前 Schema 先预检、再只创建一次；调用方只能接收白名单结果。宿主无法安全传递时按 [回退规则](../../references/auth-recovery.md#正式版不可用时回退-lite) 处理。

```javascript
import { spawnSync } from 'node:child_process';

export function createVideo({ projectName, scenarioId, profile, accountId, sourceUrl }) {
  const input = { environment: 'online', profile, account_id: accountId,
    project_name: projectName, scenario_id: scenarioId, source_type: 4,
    task_items: [{ Url: sourceUrl }] };
  function invoke(dryRun) {
    const child = spawnSync(process.execPath,
      ['../scripts/api.mjs', '--operation', 'content/+video-task-create'],
      { input: JSON.stringify({ ...input, dry_run: dryRun }),
        encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 2 * 1024 * 1024 });
    let result;
    try { result = JSON.parse(child.stdout); } catch { throw new Error('视频创建结果未确认，请保留上下文核验'); }
    if (child.error || child.status !== 0 || !result.ok)
      throw new Error('视频创建未确认成功，请保留上下文核验');
    return result;
  }
  invoke(true);
  const result = invoke(false);
  return { task_id: result.data.response.data.Result.TaskId,
    project_name: projectName, environment: result.meta.environment,
    profile: result.meta.profile, account_id: result.meta.account_id };
}
```

这是安全传参方式，不提供宿主秘密输入能力；执行工具会记录参数时，不能仅凭 `stdio:pipe` 就认为 URL 已受保护。

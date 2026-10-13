# query-result：查询异步结果并下载

用于生成和视频处理命令返回的任务，也用于用户要求查询的已有任务。三个参数均必填：

| 参数 | 含义 |
| --- | --- |
| `--thread-id` | 原任务的 `thread_id` |
| `--run-id` | 要查询的那一次运行的 `run_id`，不得混用其他运行 |
| `--download-dir` | 本地输出目录，命令在任务成功时自动下载产物 |

用户未指定目录时使用 `./xyq_output`。已知历史任务但缺少任一 ID 时，从当前上下文获取，无法确定则询问；不要通过重新生成来补 ID。

```bash
pippit-tool-cli query-result --thread-id THREAD_ID --run-id RUN_ID --download-dir "./xyq_output"
```

## 输出契约

stdout 是 JSON；命令可能将错误编码进 JSON 并以退出码 0 返回，因此必须先检查 `error_message`。

| 字段 | 含义 |
| --- | --- |
| `completed` | 是否结束；失败时也可能为 `true`，不等于成功 |
| `error_message` | 非空即错误，不能因为 `completed=false` 而忽略 |
| `thread_id` / `run_id` | 对应的查询任务 |
| `images[]` / `videos[]` | 成功后获取的媒体，每项含 `download_url`、`output_path` |

成功示例（ID、URL 和文件名仅为示意）：

```json
{
  "completed": true,
  "thread_id": "THREAD_ID",
  "run_id": "RUN_ID",
  "error_message": "",
  "images": [{"download_url": "https://example.com/image.jpeg", "output_path": "./xyq_output/asset.jpeg"}],
  "videos": []
}
```

任务尚未完成时通常返回 `completed=false`、空错误、空媒体数组。命令不提供完整会话消息、用户反问或可区分的所有状态；不能仅凭这个响应断言具体进度、取消状态或等待用户输入。轮询停止条件见 [共用流程](../workflows/async-delivery.md)。

## 下载行为

文件名由 CLI 根据产物信息生成，以 `output_path` 为准，不自行拼接编号或推测扩展名。同目录已有同名文件可能被复用；复用不证明内容相同，也不代表本次新下载。发现同名文件属于其他产物时，选择用户认可范围内的未冲突目录再查询，不删除已有文件。

找不到产物、链接缺失或下载失败时会返回错误。当前任一文件下载失败可能使整次查询只返回错误，无法据此认定其他文件都没下载或已完整交付。复查本次结果，不把输出目录里的任意旧文件当作本次产物。

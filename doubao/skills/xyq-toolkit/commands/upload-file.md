# upload-file：素材上传与 URL 导入

将本地文件或 HTTPS 媒体链接导入当前个人或团队空间，返回可复用的 Pippit 资产 ID。`--path` 与 `--url` 必须且只能提供一个。URL 模式只需用户提供链接，素材类型和内部文件名由服务端识别，不要求 `asset_type` 或 `file_name`。

先用 `pippit-tool-cli upload-file --help` 确认当前版本支持 `--url`；旧版缺少该参数时先更新到支持版本，再核对帮助。可用发布版本仍不支持时说明能力缺口，不反复升级。URL 导入还需要服务端部署对应能力，帮助检查通过不代表服务端已可用。

## Inputs

```bash
pippit-tool-cli upload-file --path "/path/to/reference.png" --team-id TEAM_ID
pippit-tool-cli upload-file --url 'https://example.com/reference?signature=...' --team-id TEAM_ID
```

示例二选一执行。`TEAM_ID` 使用本次工作流已确定的空间，个人为 `0`，后续查资产或建节点仍使用相同空间。

- `--path`：本地普通文件，支持图片、视频及 `.mp3` / `.wav` 音频。CLI 要求小于 500 MB（500000000 字节）；还须满足服务端的格式、大小和审核限制。
- `--url`：服务端可访问的 HTTPS 图片、视频或音频直链，可以是有效签名 URL，也可以没有文件后缀。服务端拒绝自动重定向，短链接或返回 3xx 的地址需换成最终素材直链。不能含 `user:password@host` 或 fragment；保留原始查询参数与签名，不擅自解码、删改或重签。shell 中为完整 URL 加单引号，避免 `&` 等字符被解释为命令。
- URL 模式由服务端探测内容并导入，CLI 不下载、读取或缓存源素材。当前服务端上限为 200 MiB，仍须通过格式校验和审核；不能仅凭 URL 后缀判断素材类型或可用性。

## Output

成功输出示例：

```json
{"team_id":"0","asset_id":"PIPPIT_ASSET_ID"}
```

保存这两个字符串。此处 `asset_id` 取自 API 的 `data.pippit_asset_id`，是稳定的 Pippit 资产 ID，不是云媒体 ID 或画布节点 ID。命令不返回 thread/run ID，也不提供 Canvas 的 `state`、`locator` 或就绪轮询；不要调用 `query-result` 等待导入。

用户只要求导入时，返回该资产 ID 与空间即可。用户还要求建立画布参考节点时，按 [Canvas 资产说明](canvas-assets.md#url-import) 和 [画布编辑流程](../workflows/canvas-edit.md) 查询素材，再用现有节点创建能力关联该 ID，写后回读。取得 ID 不代表节点已经创建或生成任务已经完成。

生成、超分与擦字幕命令的文件参数仍接收本地路径；不能将本命令返回的资产 ID 或源 URL 填入这些参数。

## Failures

双传或均未提供来源时，先修正参数。链接过期、源站拒绝访问、格式/大小不符或审核失败时，保留实际错误与可用的 LogID，按原因处理；不能把所有失败都归为审核拒绝。

收到资产 ID 后复用已有资产。超时或请求结果不确定时，保留已有 ID 和错误信息；有 ID 可在原空间查询，没有 ID 时不能猜测或声称导入成功，也不自动重放请求。批量调用控制并发，逐项保留成功 ID 与失败原因，不重跑已成功项。

URL 导入失败不自动改为本地下载再上传。画布流程也可以使用 [`canvas upload --url`](canvas-assets.md#url-import)，它复用相同服务端导入接口，但另有素材查询等待和 `state` / `locator` 输出；稳定 ID 取 `pippit_asset_id`，不能套用本命令的 `asset_id` 含义。已导入素材直接复用，不为等待就绪再调用另一个上传入口。

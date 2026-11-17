# PC Web HTML 画布交付

仅适用于 `image-coding`、`pure-coding` 的 PC Web HTML。`pure-image` 与 Mobile 不执行本文件；路线、环境、媒体展示和完整性交付按 [主入口](../SKILL.md#交付规范)。制作与检查仍按原题材和生产规范，不因交付改变路线。

## 1. 绑定当前画布

核验实际 `design-cli`、认证、`FileBatchUpload`、`present_files` 与当前 Workspace。已有唯一有效 ID 直接复用；多个 ID 无法确认归属时先澄清，不借用其他任务。`+get-workspace` 仅用于查询、恢复或排障，不作默认初始化入口。

没有 ID 时按 [workspace-create](../cli/workspace-create.md) 创建：

```bash
design-cli design-workspace +workspace-create --title "画布标题"
```

主 Agent 读取返回的原始 ID，调用 `present_files("真实WorkspaceID")` 展示初始化卡片后再制作依赖该画布的内容；独立纯图不受此门禁阻塞。CLI 的 `--canvas-workspace-id` 始终只传原始 ID。初始化卡片不替代成品卡片。

续做时先恢复本次所需源与有效版本：已知 ID 用 `+get`，位置不明用当前画布的 `+tree`／`+ls` 定位再读取。沿用仍有效的来源记录，不重复全量读取、不跨任务猜对象。子任务只回传完整源与检查结果，上传、写入及展示由主 Agent 执行。

## 2. 上传完整 HTML

按主入口的一页／面／屏分别处理，保持同版本、尺寸与顺序。用 `FileBatchUpload` 上传完整源：

```json
{"path_list":["本地完整HTML路径"]}
```

取对应文件返回的 `url`，不用 `path`、`uri` 或本地路径；已有对应当前版本的可持久访问 URL 直接复用。CLI 不负责上传文件。

## 3. 创建并回读每个 Item

每个 HTML 创建一个顶层 HTML Item，不用 HTML Frame 或 Frame 内嵌 HTML。XML 以 UTF-8 通过 stdin 传入，`--input` 只填 `-`：

```xml
<item type="HTML" path="/deliverables/题材目录" title="作品短名" brief="完整作品的内容描述">
  <size width="750" height="1500"/>
  <asset url="上传返回的真实URL"/>
</item>
```

替换全部示例值。`type`、`path`、`title`、`brief` 为必填属性；`path` 为以 `/` 开头的画布目录，不是文件路径。尺寸须与完整 HTML 一致。XML 属性正确转义 `&` 与引号。有已核验的派生来源时，在 `</item>` 前加入：

```xml
<source_ids><source_id>同一Workspace的真实来源ID</source_id></source_ids>
```

无来源省略整个标签；来源可以是 Item、Frame 或成员，不编造、不跨画布。创建时不携带旧 `item_id`。

```bash
design-cli design-workspace +create --canvas-workspace-id "真实WorkspaceID" --input - < item.xml
design-cli design-workspace +get --canvas-workspace-id "真实WorkspaceID" --item-ids "创建返回的ItemID"
```

上述重定向适用于 Bash；其他 Shell 按实际平台用子进程向 stdin 送入 UTF-8 字节，不将文件名当作 `--input` 值。协议与实际部署不一致时查当前帮助及原始响应，不能猜标签或参数。

create 的 `xml_data` 为补全 ID 的对象；get 为 `<get_result>`，从 `<items>` 提取目标，不将响应包装当请求根。get 必须指定真实 ID，单次最多10个。逐项核对同一 Workspace 中的 ID、类型、目录、标题、描述、尺寸、解码后资产 URL 与声明来源；任一不一致不交付。

## 4. 归档与版本

同套对象归入同一任务目录，已在正确目录不再更新。需移动时提交：

```xml
<item item_id="已回读的ItemID" type="HTML" path="/deliverables/题材目录"/>
```

```bash
design-cli design-workspace +update --canvas-workspace-id "真实WorkspaceID" --input - < move.xml
```

随后 get 确认仅目录变化。`+update` 仅支持顶层对象的 `path`、`brief`；归档只改 path，不提交空值。仅外部编辑使描述失真时修正 brief。

HTML 内容、样式、资产、尺寸或标题改变时创建新版本；未变文件可复用 URL，`source_ids` 记录实际派生的旧对象 ID。不把含 ID 的响应原样再次 create，不以旧回读为新版本背书。

## 5. 展示成品与预览

回读及归档核对通过后，每个 HTML 分别调用：

```text
present_files("真实WorkspaceID?item_id=当前ItemID")
```

按单值传入，键名为 `item_id`，问号两侧无空格。使用同一画布内已回读的当前 Item ID；聊天文字、普通链接、截图或原始 HTML 附件不能替代卡片。

每页／面／屏的完整预览分别上传 CDN，核验真实 HTTP(S) 地址后用 Markdown 图片展示；预览不写入画布、不调用 `present_files`。卡片和预览分别确认成功，不能互相替代；三折页内外侧须分别展示。最终按主入口核对全部应交产物，缺项不称完成。

## 6. 失败与重试

- 退出码为0且业务 `code=0` 才算调用成功，创建仍须 get 核验。参数错误先纠正，不凭通用报错更换根标签。
- Workspace 创建超时且未取得 ID 时按 workspace-create 的恢复规则处理，无法确认就停止重建。已知 Workspace 的写入超时或结果不明，先在同一 Workspace 用 tree／ls／get 对账，确认未成功再重试；无法确认就停止写入并报告，不重复创建。
- 同一对象同一步骤失败最多重试一次；只重试失败环节，不重复上传、生成或重跑作品检查。协议不明或重试后仍失败时保留真实结果与诊断，说明缺项，不改用 HTML 附件冒充完成。用户明确索要源码时按主入口处理。

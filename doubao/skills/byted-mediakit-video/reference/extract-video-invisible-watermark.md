# 提取视频暗水印

## 能力用途

从已嵌入暗水印的视频中解析并还原隐藏的数字信息；如果同一视频被多次嵌入暗水印，也能够提取出所有水印信息。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video extract-video-invisible-watermark`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `video_url` | `--video-url` | string | 是 | - | - | 待提取暗水印的视频 URL，必选。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式；分辨率最高支持 4K。 |

### 调用示例

```bash
mediakit-cli video extract-video-invisible-watermark \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频的总时长，单位为秒。 |
| `watermark_contents` | array<object> | 否 | Cloud 终态 | 提取到的暗水印数字信息列表，按系统提取顺序返回；若视频中嵌入了多次暗水印，可能返回多条结果；如果未提取到任何暗水印，列表为空。 |
| `watermark_contents[].watermark_content` | string | 否 | Cloud 终态 | 提取到的暗水印数字信息字符串。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video extract-video-invisible-watermark --help
mediakit-cli video extract-video-invisible-watermark --schema
```

# 剧本还原

## 能力用途

基于大模型视频理解能力，将短剧视频转化为结构化剧本文本，识别并提取场景、人物、对话和情节等核心元素。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-script`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--return-pkg`）只能写成 `--return-pkg=true` 或 `--return-pkg=false`，也可用裸 `--return-pkg`（等价 true）；禁止空格传值 `--return-pkg true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。

### 调用示例

```bash
mediakit-cli video drama-script \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `return_pkg` | `--return-pkg` | boolean | 否 | false | - | 控制任务结果的输出封装格式。true 时，所有任务产物会打包为 .tar.gz 压缩包，result_url 指向该压缩包，压缩包包含核心剧本 JSON、人物名及其图片、场景截图等分析结果；false 时，仅返回核心剧本数据，result_url 指向 Gzip 压缩的 JSON 文件 .json.gz。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待处理短剧视频的 URL 列表。单次任务支持传入 1 个至 100 个视频文件，并按 video_urls 的数组顺序拼接视频后进行分析。视频输入支持本地文件路径和公网 HTTP/HTTPS URL 两种协议来源，也支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流格式；不支持 HLS（M3U8）格式。单个视频文件时长不超过 120 分钟，单次任务所有视频累计时长不超过 300 分钟，视频必须包含内嵌硬字幕。适用于以人物对话和情节发展为核心的真人实拍短剧、长剧和电影；不适用于缺乏连贯真人剧情或人脸识别线索的动画、纪录片、广告和直播录屏。 |

| `output_language` | `--output-language` | string | 否 | - | 枚举: ["","zh-CN","en-US"] | 设置输出剧本的语言。如不填写或留空，默认为 zh-CN。支持的语言：zh-CN：简体中文；en-US：英语（美国） |
| `voice_language` | `--voice-language` | string | 否 | - | 枚举: ["","zh-CN","en-US","ja-JP","id-ID","es-MX","pt-BR","de-DE","fr-FR","ko-KR","fil-PH","ms-MY","th-TH","ar-SA","it-IT","bn-BD","el-GR","nl-NL","ru-RU","tr-TR","vi-VN","pl-PL","ro-RO","ne-NP","uk-UA","yue-CN"] | 指定视频中的语音语言，用于语音识别 ASR。默认行为：如不填写或为空，工具将自动检测语言。支持自动检测的语种为：中文、英文、上海话、闽南话、四川话、陕西话、粤语。支持的语种包括：zh-CN：简体中文；en-US：英语（美国）；ja-JP：日语；id-ID：印度尼西亚语；es-MX：西班牙语（墨西哥）；pt-BR：葡萄牙语（巴西）；de-DE：德语；fr-FR：法语；ko-KR：韩语；fil-PH：菲律宾语；ms-MY：马来语；th-TH：泰语；ar-SA：阿拉伯语；it-IT：意大利语；bn-BD：孟加拉语；el-GR：希腊语；nl-NL：荷兰语；ru-RU：俄语；tr-TR：土耳其语；vi-VN：越南语；pl-PL：波兰语；ro-RO：罗马尼亚语；ne-NP：尼泊尔语；uk-UA：乌克兰语；yue-CN：粤语 其中中文（zh-CN）与英文（en-US）为明确支持语种，其余语种可用但不保证识别效果。 |
### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `drama_script_task_id` | string / null | 否 | Cloud 终态 | 剧本还原任务 ID。 |
| `duration` | number / null | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `result_url` | string | 否 | Cloud 终态 | 最终生成的剧本文件下载地址，为公网 URL；有效期为 24 小时，务必及时保存。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-script --help
mediakit-cli video drama-script --schema
```

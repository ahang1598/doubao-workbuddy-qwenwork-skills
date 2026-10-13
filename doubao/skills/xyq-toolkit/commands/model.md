# model：发现可用视频模型

需要有效登录或 `XYQ_ACCESS_KEY`。生成前可查询当前账号可用的模型及参数配置；目前只支持视频模型。

```bash
# 全部可见视频模型
pippit-tool-cli model list

# 按 key 或展示名检索；search 是 list 的别名
pippit-tool-cli model search MiniMax --type video

# 按准确 key 查看参数详情；两种写法等价
pippit-tool-cli model describe MiniMax-H3
pippit-tool-cli model MiniMax-H3

# 强制重新查询服务端
pippit-tool-cli model list --refresh
pippit-tool-cli model describe MiniMax-H3 --refresh
```

`list` 输出 `models`，每项包含 `key`、`name`、`kind`、`is_default`。关键词与 key 完全一致时优先返回该项，否则按 key / name 不区分大小写检索。`describe` 只接受准确 key，输出整理后的 `model` 参数详情；不知道 key 时先查列表，不用展示名猜枚举。

两种输出均包含 `scene`、`cached`、`fetched_at`、`expires_at`。合法空列表输出 `models: []`，表示当前没有可见模型。

## 缓存与失败处理

成功结果在系统用户缓存目录的 `pippit-cli/models/` 下保留 5 分钟，命中不会延长有效期；按凭证指纹、API 地址、接口、场景及 CLI 版本隔离。缓存不保存 AK 原文。切换凭证或退出登录后，不读取先前凭证的缓存。

`--refresh` 跳过缓存重新查询。缓存过期、损坏或时间戳异常时重新请求；服务端查询失败返回非零退出状态并提示重试，不返回过期缓存或静态模型列表，也不缓存失败响应。可稍后重试原命令或加 `--refresh`；若是登录错误，先恢复登录。单次查询最长 30 秒，不自动重复请求。

缓存写入失败不丢弃本次服务端成功结果，stderr 会提示；stdout 仍为 JSON。

## 参数配置的使用

`describe` 将配置整理成可直接选择生成参数的结构。以下为示例片段，实际值以查询为准：

```json
{
  "key": "MiniMax-H3",
  "ratio": {
    "options": ["adaptive", "16:9", "21:9", "9:16", "4:3", "3:4", "1:1"],
    "default": "9:16"
  },
  "resolution": {"options": ["768p", "2k"], "default": "768p"},
  "duration": {"min": 4, "max": 15, "step": 1, "default": 10, "unit": "seconds"}
}
```

- `ratio.options/default` 按 IDL 转为字符串，可直接用于 `--ratio`。支持全部有对应生成参数的已有比例枚举；`0` 为 `adaptive`。自定义比例 `1` 没有对应的 CLI 尺寸参数，和未知枚举一样跳过；未知默认值不输出，不猜测替代值。
- `resolution.options` 去除 disabled 选项，默认值必须在有效选项内。
- `Seedance_2.0_mini`、`Seedance_2.0_mini_lite` 的生成请求可以省略 `--resolution`，服务端默认 `720p`。查询未返回分辨率维度时，不因此要求用户补填，也不在查询结果中伪造选项。
- `duration` 来自参数维度：范围输出 `min/max/step`，选项输出数字 `options`，均以秒为单位，不把选项枚举号当秒数。若只下发旧 `supported_duration_list`，暂保留该原始字段并明确提示不能直接用于 `--duration`。
- `material_limits` 保留数量字段；大小字段使用 `max_image_size_bytes`，视频时长字段使用 `min_video_duration_ms/max_video_duration_ms/max_total_video_duration_ms`。字段未返回与值为 `0` 保持区别。
- `creation_modes` 保留 `enabled`、素材校验等服务端策略，并为文本/参考/首尾帧模式标注对应 `generate_type`。`smart` 比例策略显示 `adaptive`；其他可识别模式继承模型比例。MiniMax 的文本模式排除 `adaptive`，纯文生视频使用固定比例。原始模式 key 不是生成参数，未标注 `generate_type` 的模式不代表 CLI 已接入。
- 条件维度的 `active_when_any`、参数组合约束及其他未转换字段保留；模型级选项不保证任意组合都可用。配置不一致时通过 `warnings` 提示刷新，未知比例枚举直接跳过。

内部 `config_key` 不输出。缓存仍保存服务端原始配置，列表/详情展示时转换，不修改生成请求、不新增本地模型准入限制。生成参数格式见 [生视频命令](generate-video.md)。

查询结果反映当前账号的服务端可见配置及 Skill 模型白名单；最终提交仍由服务端判断权限、参数、余额等条件。缓存最多滞后 5 分钟，需要最新值时使用 `--refresh`。生成命令不会自动请求模型列表或凭缓存拦截生成。

# 场景：从首帧过渡到尾帧

用户请求：“以 opening.png 为首帧、ending.png 为尾帧，生成从白天过渡到夜晚的视频。”

完成 [入口](../SKILL.md) 的前置步骤，确认两张图片实际位于下面的路径，读取 [生视频命令](../commands/generate-video.md)。

```bash
pippit-tool-cli generate-video \
  --prompt "以 opening.png 为首帧、ending.png 为尾帧，生成从白天过渡到夜晚的视频。" \
  --image "/path/to/opening.png" \
  --image "/path/to/ending.png" \
  --generate-type 1
```

第一个 `--image` 是首帧，第二个是尾帧，不按文件名重新排序。用户未指定模型、时长、比例和分辨率，省略这些参数。若用户仅给两张图片而未明确首尾角色，应先确认。随后执行 [异步结果与媒体交付](../workflows/async-delivery.md)。

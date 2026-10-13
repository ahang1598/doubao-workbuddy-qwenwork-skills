# 场景：擦字幕后超分

用户请求：“把 /path/to/source.mp4 先擦掉字幕，再超分到 1080p。”

用户已明确授权这两个步骤及顺序。完成 [入口](../SKILL.md) 的前置步骤，读取 [擦字幕](../commands/erase-video-subtitle.md)、[超分](../commands/video-super-resolution.md) 和 [异步交付流程](../workflows/async-delivery.md)。

第一步：

```bash
pippit-tool-cli erase-video-subtitle --video "/path/to/source.mp4"
pippit-tool-cli query-result --thread-id FIRST_THREAD_ID --run-id FIRST_RUN_ID --download-dir "./xyq_output"
```

查询使用第一步真实返回的 ID。按共用流程等待成功，核对下载的视频文件。将下面的 `FIRST_OUTPUT_PATH` 替换为对应 `videos[].output_path`，不能继续传最初的带字幕视频：

```bash
pippit-tool-cli video-super-resolution --video "FIRST_OUTPUT_PATH" --output-resolution 1080p
pippit-tool-cli query-result --thread-id SECOND_THREAD_ID --run-id SECOND_RUN_ID --download-dir "./xyq_output"
```

使用第二步的新 ID 查询，并交付最终视频附件。第一步失败时不提交第二步；第二步失败时说明组合任务尚未完成，可交付明确标注“仅完成擦字幕”的中间视频。用户只要求擦字幕时，到第一步结束，不自行增加超分。

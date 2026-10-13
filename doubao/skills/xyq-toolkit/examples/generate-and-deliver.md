# 基础示例：生成一张图并交付

用户请求：“用 seedream_5.0_pro 生成一张白底红色马克杯图片。”

先按 [入口](../SKILL.md) 完成安装检查与登录，读取 [生图命令](../commands/generate-image.md) 和 [异步交付流程](../workflows/async-delivery.md)。下列命令名替换为检查返回的 `cli_path`。

```bash
pippit-tool-cli generate-image --prompt "用 seedream_5.0_pro 生成一张白底红色马克杯图片。" --model seedream_5.0_pro --generate-image-count 1
```

此处模型与数量均来自用户请求，不添加比例或分辨率。保存实际返回的任务 ID 并展示任务链接，然后将下面的占位符替换为真实值：

```bash
pippit-tool-cli query-result --thread-id THREAD_ID --run-id RUN_ID --download-dir "./xyq_output"
```

按共用流程继续查询。成功后读取 `images[].output_path`，检查文件存在且非空，用宿主的附件工具或媒体渲染能力展示图片。回复可以是“已生成”加实际图片附件；只发送“文件位于 ./xyq_output/…”不算交付。

如果用户只问“怎么生成一张马克杯图片”，解释用法即可，不执行此收费流程。基础视频生成同样复用交付流程，提交参数改读 [生视频命令](../commands/generate-video.md)。

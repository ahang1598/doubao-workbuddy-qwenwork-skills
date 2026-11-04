# 场景：保留多张参考图的角色

用户请求：“用 Seedream 5.0 Pro，图1是底图，图2只提供猫的形象，把图1的猫换成图2的猫，背景和其他物体不变。”

用户明确图1为 `/path/to/scene.png`，图2为 `/path/to/cat.png`。完成 [入口](../SKILL.md) 的前置步骤后，读取 [生图命令](../commands/generate-image.md)。

先查询图片模型列表，确认其中包含用户指定的完整名称；以下名称仅为示例。

```bash
pippit-tool-cli generate-image \
  --prompt "用 Seedream 5.0 Pro，图1是底图，图2只提供猫的形象，把图1的猫换成图2的猫，背景和其他物体不变。" \
  --model "Seedream 5.0 Pro" \
  --image "/path/to/scene.png" \
  --image "/path/to/cat.png"
```

保留用户原文与素材顺序，不将两张图都理解成可自由混合的风格参考。图片角色或文件映射不明确时先确认。继续 [异步结果与媒体交付](../workflows/async-delivery.md)，逐项展示实际结果；具备看图能力时检查用户要求保留的主要元素，不能未经查看就宣称完全满足编辑要求。

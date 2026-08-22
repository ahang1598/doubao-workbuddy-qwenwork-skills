---
name: byted-mediakit-image
version: 0.2.0
license: MIT
description: "面向单张图片的视觉处理、质量优化、内容理解与 AI 编辑目标，适用于图像增强、文字或图标擦除、画质评估、文字识别以及背景移除。若对象和目标族已明确属于图片增强、图片理解或图片生成式编辑，但具体做法不确定，可先加载本 Skill 探索；若只说有图片而未说明业务目标，应先澄清。把多张图片做成视频或给视频叠图应路由到 editing；视频理解、视频增强或视频字幕擦除应路由到 video。"
permissions:
- shell
metadata:
  requires:
    bins:
    - mediakit-cli
  cliHelp: mediakit-cli image --help
  product: mediakit-cli-doubao/skills
  domain: image
  capability_count: 5
---
# image MediaKit Skill

## 使用规则

1. 先读取 `../byted-mediakit-shared/SKILL.md`，执行统一前置检查；该 Skill 缺失时停止并报告当前 Skill 包不完整。
2. 只从下表选择 `image` 域工具；相似能力按各工具“能力描述”和参数边界区分。
3. 执行前按需读取对应 reference；参数与结果说明来自同一份已审核文案，完整机器合同以当前 CLI `--schema` 为准。
4. 缺少必填参数、鉴权环境变量或真实输入资源时，向用户索取；通用可选字段只能透传用户明确提供的值，其他可选字段可由明确意图准确确定，但不得伪造。

## 工具列表

| 工具 | 说明 | 支持模式 | 命令 | 参考 |
| --- | --- | --- | --- | --- |
| enhance-image | 基于图像内容理解进行智能决策，提升图片的分辨率、清晰度与色彩表现。 | Cloud | `mediakit-cli image enhance-image` | [reference/enhance-image.md](reference/enhance-image.md) |
| erase-image | 可按不同场景控制自动检测并擦除图片中的文字或常见图标，擦除后的区域通过智能填充技术进行修复，修复后的区域与背景自然融合。 | Cloud | `mediakit-cli image erase-image` | [reference/erase-image.md](reference/erase-image.md) |
| evaluate-image-quality | 用于图像画质评估，对输入图片进行主客观画质和美学评分，适用于质量监控、低质图筛查、内容审核、推荐排序和训练数据清洗。 | Cloud | `mediakit-cli image evaluate-image-quality` | [reference/evaluate-image-quality.md](reference/evaluate-image-quality.md) |
| image-ocr | 用于通用印刷体文字识别（OCR），识别图片中的简体中文和英文，并提供文本块位置坐标与置信度参考。 | Cloud | `mediakit-cli image image-ocr` | [reference/image-ocr.md](reference/image-ocr.md) |
| remove-image-background | 自动识别并保留图像主体，移除背景后生成背景透明的图片，用于图像背景移除（抠图）。 | Cloud | `mediakit-cli image remove-image-background` | [reference/remove-image-background.md](reference/remove-image-background.md) |

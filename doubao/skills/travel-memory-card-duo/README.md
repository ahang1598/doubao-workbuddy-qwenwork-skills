# Travel Memory Card Duo

一个用于 Codex 的双图版旅行记忆卡技能。输入一张照片后，它会输出两张彼此匹配的图片：

1. **完整旅行记忆卡**：3:2 横版卡片，包含主插画、三个英文关键词和六枚贴纸。
2. **独立透明贴纸 PNG**：额外输出一张单独的 `.png` 文件，只保留与完整卡片相同的六枚贴纸。

## 透明 PNG 版本的含义

透明贴纸图不是从完整卡片中截取出来的预览，也不是把贴纸放在白底或棋盘格底上。它是一个独立交付文件：

- 文件格式为 **PNG**；
- 图像带有真实 **Alpha 透明通道（RGBA）**；
- 整张纸张背景被移除；
- 六枚贴纸保留暖白色手剪边缘；
- 不含标题、关键词、标签、阴影或其他装饰；
- 可直接用于二次排版、社交媒体、数字手账或贴纸打印准备。

## Two coordinated outputs

Given one source photo, this Codex skill produces:

1. A finished 3:2 collectible travel memory card.
2. A separate transparent-background `.png` sticker image containing the same six sticker motifs.

The sticker PNG is a real RGBA file with an Alpha channel, not a flattened image with a white, black, or checkerboard background.

## Usage

```text
使用 $travel-memory-card-duo 把我上传的照片做成完整旅行记忆卡，并同时输出同款六枚透明底 PNG 贴纸图。
```

## Files

- `SKILL.md` — workflow and output requirements
- `agents/openai.yaml` — Codex UI metadata
- `references/style-guide.md` — shared visual language for both images

## Installation

Copy this repository folder into your Codex skills directory, then invoke it as `$travel-memory-card-duo`.

## 案例

<img width="1536" height="1024" alt="Travel memory card example" src="https://github.com/user-attachments/assets/6bf06b40-9115-4619-b4bc-9cb2250031ee" />
<img width="1536" height="1024" alt="Transparent sticker PNG example" src="https://github.com/user-attachments/assets/2cab6521-dde5-4af7-9fec-2d5609585354" />

## License and usage restrictions

Copyright © 2026 carolinaaafy. All rights reserved.

Personal, non-commercial use is permitted. Re-uploading, mirroring, repackaging, copying for redistribution, selling, paid-service use, client projects, and other commercial exploitation are prohibited.

Source photographs, likenesses, landmarks, trademarks, and other third-party content are not licensed by this repository.

See [LICENSE.md](LICENSE.md) for the complete terms. This repository is source-available, not open source.

---
name: marketing-material-generator
description: 基于飞书多维表格的电商营销素材自动化生成工具。当用户需要为商品生成全套营销素材、产品精修图、细节特写、详情页设计、场景图、动态视频，或提到"营销素材"、"商品图"、"精修"、"详情页"、"白底图"、"场景图"、"Cinemagraph"时使用。支持从飞书Base读取产品信息，自动完成5个环节的素材生成并回写到表格。
---

# 营销素材自动生成器

基于飞书多维表格的电商营销素材流水线，一键生成从精修到动态视频的全套商品素材。

## 何时使用

- 用户提供飞书多维表格链接，要求生成营销素材
- 用户提到"精修图"、"白底图"、"产品特写"、"详情页"、"场景图"、"商品视频"
- 用户要求批量处理商品图片
- 用户说"跑一下营销素材流程"、"生成全套素材"

## 开始执行前

如果用户尚未提供已填写的模板副本链接，先暂停素材生成，并发送以下引导：

> 开始生成前，请先准备产品信息：
>
> 1. 打开[营销素材生成模板](https://bytedance.larkoffice.com/base/L6gAbtH9raeD57s8QZtcHHnsnjP?table=tblvaKMdPLeH4HmG&view=vewCai3t42)，点击右上角的「创建副本」。请勿直接编辑原模板。
> 2. 在新创建的副本中，补充需要处理的商品信息：**产品名称、产品图、产品尺寸、产品价值点**。
> 3. 填写完成后，将**副本链接**发送给我，我会从副本中读取信息并开始生成营销素材。

仅在用户发来副本链接后继续执行。不要要求用户提供原模板的编辑权限，也不要直接在原模板中写入数据。

## 表格字段约定

表格需包含以下字段（字段名可略有差异，按语义匹配）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 产品名称 | 文本 | 商品名称 |
| 产品图 | 附件 | 原始商品图 |
| 产品尺寸 | 文本 | 商品规格 |
| 产品价值点 | 文本/链接 | 产品分析报告或卖点描述 |
| 🖼️ 图像精修师 | 附件 | 输出：白底精修图 |
| 📷 产品摄影师 | 附件 | 输出：3张细节特写 |
| 🖼️ 视觉设计师 | 附件 | 输出：4张详情页图 |
| 🏗️ 场景搭建师 | 附件 | 输出：2张场景图 |
| 🎞️ 动态视觉设计师 | 附件 | 输出：1个Cinemagraph视频 |

## 工作流程

### 第一步：表格解析

1. 确认用户提供的是已填写的模板副本链接；如未提供，先按“开始执行前”的话术引导用户
2. 使用 `lark-cli base +url-resolve` 解析副本链接，获取 `base_token`、`table_id`
3. 使用 `lark-cli base +record-list` 获取记录列表
4. 定位目标行（用户指定行号/产品名，或默认第一行待处理行）
5. 下载原始产品图到本地

### 第二步：逐环节生成素材

按顺序执行以下5个环节，每个环节生成后立即上传回表格对应字段：

| 环节 | 产出数量 | 提示词参考 |
|------|----------|-----------|
| 1. 图像精修师 | 1张白底图 | [prompts.md](references/prompts.md#图像精修师) |
| 2. 产品摄影师 | 3张特写图 | [prompts.md](references/prompts.md#产品摄影师) |
| 3. 视觉设计师 | 4张详情页 | [prompts.md](references/prompts.md#视觉设计师) |
| 4. 场景搭建师 | 2张场景图 | [prompts.md](references/prompts.md#场景搭建师) |
| 5. 动态视觉设计师 | 1个视频 | [prompts.md](references/prompts.md#动态视觉设计师) |

### 第三步：回写表格

每个环节生成后，使用 `lark-cli base +record-upload-attachment` 立即上传到对应字段，不要等全部完成再批量上传。

### 第四步：视频生成确认

生成视频前必须先向用户确认参数（时长、比例、效果），用户确认后再调用 `image_to_video`。

## 关键命令参考

```bash
# 解析表格链接
lark-cli base +url-resolve --url "<url>" --as user

# 列出记录
lark-cli base +record-list --base-token <token> --table-id <tid> --as user

# 下载附件
lark-cli base +record-download-attachment \
  --base-token <token> --table-id <tid> \
  --record-id <rid> --file-token <ftoken> \
  --output ./original.png --as user

# 上传附件（可重复--file传多个）
lark-cli base +record-upload-attachment \
  --base-token <token> --table-id <tid> \
  --record-id <rid> --field-id <fid> \
  --file ./file1.png --file ./file2.png --as user
```

## 图片生成规范

- 所有图片统一使用 2048×2048 分辨率（1:1正方形）
- 模型默认使用 seedream_4.5
- 精修图和特写图必须基于上一步生成的图片URL进行参考
- 详情页和场景图必须保持色调风格统一
- 视频默认 8秒、1:1比例、seedance_2.0_fast模型

## 注意事项

1. 必须按顺序执行，后一环节依赖前一环节的产出
2. 每个环节完成后立即展示结果给用户
3. 视频环节必须先确认参数再生成
4. 如某环节生成效果不佳，可重新生成该环节，不影响其他环节
5. 处理多行记录时，逐行处理，每行完成全部5个环节后再处理下一行

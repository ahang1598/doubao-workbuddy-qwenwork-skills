---
name: lark-shortdrama-studio
description: 基于飞书多维表格的短剧创作全流程工作流。从剧本到视频的完整闭环生产，支持项目看板、剧本库、分镜库、资产库四层数据模型，资产优先保证角色一致性，按15秒/段输出视频。使用场景：短剧创作、短视频制作、动画分镜、视频内容生产、AI视频批量生成、飞书多维表格项目管理。
---

# Lark ShortDrama Studio

## Overview

基于飞书多维表格的短剧创作全流程工作流。将 Toonflow 创作方法论"飞书化"，实现从剧本到视频的完整闭环。每个项目一个独立多维表格，四层数据模型驱动，资产优先保证一致性。

## Core Architecture

四层数据模型，两两双向关联：

```
项目看板 ←→ 剧本库 ←→ 分镜库 ←→ 资产库
```

- **项目看板**：总览进度、统计数据、多项目管理
- **剧本库**：剧本管理、状态追踪、文档入口
- **分镜库**：分镜管理、视频生成任务、视频产出
- **资产库**：视觉资产管理、复用、一致性保障

详细表结构和字段设计：见 [references/base-structure.md](references/base-structure.md)

## Workflow

```
剧本输入 → 资产检查 → 资产生成 → 资产确认 → 分镜拆分 → 分镜确认 → 视频生成 → 审核交付
```

### Phase 1: 项目初始化

为每个新项目创建独立的多维表格，搭建四表结构和关联网络。

1. 新建 Base
2. 创建四张表（项目看板/剧本库/分镜库/资产库）
3. 设置表间关联
4. 删除默认表

表结构模板：见 [references/base-structure.md](references/base-structure.md)

### Phase 2: 剧本入库

读取剧本内容，录入剧本库，关联到项目。

1. 读取飞书文档/Wiki 内容
2. 录入剧本信息（名称、题材、字数、状态、文档链接）
3. 关联到项目看板
4. 更新项目统计

### Phase 3: 资产检查与生成

从剧本中提取角色/场景/道具需求，生成设定图。

**资产类型**：
- 角色：每个角色生成三视图（正面/侧面/背面）
- 场景：全景概念图
- 道具：细节设定图

**风格选项**：国风二次元（修仙/古装）、写实/现代都市（家庭/都市）

资产生成规范和提示词模板：见 [references/asset-generation.md](references/asset-generation.md)

### Phase 4: 资产确认

向用户展示资产设定图，确认后生成三视图并全部入库。

1. 展示角色/场景/道具初稿
2. 用户确认后生成侧面和背面视图
3. 所有资产记录关联到剧本和项目
4. 更新项目资产统计

### Phase 5: 分镜拆分

按场次→片段→镜头三级结构拆分。

**三级结构**：
- 场次（Scene）：完整场景段落
- 片段（Clip）：情绪/动作段落，约15秒
- 镜头（Shot）：单个镜头，3-5秒

**拆分原则**：
- 台词零删改：只设计画面，不做台词二次创作
- 缺资产不审核：资产未确认前不进入分镜审核
- 人物外观交给图片：分镜提示词不写服装/发型/长相
- 片段≤15秒：保证视频生成质量
- 长台词必须拆镜：每镜换视角/景别

详细拆分规范：见 [references/storyboard-split.md](references/storyboard-split.md)

### Phase 6: 视频生成

按片段生成视频，每段约15秒。

**生成方式**：
- 工具：image_to_video（带参考图保证一致性）
- 比例：9:16（竖屏短剧标准）
- 时长：15秒/段
- 参考图：该片段涉及的角色+场景

**为什么按片段生成**：
- 不按单个镜头：太碎，效率低
- 不按整场：太长，质量不稳定
- 15秒/段：平衡质量和效率

视频生成规范：见 [references/video-generation.md](references/video-generation.md)

### Phase 7: 审核与交付

1. 向用户展示视频片段
2. 不满意可重生成（调整提示词/参考图）
3. 全部完成后更新项目状态

## Key Principles

1. **每个项目一个独立 Base**：数据完全隔离
2. **资产优先**：先确认资产再做分镜视频，保证一致性
3. **参考图驱动**：角色+场景参考图保证视频角色不漂移
4. **状态追踪**：每个环节都有状态字段，进度可视化
5. **渐进式确认**：资产→分镜→视频，每步确认再往下走

## Commands Reference

常用命令速查（多维表格、文档、图片、视频）：见 [references/commands.md](references/commands.md)

## Best Practices

踩坑记录和最佳实践：见 [references/best-practices.md](references/best-practices.md)

## Resources

### references/
- `base-structure.md` — 多维表格四表结构和字段设计
- `asset-generation.md` — 资产生成规范和提示词模板
- `storyboard-split.md` — 分镜拆分规范
- `video-generation.md` — 视频生成规范
- `commands.md` — 常用命令速查
- `best-practices.md` — 最佳实践和注意事项

### scripts/
（暂无脚本，纯工作流 skill）

### assets/
（暂无资产文件）

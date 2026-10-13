---
name: byted-mediakit-motion-graphics
description: 为已有视频添加与内容和风格匹配的动效，包括花字、人物条、章节标题、背景介绍、产品标注和动态图解。适用于访谈、综艺、种草、产品展示和知识讲解等视频的重点强化与信息补充，自动选择出现时机和位置，合成完整视频。
---

# 视频动效制作

## 概述

面向内容创作者、剪辑与运营人员，为已有视频补充重点强调、身份与背景说明、情绪表达和动态图解，交付完整成片。

- 保留完整原片和音轨，不默认烧录字幕。
- 动效文案与原片对应片段同语言；用户指定目标语言时遵从指定。
- 根据内容与视频风格自行编写动效；同组复用代码，保证文字清晰并避开人脸、原字幕和关键细节。

## 任务边界

用于新增或修改已有视频上的辅助动效。仅做 ASR、字幕处理、普通剪辑、视频理解或从文字/图片生成视频时，使用对应能力。目标不明确时先确认是否需要添加动效；已明确目标则只补充缺少的素材。

## 核心流程

按阶段读取对应文档，不提前加载全部参考资料。`<skill>` 是本目录；`<task>` 是 Skill 外独立工作目录，最终 MP4 放在工作目录之外。

调用 MediaKit CLI 前，先加载并读取 `byted-mediakit-shared` 技能，遵循其中的 CLI 使用指南；当前会话已读取时复用。

每次执行 MediaKit CLI 命令时，按当前 shell 语法在命令前设置环境变量 `DOUBAO_MEDIAKIT_RUNTIME=scene-motion-graphics`，与共享技能要求的环境变量一并传入，包括任务提交和任务查询。

1. **准备环境**：首次运行本地工程脚本前检查，已有合格环境直接复用：Node.js ≥22.12.0、FFmpeg、FFprobe、本地字体及 Chromium。


   - 依赖缺失时，用选定 Node.js 配套的 npm 执行 `npm install --prefix <skill>`；各脚本及子进程使用同一 Node.js，PATH 中可找到 FFmpeg、FFprobe。
   - 优先复用现有浏览器；缺少时运行 `node <skill>/node_modules/hyperframes/bin/hyperframes.mjs browser ensure`。取得可执行文件路径，测量服务、单次测量、可选诊断和渲染均通过 `--browser "<路径>"` 指定。
   - 安装工具遵循宿主权限和用户授权；便携工具放在宿主可写工具目录或任务目录，不擅自替换系统 Node.js 或修改全局 PATH。

2. **理解视频**：按 [输入理解](references/input-understanding.md) 获取原片基本信息，默认执行 ASR 并分析内容；足够选点即进入规划，仅无语音或有具体画面疑问时补充画面理解。
3. **全片规划**：按 [规划](references/planning.md) 选节点、看候选时段源帧、确定风格与分组，建立 `plan.json` 和 `frames.json`。
4. **设计与实现**：由主 Agent 按 [动效编写](references/motion-authoring.md) 分组实现，每条完成即测量、修正；全任务复用一个浏览器和一个测量页面。
5. **检查与导出**：按 [执行与交付](references/verification.md) 做必要检查、局部渲染与合成；渲染默认两个并发，修复后复用未变化素材。
6. **交付**：返回最终 MP4 链接；不自动清理过程文件。

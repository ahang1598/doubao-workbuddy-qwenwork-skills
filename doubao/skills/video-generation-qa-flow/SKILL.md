---
name: video-generation-qa-flow
description: "用于 doubao-creative-video、doubao-creative-drama 或 seedance-25 已确定视频生成方案后，需要做生成前素材/参数/安全检查、失败分流和生成后验片的场景。不作为视频创作或工具调用的独立入口。"
---

# AI 视频生成质控

## 概述
这是现有视频 Skill 的 QA 扩展。所有模型、时长、比例、参考素材数量和权限限制必须从当前 Skill/Tool schema 或实际回执读取，不在本 Skill 固化。

## 使用场景
### 应使用
- 视频 brief 已确认，准备调用生成工具。
- 生成失败，需要按实际回执区分内容、权限、素材或服务问题。
- 生成成功后需要检查时长、比例、音轨、字幕和主体一致性。

### 不应使用
- 从零策划视频或写剧情/脚本。
- 已有视频的剪辑、字幕或增强。
- 图片生成或音频生成任务。

## 核心流程
### 1. 从基础 Skill 获取方案
必须先由 creative-video/drama/seedance-25 确定模式和当前工具参数。

### 2. 生成前检查
核对素材可访问性、参数 schema、用户明确时长/比例、参考素材映射、内容安全和降级影响。

### 3. 失败分流
只依据工具回执分类；硬拒停止同类重试，权限问题请用户选择，素材 URL 问题只修链路。

### 4. 生成后验片
用返回字段及 byted-mediakit-video/artifact-preview 检查时长、分辨率、音轨、字幕、主体数量和关键细节。

### 5. 交付
只有实际生成并验片后才说明完成；文件使用 present_files 或基础视频 Skill 的交付方式。

## 工具与协作
- **REQUIRED BASE SKILL:** doubao-creative-video、doubao-creative-drama 或 seedance-25 之一。
- 验片使用 byted-mediakit-video / artifact-preview；不得引用 audio_to_audio 或 NotifyHuman。

## 安全边界
- 只陈述已读取、已执行或有来源支持的结果；未验证项必须明确标注。
- 涉及删除、覆盖、发布、系统设置、生产数据或不可逆操作时，先展示目标、影响、回滚方式并取得明确确认。
- 不得记录或输出密钥、Cookie、访问令牌、身份证号、银行卡号等敏感信息；示例使用脱敏占位符。
- 不猜测平台审核规则，不绕过内容安全；真人音色、品牌/IP 和敏感身份需确认授权。

## 输出与验收
- 生成前检查单
- 实际工具/参数快照
- 失败分类或视频 URL
- 验片证据和未满足项

## 冒烟用例
### Should trigger
- 视频方案已确认，生成前帮我检查素材和参数
- 视频生成成功后检查时长、音轨和产品细节

### Should not trigger
- 帮我从零策划一个短剧
- 把已有视频剪掉前 5 秒

### 边界输入
- 工具 schema 与旧文档参数不同，必须以当前 schema 为准

## 参考文件
- `references/failure-receipts.md`

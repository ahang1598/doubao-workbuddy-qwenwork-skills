---
name: mglc-video
description: 灵创视频生成技能 - 根据提示词生成视频、图生视频、视频状态查询
version: "1.0.0"
author: "灵创 AI"
---

# 灵创视频生成 Skill

本 Skill 提供 AI 视频生成能力，支持文生视频、图生视频和多种生成模式。

## 可用命令

### video generate - 生成视频

根据提示词和参考素材生成视频。

**命令**：
```bash
# 文生视频
mglc video generate --prompt "视频描述" --duration 5

# 指定模型
mglc video generate --model-id <model_id> --prompt "视频描述" --duration 5

# 指定比例和分辨率
mglc video generate --prompt "视频描述" --duration 5 --aspect-ratio 16:9 --resolution 1080p

# 图生视频（图片转视频）
mglc video generate --prompt "视频描述" --image /path/to/image.jpg --duration 5

# 首尾帧视频
mglc video generate --prompt "视频描述" --first-image /path/to/first.jpg --last-image /path/to/last.jpg --duration 5

# 开启网络搜索增强
mglc video generate --prompt "产品介绍视频" --duration 5 --web-search
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --prompt | string | ✓ | 视频描述词 |
| --duration | int | ✓ | 视频时长（秒） |
| --model-id | int64 | - | 视频模型 ID |
| --type | string | - | 生成模式 |
| --image | string[] | - | 参考图片（COS 路径或本地文件），可重复指定多张 |
| --first-image | string | - | 首帧图片路径 |
| --last-image | string | - | 尾帧图片路径 |
| --video | string[] | - | 参考视频（COS 路径或本地文件），可重复指定多个 |
| --audio | string[] | - | 参考音频（COS 路径或本地文件），可重复指定多个 |
| --asset-id | int64[] | - | 参考图片逻辑资产 ID，可重复指定多个 |
| --video-asset-id | int64[] | - | 参考视频逻辑资产 ID，可重复指定多个 |
| --audio-asset-id | int64[] | - | 参考音频逻辑资产 ID，可重复指定多个 |
| --aspect-ratio | string | - | 视频比例 |
| --resolution | string | - | 视频分辨率 |
| --num | int | - | 生成数量，默认1 |
| --auto-bgm | bool | - | 自动添加 BGM |
| --web-search | bool | - | 开启网络搜索增强 |
| --keep-original-sound | bool | - | 保留参考音频 |
| --session-id | int64 | - | 项目生成会话 ID |

**生成模式 type 说明**：
- `text2video`：纯文本生成视频
- `firstFrame`：首帧图片引导生成
- `lastFrame`：尾帧图片引导生成
- `firstLastFrame`：首尾帧约束生成
- `subjectRef`：(角色/场景/道具)设定参考生成
- `videoRef`：视频参考生成
- `allMediaRef`：全媒体参考生成
- `videoEdit`：视频编辑
- `videoExtend`：视频扩展

## 使用建议

1. **先查模型**：使用 `mglc model list --type video` 查看可用视频模型
2. **时长**：建议 5-10 秒，更短的时长生成质量更好
3. **Prompt**：详细描述视频内容、动作、镜头运动
4. **图生视频**：使用高质量参考图效果更好
5. **进度查询**：视频生成是异步的，用 `video status` 查询结果

## 注意事项
- seedance系列视频模型可配合virtual-ip技能创作真实IP视频
- 当使用SD 合规素材库时，SD 合规素材库逻辑资产ID和资产路径必须一一对应，可通过SD 合规素材库详情获取每个SD 合规素材库对应的资产路径和ID，此时不可用本地文件
- 不同视频有不同的生成参数和参数范围，在生成前先查看模型能力，避免参数错误

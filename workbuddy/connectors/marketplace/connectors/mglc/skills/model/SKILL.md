---
name: mglc-model
description: 灵创模型管理技能 - 查看可用模型列表和模型能力参数
version: "1.0.0"
author: "灵创 AI"
---

# 灵创模型管理 Skill

本 Skill 提供灵创平台模型管理能力，可查询可用的图片和视频模型。

## 可用命令

### model list - 列出模型

列出当前可用的图片、视频模型。

**命令**：
```bash
# 列出所有模型
mglc model list

# 列出图片模型
mglc model list --type image

# 列出视频模型
mglc model list --type video
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --type | string | - | 按模型类型筛选：image / video |
| --page | int | - | 页码，默认 1 |
| --page-size | int | - | 每页数量，默认 20 |

**使用示例**：
- 查看所有可用的 AI 绘图模型
- 查看所有可用的 AI 视频生成模型
- 分页浏览大量模型

### model - 查看模型能力

查看指定模型支持的参数能力。

**命令**：
```bash
# 查看图片模型能力
mglc model --type image --model-id <model_id>

# 查看视频模型能力
mglc model --type video --model-id <model_id>
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --type | string | ✓ | 模型类型：image / video |
| --model-id | int64 | ✓ | 模型 ID |

**使用示例**：
- 查看某个图片模型支持的分辨率和比例
- 查看视频模型支持的生成模式
- 获取模型的详细参数配置用于生成任务

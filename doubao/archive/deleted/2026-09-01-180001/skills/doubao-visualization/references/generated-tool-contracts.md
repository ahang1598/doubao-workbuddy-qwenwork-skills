# Tool Contracts

## 目录

- [image_gen](#image_gen)
- [general_search](#general_search)
- [image_search](#image_search)
- [错误处理](#错误处理)

## image_gen

用于生成 1 到 6 张图片。

```json
{
  "request_list": [
    {
      "prompt": "完整中文生图 Prompt",
      "width": 2048,
      "height": 1536
    }
  ],
  "model_version": "<当前工具 schema 支持且业务要求的模型版本，可选>"
}
```

规则：

- `request_list` 必填，支持 1 到 6 项；
- 每项提供 `prompt`、`width`、`height`；
- Prompt 使用中文；
- 图片中的可见文字使用中文引号 `“”` 标注；
- 多图可以一次提交，每项允许使用不同宽高；
- 调用前读取当前工具 schema；只有当字段存在且业务环境要求固定模型时，才显式传入 `model_version`。不得因旧版本文档曾支持该字段，就向当前工具强行提交未知参数；
- 部分失败时只重试失败项。

### 强制参数检查

正确：

```json
{
  "request_list": [
    {"prompt": "横向格局图", "width": 2048, "height": 1536},
    {"prompt": "横向时间线", "width": 2048, "height": 1152},
    {"prompt": "方形关系图", "width": 2048, "height": 2048}
  ],
  "model_version": "<可选：当前工具明确支持的业务指定版本>"
}
```

错误：

```json
{
  "request_list": [
    {"prompt": "图片", "width": 768, "height": 1024}
  ]
}
```

错误原因：未根据信息关系规划尺寸；若当前业务明确要求指定模型且 schema 支持，也需补充正确的顶层 `model_version`。

### 尺寸建议

- `2048 × 2048`：中心机制、关系网络、循环；
- `2048 × 1536`：对比、三方格局、横向结构；
- `2048 × 1152`：时间线、长流程、宽系统；
- `1536 × 2048`：步骤教程、纵向层级；
- `1152 × 2048`：仅用于明确的手机竖屏内容。

## general_search

用于核验事实、年份、数据、事件顺序和背景资料。

```json
{
  "query": "搜索关键词",
  "snippet": {
    "mode": "full",
    "max_length": 300
  }
}
```

字段：

- `query`：搜索关键词；
- `snippet.mode`：`minimum` 或 `full`；
- `snippet.max_length`：片段最大 token 数。

规则：

- 多方面问题拆成多个 query，一轮不超过 3 个；
- 不重复搜索相同信息；
- 只提炼与图片直接相关的事实；
- 不把搜索结果全文直接放入 Prompt。

## image_search

用于搜索真实存在的实体图片。

```json
{
  "query": "实体名称",
  "thumbnail_size": "large",
  "image_short_edge_px": {
    "min": 640
  },
  "image_aspect_ratio": {
    "min": 0.7,
    "max": 1.5
  },
  "limit": 3
}
```

规则：

- 只搜索动植物、人物、商品、器物、建筑、地标、影视角色等具体实体；
- 多实体拆开搜索；
- 不用于抽象概念、流程图、数据图表和 UI 设计图；
- 用户需要真实图时直接使用搜索结果；
- 校准生图时只提炼可观察的外形特征，不把图片 URL 传给 `image_gen`。

## 错误处理

- 搜索无结果：改写为更具体的关键词；
- 搜索结果不可靠：不要用于事实约束；
- 生图文字乱码：减少可见文字并缩短句子；
- 生图部分失败：只重试失败图片；
- 工具不可用或无权限：不得绕过官方工具或猜测底层 API。

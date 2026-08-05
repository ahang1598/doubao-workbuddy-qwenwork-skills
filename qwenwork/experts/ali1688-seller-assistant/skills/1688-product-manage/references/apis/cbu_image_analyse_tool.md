# 图片内容解析（电商内容解析）

**接口路径**: `POST /api/cbu_image_analyse_tool/1.0.0`  
**用途**: 对商品主图进行电商内容解析，提取文字区域摘要、可见卖点、构图摘要等信息。支持提交+轮询模式。

## 请求参数

### 提交任务

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| type | string | 是 | 固定值 `"ecommerce_content_parsing"` |
| imageUrlList | string[] | 是 | 待解析的图片 URL 列表（通常单张提交） |

### 轮询结果

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| taskId | string | 是 | 提交任务时返回的任务 ID |

## 响应结构

### 提交任务响应

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| taskId | string | 异步任务 ID，用于后续轮询 |

### 轮询结果响应

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| text_region_summary | string | 图片中的文字区域摘要 |
| selling_points_visible | string[] | 图片中可见的卖点列表 |
| composition_summary | string | 图片构图摘要 |

## 示例

### 提交任务请求

```json
{
  "type": "ecommerce_content_parsing",
  "imageUrlList": ["https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg"]
}
```

### 提交任务响应

```json
{
  "success": true,
  "taskId": "task_20240101_abc123"
}
```

### 轮询请求

```json
{
  "taskId": "task_20240101_abc123"
}
```

### 轮询响应（成功）

```json
{
  "success": true,
  "text_region_summary": "2024新款 真皮手提包",
  "selling_points_visible": ["尖头设计", "珍珠装饰", "真皮材质"],
  "composition_summary": "产品居中摆放，白色背景，45度侧拍角度"
}
```

## 补充说明

- **工作模式**：提交+轮询（异步），同一接口路径，通过参数区分提交与轮询
- **轮询参数**：间隔 3 秒，超时 30 秒
- **轮询逻辑**：提交后获得 `taskId`，随后每隔 3 秒用 `{"taskId":"..."}` 请求同一接口，直到返回解析字段或超时
- **完成判断**：当响应中 `text_region_summary`、`selling_points_visible`、`composition_summary` 任一字段非空时，视为解析完成
- **响应数据可能嵌套在 `data` 字段中**（兼容格式：`resp.data.taskId`、`resp.data.text_region_summary` 等）
- **单图解析**：虽然 `imageUrlList` 为数组，实际使用中通常逐张提交解析

## CLI 阶段命令

**所属阶段**：prepare（回合①）

作为 prepare 阶段的第二步，在商品信息查询后自动调用，对每张主图并发解析卖点与构图。

**CLI 命令**：与商品查询共用同一 prepare 命令：
```bash
python3 cli.py ai_image_improve --offer_id <商品ID>
```

**并发控制**：解析使用线程池，并发上限 5。

**Agent 输出**：解析结果合并到 prepare 的「默认 prompt 表」和「解析参考表」中，详见 [cbu_offer_query_tool § CLI 阶段命令](./cbu_offer_query_tool.md)。

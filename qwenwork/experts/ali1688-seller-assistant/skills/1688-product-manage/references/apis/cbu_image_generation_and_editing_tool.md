# 图片生成（图生图）

**接口路径**: `POST /api/cbu_image_generation_and_editing_tool/1.0.0`  
**用途**: 基于原商品主图进行 AI 图片生成（图生图），生成优化后的电商主图。支持提交+轮询模式。

## 请求参数

### 提交任务

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| type | string | 是 | 固定值 `"image_to_image"` |
| imageId | string | 是 | 主图序号，从 `"1"` 起按主图位次递增 |
| imageUrlList | string[] | 是 | 原图 URL 列表（通常为单张原图） |
| prompt | string | 是 | 图片生成提示词，由 CLI 在 generate 阶段基于白名单字段（`size` / `background` / `text_selling_points`）自动拼装，Agent 无权直接编辑 |
| size | string | 是 | 生成图片比例，仅支持 `"1:1"` 或 `"3:4"` |
| params | object | 是 | 扩展参数，当前为空对象 `{}` |

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
| gen_image_urls | string[] | 生成的图片 URL 列表 |
| image_id | string | 对应的主图序号 |

## 示例

### 提交任务请求

```json
{
  "type": "image_to_image",
  "imageId": "1",
  "imageUrlList": ["https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg"],
  "prompt": "做一张1688商品电商的主图,1:1比例，突出\"双头设计\"和\"油性不晕染\"的文字卖点,背景换成米白色大理石台面搭配暖色自然光",
  "size": "1:1",
  "params": {}
}
```

### 提交任务响应

```json
{
  "success": true,
  "taskId": "gen_task_20240101_xyz789"
}
```

### 轮询请求

```json
{
  "taskId": "gen_task_20240101_xyz789"
}
```

### 轮询响应（成功）

```json
{
  "success": true,
  "image_id": "1",
  "gen_image_urls": [
    "https://ai-generated.example.com/result/img_001.jpg"
  ]
}
```

## 补充说明

- **工作模式**：提交+轮询（异步），同一接口路径，通过参数区分提交与轮询
- **轮询参数**：间隔 4 秒，超时 120 秒
- **轮询逻辑**：提交后获得 `taskId`，随后每隔 4 秒用 `{"taskId":"..."}` 请求同一接口，直到返回 `gen_image_urls` 或超时
- **完成判断**：当响应中 `gen_image_urls` 为非空数组时，视为生成完成
- **imageId 规则**：从 `"1"` 起按商品主图位次递增（第 1 张主图为 `"1"`，第 2 张为 `"2"`，以此类推）
- **size 约束**：仅支持 `"1:1"` 和 `"3:4"` 两种比例，其他值将被拒绝
- **prompt 拼装规则**（由 CLI 在 generate 阶段基于白名单字段自动拼装，Agent 无权直接编辑 prompt）：
  - **仅比例**：`做一张1688商品电商的主图,{size}比例`
  - **比例+场景**：`做一张1688商品电商的主图,{size}比例，背景换成{background}`
  - **比例+文字卖点**：`做一张1688商品电商的主图,{size}比例，突出{text_selling_points}的文字卖点`
  - **比例+文字卖点+场景**：`做一张1688商品电商的主图,{size}比例，突出{text_selling_points}的文字卖点,背景换成{background}`
  - `background` 由 Agent 通过 customize 阶段注入；`text_selling_points` 由商家手填

  > ⚠️ `text_selling_points` 是商家手填的文字卖点原文（如 `"双头设计"和"油性不晕染"`），**不是图像解析卖点**；默认为空，Agent 不得从解析结果中推断填充。
- **prompt 中的背景描述**：要求具象化的电商主图场景（如"米白色大理石台面 + 暖色侧光"），禁止使用空泛描述（如"合适的背景"）
- **响应数据可能嵌套在 `data` 字段中**（兼容格式：`resp.data.taskId`、`resp.data.gen_image_urls` 等）


## CLI 阶段命令

### customize（回合②）

prepare 后**必须立即** customize（不得停顿）。Agent 基于解析参考为每张图推荐具象场景，通过 customize 注入 background。

**CLI 命令**：
```bash
python3 cli.py ai_image_improve --offer_id <X> --customize '<JSON>'
# customize 后 Agent 必须停下等商家确认，严禁自行 generate
```

**参数说明**：

- `--customize <JSON>`：仅接受白名单字段 `size` / `background` / `text_selling_points`（详见下表）。**严禁**提交 `prompt` / `selling_points` 字段，提交后 CLI 报错 `INVALID_PARAM`。


#### customize JSON 格式

> 核心用法：Agent 基于每张图解析结果推荐 `background` 后注入。

- **逐图型（推荐）** — key 为 prepare 返回的序号：
  ```json
  {
    "1": {"size":"1:1","background":"米白色大理石台面 + 暖色侧光"},
    "2": {"size":"1:1","background":"原木桌面 + 浅灰背景"},
    "3": {"size":"3:4","background":"纯白柔光摄影棚"}
  }
  ```
- **统一型**（仅当多张图场景明显一致时使用）：
  ```json
  {"size":"1:1","background":"米白色大理石台面 + 暖色自然光"}
  ```
- ❌ **已废弃** — 完全自定义 prompt（不再支持，提交后 CLI 报错 `INVALID_PARAM`）：
  ```json
  {"1":{"prompt":"做一张1688商品电商的主图,1:1比例,突出 V领设计、蕾丝拼接，背景换成米白色大理石台面 + 暖色自然光"}}
  ```
- **含文字卖点（商家手填）**：
  ```json
  {"1":{"size":"1:1","background":"米白色大理石台面 + 暖色侧光","text_selling_points":"\"双头设计\"和\"油性不晕染\""}}
  ```

**合并规则**：
- ⛔ **提供 `prompt` 字段** → 报错 `INVALID_PARAM`；Agent 无权直接编辑提示词
- ⛔ **提供 `selling_points`** → 报错 `INVALID_PARAM`；该字段已禁用
- ✅ **仅提供 `size` / `background` / `text_selling_points`** → 按默认规则重新组装
  - `size` 仅允许 `1:1` 或 `3:4`，其他值报错
  - `background` 由 Agent 基于解析结果推荐，要求具象的电商主图场景描述
  - `text_selling_points` 默认空，仅可由商家主动填写，Agent 不得推断填充

**场景推荐示例**（具象、可视化）：
- 服饰类：浅灰墙面 + 暖色侧光 / 米白色大理石台 + 自然光
- 包袋类：原木桌面 + 浅灰背景 / 米白色亚麻布 + 柔和光线
- 编织/家居：木质台面 + 绿植点缀 / 纯白摄影棚柔光

禁用空泛描述：「合适的背景」「自然的背景」一类一律不可。

**Agent 输出要求**：「最终 prompt 表」必须含「最终 prompt（完整句子）」独立列——逐字展示每张图最终发送给图生图接口的完整 prompt（比例 + 卖点 + 背景三者拼接后的原句），不得仅展示推荐场景摘要或几个关键词。

### generate（回合④）

**CLI 命令**：
```bash
python3 cli.py ai_image_improve --offer_id <X> --generate
```

**轮询参数**：间隔 4s，超时 120s。

**Agent 输出要求**：
1. 「生成结果表」：列为 `序号 / 原图(![](url)) / 优化后图片(![](url))`
2. 三选项：1=全部应用 / 2=部分应用（请告知序号）/ 3=不应用

**并发控制**：生成使用线程池，并发上限 5。

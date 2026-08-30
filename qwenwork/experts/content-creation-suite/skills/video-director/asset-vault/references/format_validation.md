# 格式校验规范

> 本文件定义 Brief 解析报告的强校验字段规范。
> 在步骤 1（Brief 拆解）时参考，确保输出格式标准化。

---

## 必填字段（metadata.json）

以下字段在创建 metadata.json 时必须填写，无值时填空字符串或 null：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| status | string | 项目状态，枚举：`in_progress` / `delivered` / `completed` / `interrupted` / `abandoned` | "in_progress" |
| date | string | 日期 YYYY-MM-DD | "2026-05-18" |
| industry | string | 行业 | "科技" |
| platform | string | 平台 | "抖音" |

## 条件必填字段

以下字段在信息可识别时填写：

| 字段 | 类型 | 何时填写 |
|------|------|---------|
| client | string | Brief 中明确了客户名 |
| category | string | 能从产品描述推断品类 |
| content_goal | string | 能从 Brief 推断内容目标 |
| brief_summary.original_selling_points | array | Brief 中有客户卖点表述 |

## 格式规范

### 日期格式
- 统一使用 `YYYY-MM-DD`，如 `2026-05-18`

### 行业命名
- 使用简短中文名，如：科技、教育、快消、美妆、医疗、金融、餐饮、房产
- 不要用过于细分的名称作为行业（细分用 category 字段）

### 平台命名
- 使用官方简称：抖音、小红书、B站、视频号、快手
- 不要用别名（如"dy"、"xhs"）

### 文件名规范
- 项目目录：`{YYYYMMDD}_{客户名}_{项目简称}`
- step 文件：`step_{NN}_{步骤名}.md`（NN 为两位数字，如 01、02）
- 汇总文件：使用中文命名，简短明确（如"产品测评型.md"、"数据对比型.md"）

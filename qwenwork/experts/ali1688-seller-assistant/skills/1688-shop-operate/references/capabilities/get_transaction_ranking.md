```markdown
# 行业交易排名数据查询指南

## 功能说明

通过 CLI 查询店铺在所属行业中的交易排名、排名百分位及 TOP 标杆数据。

## 前置条件

- 已配置 AK（未配置时会提示运行 `cli.py configure YOUR_AK`）

## CLI 调用

```bash
python3 {baseDir}/cli.py get_transaction_ranking [--date_type <DATE_TYPE>]
```

### 参数说明

| 参数 | 缩写 | 是否必填 | 默认值 | 说明 |
|------|------|----------|--------|------|
| `--date_type` | `-d` | ❌ 否 | `RECENT_7` | 日期类型：`RECENT_7`（近7天）、`RECENT_30`（近30天）。**⚠️ 不支持 `RECENT_1`** |

### 调用示例

```bash
# 默认查询近7天全部设备
python3 {baseDir}/cli.py get_transaction_ranking

# 查询近30天数据
python3 {baseDir}/cli.py get_transaction_ranking -d RECENT_30
```

## 返回数据说明

| 返回字段 | 含义 | 用途 |
|---------|------|------|
| `industry_name` | 所属行业名称 | 行业定位 |
| `my_pay_amount` | 本店支付金额 | 行业排名依据 |
| `industry_rank` | 行业排名 | 行业地位评估 |
| `industry_total` | 行业店铺总数 | 排名百分位计算 |
| `rank_percentile` | 排名百分位（如 0.25 表示前25%） | 行业相对位置 |
| `benchmark` | TOP 标杆数据 | 与标杆差距对比 |

### benchmark 字段结构

| 子字段 | 含义 |
|--------|------|
| `top3_avg` | 行业 TOP3 平均支付金额 |
| `top10_avg` | 行业 TOP10 平均支付金额 |
| `top100_avg` | 行业 TOP100 平均支付金额 |

## 输出格式

### 成功

```json
{
  "success": true,
  "message": "行业交易排名查询成功",
  "data": { "data": { ... } }
}
```

### 失败

```json
{
  "success": false,
  "message": "错误描述信息"
}
```

## 异常处理

| 场景 | Agent 应对 |
|------|-----------|
| AK 未配置 | 引导用户执行 `cli.py configure YOUR_AK` 配置 AK |
| 使用了 RECENT_1 | 提示用户此命令仅支持 RECENT_7 和 RECENT_30 |
| 返回数据为空或不含 industry_name | 跳过行业定位分析，不报错 |
| 接口返回格式异常 | 提示"格式异常，请稍后重试" |
| 其他运行时异常 | 原样输出错误信息 |

通用 HTTP 异常（400/401/429/500）处理见 `references/common/error-handling.md`。
```

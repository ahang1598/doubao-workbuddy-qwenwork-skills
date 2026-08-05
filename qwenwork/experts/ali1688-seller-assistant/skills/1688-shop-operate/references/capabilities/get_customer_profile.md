```markdown
# 客户画像数据查询指南

## 功能说明

通过 CLI 查询店铺客户画像数据，包括支付买家数、L会员买家数、客户数与同行优秀对比、回头率、新老客 GMV 构成、客单价等。

## 前置条件

- 已配置 AK（未配置时会提示运行 `cli.py configure YOUR_AK`）

## CLI 调用

```bash
python3 {baseDir}/cli.py get_customer_profile [--date_type <DATE_TYPE>]
```

### 参数说明

| 参数 | 缩写 | 是否必填 | 默认值 | 说明 |
|------|------|----------|--------|------|
| `--date_type` | `-d` | ❌ 否 | `RECENT_7` | 日期类型：`RECENT_1`（近1天）、`RECENT_7`（近7天）、`RECENT_30`（近30天） |

### 调用示例

```bash
# 默认查询近7天数据
python3 {baseDir}/cli.py get_customer_profile

# 查询近30天数据
python3 {baseDir}/cli.py get_customer_profile -d RECENT_30
```

## 返回数据说明

### customer — 客户画像数据

| 数据项 | 说明 |
|--------|------|
| 支付买家数 vs 同行优秀 | 本店支付买家数与同行优秀水平对比 |
| L会员买家数 vs 同行优秀 | 本店L会员买家数与同行优秀水平对比 |
| 客户数 vs 同行优秀 | 本店客户数与同行优秀水平对比 |
| 买家回头率 | 老客复购比例 |
| 新老客 GMV 构成 | 新客与老客的支付金额占比 |
| 客单价 | 平均每笔订单金额 |

## 输出格式

### 成功

```json
{
  "success": true,
  "message": "客户画像查询成功",
  "data": { "data": { "customer": { ... } } }
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
| 参数值非法 | 提示用户使用合法的 date_type 值 |
| 接口返回格式异常 | 提示"格式异常，请稍后重试" |
| 其他运行时异常 | 原样输出错误信息 |

通用 HTTP 异常（400/401/429/500）处理见 `references/common/error-handling.md`。
```

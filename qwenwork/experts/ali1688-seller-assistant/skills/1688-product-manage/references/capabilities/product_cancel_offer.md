# 商品下架指南

## 功能说明

调用 1688 网关接口 `POST /api/product_cancel_offer/1.0.0` 下架指定商品。

## 前置条件

- 已配置 AK（未配置时执行 `cli.py get_ak` 自动获取）

## CLI 调用

```bash
python3 {baseDir}/cli.py product_cancel_offer --offerId "商品offerId"
```

### 参数说明

| 参数 | 缩写 | 必填 | 说明 |
|------|------|------|------|
| `--offerId` | `-o` | 是 | 要下架的商品 offerId |

> userId 由系统自动从 AK 中提取并注入请求体，无需手动传入。

### 调用示例

```bash
python3 {baseDir}/cli.py product_cancel_offer --offerId "1044666562188"
```

## 输出格式

### 成功

```json
{
  "success": true,
  "markdown": "✅ 商品 `1044666562188` 下架成功",
  "data": { "data": {} }
}
```

### 失败

```json
{
  "success": false,
  "markdown": "错误描述信息"
}
```

## Agent 处理流程

1. 从用户消息中提取商品 offerId
2. 执行 `python3 {baseDir}/cli.py product_cancel_offer --offerId <offerId>`
3. 检查输出：success=true → 告知"商品已下架成功"；success=false → 输出错误信息

## 批量下架

逐个调用并分别校验每个响应，避免静默失败：

1. 逐个执行 `product_cancel_offer --offerId <id>`
2. 每次检查 success 字段
3. 汇总成功/失败结果反馈给用户

## 异常处理

| 场景 | Agent 应对 |
|------|-----------|
| AK 未配置 | 执行 `python3 cli.py get_ak` 自动获取 AK |
| offerId 缺失 | 提示用户提供要下架的商品 offerId |
| 其他异常 | 原样输出错误信息 |

通用 HTTP 异常（400/401/429/500）处理见 SKILL.md 异常处理章节。

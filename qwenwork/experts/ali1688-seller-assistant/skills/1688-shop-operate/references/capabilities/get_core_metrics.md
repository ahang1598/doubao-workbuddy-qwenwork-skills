```markdown
# 店铺核心指标同行对比及趋势数据查询指南

## 功能说明

通过 CLI 查询店铺 7 项核心经营指标的本店值、同行同层平均值、评级，以及各指标的趋势对比数据。

## 前置条件

- 已配置 AK（未配置时会提示运行 `cli.py configure YOUR_AK`）

## CLI 调用

```bash
python3 {baseDir}/cli.py get_core_metrics [--date_type <DATE_TYPE>]
```

### 参数说明

| 参数 | 缩写 | 是否必填 | 默认值 | 说明 |
|------|------|----------|--------|------|
| `--date_type` | `-d` | ❌ 否 | `RECENT_7` | 日期类型：`RECENT_1`（近1天）、`RECENT_7`（近7天）、`RECENT_30`（近30天） |

### 调用示例

```bash
# 默认查询近7天数据
python3 {baseDir}/cli.py get_core_metrics

# 查询近30天数据
python3 {baseDir}/cli.py get_core_metrics -d RECENT_30
```

## 返回数据说明

### core_metrics — 7 项核心指标

| metric_code | 指标名 |
|-------------|--------|
| `impression` | 展现次数 |
| `visitor` | 访客数 |
| `page_view` | 浏览量 |
| `click_cvr` | 点击转化率 |
| `pay_cvr` | 支付转化率 |
| `buyer_count` | 支付买家数 |
| `pay_amount` | 支付金额 |

每项指标包含：本店值、同行同层平均、评级（优秀/持平/略低/极低）。

### rating 评级含义

| 评级 | 含义 | ratio_to_peer 参考范围 |
|------|------|----------------------|
| 优秀 | 高于同行同层平均 | >= 1.1 |
| 持平 | 接近同行同层平均 | 0.9 - 1.1 |
| 略低 | 低于同行同层平均 | 0.5 - 0.9 |
| 极低 | 远低于同行同层平均 | < 0.5 |

### trend — 趋势对比数据

| 子字段 | 含义 | 计算基准 |
|--------|------|---------|
| `year_on_year` | 年同比 | RECENT_1: 今天 vs 去年同一天；RECENT_7: 本周 vs 去年同一周；RECENT_30: 本月 vs 去年同一月 |
| `week_on_week` | 周期环比 | RECENT_1: 今天 vs 昨天；RECENT_7: 本周 vs 上周；RECENT_30: 本月 vs 上月 |
| `vs_peer_avg` | 较同行平均的变化率 | 本店变化率 vs 同行平均变化率 |
| `vs_peer_good` | 较同行优秀的变化率 | 本店变化率 vs 同行优秀变化率 |

> ⚠️ trend 数据仅覆盖：impression、visitor、page_view、click_cvr、buyer_count、ad_impression。**缺失** pay_cvr 和 pay_amount 的趋势数据。

## 输出格式

### 成功

```json
{
  "success": true,
  "message": "核心指标查询成功",
  "data": { "data": { "core_metrics": [...], "trend": [...] } }
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

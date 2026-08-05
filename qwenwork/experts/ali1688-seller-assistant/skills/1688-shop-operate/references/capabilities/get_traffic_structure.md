```markdown
# 店铺流量结构数据查询指南

## 功能说明

通过 CLI 查询店铺流量来源排行、新老访客比、PC/无线占比、跳失率、入店搜索词等流量结构数据。

## 前置条件

- 已配置 AK（未配置时会提示运行 `cli.py configure YOUR_AK`）

## CLI 调用

```bash
python3 {baseDir}/cli.py get_traffic_structure [--date_type <DATE_TYPE>]
```

### 参数说明

| 参数 | 缩写 | 是否必填 | 默认值 | 说明 |
|------|------|----------|--------|------|
| `--date_type` | `-d` | ❌ 否 | `RECENT_7` | 日期类型：`RECENT_1`（近1天）、`RECENT_7`（近7天）、`RECENT_30`（近30天） |

### 调用示例

```bash
# 默认查询近7天数据
python3 {baseDir}/cli.py get_traffic_structure

# 查询近1天数据
python3 {baseDir}/cli.py get_traffic_structure -d RECENT_1
```

## 返回数据说明

### traffic — 流量结构数据

| 数据项 | 说明 |
|--------|------|
| 流量来源排行 | 各渠道来源的访客数和占比 |
| 新老访客比 | 新访客与老访客的比例 |
| PC/无线占比 | PC 端与无线端的流量分布 |
| 跳失率 | 仅浏览一页即离开的访客比例 |
| 入店搜索词 | 用户通过搜索进入店铺的关键词 |

## 输出格式

### 成功

```json
{
  "success": true,
  "message": "流量结构查询成功",
  "data": { "data": { "traffic": { ... } } }
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

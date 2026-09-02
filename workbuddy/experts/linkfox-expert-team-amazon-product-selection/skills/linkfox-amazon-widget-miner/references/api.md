# Amazon Widget 卡片挖掘 API

- **端点**：`GET https://www.{domain}/suggestions`（Amazon 公开自动补全 API）
- **无需登录/鉴权**

## 参数表

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--seed` | str | 是 | - | 种子词 |
| `--depth` | int | 否 | 2 | 递归深度（1=只扫描, 2=+标签二次扩展, 3=+三轮嵌套） |
| `--max-labels` | int | 否 | 15 | 每轮最多取多少个 Widget 标签做扩展 |
| `--market` | str | 否 | US | 站点简码 |
| `--delay` | float | 否 | 0.5 | 请求间隔基数（秒） |
| `--verbose` | flag | 否 | false | 详细输出 |
| `--xlsx` | str | 否 | - | Excel 输出路径 |
| `--output` | str | 否 | - | JSON 输出路径 |

## WidgetSuggestion 响应结构

```json
{
  "suggType": "WidgetSuggestion",
  "type": "WIDGET",
  "value": "summer dresses for women maxi",
  "widgetId": "summer-dresses-for-women-maxi",
  "strategyId": "hit-sc12",
  "template": "card-carousel",
  "metadata": {
    "title": "summer dresses for women maxi by type"
  },
  "widgetItems": [
    {
      "metadata": {
        "text": "Short Sleeve",
        "image_url": "https://m.media-amazon.com/images/I/xxx.jpg",
        "link_url": "/s?k=womens+short+sleeve+maxi+dresses+for+summer"
      }
    }
  ]
}
```

## Excel 输出 Sheet 结构

| Sheet | 内容 |
|-------|------|
| 摘要 | 种子词、站点、Widget卡片数、分类组数、各轮统计 |
| Widget分类卡片 | 轮次/Widget标题/子分类标签/完整关键词/触发前缀/图片URL/搜索URL |
| 关键词 | 所有关键词（含 Widget 子分类词和普通建议词） |

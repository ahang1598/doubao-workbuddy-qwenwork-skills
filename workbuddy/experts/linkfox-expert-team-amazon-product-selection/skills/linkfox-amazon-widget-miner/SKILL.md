---
name: linkfox-amazon-widget-miner
description: >
  Amazon Widget 分类卡片专门挖掘工具。基于 www.amazon.com/suggestions API，
  专注发现和提取 Amazon 推荐引擎返回的 WidgetSuggestion 分类卡片（含子分类标签、完整关键词、商品图片URL、搜索URL）。
  采用多策略触发（a-z扫描+品类修饰词+数字单位后缀+介词扩展）+ Widget标签递归扩展（把子分类标签拼回种子词做二次/三轮查询，发现嵌套分类）。
  用户说"挖Widget卡片""Widget分类词""Amazon卡片词""分类卡片挖掘""widget mining""card mining""挖带图片的分类词""by type扩展"时触发。
  即使用户没说"Widget"，只要意图是"获取Amazon搜索建议中的分类卡片（带图片和搜索链接的高价值分类词）"就应触发本skill。
  与 linkfox-amazon-suggestion-miner 的区别：后者覆盖全部关键词建议（7种模式），本skill专注Widget卡片这一高价值子集，
  用更多前缀组合+递归扩展最大化卡片产出。两者互补：suggestion-miner 挖全量词，widget-miner 专挖带图片的分类卡片。
  直接调Amazon公开API，不计费。
---

# Amazon Widget 分类卡片专门挖掘工具

专注挖掘 Amazon 搜索建议中的 **WidgetSuggestion** 分类卡片——带商品图片 URL 和搜索 URL 的高价值分类词。

## 什么是 Widget 卡片

Amazon Suggestions API 返回两类数据：
- **KeywordSuggestion**：普通关键词建议（10 条）
- **WidgetSuggestion**：分类卡片（1 条），包含 10-15 个子分类标签，每个标签带完整关键词、商品图片 URL、搜索 URL

Widget 卡片的标题格式通常是 **"种子词 by type"**，例如 "summer dresses for women maxi by type"，子分类包括 Short Sleeve / Cotton / Wrap / Boho 等。

## 核心特点

- **多策略触发**：a-z 后缀扫描 + 品类修饰词扩展 + 数字单位后缀 + 介词扩展，最大化触发 Widget 卡片
- **递归扩展**：把 Widget 子分类标签拼回种子词做二次/三轮查询，发现嵌套的 "by type" 分类
- **带图片和链接**：每个卡片子分类都带商品图片 URL 和 Amazon 搜索 URL
- **防封机制**：随机抖动延迟 + 指数退避重试

## 参数概览

- **必填**：`--seed`（种子词）
- **可选**：`--depth`（递归深度 1/2/3，默认 2）、`--max-labels`（每轮最多取多少标签，默认 15）、`--market`（站点，默认 US）

## 调用方式

```bash
python3 scripts/widget_miner.py --seed "Summer Dresses for Women" -v
python3 scripts/widget_miner.py --seed "dog toy" --depth 3 --max-labels 20 -v
python3 scripts/widget_miner.py --seed "wireless charger" --market DE -v
```

**输出策略**：
- **始终**将结果（xlsx + json）写入会话目录
- 对话中输出摘要（Widget 卡片数、分类组数、各轮统计、前 20 条预览）

## 使用指引

### 深度控制

| 深度 | 说明 | 预期 Widget 卡片数 |
|------|------|-------------------|
| 1 | 只做多策略触发扫描 | 30-80 |
| 2 | + Widget 标签二次扩展（推荐） | 80-150 |
| 3 | + 嵌套标签三轮扩展 | 120-200 |

### 触发策略

第 1 轮自动尝试多种前缀组合：
- a-z 后缀扫描（种子词 + a-z）
- 品类修饰词（casual/long/short/maxi/midi/plus size/floral 等 24 个）
- 数字单位后缀（mm/inch/oz/pack/set 等，试跑经验：意外触发大量 Widget）
- 介词 + a-z（for/with/without + a-z）

### 示例

```bash
# 标准挖掘（推荐）
python3 scripts/widget_miner.py --seed "Summer Dresses for Women" -v

# 深度挖掘（三轮递归）
python3 scripts/widget_miner.py --seed "dog toy" --depth 3 -v

# 限制标签数（控制时间）
python3 scripts/widget_miner.py --seed "fan" --max-labels 10 -v
```

## 展示规则

- 告知 Widget 卡片总数、分类组数、各轮统计
- 展示 Widget 分类组详情（每个标题有多少子分类）
- 展示前 20 条 Widget 卡片预览（标签 → 完整关键词）
- 引导用户打开 Excel 查看完整卡片（含图片 URL 和搜索 URL）

## 限制

- API 无需登录，内置防封机制
- 5 个站点（UK/AU/BR/SG/TR）可能需浏览器辅助
- 深度 3 时请求量较大（100+ 个前缀），建议适当增加 `--delay`

## 适用与不适用

**适用**：
- 专门挖掘带商品图片的分类卡片
- 发现 Amazon 推荐引擎的 "by type" 分类结构
- 获取带搜索 URL 的高转化分类词

**不适用**：
- 挖普通长尾关键词 → 用 `linkfox-amazon-suggestion-miner`
- 按 ABA 排名/时间条件筛选搜索词 → 用 `linkfox-aba-new-keyword-miner`
- 评估关键词竞争度 → 需额外工具

---
name: linkfox-amazon-suggestion-miner
description: >
  Amazon搜索建议词（自动补全）挖掘工具。完整自动化「手动下拉框挖词技巧」，
  基于 www.amazon.com/suggestions API，从种子词出发批量扩展长尾关键词。
  支持7种模式：批量扩展(expand)/A-Z后缀(az)/A-Z前缀(az_prefix)/数字拓展(numbers)/空格间隙插入(gap)/逆向滚雪球(reverse)/深度递归(deep)。
  内置随机抖动+指数退避重试防封机制。支持23个Amazon全球站点+种子词自动翻译，最终交付 Excel(xlsx) 多Sheet结构化词库。
  用户说"搜索建议词""自动补全""suggestion""autocomplete""长尾词挖掘""搜索词扩展""关键词扩展"
  "suggestion mining""keyword expansion""Amazon下拉词""搜索框建议""搜索联想词""手动挖词""下拉框挖词"时触发。
  即使用户没说"挖掘"二字，只要意图是"从Amazon搜索框扩展大量长尾关键词并导出Excel"就应触发本skill。
  与 linkfox-aba-new-keyword-miner 的区别：本skill从搜索框自动补全扩展长尾词（种子词驱动），
  ABA新词挖掘从ABA品牌分析数据库按时间/排名条件筛选搜索词（条件驱动）。两者互补，可串联使用。
  直接调Amazon公开API，不通过LinkFox网关，不计费。建议每2-4周重新挖掘一次以获取最新数据。
---

# Amazon 搜索建议词挖掘工具（手动下拉框技巧自动化版）

从种子词出发，利用 Amazon 搜索框自动补全 API，**完整复刻并批量执行纯手动下拉框挖词技巧**，输出多 Sheet Excel 词库。

## 核心特点

- **7 种模式完整覆盖手动技巧**：字母顺推(后缀/前缀)、数字拓展、介词/场景/人群/材质/季节扩展、空格间隙插入、滚雪球反向扩展、深度递归
- **防封机制**：随机抖动延迟 + 指数退避重试 + 随机 session-id，避免被 Amazon 限流
- **23 个站点支持**：覆盖北美、欧洲、亚洲、中东全部 Amazon 站点
- **种子词自动翻译**：内置品类词典 + Google Translate + 英文原词三层保底
- **多 Sheet Excel 输出**：摘要 / 关键词 / Widget分类词 / 问句式关键词四表结构化输出

## 手动技巧 → 模式映射

| 手动下拉框技巧 | 对应模式 | 说明 | 典型产出 |
|---------------|----------|------|---------|
| 字母顺推法（后缀） | `az` | 核心词 + 空格 + a-z | 150-260 条 |
| 字母顺推法（前缀） | `az_prefix` | a-z + 空格 + 核心词 | 100-200 条 |
| 数字拓展法 | `numbers` | 核心词 + 数字/单位/包装 | 50-120 条 |
| 介词/疑问词拓展法 | `expand` | for/with/without/how/what 等模板 | 150-350 条 |
| 空格间隙插入法 | `gap` | 多词中间插入热门修饰词 | 80-200 条 |
| 滚雪球反向扩展 | `reverse` | 先扫描再高频词前置，两步联动 | 400-550 条 |
| 滚雪球深度版 | `deep` | 单次查询后取高频词层层递归 | 60-110 条 |

## 参数概览

- **必填**：`--seed`（种子词，如 "dog toy"、"wireless charger"）
- **可选**：`--mode`（expand/az/az_prefix/numbers/gap/reverse/deep，默认 expand）、`--market`（站点，默认 US）、`--markets`（多站点批量）、`--auto-translate`（自动翻译种子词）

完整参数表、响应字段结构与限制，见 [`references/api.md`](references/api.md)。

## 调用方式

```bash
python3 scripts/suggestion_miner.py --seed "dog toy" --mode expand --rounds 2 -v
python3 scripts/suggestion_miner.py --seed "dog toy" --mode az -v
python3 scripts/suggestion_miner.py --seed "dog toy" --mode az_prefix -v
python3 scripts/suggestion_miner.py --seed "dog toy" --mode numbers -v
python3 scripts/suggestion_miner.py --seed "dog toy" --mode gap -v
python3 scripts/suggestion_miner.py --seed "wireless charger" --mode reverse --top-n 30 -v
python3 scripts/suggestion_miner.py --seed "fan" --mode deep --depth 2 --top-n 5 -v
python3 scripts/suggestion_miner.py --seed "feather duster" --markets US,DE,JP --auto-translate -v
```

**推荐组合**：`expand` + `az` + `numbers`（覆盖最全，效率最高）

**输出策略**：
- **始终**将完整结果（xlsx + json）写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/` 目录
- 对话中通过 `print_summary()` 输出摘要（种子词、模式、关键词数、Widget数、前20条预览）
- 完整词表引导用户打开 Excel 文件查看
- 用户指定 `--xlsx`/`--csv`/`--output` 时额外保存到用户路径

## 使用指引

### expand — 批量扩展（建库主力，对应最多手动技巧）

一次覆盖：介词拓展、场景/人群、材质/功能/痛点、季节节日、疑问词。40+ 个前缀模板自动生成。

### az — A-Z 后缀扫描（字母顺推法-后缀）

种子词 + 空格 + a-z，穷举式覆盖。

### az_prefix — A-Z 前缀扫描（字母顺推法-前缀）

a-z + 空格 + 种子词，挖属性词和前置修饰。

### numbers — 数字/规格拓展（数字顺推法）

常见数字、pack、set、inch、mm 等，挖出尺寸与包装长尾。

### gap — 空格间隙插入（空格间隙插入法）

对多词种子词，在中间强制插入热门修饰词（chew/plush/portable 等），模拟手动把光标移到词中间敲空格。

### reverse — 逆向滚雪球（滚雪球反向扩展）

先 A-Z 扫描，再提取高频词做前置检索，两步联动。

### deep — 深度递归（滚雪球深度版）

单次查询后取 Top-N 高频词递归扩展，逐层深入。

### 多站点挖词

非英语站点不能简单用英文种子词。使用 `--auto-translate` 自动翻译，或用 `--translations "DE:Staubwedel,JP:ハタキ"` 手动指定。

## 展示规则

- 告知用户结果总数、Excel 文件路径和 JSON 文件路径
- 对话中展示前 20 条关键词作为预览
- Widget 分类卡片展示前 15 条
- 问句式关键词单独分类展示
- 多站点模式逐站点展示统计

## 限制

- API 无需登录，无反爬（内置随机抖动+退避重试防封机制）
- 5 个站点（UK/AU/BR/SG/TR）curl 可能返回 202 空，需浏览器辅助
- 数据反映近期搜索热度，建议每 2-4 周重新挖掘
- gap 模式对单关键词效果有限，建议用于 2 词及以上种子词
- Google Translate 翻译可能不准，务必看返回量验证

## 适用与不适用

**适用**：
- 从种子词扩展大量 Amazon 长尾关键词
- 多站点多语言关键词挖掘
- 季节性/趋势性关键词发现（配合 ABA 新词挖掘使用）

**不适用**：
- 按 ABA 排名/时间条件筛选搜索词 → 用 `linkfox-aba-new-keyword-miner`
- 查单个词的排名趋势 → 用 `linkfox-aba-intelligent-query`
- 评估关键词竞争度/机会分 → 需额外接入关键词研究工具

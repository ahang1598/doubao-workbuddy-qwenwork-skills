---
name: linkfox-aba-new-keyword-miner
description: ABA 新词挖掘专家（ABA New Keyword Mining Expert）——完整流程：ABA 智能查询返回 searchTerm + searchFrequencyRank，AI 批量翻译为中文，合并导出 6 列 CSV（序号/搜索词/中文翻译/搜索频率排名/标记/备注），支持 OFFSET 分页获取不重复批次。用户说"找季节性关键词""找爆发词""找新进入榜单的词""ABA挖词""导出ABA结果""找去年某月突然上榜的词""找近N周新进榜单的词""批量挖ABA关键词""导出CSV方便筛选""ABA关键词翻译""ABA新词挖掘""seasonal keyword mining""ABA keyword export""find trending search terms""export ABA to CSV""translate ABA keywords""ABA new keyword mining"时触发。即使用户没说"挖掘"二字，只要意图是"用ABA数据按时间/排名条件筛选搜索词并导出"就应触发本skill。与linkfox-aba-intelligent-query的区别：本skill专注"挖掘+翻译+导出"完整工作流，自带AI翻译、CSV落盘和分页去重；如果只需查单个词的排名趋势或Top ASIN点击转化，用linkfox-aba-intelligent-query。按动态规则计费，同一会话同参数24h缓存。
---

# ABA 新词挖掘专家

封装"描述筛选条件 → ABA 智能查询 → AI 批量翻译 → CSV 导出（6 列）→ 分页去重"这个高频挖词工作流。底层调 `/aba/intelligentQuery`，翻译调 `linkfox-aigc-textgen`，上层增加 CSV 落盘和 OFFSET 分页能力。

## 核心特点

- **自然语言挖词**：用 `analysisDescription` 描述筛选意图（如"去年10-11月进前20万但1-9月未进50万的词"），后端自动转 SQL，无需手写查询语句。
- **AI 批量翻译**：查询结果自动调 `linkfox-aigc-textgen`（GEM_3_FLASH 模型）一次性批量翻译所有搜索词为中文，翻译失败时对应位置留空不影响导出。
- **6 列 CSV 导出**：结果自动导出为 CSV（UTF-8 BOM 编码，Excel 直接打开），含 `序号 / 搜索词 / 中文翻译 / 搜索频率排名 / 标记 / 备注` 六列，方便后续人工筛选和标注。
- **OFFSET 分页去重**：通过在 analysisDescription 中指定"跳过前 N 个"实现分页，获取下一批不重复的词。同一排序方式下分页结果天然不重叠。
- **预置挖词模式**：SKILL.md 内置季节性爆发词、新进入榜单词、排名跃迁词三种常见挖词模板，agent 可直接套用。

## 参数概览

- **必填字段**：`analysisDescription`（自然语言筛选描述）
- **可选字段**：`region`（站点，默认 `US`）、`exportCsv`（是否导出 CSV，默认 `true`）、`translate`（是否 AI 批量翻译为中文，默认 `true`）

完整参数表、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 调用方式

- **API 端点**：`POST /aba/intelligentQuery`（完整参数/响应/错误码见 `references/api.md`）
- **Python 脚本**：`python scripts/aba_new_keyword_miner.py '<JSON 参数>' [--inline]`

**输出策略（脚本默认行为）**：
- **始终**将完整响应写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-aba-new-keyword-miner-<timestamp>.json`
- 当 `translate` 为 `true`（默认）时，查询成功后自动调 `linkfox-aigc-textgen` 批量翻译搜索词
- 当 `exportCsv` 为 `true`（默认）时，翻译完成后**同时**导出 6 列 CSV 到 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-aba-new-keyword-miner-<timestamp>.csv`
- 响应体 ≤ 8 KB：落盘后把完整 JSON 打印到 stdout
- 响应体 > 8 KB：落盘后 stdout 只输出摘要（顶层字段、常见计数如 `total`/`costToken`、最大列表字段的长度 + 前 3 条样本）
- 加 `--inline` 强制全量打印到 stdout（同样落盘）

**读数据建议**：先看摘要判断结果数量是否够用；需要完整词表直接打开导出的 CSV 文件；需要原始 JSON 字段用 `jq` 从保存的 json 文件按需抽取。

## 使用指引

### analysisDescription 编写原则

1. 开头指明站点（如"筛选美国站"）
2. 用精确数字范围而非模糊描述（写"searchFrequencyRank <= 200000"而非"排名比较靠前"）
3. 明确时间范围（写"2025年10月至2025年11月"而非"去年秋天"）
4. 对比基线要写清时间点（"在…期间"vs"在…之前"）
5. 多条记录需指定去重逻辑（"按 searchTerm 去重"）
6. 需要分页时加"按 searchTerm 字母升序排列，跳过前 N 个，返回第 N+1 到 N+100 个"
7. 需要搜索频率排名时加"返回 searchTerm 及其 searchFrequencyRank"

### 预置挖词模板

**1. 季节性爆发词**（某时段连续上榜，之前完全不在榜单）
```
筛选{站点}站。找出符合以下条件的搜索词：
1. 在{起始月份}至{结束月份}期间，每周的 searchFrequencyRank 都 <= {上榜阈值}；
2. 在这之前的{对比周数}周内，该搜索词完全不在 ABA 榜单中（即没有任何记录）。
按 searchTerm 去重，按 searchTerm 字母升序排列，跳过前 {offset} 个，返回第 {offset+1} 到 {offset+limit} 个搜索词。
```

**2. 排名跃迁词**（某时段排名突进，之前排名很靠后）
```
筛选{站点}站。找出符合以下条件的搜索词：
1. 在{起始月份}至{结束月份}期间，每周的 searchFrequencyRank 都 <= {严格阈值}；
2. 在{对比起始月份}至{对比结束月份}期间，没有任何一周的 searchFrequencyRank <= {宽松阈值}。
按 searchTerm 去重，按 searchTerm 字母升序排列，跳过前 {offset} 个，返回第 {offset+1} 到 {offset+limit} 个搜索词。
```

**3. 新进入榜单词**（近N周连续进入，之前M周完全不在）
```
筛选{站点}站。找出符合以下条件的搜索词：
1. 在最近 {N} 周内，每周的 searchFrequencyRank 都 <= {上榜阈值}；
2. 在这最近 {N} 周之前的连续 {M} 周内，该搜索词完全不在 ABA 榜单中。
按 searchTerm 去重，按 searchTerm 字母升序排列，跳过前 {offset} 个，返回第 {offset+1} 到 {offset+limit} 个搜索词。
```

### 示例

**1. 季节性爆发词（第一批 100 个）**
```json
{
  "analysisDescription": "筛选美国站。找出符合以下全部条件的搜索词：1. 在2025年10月至2025年11月期间，每周的searchFrequencyRank都<=200000；2. 在2025年1月至2025年9月期间，没有任何一周的searchFrequencyRank<=500000。按searchTerm去重，按searchTerm字母升序排列，返回前100个搜索词。",
  "region": "US",
  "exportCsv": true
}
```

**2. 同一查询获取第二批不重复的词**
```json
{
  "analysisDescription": "筛选美国站。找出符合以下全部条件的搜索词：1. 在2025年10月至2025年11月期间，每周的searchFrequencyRank都<=200000；2. 在2025年1月至2025年9月期间，没有任何一周的searchFrequencyRank<=500000。按searchTerm去重，按searchTerm字母升序排列，跳过前100个，返回第101到200个搜索词。",
  "region": "US",
  "exportCsv": true
}
```

**3. 近4周新进入榜单词**
```json
{
  "analysisDescription": "筛选美国站。找出符合以下全部条件的搜索词：1. 在最近4周内，每周的searchFrequencyRank都<=500000；2. 在这最近4周之前的连续12周内，该搜索词完全不在ABA榜单中。按searchTerm去重，按searchTerm字母升序排列，返回前100个搜索词。",
  "region": "US",
  "exportCsv": true
}
```

## 展示规则

- 查询完成后，告知用户结果总数、CSV 文件路径和 JSON 文件路径
- 对话中展示前 5-10 条搜索词（含中文翻译和搜索频率排名）作为预览，完整词表引导用户打开 CSV
- 如果结果数为 0，告知用户"未找到符合条件的搜索词"，建议放宽筛选条件
- 翻译失败时告知用户"部分翻译未成功，CSV 中对应位置为空"，CSV 仍可正常使用

## 限制

- ABA 数据为周维度（非日维度），约 3 年历史数据
- 单次查询最多返回 10,000 条记录
- 同一会话同参数组合 24h 本地缓存，不重复计费
- 计费按动态规则：初始 SQL 生成积分 + 各任务执行积分 + CSV 文件大小积分
- 支持站点：US、DE、BR、CA、AU、JP、AE、ES、FR、IT、SA、TR、MX、SE、NL

## 适用与不适用

**适用**：
- 按时间/排名条件批量挖掘 ABA 搜索词
- 季节性关键词发现（节日、事件驱动的搜索爆发）
- 新趋势词发现（近期突然进入榜单的词）
- 需要导出 CSV 做后续人工筛选和标注

**不适用**：
- 查单个词的排名趋势 → 用 `linkfox-aba-intelligent-query`
- 查 Top ASIN 点击转化数据 → 用 `linkfox-aba-intelligent-query`
- 需要 HTML 分析报告 → 查询后用 `linkfox-report-generator` 生成

## 反馈

参见 `references/api.md`。

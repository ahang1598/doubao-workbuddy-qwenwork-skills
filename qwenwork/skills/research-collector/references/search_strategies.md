# 搜索策略指南

各平台的搜索关键词构造方法和反爬应对策略。

## 学术来源

### arXiv

- 搜索方式：`WebSearch` 使用 `site:arxiv.org [关键词]`
- 关键词构造：英文术语 + 技术变体名（如 "retrieval augmented generation" / "RAG"）
- 时间限定：可加 `after:2024` 限定近期论文

### Semantic Scholar API

- Endpoint: `https://api.semanticscholar.org/graph/v1/paper/search`
- 参数：`query=[关键词]&limit=10&fields=title,authors,year,abstract,citationCount,url,venue`
- 无需认证，免费使用

### GitHub

- 搜索方式：`WebSearch` 使用 `site:github.com [关键词]`
- 关键词构造：技术名 + 语言/框架（如 "RAG framework python"）
- 也可通过 GitHub API：`https://api.github.com/search/repositories?q=[关键词]&sort=stars&order=desc`

## 中文内容平台

### 百度搜索（百家号）

- 搜索方式：`WebSearch` 搜索 `百家号 [关键词]` 或 `site:baijiahao.baidu.com [关键词]`
- 百家号 URL 特征：`baijiahao.baidu.com/s?id=...`
- 反爬注意：百度搜索返回的百家号页面可以直接访问，但 WebFetch 可能被拦截，优先使用 WebSearch 摘要

### 微信公众号

- 搜索方式：
  1. `WebSearch` 搜索 `site:mp.weixin.qq.com [关键词]`
  2. `WebSearch` 搜索 `微信公众号 [关键词]`
- 微信公众号 URL 特征：`mp.weixin.qq.com/s/...`
- 反爬注意：微信页面有访问限制，WebFetch 可能无法访问完整内容，依赖 WebSearch 摘要即可

### 知乎

- 搜索方式：`WebSearch` 搜索 `site:zhihu.com [关键词]`
- 知乎 URL 特征：`zhuanlan.zhihu.com/p/...`（专栏文章）或 `zhihu.com/question/...`（问答）
- 专栏文章通常信息量更大，优先选用

### CSDN / 掘金 / 博客园

- CSDN: `site:blog.csdn.net [关键词]`
- 掘金: `site:juejin.cn [关键词]`
- 博客园: `site:cnblogs.com [关键词]`

## 关键词构造规则

### 通用规则

1. **核心词**：研究方向的直接名称
2. **同义词**：技术名的不同叫法（如 "大语言模型" / "LLM" / "Large Language Model"）
3. **上下游词**：相关技术、工具、框架
4. **时间限定**：加年份或 `latest` / `最新` 限定近期内容

### 中文平台关键词

```
[核心技术名] + 调研 / 综述 / 趋势 / 盘点
[核心技术名] + 应用 / 实践 / 案例
[核心技术名] + 对比 / 评测 / 比较
```

### 英文平台关键词

```
[keyword] + survey / review / overview
[keyword] + benchmark / comparison
[keyword] + latest / 2025 / 2026
[keyword] + framework / toolkit / library
```

## 搜索量建议

| 模式 | 搜索关键词数 | 每关键词搜索条数 | 预期结果 |
|------|------------|----------------|---------|
| 快速 | 2-3 | 3-5 | 5-8 条 |
| 默认 | 4-6 | 5-8 | 10-15 条 |
| 全面 | 8-10 | 8-12 | 20-30 条 |

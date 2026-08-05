# Crossref 检索手册

## 端点

- **反查题录**（已知标题+作者）：`https://api.crossref.org/works?query.bibliographic=<q>&rows=3`
  - `<q>` = 论文标题 + 第一作者姓，空格用 `+` 或 `%20` 编码。
- **DOI 直查**（校验已知 DOI）：`https://api.crossref.org/works/<DOI>`
  - 返回 404 = 该 DOI 不存在于 Crossref（可能是编造的，也可能是中文注册机构的 DOI——结合文献语言判断）。
  - 返回 200 但标题对不上 = 张冠李戴，按"不一致"处理。

## 两个已验证的陷阱

- `https://doi.org/<DOI>` 会 302 跳转到出版商页面，链接读取工具通常报错（link fetch error）。**一律走 api.crossref.org。**
- 裸 DOI 字符串直接作为 `general_search` 的 query，返回的是共享相同 DOI 前缀的无关文献。**不要这样搜**；网页通道用"标题 + 期刊名"检索。

## JSON 字段映射

| 报告字段 | Crossref JSON 路径 | 备注 |
|---|---|---|
| 题目 | `message.title[0]` | |
| 作者 | `message.author[].family` / `.given` | |
| 期刊全称 | `message.container-title[0]` | |
| 卷 | `message.volume` | |
| 期 | `message.issue` | 部分期刊部分卷无期号，缺失是正常的，如实写"该卷无期号"，不要编 |
| 页码 | `message.page` | article-number 时代的期刊可能返回文章号而非页码区间，照抄即可 |
| DOI | `message.DOI` | |
| 正式刊出时间 | `message.published-print.date-parts` | 参考文献年份以此（卷期归属）为准 |
| 在线发表时间 | `message.published-online.date-parts` | 与 print 都记录，两者差一年以上很常见 |
| 被引数 | `message.is-referenced-by-count` | Crossref 口径，与 Google Scholar 被引数不同，标注口径 |

## 匹配判定（误匹配防御细则）

`query.bibliographic` 返回按相关度排序，第一条不保证是目标。对 rows 内每条结果检查：

1. **标题归一化比对**：双方标题转小写、去标点、连字符与空格互换视为等同、忽略首尾空白后，一致或仅有极小差异（如单复数、英式美式拼写）。
2. **第一作者姓氏一致**：注意中文姓名拼音可能姓/名顺序颠倒（"Qin Zhu" vs "Zhu Qin"），姓氏能对上即可。
3. **期刊名核对**（若上游给了期刊）：container-title 一致或为公认缩写。

条件 1、2 必须同时满足才算命中；否则按未命中处理，进入网页通道。**宁可未核验，不可错核验。**

## 常见陷阱

- **在线年 vs 刊出年**：online-first 与正式编卷常跨年（2022 在线、2023 编入 23 卷）。凡两者不同，都记录，正文与参考文献用刊出年。
- **预印本与正式版**：arXiv 版与期刊版是不同 DOI，确认引的是哪个版本。
- **会议论文**：container-title 是论文集名，常无卷期页，以返回为准，不补全。
- **中文期刊**：多数不在 Crossref（DOI 归中文注册机构管理），Crossref 404 不等于不存在，直接走网页通道查知网/万方/期刊官网。
- **Elsevier DOI 后缀**：2019 年前后规则不同——前期是任意序号（如 `j.enpol.2012.05.068`），后期等于文章号（如 `j.jclepro.2020.121479`）。任意序号无法从页码或年份推出，这正是禁止构造 DOI 的原因。

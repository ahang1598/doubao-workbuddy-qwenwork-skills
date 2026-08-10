# 交付复杂度路由

- `direct`：软目标 1400 中文字符；必需槽位：bottom_line、minimum_evidence、counterpoint、limitations
- `brief`：软目标 2600 中文字符；必需槽位：bottom_line、evidence_chain、countercase、verification_queue、sources
- `full`：软目标 5200 中文字符；必需槽位：executive_summary、business、competition、financial_quality、valuation_boundary、countercase、risks、sources

字符数仅用于写作压缩，不是交付失败条件。只有 provider 的 incomplete、finish_reason=length/max_tokens 或结构截断触发安全上限失败。用户问题越短不代表可以省略直接结论；证据搜索复杂度不自动扩大最终输出。

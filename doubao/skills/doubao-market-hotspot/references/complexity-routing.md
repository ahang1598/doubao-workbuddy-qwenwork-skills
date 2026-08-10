# 交付复杂度路由

- `direct`：软目标 1400 中文字符；必需槽位：bottom_line、causal_chain、winners_losers_or_unknown、conditions
- `brief`：软目标 2800 中文字符；必需槽位：event_status、mechanisms、impact_matrix、financial_mapping、countercase、monitoring
- `full`：软目标 5400 中文字符；必需槽位：event_status、mechanism_decomposition、transmission、impact_matrix、financial_mapping、priced_in_boundary、scenarios、countercase、monitoring、sources

字符数仅用于写作压缩，不是交付失败条件。只有 provider 的 incomplete、finish_reason=length/max_tokens 或结构截断触发安全上限失败。用户问题越短不代表可以省略直接结论；证据搜索复杂度不自动扩大最终输出。

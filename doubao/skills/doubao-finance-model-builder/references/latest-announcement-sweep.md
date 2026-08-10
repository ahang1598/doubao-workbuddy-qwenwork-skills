# 最新公告增量检索协议

本协议适用于所有正式财务建模和估值任务。目的不是重复下载历史财报，而是在模型采用的最后一份公开披露之后，扫清截至信息截止日的新公告，防止财务、指引、股本或资本结构已经变化而模型仍使用旧数据。

## 检索时点

- 当前分析：估值日默认采用查询日，`information_cutoff_date` 不晚于估值日；价格使用此前最近交易日。若用户另要追踪估值日后事项，建立独立补充清单，不回填估值模型。
- 历史复盘：检索截止估值日当地收盘，只纳入 `public_date <= valuation_date` 的公告。
- `search_start_date` 不晚于模型已纳入的最新财务披露公开日；`search_end_date` 等于 `information_cutoff_date`。
- 记录查询时间、时区、官方入口、检索条件和结果页。无结果也保存官方查询回执或结果快照。

## 必查公告类别

1. 定期报告、业绩公告、业绩预告/快报、盈利警告、重述和会计差错更正。
2. 管理层指引、订单/合同、产品、价格、产能、停复产及重大经营数据变化。
3. 分红派息、送股、资本公积转增、拆股/合股、配股、供股、公开或定向增发、库存股、回购注销、股权激励归属/行权、可转证券转换、A/H 股本和 ADR 比率变化。
4. 债务发行、再融资、担保、违约、评级触发、流动性安排及重大资本开支。
5. 并购、出售、分拆、重大投资、诉讼、监管处罚、审计意见、持续经营或退市风险。

只把与公司或证券身份匹配的正式文件视为公告证据。新闻和搜索摘要只能用于发现线索。

## 官方入口与建议查询词

- A 股：巨潮资讯及上交所、深交所、北交所公告检索。组合公司名/代码与“业绩预告、业绩快报、权益分派、除权除息、送股、转增、配股、增发、回购注销、可转债转股、股本变动”等词。
- 港股：港交所披露易公告、月报表及翌日披露报表。检索“results/profit warning, dividend, bonus issue, rights issue, placing, share consolidation/subdivision, repurchase, conversion, next day disclosure return”。
- 美股：SEC EDGAR 的 10-K、10-Q、8-K、20-F、6-K、注册声明、招股补充和发行人公司行动文件；再以公司投资者关系网站补充财报与指引。

不要依赖单一关键词：先按发行人和日期范围浏览完整公告列表，再用类别词复核。结构化 `seed_finance_search` 可用于定位候选项，但不能替代官方结果页与公告正文。

## 证据清单和处置

建立 `announcement-sweep.json` 与本地证据目录，并运行：

```bash
python3 scripts/common/validate_announcement_sweep.py \
  announcement-sweep.json --root . --output announcement-sweep-validation.json
```

官方结果页文本为每项相关公告写入 `[DISCOVERED_ANNOUNCEMENT_ID:编号]`；确无相关公告时写入 `[NO_RELEVANT_ANNOUNCEMENTS]`，两者不得同时出现。每项发现必须：

- 保存官方正文及可搜索文本和 SHA-256；
- 记录公告日、生效/除权日（如适用）、类别、影响字段和来源 ID；
- 标记为 `incorporated`、`not_material` 或 `blocking`，并写明理由；
- 对 `incorporated` 项更新历史数据、预测、净债务、股数桥或情景；
- 对 `blocking` 项停止相关结论，不能以免责声明绕过。

权益分派和股本变化还必须执行 `references/equity-evidence-acquisition.md`。除权日只决定价格是否含权；股数变化按法律生效/登记完成口径进入股数桥。不得把“公告已发布”误当作“股本已生效”，也不得用复权价乘估值日股数计算市值。

<!-- END OF FILE: latest-announcement-sweep.md -->

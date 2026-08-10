# 股本证据取得与冻结

本协议适用于使用股价、每股价值、市值或交易倍数的正式任务。顺序固定为：**先取得证据，再建股数桥，最后验证**。不得为了先运行验证器而用最近报表股数、数据库当前值或假设值填充输入。

## 1. 先检索，不先填估值日股数

对每个证券类别分别执行：

1. 从估值日向前找到最近一份可靠股本披露，记录基准股数、股本日期和官方文件。
2. 以该股本日为起点，检索至估值日当地收盘，覆盖权益分派、送转、拆合股、发行、配售、回购注销、库存股、可转证券转换、期权行权、限制性股票归属、A/H股本变化和ADR比率变化。
3. 打开搜索结果中的公告正文；区分公告日、股权登记日、除权日、生效日和登记完成日。只有估值日前已经生效的变化进入股数桥。
4. 将基准披露、官方检索结果页及每项公司行动正文保存为本地证据文件，同时保存可搜索文本和SHA-256。只有URL、搜索摘要或模型转述不算证据。
5. 检索无结果时也必须保存官方检索结果页或查询回执；不得仅填写“无公司行动”。

官方入口优先级：A股使用交易所或巨潮资讯；港股使用港交所披露易及月报表/翌日披露报表；美股使用SEC EDGAR。公司网站只作为官方文件补充。

## 2. 证据包

建立 `equity-evidence.json` 和 `evidence/` 目录。每条证据至少记录：

`evidence_id | security_id | role | authority_tier | url | published_date | local_file | text_file | sha256 | text_sha256`

其中：

- `role` 使用 `baseline_share_disclosure`、`corporate_action_search_result` 或 `corporate_action_announcement`；
- 基准股本、检索结果和公司行动必须为 `authority_tier=primary`；
- `local_file` 保存原始PDF、HTML或交易所下载文件，`text_file` 保存其文本提取结果；
- 原文件与文本文件都必须存在并通过哈希复算；
- 文本必须包含发行人名称、证券代码或已登记别名之一；
- 文件公开日不得晚于信息截止日。

正式任务不得使用 skill 内的示例证据作为公司证据。示例只用于测试字段结构。

## 3. 公司行动检索记录

每个证券类别保存：

`security_id | baseline_date | search_start_date | search_end_date | official_entry_url | queries | result_evidence_ids | discovered_action_ids | completed | coverage_gaps`

硬条件：

- `search_start_date` 不晚于基准股本日；
- `search_end_date` 等于估值日；
- 至少保存一份官方检索结果证据；
- 在检索结果文本末尾为每项发现写入 `[DISCOVERED_ACTION_ID:行动编号]`；确实无结果时写入 `[NO_ACTIONS_FOUND]`，两者不得同时出现；
- `completed=true` 且 `coverage_gaps=[]`；
- 检索发现的每个行动都必须进入股数桥，或列入阻断问题并停止。

## 4. 股数桥

逐证券建立：

```text
官方基准股数
+ 已生效发行、送转、转换和行权
- 已生效注销或库存股扣减
= 估值日流通在外经济股数
```

每项行动必须引用本地冻结的官方公告证据。不得把损益表加权平均股数当作期末股数；不得将A股价格乘全部A/H股数。

估值日前90日存在送转、拆合股时，另行核对不复权价格、除权后股数和历史EPS口径。价格与股数口径无法统一时停止估值。

## 5. 验证与后续顺序

证据和股数桥完成后运行：

```bash
python3 scripts/common/validate_equity_evidence.py \
  equity-evidence.json --root . --output equity-evidence-validation.json
```

只有 `model_status_code=PASS` 才能把估值日股数写入DCF、可比公司或Excel输入。随后再执行不复权收盘价×估值日分证券股数×汇率的市值反向勾稽。

以下情况直接 `FAIL`：

- 只有URL，没有本地原文件与文本快照；
- 文件哈希不匹配；
- 基准股本或公司行动不是官方来源；
- 官方检索结果未保存；
- 搜索结束日早于估值日；
- 检索发现的行动没有进入股数桥；
- 仍有“待核实”、覆盖缺口或其他阻断问题。

<!-- END OF FILE: equity-evidence-acquisition.md -->

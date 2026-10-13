# V6.0 报告数据契约

`collection_result.json` 是任务内审计记录；`report_data.json` 是结构化报告草稿。两者先经同一校验器处理，再生成面向商家的 HTML 或妙搭展示数据。

## DOM 账号校验

`collection_result.account_consistency` 必须由本 Skill 读取两端页面 DOM 后生成：

```json
{
  "status": "matched",
  "checked_by": "local-life-service-holiday-business",
  "method": "dom",
  "entry": "existing_verified_tab",
  "backend_merchant_name": "已读取的来客商家名称",
  "platform_merchant_name": "已读取的生意经商家名称",
  "merchant_name": "已校验商家名称",
  "checked_at": "2026-09-10T10:00:00+08:00"
}
```

只有两端名称一致，且 `status=matched`、`checked_by=local-life-service-holiday-business`、`method=dom` 时才继续。`entry` 仅支持可见入口或已验证标签页。不比较生意经与来客的门店数量，不以数量差异拦截。`target` 仅记录本次用户要分析的单店或多店范围：`display_name` / `mode` / `store_names` / `categories`；可选 `store_keys` 只校验经营明细是否属于本次分析范围，不作跨平台数量比较。

## 逐指标记录

`collection_result` 顶层为 `target/account_consistency/sources/items`，可选 `ad_history_evidence`。`sources` 是任务内证据字典，每项必须带 `method: dom`；`items` 每个子指标一条：

```json
{
  "id": "R01", "check_id": "DP0-02", "metric_key": "transaction_amount",
  "priority": "core_required", "source_id": "S01",
  "evidence_ref": "本次页面字段位置", "actual_scope": "store_set",
  "scope_store_keys": ["任务内范围A", "任务内范围B"],
  "status": "zero", "raw_value": 0, "reason": null,
  "window": {"start": "2026-08-11", "end": "2026-09-09"}
}
```

机器唯一清单为 [data-manifest.json](data-manifest.json)，中文说明为 [data-manifest.md](data-manifest.md)。`check_id` / `metric_key` / `priority` / 平台必须匹配。每行所有子项均有状态和证据后才计入 P0 完成度；完成数由脚本派生，不手填。

四态口径：`observed` 有事实；数值 0 或明确空榜单为 `zero`；`unavailable/not_applicable` 的 `raw_value` 必须为 `null` 并说明 `reason`。页面报错、无权限和未显示不能当 0。门店数可作经营规模指标，不参与账号一致性判定。

## 展示契约

`report_data.json` 顶层保留 `report/store/collection/holidays/overview/metrics/actions/insights/timeline/sources/missing/next_tasks`，便于校验。渲染时会转换为商家展示投影：

- 删除 `sources`、来源编号、采集路径、证据记录 ID、P0/P1 进度和内部版本字段。
- 正常数值不显示“已取得”状态。明确零值可显示“零值”。
- `unavailable/not_applicable` 指标卡不渲染；无内容的洞察 Tab、空表格和空图表不渲染。
- 页面只在总览下方合并显示一句“……暂无数据，相关模块已隐藏。”
- 不生成来源入口、来源弹窗、采集说明或“拿到了哪些数据”类文案。

`report.title` 固定为“中秋国庆经营方案”。`actions` 保留 5—8 条互不重复的可执行建议，有真实亮点才使用“延续亮点”。任何动作不得包含改价、调价、涨价、降价、加深折扣或具体价格建议。价格带仅用于理解客群与商品结构。

近 30 日消耗 0 只说明该窗口未见消耗。只有任务内存在全历史页面证据时才能写“从未投放”。滞销不等于下架或不可售。

## 校验与交付

```bash
python3 scripts/render_report.py report_data.json output.html --collection collection_result.json
python3 scripts/render_report.py report_data.json validated_report.json --collection collection_result.json --data-only
```

两种输出使用同一账号校验交接和逐指标校验。`--allow-incomplete` 只用于运行中预览。分享内容禁止 Cookie、Token、密码、私钥、groupid、门店 ID、后台参数和可执行文本。文件名统一为 `{\u8303围名}-{\u5e74份}\u4e2d\u79cb\u56fd\u5e86\u7ecf\u8425\u65b9\u6848.html`；运行中预览追加“-运行中预览”。

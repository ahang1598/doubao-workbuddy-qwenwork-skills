# 账号一致性

本 Skill 通过浏览器 DOM 直接完成登录态接续、商户上下文确认和跨平台商家一致性校验，不调用其他 Skill，也不通过 `mcp-http` 或页面内部接口判断。

任务内只保存下列结果摘要：

```json
{
  "account_consistency": {
    "status": "matched",
    "checked_by": "local-life-service-holiday-business",
    "method": "dom",
    "entry": "existing_verified_tab",
    "backend_merchant_name": "页面展示的来客商家名称",
    "platform_merchant_name": "页面展示的生意经商家名称",
    "merchant_name": "页面已核验的商家名称",
    "checked_at": "2026-09-10T10:00:00+08:00"
  }
}
```

`entry` 只允许 `visible_life_data_link` 或 `existing_verified_tab`。只有两端页面 DOM 的商家名称按规则精确一致，且 `status=matched`、`checked_by=local-life-service-holiday-business`、`method=dom` 时才继续。

门店数量不参与账号一致性判断：不比较数量、不按数量差异停止、不打开门店管理页枚举未通过资质验证的门店。门店数可作为经营规模信息记录，但不能成为账号匹配或异常结论。

登录未接续、商家不一致、导航异常、权限不足或无法确认时，停止后续取数并说明用户需要完成的单一操作。具体接续与重试规则见 [DOM 取数与登录接续](dom-collection.md)。

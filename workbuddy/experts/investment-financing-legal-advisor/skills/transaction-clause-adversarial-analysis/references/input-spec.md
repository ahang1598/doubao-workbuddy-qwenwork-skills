| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agreement_files | file[] | 是 | 投资协议（SPA/SHA） |
| founder_side | boolean | 否 | 是否从创始方视角（默认是） |
| focus_traps | list | 否 | 聚焦陷阱类型（T1-T12 子集） |
| existing_modifications | text | 否 | 已提出的修改方案（评估是否充分） |
| deal_context | object | 否 | 交易情境，用于严重度调节：{ stage: 早期/成长期/Pre-IPO, investor_position: 控股/少数, founder_leverage: 强/弱, founder_financial_dependency: 高/低, round_structure: 单轮/多轮 } |

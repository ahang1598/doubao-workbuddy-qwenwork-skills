# 输入字段定义 — tm-damage-calc

> **所属技能**：tm-damage-calc | **文件角色**：输入规格 | **版本**：v1.3.0

---

## 必填字段（L3级——缺失则触发 SOFT_DEGRADED）

| 参数 | 类型 | 法律含义 | 约束 | 降级标记 |
|------|------|---------|------|---------|
| `infringement_duration` | string | 侵权持续时间 | 非空，如"2024年1月至2025年6月" | L3 |
| `infringement_scope` | string | 侵权范围 | 非空，描述地域/渠道 | L3 |

> **L3 缺失处理**：缺少上述任一字段 → SOFT_DEGRADED，仅输出赔偿要素清单+法定范围

---

## 计算基础字段（L2级——至少提供一项，缺失则降级）

| 参数 | 类型 | 法律含义 | 对应路径 | 降级标记 |
|------|------|---------|---------|---------|
| `plaintiff_loss` | number | 权利人实际损失（元） | 路径1 | L2 |
| `plaintiff_loss_basis` | string | 损失计算依据 | 路径1 | L2 |
| `defendant_profit` | number | 侵权人获利（元） | 路径2 | L2 |
| `defendant_profit_basis` | string | 获利计算依据 | 路径2 | L2 |
| `license_fee` | number | 商标许可使用费（元/年） | 路径3 | L2 |
| `license_fee_multiple` | number | 建议倍数 | 路径3 | L2 |
| `license_contract_date` | date | 许可合同签订日期 | 路径3 | L2 |

> **L2 缺失处理**：缺少全部计算基础 → 仅路径4（法定赔偿）可用，输出举证妨碍提示
> **L2 部分缺失**：缺少部分计算基础 → 可用路径正常计算，缺失路径标注"[待补充]"

---

## 惩罚性赔偿字段（L2级——条件必填）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `is_malicious` | boolean | 是否恶意侵权 | L2 |
| `malicious_evidence` | string | 恶意证据描述 | L2 |
| `is_serious` | boolean | 是否情节严重 | L2 |
| `serious_evidence` | string | 情节严重证据描述 | L2 |
| `punitive_multiple` | number | 建议惩罚倍数（1-5） | L2 |

> **条件说明**：`is_malicious` 和 `is_serious` 须同时为 true 才触发惩罚性赔偿计算

---

## 合理开支字段（L1级——缺失则标注[待补充]后继续生成）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `lawyer_fee` | number | 律师费（元） | L1 |
| `notary_fee` | number | 公证费（元） | L1 |
| `investigation_fee` | number | 调查费（元） | L1 |
| `purchase_fee` | number | 购买侵权产品费（元） | L1 |
| `travel_fee` | number | 差旅费（元） | L1 |
| `other_fee` | number | 其他费用（元） | L1 |

> **L1 缺失处理**：完整测算正常输出，缺失处标注"[待补充]"

---

## 法定赔偿字段（路径4兜底，选填）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `statutory_claim` | number | 建议法定赔偿金额（元） | 选填 |
| `statutory_basis` | string | 法定赔偿理由（侵权情节描述） | 选填 |

---

## 案件背景信息字段（选填——有则体现，无则不体现）

> **渲染规则**：此类字段为用户补充的案件背景信息，**有则输出，无则省略**，不标注"[待补充]"占位符。不影响降级等级。

| 参数 | 类型 | 说明 | 输出位置 |
|------|------|------|---------|
| `plaintiff_name` | string | 权利人名称 | 案件概况 |
| `trademark_reg_no` | string | 商标注册号 | 案件概况 |
| `trademark_name` | string | 商标名称 | 案件概况 |
| `trademark_class` | string | 商标类别（如"第9类"） | 案件概况 |
| `trademark_reg_date` | date | 商标注册日期 | 案件概况 |
| `trademark_renewal_deadline` | date | 商标续展截止日期 | 案件概况 |
| `trademark_fame` | string | 商标知名度（如"驰名商标""知名品牌"） | 案件概况 |
| `defendant_name` | string | 侵权人名称 | 案件概况 |
| `defendant_info` | string | 侵权人其他信息 | 案件概况 |

---

## 降级分层汇总

| 降级等级 | 缺失字段 | 输出范围 |
|---------|---------|---------|
| **L0 完整** | 无缺失 | 完整测算报告 + 撰写指引 + 证据清单 |
| **L1 轻度** | 缺少合理开支等推荐字段 | 完整测算报告，缺失处标注"[待补充]" |
| **L2 中度** | 缺少全部计算基础 | 仅路径4 + 举证妨碍提示 + 占位标注 |
| **L3 重度→SOFT_DEGRADED** | 缺少必填字段 | 仅赔偿要素清单 + 法定范围（C+D+G最小骨架） |

# 输入规范 — overseas-investment-structure-design

> 版本：v1.2.0

## 1. 输入模型

### 1.1 必需输入

| 字段 | 类型 | 法律含义 | 约束 |
|------|------|---------|------|
| target_country | string | 投资目标国（东道国） | 单一国家，ISO 3166-1英文名或中文名 |
| investment_purpose | string | 投资目的 | 枚举：manufacturing(制造工厂) / sales_office(销售办事处) / R&D(研发中心) / regional_holding(区域控股) / holding(纯控股) |
| investment_amount | string | 投资规模 | USD或CNY金额，须注明币种 |

### 1.2 可选输入

| 字段 | 类型 | 法律含义 | 默认值 |
|------|------|---------|--------|
| holding_jurisdiction | string[] | 中间控股地候选 | 自动推荐：HK(首选)/SG/BVI/Cayman |
| exit_plan | string | 退出计划 | undetermined |
| repatriation_plan | string | 利润汇回计划 | dividend |
| industry_sector | string | 行业领域 | 按investment_purpose推断 |
| existing_structure | string | 现有境外架构描述 | 无（全新架构） |
| timeline_requirement | string | 时间要求 | 标准周期（6-12月） |
| parent_company_type | string | 母公司类型 | 有限责任公司 |
| risk_appetite | string | 风险偏好 | balanced（balanced/conservative/aggressive） |
| output_language | string | 输出语言 | zh-CN |

## 2. 输入验证规则

### 2.1 国家验证

```
验证逻辑：
1. 检查 target_country 是否为可识别的国家名
2. 不支持的国家 → 标注"⚠ 该国投资法规信息有限，架构建议置信度较低"
3. 受制裁国家 → [阻断]，提示"该目标国受国际/中国制裁，不建议投资"
```

### 2.2 投资目的自动推断

| investment_purpose | 自动推荐架构特征 | 推断逻辑 |
|-------------------|----------------|---------|
| manufacturing | 香港→东道国WFOE，关注利润汇回+退出 | 制造业重资产，需优化税负+退出灵活 |
| sales_office | 香港→东道国分支机构/子公司，轻架构 | 轻资产，架构从简 |
| R&D | 香港→东道国WFOE，关注IP归属 | 研发产出IP，需设计IP持有架构 |
| regional_holding | 香港/新加坡→多国子公司，控股平台 | 需多国协调，新加坡适合东南亚区域中心 |
| holding | BVI/Cayman→东道国，纯持股 | 纯持股无运营，关注经济实质法合规 |

### 2.3 控股地候选自动推荐

| 场景 | 首选 | 次选 | 理由 |
|------|------|------|------|
| 东南亚制造业 | 香港 | 新加坡 | 中港税收协定股息预提5%，香港无资本利得税 |
| 全球多区域 | 新加坡 | 香港 | 新加坡税收协定网络更广（80+国） |
| 纯持股+退出 | BVI/Cayman | 香港 | 离岸地零税+退出无障碍，但需满足经济实质法 |
| IPO规划 | 开曼→香港→东道国 | — | 红筹/VIE上市标准路径 |

## 3. 容错与降级

### 3.1 输入不完整

| 缺失项 | 处理 |
|--------|------|
| target_country缺失 | [阻断]，必须提供 |
| investment_purpose缺失 | 提示选择，默认manufacturing |
| investment_amount缺失 | [阻断]，影响ODI审批路径判定 |
| holding_jurisdiction缺失 | 自动推荐，基于target_country+purpose |

### 3.2 SOFT_DEGRADED触发

当东道国投资法规信息不足时：
- **C层**：列出缺失信息项（如"XX国外商投资负面清单最新版未检索到"）
- **D层**：声明输出限制——"部分准入结论基于2024年数据，建议咨询目标国律师确认最新政策"
- **G层**：下一步建议——"建议联系XX国律所完成准入可行性确认"

## 4. 支持的目标国列表（首版）

### 4.1 高置信度国家（[已核实]）

| 地区 | 国家 |
|------|------|
| 东南亚 | 越南、泰国、印度尼西亚、马来西亚、新加坡、菲律宾 |
| 东亚 | 日本、韩国 |
| 南亚 | 印度 |
| 欧洲 | 德国、法国、英国、荷兰 |

### 4.2 中置信度国家（[参考来源]）

| 地区 | 国家 |
|------|------|
| 东南亚 | 缅甸、柬埔寨、老挝 |
| 中东 | 阿联酋、沙特阿拉伯 |
| 非洲 | 南非 |
| 拉美 | 墨西哥、巴西 |

### 4.3 低置信度国家（[需当地确认]）

不在上述列表中的国家，技能仍可尝试设计，但准入结论将标注为[需当地确认]。

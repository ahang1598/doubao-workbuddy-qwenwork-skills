# AI 敏感数据识别规则参考

本文档是 SKILL.md 工作流 A 阶段 4 的补充参考，包含降噪排除规则、误报场景处理和采样值校验规则的详细定义。

---

## 第一阶段：降噪排除规则

> ⚠️ 排除规则必须保守。只有字段名**完整语义**明确指向非敏感用途时才排除。如果字段 Comment 中提及敏感数据含义，即使字段名命中排除模式也必须保留。

| 排除类别 | 字段名特征 | 说明 |
|---------|-----------|------|
| **纯标识符** | 字段名为 `id` 或以 `_id`、`_uid`、`_uuid`、`_guid`、`_pk`、`_fk` 结尾 | 业务主键/外键，非数据本身 |
| **枚举/状态** | 以 `_type`、`_status`、`_state`、`_code`、`_flag`、`_level`、`_category`、`_kind`、`_mode` 结尾 | 枚举分类值 |
| **度量/统计** | 含 `count`、`cnt`、`amount`、`total`、`sum`、`avg`、`quantity`、`price`、`cost`、`fee`、`ratio`、`score`、`weight`、`rank` | 数值度量 |
| **时间** | 含 `time`、`timestamp`、`datetime`、以 `_at`/`_ts` 结尾、以 `created`/`updated`/`deleted`/`expired` 开头 | 时间字段 |
| **布尔** | 以 `is_`、`has_`、`can_` 开头 | 布尔标志 |
| **技术配置** | 含 `version`、`config`、`setting`、`param`、`schema`、`format`、`encoding`、`charset`、`partition`、`bucket`、`protocol` | 系统配置 |

> **注意**：含 `name`/`phone`/`email`/`address`/`card`/`account`/`passport`/`license`/`ssn` 等敏感关键词的字段，即使含 `_no`/`_number` 后缀也不应排除。

---

## 第二阶段：误报场景处理

> ⚠️ **必须以 ListLabels 实际返回的标签为准**，不要假设固定的标签列表。

**匹配方法**：对每个通过第一阶段的字段，遍历 ListLabels 返回的所有脱敏标签，利用标签的 `Name`（如 `class.phone_number`，提取 `.` 后的语义关键词）和 `Description`（如"手机号或固定电话号码"）进行语义匹配。

**减少误报的关键规则**：

| 易误报场景 | 正确处理 |
|-----------|---------|
| 字段含 `name` 但指向系统对象（`file_name`/`table_name`/`host_name`/`task_name`/`project_name`/`app_name`/`service_name`/`event_name`/`asset_name`） | 不匹配姓名类标签，仅当修饰词指向自然人（`user`/`customer`/`employee`/`contact`/`person`/`real`/`full`/`first`/`last`）时匹配 |
| 字段含 `address` 但指向技术地址（`mac_address`/`memory_address`/`ip_address`） | 不匹配地理位置类标签，`ip_address` 应匹配 IP 地址类标签 |
| 字段含 `url`/`link` 但为纯技术用途（`api_url`/`callback_url`/`redirect_url`/`endpoint`） | 不匹配 URL 类标签 |
| 字段含 `account` 但为属性（`account_type`/`payment_method`） | 不匹配金融账户类标签 |
| 字段含敏感关键词但以 `_type`/`_model`/`_brand`/`_template`/`_server` 结尾 | 属于该敏感数据的属性描述，非敏感数据本身，不匹配 |
| 各国特有证件类标签（如 `us_ssn`/`uk_nhs`/`de_id_card`/`au_tfn`/`br_cpf`） | 仅当字段描述或表上下文涉及对应国家时匹配 |

---

## 采样值校验规则

当 `FieldInfo.SampleValues` 非空时启用，用于交叉验证元数据匹配结论。

| 标签类别 | 采样值典型特征（用于确认匹配） | 不匹配特征（用于推翻误判） |
|---------|----------------------------|---------------------------|
| 中国手机号 | 11 位数字，以 `1[3-9]` 开头 | 长度不一、含字母、明显非手机号格式（如纯递增 ID） |
| 邮箱 | 含 `@` 且符合 `xx@xx.xx` 格式 | 全部不含 `@` |
| 中国身份证号 | 15 位或 18 位（末位可为 X） | 明显长度/格式不符 |
| IP 地址 | `xxx.xxx.xxx.xxx`（IPv4）或 IPv6 格式 | 非 IP 格式字符串 |
| 银行卡号 | 13~19 位纯数字 | 含字母或长度明显不符 |
| 姓名 | 2~4 个汉字 / 英文 First Last | 全是数字、过长（明显是描述）、值为系统名 |
| URL/链接 | 以 `http://` `https://` 开头 | 不符合 URL 格式 |
| 日期/出生日期 | `YYYY-MM-DD` 等日期格式 | 非日期格式 |

---

## 采样值与元数据匹配的判定规则

- 元数据匹配 + 采样值符合 → **强匹配**，直接纳入识别结果（识别依据标注「字段名+采样值」）
- 元数据匹配 + 采样值明显不符 → **推翻匹配**，作为误报排除（如字段名 `phone` 但采样值全是日期，则不打标）
- 元数据匹配 + 采样值缺失或为空 → **维持元数据匹配结论**，识别依据标注「字段名/描述」
- 元数据未匹配 + 采样值强烈指向某敏感类型（如全是 11 位手机号格式） → 仍可纳入候选，识别依据标注「采样值特征」，但需在输出中标注置信度较低供用户确认

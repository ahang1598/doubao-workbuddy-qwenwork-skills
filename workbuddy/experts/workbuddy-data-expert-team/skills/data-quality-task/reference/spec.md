# 数据质量任务领域规范（Data Quality Task）

> 本文件定义质量任务的**实体模型、YAML 规范、诊断决策树、自检清单**。字段以 `protocol/data-quality/service/data_quality_service.proto` 为准。

---

## 实体模型

```
Workspace
  └── 质量任务（DataQualityTask，绑定一张表）
        ├── 质量规则（table_rules / field_rules）
        │     ├── rule_type: system_template / custom_sql
        │     ├── dimension: completeness / accuracy / validity / uniqueness / consistency / timeliness
        │     └── trigger_condition: 满足条件 → 判定为异常
        ├── 版本（draft / published / abandoned）
        ├── 告警配置（AlarmChannels + AlertRuleNames，独立于 YAML）
        └── 被工作流引用（WorkflowRef）
```

---

## 枚举定义

- **VersionStatus**: draft(草稿) / published(已发布) / abandoned(已废弃)
- **ExecResultStatus**: passed(通过) / triggered(异常) / failed(执行失败) / not_executed(未执行)
- **ExecMode**: try_run(试运行) / scheduled(调度执行)
- **RuleType**: system_template(系统模板) / custom_sql(自定义SQL)
- **Dimension**: completeness(完整性) / accuracy(准确性) / validity(有效性) / uniqueness(唯一性) / consistency(一致性) / timeliness(时效性)

---

## RulesYaml 规范

> 对齐后端 `parser.go` 的 `YamlRuleBatchConfig` / `YamlRuleConfig` 结构。

### 关键纠偏（AI 易犯错点）

| 错误 | 正确 |
|------|------|
| 顶层写 `version`/`task`/`rules`/`alarm_channels` | 只有 `table_rules`/`field_rules` |
| 写 `scope`/`check_object`/`execution_order`/`filter_condition`/`trigger_level` | 这些字段不存在 |
| `trigger_condition: "> 0%"` | `"> 0"`（不支持百分比） |
| `system_template` 写 `dimension` | 禁止（system_template 不填 dimension） |
| `custom_sql` 的 `trigger_condition` 不带字段名 | 必须带（如 `cnt < 25`） |
| `FROM ${table_name}` | 必须三段式全称 |
| `filter_condition: "..."` | 字段名是 `filter` |

### 整体结构

```yaml
table_rules:          # 表级规则
  - rule_name: ...
    ...
field_rules:          # 字段级规则
  - field_name: <列名>
    rule_name: ...
    ...
```

- 两个列表至少一个非空，合计 ≤ 100 条
- `rule_name` 全局唯一（跨两个列表），≤128 字符

### YamlRuleConfig 字段定义

| 字段 | 必填 | 说明 |
|------|------|------|
| `rule_name` | | 全局唯一，≤128 字符 |
| `rule_type` | | `system_template` / `custom_sql` |
| `template_code` | system_template 时 | 必须来自 `ListDataQualityRuleTemplates` 真实值 |
| `custom_sql` | custom_sql 时 | ≤10000 字符，禁止分号/DDL/DML，FROM 必须三段式 |
| `dimension` | custom_sql 时 | `completeness`/`accuracy`/`validity`/`uniqueness`/`consistency`/`timeliness`；system_template **禁止**填 |
| `field_name` | field_rules 下 | 仅 `field_rules` 使用 |
| `trigger_condition` | （固定触发模板除外） | 见下方语法 |
| `filter` | — | WHERE 子句（不含 WHERE 关键字），禁止分号 |
| `params` | 部分模板 | 如 `enum_range_consistency` 必须 `enum_values` |
| `alert.enable` | — | 默认 `false` |

### trigger_condition 语法

**语义**：满足条件 → 判定为异常。

| 形式 | 示例 | 备注 |
|------|------|------|
| 简单比较 | `"> 100"` / `"== 0"` | 加引号 |
| 区间 | `not_between [1000, 5000000]` | `[`闭`(`开 |
| 组合 | `< 100 OR > 1000000` | |
| 带字段名 | `cnt < 25` | custom_sql **必须**用此形式 |

**不支持**：百分比 / `in(...)` / SQL 片段

### 固定触发模板（不写 trigger_condition）

| template_code | 必须提供 |
|---------------|---------|
| `data_timeliness` | 可选 `filter` |
| `enum_range_consistency` | **必须** `params.enum_values` |

### 正确写法示例

```yaml
table_rules:
  - rule_name: 表行数校验_预期不少于25行
    rule_type: custom_sql
    dimension: completeness
    custom_sql: |
      SELECT COUNT(*) AS cnt
      FROM DataLakeCatalog.jayden_ads.ads_monthly_sales_report
    trigger_condition: cnt < 25

field_rules:
  - field_name: gmv_mom_rate
    rule_name: GMV环比增长率空值检查
    rule_type: system_template
    template_code: null_rate
    trigger_condition: "> 0"
```

---

## 诊断决策树

强制输出三段式，匹配到第一个分支即输出：

```markdown
### 事实数据
- 规则/监控对象/触发条件/实际值/阈值/执行结果/执行时间

### 系统分析
- 匹配分支 + 推断

### 建议动作
```

### 分支定义

| 分支 | 条件 | 关键动作 |
|------|------|---------|
| A 执行失败 | `ExecResultStatus=failed` 或 `SubInstanceStatus=cancelled` | 查 `GetDataQualityRuleExecLog` |
| B 未执行 | `ExecResultStatus=not_executed` | 检查前序规则/启用状态 |
| C 严重异常 | `triggered` + 偏离≥50% | 自动追溯上游血缘 |
| D 边界异常 | `triggered` + 偏离<50% | 查历史，建议调阈值 |
| E 持续恶化 | `triggered` + 近5次全触发 + 单调恶化 | 必须追溯上游（最多3层） |
| F 通过但量异常 | `passed` + 数据量与历史差异>50% | 追溯上游，建议补规则 |
| G 正常 | `passed` + 平稳 | 规则通过 |

### 多规则诊断

按 `TriggerLevel`（high→medium→low）排序，同级先 `failed` 再 `triggered`，每条独立三段式，最后整体总结。

---

## 自检清单（14 项）

调 `wedatacli quality-task create` 前逐项核对：

**YAML 11 项**：
1. 顶层只有 `table_rules`/`field_rules`
2. 任务元信息在请求顶层不在 YAML
3. 表级无 `field_name`、字段级有
4. 无 `scope`/`check_object`/`execution_order`/`filter_condition`
5. 过滤条件用 `filter`
6. `system_template` 无 `dimension`、`custom_sql` 有且为英文枚举
7. `template_code` — 仅 `system_template` 时需查 `ListDataQualityRuleTemplates` 确认真实值；`custom_sql` 跳过此步
8. 阈值纯数值无 `%`
9. `between` 括号语义正确
10. `custom_sql` 的 `trigger_condition` 带字段名前缀
11. 固定触发模板不写 `trigger_condition`

**告警 3 项**：
12. `AlarmChannels`/`AlertRuleNames` 在请求顶层、不在 YAML 内
13. `ChannelId` 由 `prepare_create` 返回的 `notifications` 中获取
14. `AlertRuleNames` 精确匹配 YAML 中 `rule_name`

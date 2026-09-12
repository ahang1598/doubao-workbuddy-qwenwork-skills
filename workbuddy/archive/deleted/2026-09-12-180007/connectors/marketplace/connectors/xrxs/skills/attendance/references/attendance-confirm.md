# attendance 考勤确认

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

考勤确认。发放记录的创建、查询、明细、撤回,提醒发送,以及方案、账套月份、通知渠道等前置数据查询。

## 🔄 核心场景

#### 发放考勤确认并跟进至全员确认

按账套月份发放考勤确认,查询发放记录并催办未确认员工,跟进至 100% 确认。

**发放并跟进至全员确认**

**步骤 1**: `getConfirmAvailableMonthList` - 获取可发放的账套月份列表(data[] 为 yyyyMM 整数数组),取目标 **yearmo**
**步骤 2**: `getConfirmSendPlanList` - 获取可用考勤确认方案(data[] 含 planId/version/planName),选取目标方案,取 **confirmPlanId**(=planId)、**version**、**planName**
**步骤 3**: `sendConfirmNotifyPreview` - 预览发放,入参与正式发放相同:**yearmo** + **sendPlanAndNames[]**(每项 **confirmPlanId**=步骤2 planId、**version**=步骤2 version、**distributeName**=发放名称);**distributeName** 必填(1~40 字符),用户未指明考勤确认单名称时按 `yearmo-planName` 主动生成(如 `202606-智能创作中心考勤确认`);返回发放月份、方案数与明细,不实际发放
**步骤 4**: `sendConfirmNotify` - 发放考勤确认通知并创建发放记录(入参与步骤3预览一致,确认预览无误后调用)
**步骤 5**: `getConfirmRecordList` - 查询发放批次,取 **recordId** 与发放状态
**步骤 6**: `getConfirmRecordDetailList` - 按 recordId 分页查员工级发放明细,按已读/确认/发放失败等状态筛选未确认员工,取 **recordDetailId**
**步骤 7**: `getConfirmRemindChannelList` - 获取该记录已启用的通知渠道(员工端/钉钉/企微等)
**步骤 8**: `sendConfirmRemind` - 对未确认员工发送提醒(入参 recordId + distributeTypeList 渠道),跟进至 100% 确认

> 💡 `sendConfirmNotify` 与 `sendConfirmRemind` 均有 preview 接口,正式操作前建议先预览;整批撤回用 `withdrawAllConfirmRecords`,单人撤回用 `withdrawOneConfirmRecord`。`distributeName` 必填(1~40 字符),用户未指明考勤确认单名称时按 `yearmo-planName` 主动生成(如 `202606-智能创作中心考勤确认`),planName 来自 `getConfirmSendPlanList`。`sendConfirmNotify` 目标月份必须已有归档记录,同一管理员账号 1 分钟内只能发放一次。

## 命令

### sendConfirmNotify

按账套月份和考勤确认方案创建发放记录，并向方案覆盖的员工发送确认通知。 调用前先通过 ajax-get-confirm-available-month-list.json 获取可用账套月份， 通过 ajax-get-confirm-send-plan-list.json 获取方案； 目标月份必须已有归档记录，同一管理员账号 1 分钟内只能发放一次。

```bash
xrxs-cli attendance sendConfirmNotify --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### sendConfirmNotifyPreview

是否确认发放考勤确认使用与正式发放接口相同的请求参数，返回发放月份、方案数量以及所选方案明细。 本接口只读取当前可发放方案，不加发放锁、不创建记录，也不发送通知。

```bash
xrxs-cli attendance sendConfirmNotifyPreview --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getConfirmRecordList

查询指定账套月份下的全部考勤确认发放批次，用于获取 recordId、发放状态和发放信息。 返回的 recordId 可继续用于查询员工明细、发送提醒或撤回整批记录。

```bash
xrxs-cli attendance getConfirmRecordList --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getConfirmRecordDetailList

按发放记录 ID 分页查询员工级发放明细，支持员工关键字和已读、确认、发放失败等状态筛选。 recordId 由 ajax-get-confirm-record-list.json 获取，返回的 recordDetailId 可用于查询单个员工详情或撤回单条明细。

```bash
xrxs-cli attendance getConfirmRecordDetailList --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### withdrawAllConfirmRecords

撤回指定发放记录下的全部员工考勤确认。该操作会修改已发放数据， Agent 仅应在用户明确要求撤回整批记录并确认 recordId 后调用。

```bash
xrxs-cli attendance withdrawAllConfirmRecords --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### withdrawOneConfirmRecord

仅撤回指定员工发放明细，不影响同一发放批次中的其他员工。 该操作会修改已发放数据，recordDetailId 应从 ajax-get-confirm-record-detail-list.json 的结果中取得。

```bash
xrxs-cli attendance withdrawOneConfirmRecord --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### getConfirmRecordDetail

根据员工发放明细 ID 查询该员工收到的考勤确认内容、字段和值。 调用前先通过 ajax-get-confirm-record-detail-list.json 获取 recordDetailId。

```bash
xrxs-cli attendance getConfirmRecordDetail --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### sendConfirmRemind

对指定发放记录中的未确认员工手动发送提醒，并按 distributeTypeList 选择通知渠道。 调用前先通过 ajax-get-confirm-remind-channel-list.json 获取该记录支持的渠道； 每条发放记录每天只能提醒一次。

```bash
xrxs-cli attendance sendConfirmRemind --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### sendConfirmRemindPreview

是否确认提醒员工进行考勤确认使用与正式提醒接口相同的参数，汇总展示月份、方案数和待确认人数， 明细展示报表月份、考勤方案、确认单名称、待确认人数及提醒渠道。 本接口不获取每日提醒锁，也不发送提醒。

```bash
xrxs-cli attendance sendConfirmRemindPreview --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getConfirmAvailableMonthList

返回当前公司已有考勤归档的账套月份；尚无历史归档时返回活动账套月份。 该接口是查询发放记录和创建考勤确认发放前的账套月份数据源。

```bash
xrxs-cli attendance getConfirmAvailableMonthList [flags]
```

- schema 未声明入参,可直接调用。


### getConfirmSendPlanList

返回当前公司可用的考勤确认方案、方案字段中文名称、公告配置和方案版本。 调用 ajax-send-confirm-notify.json 前，应先使用本接口选择 confirmPlanId 并保留对应 version。

```bash
xrxs-cli attendance getConfirmSendPlanList [flags]
```

- schema 未声明入参,可直接调用。


### getConfirmRemindChannelList

根据发放记录关联的确认方案，返回该记录已启用的员工端、钉钉、企业微信等通知渠道。 返回结果的渠道 key 可作为 ajax-send-confirm-remind.json 的 distributeTypeList。 常见渠道 key 包括 employeeClient（员工端）、workEmail（工作邮箱）、 personEmail（个人邮箱）、dismissEmail（离职邮箱）、dTalk（钉钉）、 workWeiXin（企业微信）、lark（飞书）、cloudHub（云之家）和 weaver（泛微）； Map 的 value 包含 value（是否启用）、desc（展示名称）和 sort（展示顺序）。

```bash
xrxs-cli attendance getConfirmRemindChannelList --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


## 参考
- [attendance](../SKILL.md) - 全部命令

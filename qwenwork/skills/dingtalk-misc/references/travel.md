# 差旅参考

差旅（travel）CLI 用于显式调用钉钉AI差旅 MCP 服务。

## 能力范围与路由

差旅（AI差旅）仅提供 2 项专属能力，全部归本 skill：

| 用户意图 | 能力 | 命令面 |
|---|---|---|
| 查询出差模版列表 / 查询出差流程列表 / 查出差审批流程模版 | 查询企业 OA 出差模版列表，为提交出差单选定模版 | `dws travel process list` |
| 提交出差单 / 提交出差审批 / 创建出差审批 / 提交出差申请 | 根据出差事由、审批模板 CODE 与行程列表自动提交出差审批单，返回单据实例 ID 与详情页 URL | `dws travel process submit` |

- 提交出差单、提交出差审批是 travel 专属能力：不要用 `oa` 审批代做（`oa` 只承接报销、采购、用印等通用审批），也不要落回 `attendance` 考勤模板入口（请假/加班/外出/补卡才走考勤审批）。
- 仅查询已提交的出差/外出审批记录，不属于本 skill。
- 用户要提交出差单时，不要改用 `oa` 或考勤模板入口代提交出差。
- 前置约束：组织没有出差套件流程模版（`dws travel process list` 返回空列表）时，不能走本 skill 的提单能力——`travel process submit` 依赖审批模板 CODE，无模版即无从提单；此时可以考虑改用 `dws oa` 命令提交普通单据。

## 服务与工具

- MCP 服务：`travel`（AI差旅）
- MCP 工具：`queryTravelOaTemplateList`（查询企业的OA出差模版列表，仅返回当前用户可见且已发布的模版，按最近一次发布时间倒序，默认返回 10 个）
- MCP 工具：`autoSubmitApprovalProcess`（提交出差审批单：按出差事由、审批模板 CODE、行程列表自动提交；自动提单成功返回单据实例 ID 与详情页 URL，部分成功返回单据草稿详情页 URL）

## 命令示例

```bash
# 查询企业出差单模版列表
dws travel process list

# 按模版标题关键字过滤，并限制返回数量
dws travel process list --name-keyword 拜访客户出差 --max-count 3

# 提交出差审批单（单行程）
dws travel process submit --reason 拜访客户X公司 --process-code PROC-24BBEB93-F5AE-476F-A3EA-F5AC4120E522 --itineraries '[{"departureTime":"2026-08-11 08:00:00","singleOrReturn":"单程","placeOfDeparture":"杭州","destination":"上海","returnTime":"2026-08-12 18:00:00","vehicle":"TRAIN"}]'

# 提交出差审批单（多行程，跨段拼接）
dws travel process submit \
  --reason 北京客户拜访 \
  --process-code PROC-24BBEB93-F5AE-476F-A3EA-F5AC4120E522 \
  --itineraries '[{"departureTime":"2026-08-11 08:00:00","singleOrReturn":"单程","placeOfDeparture":"杭州","destination":"上海","returnTime":"2026-08-12 18:00:00","vehicle":"TRAIN"},{"departureTime":"2026-08-13 08:00:00","singleOrReturn":"单程","placeOfDeparture":"上海","destination":"北京","returnTime":"2026-08-15 18:00:00","vehicle":"FLIGHT"}]'
```

## 提交出差单要点

- `--reason`（出差事由）、`--process-code`（审批模板 CODE）、`--itineraries`（行程 JSON 数组，至少一个行程对象）均为必填；审批模板 CODE 先用 `dws travel process list` 查询获取，查询结果为空说明组织未配置出差套件流程模版，此时不能提单，改用 `dws oa` 提交普通单据。
- 行程对象必填字段：`departureTime`（出发时间，格式 yyyy-mm-dd hh:mi:ss；时间粒度为半天时，上午出发建议 8 点、中午出发建议 12 点）、`returnTime`（返回时间；上午到达建议 12 点、下午到达建议 18 点）、`placeOfDeparture`（出发城市中文名，如 杭州）、`destination`（目的地城市中文名，如 北京）、`singleOrReturn`（"单程" 或 "往返"）、`vehicle`（FLIGHT 飞机 / TRAIN 火车；市内自驾、打车等场景按火车填写）。
- `--dept-id` 可选，缺省取员工主部门；企业/用户身份由服务端按登录态推导，无需 CLI 传入；`--args` 可透传额外 JSON 参数。
- 提交是写操作且需用户确认：交互终端会提示确认；agent/CI 等非交互环境必须在用户明确确认后追加 `--yes` 执行。
- 执行结果三种情况：自动提单成功，返回 `result.instanceId` 与 `result.detailUrl`；部分成功（草稿），仅返回 `result.detailUrl`，需访问草稿详情页补充信息后重新提交；自动提单与保存草稿均失败时两者为空，查看 `result.createStatusEnum`、`result.createStatusTip` 与 `errorCode`、`errorMsg` 定位原因。

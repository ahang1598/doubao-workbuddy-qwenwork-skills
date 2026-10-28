# 钉钉招聘

`dws recruit` 是独立的招聘私有产品能力，与教育产品同级。它封装招聘 MCP 的 13
个工具，覆盖职位、招聘候选人、公司/个人人才库及其标签、归档原因和简历渠道，而不是公共产品下的三个
职位命令。身份信封字段由登录态和 Connector 注入，不要让用户填写 `corpId`、
`bizCode`、`opUserId` 或当前操作人 `userId`。

## 路由

| 用户意图 | 命令 |
|---|---|
| 筛选职位 | `dws recruit job list` |
| 查看一个职位 | `dws recruit job get` |
| 创建职位 | `dws recruit job create` |
| 修改职位内容 | `dws recruit job update` |
| 开放、重新开放或关闭职位 | `dws recruit job set-status` |
| 筛选正在招聘流程中的候选人 | `dws recruit candidate list` |
| 查看候选人的完整流程详情 | `dws recruit candidate get` |
| 查询企业共享人才库 | `dws recruit talent company list` |
| 查询当前操作人的个人人才库 | `dws recruit talent personal list` |
| 查看个人人才库完整简历 | `dws recruit talent personal get` |
| 查找人才或流程标签 ID | `dws recruit tag list` |
| 查询人才归档原因编码 | `dws recruit archive-reason list` |
| 查询简历渠道 code | `dws recruit resume-channel list` |

所有命令都应加 `--format json`。未列出的可选筛选条件以对应 `--help` 和 leaf
Schema 为准。

## 职位读取与写入

```bash
dws recruit job list --keyword "Java" --status open --size 20 --format json
dws recruit job get --job-id JOB_ID --format json
dws recruit job create --from ./job.json --dry-run --format json
dws recruit job update --job-id JOB_ID --from ./job-update.json --dry-run --format json
dws recruit job set-status --job-id JOB_ID --status closed --dry-run --format json
```

列表首页不传 `--cursor`，续页使用响应中的 `meta.pagination.next_token`。详情、更新
和状态修改的 `jobId` 必须来自真实列表或业务上下文。

创建、更新和状态修改会写入远端。先用 `--dry-run` 展示将要执行的动作，实际执行
前取得明确确认并交由 CLI 确认流程处理。更新 JSON 是部分更新：只包含用户明确要
改变的字段，省略字段保持不变，不传 `null`。`set-status` 只接受 `open` 或
`closed`，分别映射到 MCP 的 1 和 2；其他职位内容变化使用 `job update`。

创建 JSON 必填 `name`、`description`、`jobNature`、`requiredEdu`、`extData`、
`creatorUserId`。`campus` 未提供或为 `null` 时 CLI 默认补为 `false`；只有用户或
业务上下文明确信息为校招职位时才传 `true`。`creatorUserId` 和可选
`ownerUserIds` 必须来自当前 profile 下的真实通讯录结果，禁止猜测。JSON 文件只写
业务对象，不写 MCP 外层参数名或身份字段。

## 招聘候选人

```bash
dws recruit candidate list --keyword "Java" --query-scope recruiting --page-size 20 --format json
dws recruit candidate get --candidate-id CANDIDATE_ID --format json
```

`candidate list` 可按姓名、手机号、职位、学历、学校、公司、工作年限、简历标签、
渠道、招聘范围和流程状态等筛选，单页范围 1–200。先从列表取得真实
`candidateId`，再查询候选人的简历、应聘职位、流程节点、面试、评价、Offer 和
备注。

## 公司人才库与个人人才库

```bash
dws recruit talent company list --query-scope recruiting --keyword "Java" --page-size 10 --format json
dws recruit talent personal list --keyword "Java" --page-size 20 --format json
dws recruit talent personal get --resume-id RESUME_ID --format json
```

公司人才库是企业内有权限访问的共享范围，`query-scope` 支持 `all`、
`unMatchedJob`、`recruiting`、`archived`、`dimission`，不同范围允许的筛选参数
不同，CLI 会拒绝无效组合。个人人才库是当前操作人维护的范围；需要完整简历时，
必须使用其列表返回的真实 `resumeId`，不要混用 `candidateId`、`talentUid`、附件
文件 ID 或公司人才库中的标识。

## 标签、归档原因与简历渠道

```bash
dws recruit tag list --source custom --keyword "Java" --size 20 --format json
dws recruit tag list --source flow --size 20 --format json
dws recruit archive-reason list --format json
dws recruit resume-channel list --format json
```

标签返回 `data.tags`。`source=custom`（默认）查询人才标签，其 `tagId` 用于公司
人才库 `--tag-ids`；`source=flow` 查询流程标签，其 `tagId` 用于 `--flow-tag-ids`。
名称只做模糊匹配，同名标签须结合返回信息区分，不能直接选第一项。`--size` 接受
1–200，默认或传 0 使用 200。`--cursor` 是非负整数，首次省略或传 0；续页保持
`source`、`keyword` 不变，将 `meta.pagination.next_token` 原样回填，不按页码递增。

归档原因返回 `data.reasons`，包含系统和企业自定义选项；将 `reasonCode` 用于
公司人才库 `--query-scope archived` 下的 `--archive-reasons`。简历渠道返回
`data.channels`，将 `code` 用于公司人才库 `--resume-channels`。这两个查询均无
业务入参、不分页，保留名称、分组、类型和启用状态等原始信息，选择前核对可用性。
不要把标签 `tagId` 当作个人人才库 `--resume-tags` 的标签值，或把渠道 code 当作
`--resume-sources` 的整数来源类型；不要猜测 ID 或编码。

候选人与人才库响应可能包含手机号、邮箱、生日、教育和工作经历、评价、Offer、
备注及附件，均按敏感个人信息处理；只输出完成用户请求所需的字段，不扩散原始
简历数据。

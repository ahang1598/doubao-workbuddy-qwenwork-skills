# 学校社团真实性核验协议

## 1. 适用条件

用户给出具体学校、学院、书院或校区，并要求推荐真实社团、查询招新或准备某社团选拔时，
必须执行本协议。学校未唯一定位前，不开始生成具体校内社团名单。

## 2. 来源优先级

按以下顺序找来源：

1. 学校官网的校团委、学生工作部、社团管理部门、书院或学院页面；
2. 学校官方社团名录、年审名单、星级评定、招新公告、百团大战/社团文化节页面；
3. 由学校官网明确链接或认证的社团官方公开账号与招新页；
4. 学校官方新闻中对社团活动、获奖或换届的报道；
5. 公开社交平台、论坛和学生经验帖，只能作为线索，不能单独确认存在。

优先使用原始页面。搜索结果摘要、AI 摘要、转载和聚合名单只用于定位，不作为最终证据。

## 3. 查询策略

先确定学校官网域名，再组合少量定向查询：

```text
site:<官方域名> 学生社团 名单
site:<官方域名> 团委 社团 招新
site:<官方域名> 社团 年审
site:<官方域名> 百团大战 <年份>
<学校官方全称> <社团名称> 招新
```

使用 `general_search` 定位，再用 `web.fetch` 打开原始页面。动态页面无法读取时，可保存
页面标题、URL 和访问失败状态，并寻找同一主管单位的其他官方页面。不要循环猜 URL、绕过
验证码或付费墙。

## 4. 单个社团证据记录

```yaml
club_name: string
school: string
campus: string | unknown
supervising_unit: string | unknown
verification_status: verified_current | verified_exists | probable | stale | unverified | conflict
recruitment_status: open | announced | closed | unknown
selection_process: open_enrollment | interview | audition | written_test | mixed | unknown
checked_at: YYYY-MM-DD
sources:
  - title: string
    url: https://...
    publisher: string
    published_or_updated_at: YYYY-MM-DD | unknown
    source_type: school_official | supervising_unit | verified_club_account | school_news | community_lead
    supports: [existence, campus, recruitment, schedule, selection_process]
    limitation: string | null
```

来源必须能直接支持所绑定字段。活动新闻可支持“当时存在”，但不能自动支持“本期正在招新”；
社团自己的公开账号可支持近期活动线索，但若无法确认学校认证关系，不足以单独标记
`verified_exists`。

## 5. 时效规则

以访问日为基准：

- `verified_current`：本学年或近 12 个月学校官方名录、年审或招新信息；
- `verified_exists`：近 36 个月官方存在证据；无日期名录不能单独证明当前存在，需降级为 `unverified` 或 `stale`；
- `stale`：唯一官方证据超过 36 个月，且没有近期官方活动/年审/招新补强；
- `conflict`：官方来源之间对名称、校区、存续或招新方式存在无法解释的冲突。

“页面仍可访问”不等于“信息仍有效”。招新截止日期、报名二维码和群号等变化快的字段必须
单独核验。

## 6. 停止与降级

遇到以下情况，停止确定性推荐：

- 学校同名且用户没有确认城市/校区；
- 官网不可达，且没有可替代的官方主管单位页面；
- 只能找到学生自媒体、论坛或商业聚合页；
- 官方来源显示社团暂停、注销或年审不合格；
- 当前招新时间、报名方式或选拔形式互相冲突。

输出已查查询、访问日期、找到的线索和仍需用户提供的官方材料。可继续推荐“社团类型”，
但不得把线索名称写成该校确定存在的社团。

## 7. 隐私门

查询只包含学校、校区、社团名称/类别、年份和公开事件。不发送用户姓名、学号、专业、性格
偏好、可用时段、个人故事或联系方式。不得进入封闭群、私域招新群或非公开通讯录核验。

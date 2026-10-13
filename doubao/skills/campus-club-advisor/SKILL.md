---
name: campus-club-advisor
description: "当学生想探索适合自己的校园社团、核验指定学校的公开社团信息，或为已选社团准备报名与选拔时使用。根据兴趣、互动偏好、可投入时间、技能和目标给出可解释候选；不处理企业求职、升学选校、论文选题、心理测评、校园活动日程或社团负责人运营任务。"
---

# 校园社团匹配与面试准备

## 目标

把新生的兴趣、社交与协作偏好、时间预算、已有技能和成长目标转成可解释的社团候选；
用户给出学校时，只把有公开证据支持的真实社团列为校内候选，并按已核验的招新形式准备。

遵守四条原则：

1. 先理解用户，再推荐；只收集会改变选择的必要信息。
2. 把个人匹配度与社团真实性、信息时效分开，不能用一个总分掩盖未知。
3. 性格只表示用户自述偏好，不做临床判断，也不把“内向/外向”当成排除条件。
4. 不编造社团、招新时间、报名链接、面试题、活动强度或录取承诺。

## 路由边界

按当前主交付物路由，不按“面试”“推荐”“学校”等单个词命中。

| 主交付物 | 路由 |
| --- | --- |
| 校园社团类型或真实校内社团的匹配、比较、招新准备 | 本 Skill |
| 企业、实习、校招、研究生复试或公务员面试 | 对应求职/升学面试能力 |
| 学校、专业、导师、留学项目的申请匹配 | 对应院校/项目匹配能力 |
| 研究方向、论文题目或开题计划 | `paper-research-opening` |
| 对既定论文题目评分 | `doubao-academic-evaluator` |
| 某天校园活动、讲座、比赛日程 | 通用校园信息检索能力 |
| 社团负责人要制定招新流程、排班、招新文案、面试题或摊位话术 | `build-club-recruitment-kit` |
| 社团章程、财务制度、会员管理或全年运营方案 | 通用写作/运营能力 |
| MBTI、临床人格或心理健康评估 | 专门心理测评或健康能力 |

混合请求只处理社团选择与社团招新准备部分，并清楚列出 handoff。不要把社团经历包装成
求职材料，除非用户另行要求并切换能力。

## 首轮交互

用户只输入 `/campus-club-advisor` 或没有提供必要信息时，回复：

```text
我们先确定推荐范围。

你想按哪所学校和校区的真实社团来匹配，还是先做通用的社团类型探索？
```

随后每轮只问一个主问题，最多用 5 轮补齐会改变推荐的缺口。用户已提供的信息不要重复
追问；若用户希望快速推荐，可在明确标注未知项后继续。

## 输入契约

将信息整理为 `StudentClubProfile`：

| 字段 | 必要性 | 说明 |
| --- | --- | --- |
| `school`、`campus` | 学校定向时必需 | 使用学校官方全称；校区未知时标记 `unknown` |
| `interests` | 必需 | 2-6 个愿意持续投入的主题，而非只问“喜欢什么” |
| `personality_preferences` | 推荐 | 大组/小组、公开表达/幕后创作、结构化/自由探索等偏好 |
| `time` | 必需 | 每周小时、可用时段、考试周或通勤限制 |
| `skills.have` | 推荐 | 已有技能与大致熟练度 |
| `skills.want_to_learn` | 推荐 | 希望在社团中发展的技能 |
| `goals` | 必需 | 交友、作品、比赛、公益、运动、领导力等，可多选并排序 |
| `hard_constraints` | 推荐 | 最大周投入、健康/无障碍、校区、费用或明确避开项 |

不得要求姓名、学号、手机号、宿舍、身份证、精确课程表或账号密码。读取完整字段和同义词
归一化规则时，使用 [references/recommendation-framework.md](references/recommendation-framework.md)。

## 标准工作流

### P0. 确认范围与边界

1. 判断是通用社团类型探索、指定学校真实社团匹配、候选比较，还是招新准备。
2. 收集最少必要画像；把未知写成 `unknown`，不从专业、性别或人格标签推断。
3. 询问用户最多想同时认真参与几个社团，默认建议“1 个主投入 + 1 个低负担探索”，不把
   加入数量当作越多越好。

### P1. 核验学校与候选社团

用户给出具体学校或可唯一定位的校区时，本阶段为强制步骤。完整执行
[references/school-club-verification.md](references/school-club-verification.md)：

1. 先确认学校官方全称、校区和官网域名，处理同名学校。
2. 用已挂载的 `general_search` 定位学校官网、校团委/学生工作部门、官方社团名录、学校
   官方招新公告或受学校认证的公开账号；再用 `web.fetch` 打开原始页面核验。
3. 搜索只发送学校、校区、社团类别和公开查询词，不发送用户画像或身份信息。
4. 每个候选记录名称、主管/挂靠单位、校区、来源标题、URL、发布日期、访问日期、招新
   状态和证据限制。
5. 至少有一条学校官方或校内主管单位来源，且该来源不超过 36 个月，才能标记 `verified_exists`；只有本学年或近 12 个月的官方名录/招新信息才能标记 `verified_current`。
6. 只有旧来源、非官方线索或来源冲突时，分别标记 `stale`、`probable` 或 `conflict`，
   不作为“已确认真实且正在招新”的事实。

未挂载联网工具、官方页面不可达或学校无法唯一定位时，不从记忆生成该校社团名单。请求
用户提供官方名录/招新链接，或退回“社团类型建议”，并保留 `unverified`。

### P2. 建立候选卡

为每个候选建立 `ClubCandidate`，至少包含：

- `attributes.interests`、`environment_tags`、`goals`；
- `useful_skills`、`skill_opportunities`；
- `expected_hours_per_week`、`meeting_periods`、校区、费用和通勤信息；
- `selection_process`：open_enrollment / interview / audition / written_test / unknown；
- `verification.status` 与证据数组。

未知字段保持空值，不把同类社团的一般特征套给具体社团。可从
[assets/profile-and-clubs-template.json](assets/profile-and-clubs-template.json) 复制结构。

### P3. 匹配、过滤与排序

先应用硬约束，再分别计算兴趣、目标、互动环境、技能和时间五个维度。执行：

```bash
python3 scripts/validate_club_packet.py --input profile-and-clubs.json --kind input
python3 scripts/score_clubs.py \
  --input profile-and-clubs.json \
  --output ranked-clubs.json \
  --markdown ranked-clubs.md
```

严格遵守以下规则：

- 时间超上限、固定时段完全冲突、不可接受的费用/地点/活动标签属于 veto，不能被兴趣高分
  抵消。
- 匹配分只表示“适合该用户”，真实性状态单独展示，不把二者相加。
- 缺证据是 `unknown`，不是 `fail`；匹配覆盖率低于 60% 时，不给确定性排序。
- `verified_current` 和 `verified_exists` 可进入推荐区；后者必须提示“本期招新待确认”。超过 36 个月的唯一官方证据只能标记 `stale`，不得进入推荐区。
- `probable`、`stale`、`unverified`、`conflict` 只进入待核验区。
- 至少保留一个“稳妥匹配”和一个合理的“探索选项”；探索选项仍必须满足硬约束。

评分定义、同义词归一化和状态解释见
[references/recommendation-framework.md](references/recommendation-framework.md)。

### P4. 给出可行动推荐

默认给 3-5 个候选，按 [assets/recommendation-report-template.md](assets/recommendation-report-template.md)
输出。每个候选写清：

1. 为什么适合：只连接到用户明确说过的兴趣、目标、偏好或技能。
2. 可能不适合：时间、社交强度、费用、校区、技能门槛或证据缺口。
3. 真实性与时效：状态、访问日期和官方来源链接。
4. 下一步：参加体验活动、联系官方渠道、准备材料或确认本期招新。

不要展示原始 JSON、内部权重或冗长计算过程，除非用户明确要求。不要暗示推荐结果等于录取
概率、未来职业收益或人格定论。

### P5. 准备招新流程

仅对用户选定的 1-2 个社团进入本阶段。先核验该社团实际采用面试、笔试、试演、作品集、
体能测试还是开放报名；无法核验时将问题标为“通用预测”，不能说是该社团往年真题。

读取 [references/recruitment-preparation.md](references/recruitment-preparation.md)，完成：

1. 从用户真实经历建立 4-6 个证据故事：兴趣起点、合作、主动性、挫折反思、技能作品、
   时间承诺。允许没有正式社团经历。
2. 生成 45-60 秒自我介绍、5-8 个高概率问题、回答要点、可向社团反问的问题。
3. 用 `背景-行动-结果-反思` 组织故事；没有量化结果时使用可观察结果，不编数字。
4. 模拟面试每次只问一题，等待用户回答，再按相关性、具体性、真实性、表达四项反馈。
5. 若实际是试演/作品集/笔试，改为相应准备清单，不强行套面试模板。

## 路由与工具门禁

- 仅在主交付物是校园社团探索、具体学校社团核验、候选比较或社团报名/选拔准备时触发。
- 若主请求是企业求职面试、升学选校、论文选题、心理测评、校园活动日程或社团负责人运营，停止本 Skill 主流程并交给对应能力。
- 具体学校请求必须先调用 `general_search` 发现候选来源，再调用 `web.fetch` 读取原始页面；若工具缺失、页面不可达或学校不唯一，只输出社团类型建议或待核验线索。
- 通用类型探索不需要联网，但必须明确这是类型建议而非真实校内社团名单。
- 混合请求先完成社团匹配或选拔准备，再用一句话列出 handoff，不替其他能力执行提交、联系或运营操作。

## 输出与异常处理

输出 `recommendation-report-template.md` 的优先体验、探索选项、待核验和招新准备区块。每个真实校内候选同时展示匹配分、覆盖率、硬约束、真实性状态、访问日期和官方来源；不得把 `verified_exists` 写成当前招新已确认。

若学校、校区、来源、日期或招新状态存在缺口，标记 `unknown`、`stale`、`probable` 或 `conflict`，说明缺口和最小确认动作。不要用记忆补齐，不要因脚本失败继续生成旧排序文件。

## 隐私与安全

默认只处理当前豆包会话内的最小画像，只检索公开校园信息。

- 不把用户的性格偏好、课程表、个人经历或联系方式发送到公共搜索。
- 不访问封闭群、私人朋友圈、非公开通讯录、泄露名单或需绕过登录/验证码的页面。
- 官方报名表需要个人信息时，只提供填写建议；不得替用户提交、发送或保存敏感字段。
- 对身体条件、宗教、政治观点、民族、性取向、残障等敏感属性，不用于排除或推断，除非
  用户主动提出与安全/无障碍直接相关的硬约束。
- 不承诺“包过”，不伪造经历、证书、作品、技能水平或内部关系。

## 完成标准

只有同时满足以下条件才可称为“校内真实社团推荐”：

- 学校与校区已唯一定位；
- 每个推荐项有官方存在证据和访问日期；
- 匹配度、硬约束、真实性、招新状态分开呈现；
- 未知、冲突和旧信息均显式保留；
- 面试/试演准备基于真实经历，预测题已与官方信息区分；
- 给出可执行的下一步和官方来源，而非只列名称。

发布到豆包 ActionHub 前，按
[references/actionhub-routing.md](references/actionhub-routing.md) 执行正反例与混合请求验收。

## 脚本参数与调用

从 Skill 根目录运行脚本；`score_clubs.py` 会导入同目录的 `validate_club_packet.py`，发布和复制
时必须保留两个脚本的相对位置。

| 脚本 | 参数 | 默认值与关系 |
| --- | --- | --- |
| `validate_club_packet.py` | `--input PATH` 必填；`--kind {input,output}` 可选 | `--kind` 默认 `input`；参数间无互斥关系 |
| `score_clubs.py` | `--input PATH`、`--output PATH` 必填；`--markdown PATH` 可选 | `--markdown` 默认不生成；参数间无互斥关系；缺少 `weights` 时使用脚本内五维默认权重 |

先验证输入，再评分，最后验证 JSON 输出：

```bash
python3 scripts/validate_club_packet.py \
  --input profile-and-clubs.json \
  --kind input

python3 scripts/score_clubs.py \
  --input profile-and-clubs.json \
  --output ranked-clubs.json \
  --markdown ranked-clubs.md

python3 scripts/validate_club_packet.py \
  --input ranked-clubs.json \
  --kind output
```

验证或评分失败时保留标准输出中的 JSON 错误，停止后续步骤，不把已有旧输出当成本次结果。
运行前可用 `python3 scripts/<脚本名> --help` 查看当前参数。

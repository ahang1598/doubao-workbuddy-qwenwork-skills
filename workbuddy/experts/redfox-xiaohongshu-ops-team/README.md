# 小红书增长专家团 / Xiaohongshu Growth Expert Team

一站式小红书内容操盘团队：从灵感洞察、爆款对标、笔记生成、封面设计、文案诊断到账号优化诊断，按需求灵活组合。

## 类型

Team 型（多角色协作团队）

## 怎么用：先判需求，再选技能

编排前先读各 SKILL.md，确认每个 skill **是否自带数据** 与 **服务于哪类需求**。核心判断：
- `xiaohongshu-write` / `xiaohongshu-cover` **自带 2000+ 爆款数据** → 生成笔记/封面时直接调用，**不需要搜狐川先去外部采数**。
- 搜狐川的榜单/爬取/对标技能是**外部实时采数**，只服务于"灵感洞察 / 爆款对标"。

### 用户需求 → 技能组合矩阵
| 用户需求 | 要什么 | 技能组合 | 由谁执行 |
|---------|--------|---------|---------|
| 灵感洞察 | 现在什么火、该做什么选题 | dailytop / lowtop / top-account / crawler / similar-account（+ search） | 搜狐川 |
| 爆款对标 | 找标杆、对比爆款/竞品 | search / crawler / similar-account | 搜狐川 或 主理人 |
| 只是生成正文 | 一篇能发的笔记 | write（自带数据，无需外部采数） | 笔狐生 / 主理人 |
| 正文封面都需要 | 笔记 + 封面 | write + cover（均自带数据） | 笔狐生 / 主理人 |
| 文案诊断 | 标题评分 / 违禁词 / 改写 | title-score / prohibited-word / rewrite | 笔狐生 |
| 账号运营优化诊断 | 账号体检 + 优化建议 | account-analyzer → 诊断报告 | 诊狐康 |

## 成员与技能
| 成员 | 角色 | 技能 | 服务的需求 |
|------|------|------|-----------|
| redfox-xhs-he（主理人） | 操盘手/编排 | 统筹调度，可亲自调用任意 skill | 全部 |
| redfox-xhs-sou（搜狐川） | 灵感猎手 | top-account、dailytop、lowtop、crawler、similar-account、search | 灵感洞察、爆款对标 |
| redfox-xhs-bi（笔狐生） | 内容创作 | write、cover、rewrite、title-score、prohibited-word | 生成正文、正文+封面、文案诊断 |
| redfox-xhs-zhen（诊狐康） | 账号诊断 | account-analyzer | 账号运营优化诊断 |
| redfox-xhs-cai（采狐生） | 素材下载 | video-downloader | 视频下载 |

## 技能能力与数据来源
| 技能 | 自带数据 | 功能 |
|------|---------|------|
| xiaohongshu-write | ✅ 内置 2000+ 爆款，拉最多 50 条当种子 | 生成 标题3-6+正文+标签5-10+爆款公式来源 |
| xiaohongshu-cover | ✅ 内置爆款封面数据 | 3 套封面方案+生图提示词（3:4 1080×1440） |
| xiaohongshu-search | 实时热门 | 关键词搜热门 |
| xiaohongshu-crawler | 实时作品 | 按关键词/日期爬竞品 |
| xiaohongshu-lowtop | TOP50 低粉爆款 | 找低粉黑马 |
| xiaohongshu-dailytop | TOP50 每日爆款 | 每日趋势 |
| xiaohongshu-top-account | TOP50 账号榜 | 账号榜单 |
| xiaohongshu-similar-account | 对标匹配 | 找同阶/标杆账号 |
| xiaohongshu-title-score | 分析 | 标题六维评分+生成 |
| xiaohongshu-prohibited-word | 词库 | 合规检测替换 |
| xiaohongshu-rewrite | 分析 | 改写成小红书风 |
| xiaohongshu-account-analyzer | 分析 | 七维账号诊断+HTML 报告 |

## 使用示例
- "基于爆款生成可直接发布的小红书笔记" → 生成类（write，按需 +cover）
- "帮我看看这个标题好不好" → 文案诊断（title-score）
- "最近美食探店有什么能抄的" → 灵感洞察（搜狐川）
- "诊断我的账号" → 账号运营优化诊断（诊狐康）

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\NPC-268\.workbuddy\plugins\marketplaces\my-experts\plugins/redfox-xiaohongshu-ops-team/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r redfox-xiaohongshu-ops-team.zip redfox-xiaohongshu-ops-team/
```

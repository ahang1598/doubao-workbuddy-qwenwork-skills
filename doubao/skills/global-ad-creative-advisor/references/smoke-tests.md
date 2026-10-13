# 冒烟用例集（触发与边界回归）

> 用途：每次改动 description、阶段流程、平台入口或能力边界后，用本文件回归触发判断与脚本可用性。本 Skill 定位为**公开情报查询/采集/结构化分析**，不承接创意创作产出。

## 1. should-trigger query（应命中本 Skill）

1. "我们做了一个 AI 音乐 App，想投印尼和巴西，帮我查一下当地同类型产品最近在投什么广告素材"——P1+P2 全流程查询。
2. "分析 Replika 在 Meta Ad Library 和 Google 透明度中心的在投视频，拆一下跑量素材的共性模式"——P2 素材查询 + 九维拆解/模式聚类（分析，非创作）。
3. "看看泰国市场这一周 TikTok 和 YouTube 上 AI 陪伴相关的原生热门内容有哪些、在搜什么词"——P3 近 7 天热点 + Trends 查询。
4. "帮我整理印尼市场 AI 音乐类目的 App Store/Google Play 榜单、评分评论和 iTunes 元数据"——P1 官方商店数据查询。
5. "把这几家同类型产品在欧盟的 TikTok 商业内容法定库和 Apple Ad Repository 记录导出来"——P2 DSA 法定库查询。

## 2. should-not-trigger query（不应命中 / 应转交）

1. "帮我在 TikTok Ads 后台把这条广告预算调到 50 美金"——账户操作，转 tiktok-ads / 投放执行类能力，本 Skill 不连账户。
2. "基于这份调研产出 3 个广告创意方向，写出分镜脚本和双语广告文案"——**创意创作产出（创意方向/分镜/文案/brief），本 Skill 只提供素材与模式分析输入，转创意策划/短视频脚本类能力**。
3. "给我写一份这轮投放的 creative brief"——brief 撰写不属于查询能力，转创意策划类能力。
4. "根据这份素材清单直接生成 3 条可投放成片视频"——成片制作，转创意视频/创意设计类能力。
5. "查一下 Similarweb 上 Mureka 的月访问量估算"——第三方商业数据，本 Skill 不接入，改走官方代理指标。
6. "用 Picuki 看看这个 Instagram 账号的隐藏内容"——第三方镜像/绕过登录，红线拒绝。

## 3. 边界输入（应按口径降级，不报错不编造）

1. **只给品类不给产品**：先按品类词做 P1 四层识别，收敛 Top3 后继续，并在报告标注"未指定我方产品，差异化矩阵以品类通用维度呈现"。
2. **非欧盟市场要求查 Apple Ad Repository / TikTok CCL**：脚本应主动报错提示法域，改走 App Store 搜索广告位抽样巡查 + Top Ads 免登录部分，并登记缺口。
3. **Meta/IG 页面弹登录墙**：不登录、不关弹窗、不绕，换官方公开入口；仍取不到则按实际数量展示并进覆盖缺口表，绝不用记忆或占位图凑数。
4. **用户只问一段**（如"只拆这几条广告""只看本周热点"）：从对应阶段切入，不强制全流程，但零登录、真实封面链接、零第三方、只分析不创作的口径不变。
5. **用户要求精确曝光/花费/ROI/月搜索量**：说明开放渠道不可得（D 级），只给页面显示档位与官方代理指标，不编数字。
6. **用户同时要创意产出**：先交付查询分析结果，再明确创意方向/分镜/文案/brief 需转交对应能力，不在本 Skill 内代做。

## 4. 脚本回归命令（改动后必跑，均应零报错）

```bash
cd scripts
python3 build_adlibrary_url.py --selftest
python3 build_openintel_urls.py --selftest
python3 build_trend_urls.py --selftest
# 红线：被禁主动探查入口必须被拒绝（退出码 2）
python3 build_trend_urls.py --source fb-watch --keyword x ; echo $?   # 期望 2
python3 build_trend_urls.py --source ig-tag --hashtag x ; echo $?     # 期望 2
# --plan 结果中不得出现 fb-watch / ig-tag / creativecenter 之外的广告后台入口
python3 build_trend_urls.py --plan --markets ID --keyword "lagu AI" --format tsv | cut -f1 | sort -u
```

## 5. 通过标准

- should-trigger 全部命中本 Skill，且只走查询/采集/分析路径，不产出创意方向、分镜、文案、brief、成片。
- should-not-trigger 全部正确拒绝或转交，尤其是创意创作类需求不得在本 Skill 内代做。
- 三个 selftest 全过；fb-watch/ig-tag 被 argparse 拒绝（退出码 2），fb-page/ig-profile/ig-reel 已知直链通道保留。
- 全包无 `assets/`、无 creative-brief 模板悬空引用；整目录 11 个文件、无 `__pycache__`。

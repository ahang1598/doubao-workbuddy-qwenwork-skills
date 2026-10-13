# P2 核心媒体平台付费创意物料采集手册（GG / Meta / TT / ASA + 搜索词包）

> 何时读取：P1 锁定 Top3 与检索计划后执行 P2，可与 P3 并行。目标：四个主线投放平台**每平台先建 Top10 采集/分析池（共约 40，不足说明原因），报告再按同类型产品分组、每个同类型产品展示 Top5 真实素材（带封面+原内容链接）**，并产出 GG/ASA/TT 搜索词包。本手册替代原"仅 Meta"版本，文件名沿用。
>
> **口径底线（先读）**：①全程零登录、零 MCP，只采公开可见内容，登录墙后内容不取、不绕验证；②商业广告无精确曝光/花费/出价/ROI，Meta total_impressions、TT 表现标签均为相对信号，**严禁写具体曝光数、花费、CTR、ROI**；③所有检索链接由脚本生成（Meta 用 `build_adlibrary_url.py`，其余三平台与搜索词用 `build_openintel_urls.py`），禁止手工硬拼；④素材仅用于内部分析展示，不下载搬运对外发布；⑤**每条展示物料必须带真实封面图 + 可点击原内容链接（字段见第 7 节、链接策略见第 9 节），严禁占位图/生成图/记忆图冒充，采不满按实采数量全列并登记缺口。**

## 目录
1. 核心媒体平台素材源总览（能力边界先看清）
2. Meta Ad Library 采集规范
3. Google Ads 透明度中心采集规范
4. TikTok：Top Ads + 欧盟商业内容库 + 站内赞助补充
5. ASA：欧盟 Ad Repository + 非欧盟 App Store 巡查
6. 搜索词包采集（GG / ASA / TT / Meta 反推）
7. 统一素材记录 schema（核心媒体平台对齐）
8. 优势素材判定规则（采集池每平台选 10，报告按同类型产品展示 Top5）
9. 通用采集 SOP 与截图规范
10. 常见坑与红线

## 1. 核心媒体平台素材源总览（能力边界先看清）

| 平台 | 零登录开放入口 | 能看到 | 核心限制（取不到就过滤+登记缺口） |
|---|---|---|---|
| Meta | Ad Library（facebook.com/ads/library） | FB/IG/Messenger/Audience Network 在投及历史素材、正文、标题、CTA、开投日、版本数、版位、相对展示排序 | 无曝光/花费/定向数值；模糊词会召回无关广告主，需人工核对 |
| Google Ads | Ads Transparency Center（adstransparency.google.com） | 按域名/广告主看 Search/Display/YouTube/Shopping/Maps 广告、素材、变体、最后展示时间、保留约 1 年 | **只支持域名/广告主、不支持关键词发现**；新广告延迟 48–72h；欧盟可见有限定向区间 |
| TikTok | ①Creative Center Top Ads ②欧盟/英/瑞 Commercial Content Library ③站内搜索"Sponsored/赞助"标记 | Top Ads：按地区/行业/目标/形式/周期筛选的授权热门样本；CCL：欧盟法定全量、可按广告主查 | **Top Ads 未登录仅展示前若干张卡片**，能采多少采多少；CCL 仅欧盟/英/瑞；均为广告主授权样本非全量；无花费 |
| ASA | ①Apple Ad Repository（adrepository.apple.com，**仅欧盟 DSA 法域**）②非欧盟：App Store 搜索结果顶部广告位逐词巡查 + 商店 listing | 欧盟：App/开发者在各国的版位（搜索结果/Search Tab/Today）、素材与本地化文案、定向维度、投放起止；非欧盟：某词下"谁在投、用哪套 listing 素材" | **ASA 全球无统一公开广告库**；非欧盟只能抽样巡查，拿不到出价/全量素材；ASA 素材本体=App Store listing（截图/预览视频/副标题/自定义产品页） |

> 平台官方入口与免登录等级的完整登记见 `05-creative-sources.md`；地区是否属欧盟决定 TT/ASA 走"法定全量库"还是"免登录替代链"。

## 2. Meta Ad Library 采集规范

### 2.1 链接（必须脚本生成）
`python3 scripts/build_adlibrary_url.py --keyword <词> --markets <ISO> --media-types video [--languages en] [--search-type page] [--format tsv --out meta_plan.tsv]`

> CLI 参数以脚本 argparse 为准：市场 `--markets`（可逗号分隔多个 ISO/ALL）、媒体类型 `--media-types`（all/image/video/meme/none）、在投状态 `--active-status`、检索方式 `--search-type`、版位 `--platforms`、语言 `--languages`；批量词用 `--keywords-file`。下表是 Ad Library **前台筛选概念**对照，帮助理解每个 CLI 参数在页面上对应什么。

| 参数 | 取值 | 说明 |
|---|---|---|
| active_status | active（默认，对标当下）/ inactive（复盘历史爆款）/ all | 不要混用排序后直接比较 |
| country | ALL / ISO 两位 | **分市场结论必须逐国检索**，ALL 看不出单国分布 |
| media_type | all / video / image / meme / none | 跑量视频用 video |
| search_type | keyword_unordered（默认模糊）/ keyword_exact_phrase / **page（看某同类型产品全部在投）** | 看单一同类型产品用 page + 其 Page 名 |
| sort | total_impressions + desc（默认保持） | 找优势素材不改成最近排序 |
| publisher_platforms / languages | facebook/instagram/…；ISO 639-1 | 可选限定版位/语言 |

### 2.2 采集要点
1. 按 P1 计划：每市场 ≥1 品类词 + Top3 品牌词（品牌词优先 `page` 精确检索）+ 1 本地痛点词。
2. 核对顶部筛选器（国家/媒体类型/active/总展示降序）；页面懒加载，**必须滚动**直到凑够目标条数（单次检索 ≤20 条防卡顿，不够就换词）。
3. 视频记录时长、封面与前 3 秒、是否口播/burned-in 字幕；点开 "N versions/See all versions" 记版本数与变体差异（换封面/换开头/换 CTA）。
4. 原内容链接：能取到单条 LIBRARY_ID 时用永久详情链接 `https://www.facebook.com/ads/library/?id=<LIBRARY_ID>`；**零登录列表视图通常不暴露单条 id，此时不伪造 id，改用脚本生成的带参检索页（country/active/media_type/排序齐全）作为"该批素材所在列表页"链接，并在报告注明口径**。
5. 浏览器注意：官方库深链偶发打不开/空白时，回到官方广告库检索页用相同筛选条件重新检索即可（**不做任何绕过、不清除或伪造会话**）；SPA 打开后等待 3–5s 渲染再截图。
6. 去重：同广告主同素材多版本合并为一条；在多个词/市场复现的记录复现词。

## 3. Google Ads 透明度中心采集规范

### 3.1 链接（脚本生成）
`python3 scripts/build_openintel_urls.py --source gg-transparency --market <ISO> --domain <同类型产品根域名> [--preset-date "Last 30 days"]`

### 3.2 采集要点
1. **优先域名**（覆盖同域名下全部广告账户），无域名才用广告主名；域名来自 P1 档案。
2. 页内分平台查看并分别记录：Search（文本广告：标题/描述/落地页）、YouTube（视频广告：视频/时长/最后展示）、Display（图文）、Shopping（商品）。
3. Region=目标市场；时间预设 Last 30 days（看当下）或 Any time（看投放跨度，P1 概览已用）；Format 分 video/text/image。
4. 记录：广告变体数、最后展示日期、各平台分布、落地页 URL、YouTube 视频是否可公开播放（可播放则按第 7 节 schema 补钩子/时长）。
5. 局限写清：不支持关键词发现（**GG 在投哪些搜索词要靠第 6 节搜索词链反推**）；新广告延迟 48–72h；无效果数值。
6. 浏览器 gotcha 与口径：免登录透明度页**通常只稳定呈现首屏、继续滚动会到底**，首屏能采几条算几条；顶部"在投广告条数"档位会随"所有平台/所有格式 vs 仅视频/仅某平台"的筛选口径变化（可能从约 3000 变到约 5000），**正文与图表必须用同一口径，跨口径时写区间并注明差异来源**；原内容链接用脚本生成的"region+domain+preset-date"域名页（单条广告无免登录固定链接）。

## 4. TikTok：Top Ads + 欧盟商业内容库 + 站内赞助补充

### 4.1 主源 Top Ads（Creative Center，免登录公开部分）
- 链接：`build_openintel_urls.py --source tt-topads --market <ISO> [--period 7|30|180] [--keyword <词>]`
- 页内筛选：Region=目标市场、Period（近 7/30 天）、Industry=品类、Objective 对齐营销目标（转化/安装/流量）、Format=视频；排序优先表现指标（CTR/点赞等**表现标签只记相对高低档，不记数值**）。
- **免登录配额现实**：未登录只加载前若干张卡片，出现登录提示即停止，**不登录、不绕**，采到几条算几条，并在缺口表登记"TopAds 未登录仅见 N 条"。
- 记录：广告主、地区、行业、目标、形式、时长、点赞/表现档位、前 3 秒、文案、CTA、视频链接；Top Ads 为广告主授权的**已结束/样本素材**，注明"授权样本非全量在投"。

### 4.2 欧盟/英国/瑞士：Commercial Content Library（法定全量，免登录）
- 链接：`build_openintel_urls.py --source tt-ccl --market <ISO> --keyword <品牌/品类词>`
- 仅对 DSA 法域（欧盟成员国 + GB/CH 等，以页面实际可选地区为准）有效；按广告主名/关键词查全量商业内容，补 TopAds 配额不足；记录投放地区、时间、素材形式、广告主体。
- 非该法域市场本入口不可用，过滤不展示，不硬套。

### 4.3 补充：TT 站内搜索中的赞助内容
- 用 `build_trend_urls.py --source tt-search` 打开品类/品牌词原生搜索，结果中带 "Sponsored/赞助/Ad" 标记的卡片单独记入 P2（不计入 P3 原生统计），记录命中词、广告主、素材形式与前 3 秒。

## 5. ASA：欧盟 Ad Repository + 非欧盟 App Store 巡查

### 5.1 欧盟市场：Apple Ad Repository（官方法定库，免登录）
- 链接：`build_openintel_urls.py --source apple-adrepo [--market <ISO>]`（SPA 页，脚本给基址，页内选 App/开发者 + 国家 + 时间范围）。
- 按 P1 的 Top3 App/开发者逐一查，记录：广告记录条数档位、版位（Search Results / Search Tab / Today tab）、覆盖欧盟国家、投放起止时间、**素材（即其自定义产品页 CPP 截图/应用预览视频/本地化文案）**、可见定向维度。
- 素材采集：把该 App 用于广告的 listing 素材截图，按第 7 节 schema 记录（ASA 没有独立于商店的广告素材）。

### 5.2 非欧盟市场：App Store 搜索结果广告位逐词巡查（免登录）
- ASA 在非欧盟**没有任何公开库**，广告只渲染在 App Store 搜索结果顶部（浅蓝底 + "Ad/广告"标识）。做法：
  1. 用 P1 词表（品类词/功能词/同类型产品词/本地语词，每市场 15–30 个核心词）生成链接：`build_openintel_urls.py --source appstore-search --market <ISO> --keyword <词>`；
  2. 逐词打开对应国家店面，记录：该词顶部是否有广告、广告 App 是谁、用哪套 listing 素材（截图/副标题/预览视频）、自然排名前三是谁；
  3. 汇总"同类型产品 × 词"命中矩阵：Top3 各出现在多少个巡查词的广告位（命中次数/巡查词总数），这是 ASA 投放强度的唯一免登录代理。
- 同时采集同类型产品 App Store listing 全要素（截图组、App Preview 视频、副标题、描述、促销内购、评论），作为 ASA"素材"分析对象。**云环境/免登录下若网页竞价位被重定向到错误国家店面或不渲染广告位，改用 iTunes Search API（`https://itunes.apple.com/search?term=<App名>&country=<ISO>&entity=software`，免 key）稳定拉取：评分/评论量（A 级）、`artworkUrl` 图标、`screenshotUrls` 截图（尺寸后缀如 /392x848bb.jpg 可正则替换放大）、`trackViewUrl`（即该国产品页直链，作为该素材的原内容链接）。**
- 局限写清：抽样时点值、非全量、无出价/花费；不同时刻结果会变，记录巡查日期与时点。

### 5.3 ASA 素材分析重点
ASA 素材=商店页资产，分析维度不同于视频广告：**截图首图信息钩子、截图文案顺序、预览视频前 3 秒、副标题关键词布局、评分与评论的社会证明利用、是否做本地化截图/自定义产品页（CPP）**。

## 6. 搜索词包采集（零登录替代链，分平台成包）

| 平台 | 零登录取词通道（脚本入口） | 产出 |
|---|---|---|
| Google Ads | ①Google Trends（`gtrends-web`，近 12 个月品类走势 + Rising 上升词，近 7 天看风向）②Google SERP 搜索下拉、"相关搜索/People also ask"（`gg-suggest`）③GG 透明度中心同类型产品广告标题/描述反推其竞价词 | GG 词包：核心词/长尾问题词/同类型产品词/上升词，标词来源与趋势方向（**不使用 Keyword Surfer 等第三方插件**） |
| ASA | ①App Store 搜索下拉联想（`appstore-search` 输入时记录联想）②iTunes 公开搜索接口（`itunes-search`，免 key，看哪些 App 自然排在该词前）③巡查命中词 | ASA 词包：高相关搜索词 + 同类品牌词 + 本地语词；无官方 popularity 真值，以联想/自然排名做相关度相对档位（**不使用 ASO.dev 等第三方 ASO**） |
| TikTok | Creative Center 趋势词/热门话题（免登录可见部分）、站内搜索联想、话题页（`tt-tag`）播放量级 | TT 话题/标签词包 |
| Meta | 无公开关键词工具：从同类型产品广告正文/标题高频词、评论区用户表达反推兴趣与话术词 | 话术/兴趣方向词（不称为搜索量） |

词包统一字段：keyword、语言、市场、平台、词类（品类/功能/痛点/同类型产品/本地语）、趋势（升/平/降）、热度档位、来源、采集日。**禁止给出精确月搜索量**（零登录、零第三方渠道只有 Trends 相对指数与商店联想/自然排名的相对档位）。

## 7. 统一素材记录 schema（核心媒体平台对齐，TSV 落盘）

| 字段 | 说明 |
|---|---|
| id / platform | 序号；meta / google / tiktok / asa |
| market / query | 市场；命中的检索词或域名/App |
| advertiser | 广告主体（Meta Page 名 / 域名主体 / TT 广告主 / ASA App 名，人工核对归属） |
| surface | 具体版位：IG Reels/FB Feed、YT/Search/Display、TT In-Feed/TopView、ASA Search Results/Search Tab/Today |
| format / duration | image/video/carousel/text/listing-screenshot；视频时长（秒） |
| copy_original / copy_translation | 原文（不翻译照录）/ 中文译文另列 |
| cta / landing | 按钮文案；落地页 URL（ASA 为商店页/CPP） |
| first_seen / running_span / variants | 最早可见日期、投放跨度、版本/变体数（各平台对应字段，无则 -） |
| hook_0_3s | 前 3 秒钩子：画面 + 文案/口播（ASA 填首图/预览视频钩子） |
| visual_elements | 人物、场景、字幕花字、镜头节奏、关键帧（ASA 填截图信息架构） |
| relative_signal | 相对信号：Meta 排序位次/在投天数/版本数；GG 变体与跨度；TT 表现档位；ASA 巡查命中——**只写相对信号不写数值** |
| local_score | 本地化：本地语言/本地人物场景/本地支付与节点，强中弱无 |
| cover_image | **报告展示用真实封面**：本次零登录截图/官方接口图裁剪压缩后的相对路径，命名 `平台_市场_主体_序号.jpg`；无封面填"无公开封面"并登记缺口，禁止占位/生成图 |
| url / screenshot | 原始永久链接（单条 id 链接，取不到则为列表页链接）；原始整页截图路径，命名 `平台_市场_主体_id.png` |
| source_link / link_type | 报告里可点击的原内容链接；`direct`=单条直链（ASA 的 trackViewUrl、可见单条 id）/ `listing`=该素材所在检索页或域名页（Meta/GG/TT 常用），listing 必须带齐国家/在投/排序参数 |
| select_reason | 入选理由（第 8 节信号） |
| notes | 其他（授权样本/延迟/口径区间/缺口等） |

## 8. 优势素材判定规则（采集池每平台选 10，报告按同类型产品展示 Top5）

**分平台信号**：
- Meta：排序靠前 + 在投天数 >30/60/90 三档 + 版本数 ≥3（持续迭代）+ 多市场复现。
- Google：变体数量多 + 投放跨度长 + 多平台（Search+YT）同时在投 + 落地页持续更新。
- TikTok：Top Ads 表现档位高 + 近 7/30 天在榜 + 欧盟 CCL 长期可见 + 同模式多广告主复现；**免登录样本少，优先选可验证到长效/复现信号的，不为凑数降低标准**。
- ASA：欧盟库中投放期长/覆盖多国/多 CPP 版本；非欧盟巡查中在多核心词稳定命中广告位 + listing 素材完整度高/本地化强。

**共性规则**：一个"跑量模式"至少 2 条素材支撑或在 2 个词/市场复现，单源孤证只作灵感；每条入选必须写一句基于信号的理由（不写主观空话）；配额不足 10 条时如实写"该平台免登录可见 N 条，已全采，缺口见第 X 节"。

**采集池与报告展示配额（区分）**：每平台 Top10 是**采集/分析池**；**HTML 报告按同类型产品分组展示，每个同类型产品列 Top5 物料，每条配真实封面 + 原内容链接**。某同类型产品免登录可见不足 5 条时按实际数量全列并标注"已全列 N 条"，不用其他同类型产品或旧素材补足；同一同类型产品在同一检索词下的多版本合并取最强封面。

## 9. 通用采集 SOP 与截图规范

1. 脚本按 P1 计划批量生成 TSV → 浏览器逐条打开（**不登录**）→ 核对筛选器 → 滚动加载 → 按 schema 落表 → 每条至少 1 张截图（视频取封面+关键帧，ASA 取商店素材）→ 去重合并 → 每平台建 Top10 采集/分析池（报告再按同类型产品展示 Top5，见第 8 节）。
2. 遇登录墙/人机验证/同意页：**不接管、不绕过**；换同平台其他公开入口（Meta 关键词↔page；GG 域名↔广告主；TT TopAds↔CCL↔站内赞助；ASA 欧盟库↔商店巡查），仍取不到登记缺口。
3. 工作目录建 `creatives/<platform>/`（原始截图 `raw/`、web 用图 `web/`）、`p2_materials.tsv` 存全量采集池记录；**报告按同类型产品分组、每个同类型产品展示 Top5（采集池每平台保留 Top10 备查）**。
4. 采集与 P3 尽量同一时间窗，记录采集日期；跨平台素材在汇总分析前不做数值横比。
5. **封面加工链（报告必做）**：整页零登录截图落盘 `creatives/<平台>/raw/` → 按卡片裁剪出单条封面、统一压缩成 web 用图存 `creatives/web/` → 拼一张联系表（contact sheet）用读图能力逐张核对"封面与所标注物料一致、清晰、无水印/无防盗链占位" → HTML 相对路径引用（静态写进 `<img src>`，不经 JS 拼接）；交付前内嵌成单文件：有 html skill 时跑其 `scripts/embed.py <html>` 交付 `_embed.html`，无则用其他内嵌工具或 creatives 同目录打包；双端自检有 html skill 时跑其 `scripts/shot.py`（桌面+移动），无则按"封面不裁字、窄屏网格正常、无 console 报错"人工自检。
6. **原内容链接落地**：报告每张素材卡底部放可点击链接（新窗口打开）。ASA 用 iTunes `trackViewUrl`（direct）；Meta/GG/TT 单条无免登录固定链接时，用脚本生成带完整参数的检索页/域名页/话题页（listing），并在该章引言统一说明"单条无公开固定链接，已定位到该批素材所在列表页"；禁止手拼或编造任何 id。

## 10. 常见坑与红线

- Meta `q` 模糊匹配会召回无关广告主，必须核对 advertiser；`country=ALL` 不能下分市场结论；active/inactive 不混排比较。
- GG 透明度中心**不能发现关键词**，别把它当词工具；欧盟以外看不到定向区间。
- TT TopAds 是"广告主授权样本"而非全量在投库，免登录还有卡片数量限制；CCL 有严格地区边界，不可对非欧盟市场声称"全量"。
- ASA 非欧盟的巡查结论是抽样代理，不能表述为"同类型产品 ASA 投放全貌"；ASA 无独立视频素材，别把商店 listing 误当独立广告片。
- 任何平台都不写曝光数、花费、出价、CTR、ROI；不搬运同类型产品视频/音乐对外发布；敏感品类按 `04` 与合规要求逐条审。
- 平台前台参数若调整，先更新脚本枚举与本手册再采集，不硬猜参数。

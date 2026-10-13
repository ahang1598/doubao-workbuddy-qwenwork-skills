# 字体推荐入口

<!-- source-of-truth: assets/fonts/font-curated-pool.json -->
<!-- recommendation-scope: curated-entry-not-whitelist -->
<!-- query-role: deterministic-query-and-diagnostics -->
<!-- row-quota: none -->
<!-- html-font-gate: resolver-required -->
<!-- locked-font-failure: user-confirmation-required -->

本文是字体视觉选型的统一入口。下方清单是经过编辑分类的精选候选，不是封闭白名单；表外的品牌指定字体或后续审核字体可以进入受控解析流程。条目数量不固定，表格行序仅保证生成稳定，不表示推荐优先级。

## 选型顺序

1. 先服从用户锁定的语言、品牌字体、文字角色和关键字形要求。
2. 未锁定精确字体时，按语言、角色、形态与气质取交集；需要主题或组合排序时调用 `scripts/runtime/select_fonts.py`。查询器只返回确定性候选、缺口和诊断，不替代真实文案试排与视觉判断，也不把表外字体直接判为不可用。
3. 比较 2–3 个满足约束的候选。短缺时保留 `shortfall`，不得删除条件、切换语言或用不兼容字体凑数。
4. 确认视觉候选后，再进入 [字体资源与执行](font-family-library.md)；正式 HTML 另遵循 [Web 字体契约](web-font-contract.md)。

## 角色与字重起点

| 角色 | 视觉职责 | 字重起点 | 相对字号起点 |
|---|---|---|---|
| `hero` | 唯一最高主标题与传播钩子 | `600–900` | 正文的 `3–6×` |
| `sub` | 章节题、商品卖点和次级标题 | `500–700` | 正文的 `1.5–2.5×` |
| `body` | 连续阅读、说明和事实正文 | `400–500` | 基准 `1×` |
| `meta` | 标签、来源、编号与辅助信息 | `400–600` | 正文的 `0.75–0.95×` |

这些范围只是排版试起点，不证明字体存在对应实例。`family`、`face`、`weight` 和 `style` 不得任意组合；可变字体轴与离散字重都必须在资源层核验。强展示体、手写体、书法字和极细／极黑 face 只在真实阅读尺寸通过后承担相应角色，不能因为家族被推荐便把所有 face 用于正文。

## 候选与资源状态分离

- `editorial_candidate` 只表示视觉候选已经完成编辑分类，不表示已安装、许可已批准、目标文字覆盖完整或当前 Web 环境可加载。
- `registered_unclassified` 只登记身份，不进入默认推荐；补齐形态、气质和角色证据后才能转为候选。
- 语言标签表示推荐方向，不证明简繁地区字形、组合符号或复杂整形已经覆盖。
- 静态推荐表不记录本机安装、CDN 在线状态或当前运行时可用性，也不猜测下载地址。

## 正式 HTML 门禁与替代

正式 HTML 写入前，必须通过 Resolver 核验实际 `family`、`face`、`weight`／`style`、许可、目标文案覆盖和 Web 加载链路，再在目标背景和版式中等待字体加载并检查实际渲染、换行、裁切与可读性。浏览器 fallback、FontFace 已加载或截图“看起来正常”都不能单独证明锁定字体已命中。

资源便利性不得压过用户锁定约束。未锁定精确字体时，资源失败可以触发同语言、同角色、同关键形态与气质内的受约束重选，并记录差异；用户锁定精确字体或关键字形时，任一门禁失败都必须停止该字体定稿并请求用户确认替代或补充资源，不得静默换成中性字体、浏览器默认字体，也不得改变产物路线或把可编辑文字栅格化绕过问题。

`胡敬礼毛笔行书`、`HuJingLi-Mao` 与 `胡敬礼毛笔行书简.TTF` 保持禁用；候选、精确解析和回退链都不得绕过。`沐瑶软笔` 默认不推荐，只有明确同时命中“可爱＋毛笔／软笔”的短标题意图时才进入候选，并排在其他合格候选之后。

## 默认精选候选

以下区域由 `scripts/maintenance/generate-font-recommendation-list.py` 从 `assets/fonts/font-curated-pool.json` 生成，请勿手改。`font_key` 是跨文档与工具关联用的稳定标识，不是 CSS `font-family`。

<!-- BEGIN GENERATED:FONT_RECOMMENDATIONS -->
<!-- generated-count: 157 -->
| font_key | 推荐字体 | 语言 | 角色 | 形态 | 气质标签 | 设计说明 |
|---|---|---|---|---|---|---|
| `acy` | Acy手写体 | zh | hero / sub | handwritten | fresh / handwritten / personal / playful | 个人笔迹与手帐方向，不默认用于参数。 |
| `assorted` | 猫啃什锦黑 | zh | hero / sub | display-sans | creative / display / experimental / playful / sans | 趣味展示方向，适合短句和活动标题。 |
| `butter` | 站酷庆科黄油体 | zh | hero / sub | display-rounded | bold / creative / cute / display-rounded / food / playful / rounded | 圆润块面与玩趣标题；适合零食、亲子和创意封面。 |
| `carefree` | 悠哉字体 | zh | hero / sub | handwritten | casual / fresh / handwritten / journal | 松弛自然的手写风格；适合日常、旅行、手账和生活方式。 |
| `chenluo` | 辰宇落雁体 | zh | hero / sub | calligraphic-handwritten | calligraphic / calligraphy / elegant / handwritten / literary / organic | 行笔起伏明显、识别度高；适合国风、文艺、生活方式与情绪短标题。 |
| `chill_zhengkai` | 寒蝉正楷体 | zh | hero / sub / body | kai | calligraphic / calligraphy / formal / kai / literary / readable / traditional | 端正但保留书写气息；适合传统文化、阅读、文旅和克制的编辑排版。 |
| `chillround` | 寒蝉全圆体 | zh | hero / sub / body | rounded | creative / cute / geometric / playful / rounded | 几何圆润方向；童趣和亲和品牌。 |
| `cloud_ink` | 寒蝉雲墨黑 | zh | hero / sub | display-sans | art / creative / display / ink / oriental / sans | 墨感展示方向；先核验实际笔画与清晰度。 |
| `coriander` | 芫荽 | zh | hero / sub | handwritten | fresh / handwritten / humanist / readable | 自然手写阅读方向；混排逐字验证。 |
| `cute_seto` | 日本濑户可爱风 | zh | hero / sub | handwritten-rounded | casual / cute / fresh / handwritten / japanese / rounded | 日系可爱手写气质；适合亲子、手账、旅行和轻松消费内容。 |
| `damaged_serif` | 极影毁片文宋 | zh | hero / sub | experimental-serif | creative / display / distressed / experimental / horror / retro / serif | 带破损与印刷感的文宋结构；适合复古、悬疑、档案和实验标题。 |
| `dela` | 德拉黑体 | zh | hero / sub | display-sans | bold / creative / display / power / promo / sans / sporty / tech | 高黑、粗重、字腔紧凑；适合运动、促销、科技和强冲击标题。 |
| `douyin` | 抖音美好体 | zh | hero / sub | display-sans | bold / creative / display-sans / power / promo / sans / sporty / tech | 有力度的科技和促销标题；目录提供 Bold。 |
| `fangsong` | 朱雀仿宋 | zh | hero / sub / body | fangsong | fangsong / formal / literary / traditional | 仿宋方向；适合传统、文化与正式长文。 |
| `fanwun` | 繁媛明朝 | zh | hero / sub | serif | serif | 宋／明体方向标题候选；真实文案试排后判断是否适合克制的东方留白。 |
| `fengkai` | 风楷 | zh | hero / sub / body | kai | calligraphy / fresh / kai / literary / readable / traditional / warm | 楷意清晰、气质温润；适合文艺、日系、国风和人文阅读。 |
| `genwan` | 源云明体 | zh | hero / sub | serif | serif | 宋韵留白、当代东方标题候选；正文须在目标字号另验细笔画与简繁覆盖。 |
| `happy` | 站酷快乐体 | zh | hero / sub | display | creative / cute / display / playful / youth | 活泼童趣的展示标题；先核实内嵌用途许可。 |
| `inorganic` | 寒蝉无机体 | zh | hero / sub | geometric-display | creative / display / experimental / game / geometric / tech | 硬质几何与机械感突出；适合科技、游戏、酸性和暗黑主题。 |
| `ja-source-han` | 思源黑体日文版 | ja | hero / sub / body / meta | sans | sans | 日文阅读候选；核验假名、汉字与地区字形。 |
| `ja-source-han-serif` | 思源宋体日文版 | ja | hero / sub / body / meta | serif | serif | 日文明体候选；不根据同名推断平台支持。 |
| `jagged` | 铁蒺藜体 | zh | hero / sub | decorative | creative / display / experimental / horror / sharp / street | 尖锐、粗粝且具有强烈张力；适合街头、暗黑、摇滚和实验标题。 |
| `jason7` | 清松手寫體7 | zh | hero / sub | handwriting | casual / handwriting / handwritten | 自然生活、手帐短标题或短句，轻松手写笔触；固定第7款，不把第8/9款或其他清松版本视为同款，简体文案须逐字验覆盖。 |
| `junyu_round` | 俊羽圆体 | zh | hero / sub / body | rounded | cute / fresh / readable / rounded / soft | 柔和圆体，字面清晰；适合清新、亲子、美妆和生活方式。 |
| `ko-noto-sans` | Noto Sans KR | ko | hero / sub / body / meta | sans | sans | 韩文无衬线候选；真实覆盖待测试。 |
| `ko-noto-serif` | Noto Serif KR | ko | hero / sub / body / meta | serif | serif | 韩文衬线候选；核验Hangul、货币、标点和混排基线。 |
| `ko-source-han` | 思源黑体韩文版 | ko | hero / sub / body / meta | sans | sans | 韩文阅读候选；不借用简中family或未提供字重。 |
| `legacy-10` | Exo | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-11` | Caskaydia Cove | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-12` | Public Sans | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-13` | Metropolis | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-14` | B612 | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-15` | Comme | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-16` | Source Sans | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-17` | Raleway | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-18` | Barlow | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-19` | Gidole | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-20` | 源流明体 | zh | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-21` | Bodoni Moda | en | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-22` | Playfair Display | en | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-23` | Cormorant | en | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-24` | Lora | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-25` | Merriweather | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-26` | Alice | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-27` | 源泉圆体 | zh | hero / sub / body / meta | rounded | rounded | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-28` | Tsukimi Rounded | en / ja | hero / sub | rounded | rounded | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-29` | Cookie | en | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-30` | Dosis | en | hero / sub / body / meta | rounded | rounded | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-31` | Rubik | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-32` | Duru Sans | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-33` | I.Ming | zh | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-34` | Montagu Slab | en | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-35` | IM FELL | en | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-36` | Kaisei Decol | en / ja | hero / sub | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-37` | Aleo | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-38` | Bitter | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-39` | Libre Baskerville | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-40` | PT Serif | en | hero / sub / body / meta | serif | serif | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-41` | 仓耳飞白 | zh | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-42` | Yuji Mai | en / ja | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-43` | DynaPuff | en | hero / sub | rounded | rounded | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-44` | Schoolbell | en | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-45` | Chewy | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-46` | Andika | en | hero / sub / body / meta | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-47` | Kite One | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-48` | 沐瑶手写 | zh | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-49` | Rock Salt | en | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-50` | Permanent Marker | en | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-51` | Amatic SC | en | hero / sub | handwritten | handwritten | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-52` | Archivo Black | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-53` | Fjalla One | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-54` | Facon | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-55` | Quicksand | en | hero / sub / body / meta | rounded | rounded | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-56` | Nosifer | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-57` | Rubik Wet Paint | en | hero / sub | display | display | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `legacy-9` | Space Grotesk | en | hero / sub | sans | sans | 保留旧主题推荐；先核对精确家族/face，再用真实文案试排。未解析记录不能冒充可用资源。 |
| `liujiang` | 钟齐流江毛笔草体 | zh | hero | brush-script | brush / calligraphic / calligraphy / script / traditional / wild | 草化省笔、牵丝回环与欹侧结体形成洒脱狂放、流动飘逸的短标题；不因笔画纤细直接判清新。 |
| `longzang` | 寒蝉书体 龙藏 | zh | hero / sub | calligraphy | calligraphy / ceremonial / oriental / traditional | 东方书写与仪式标题；正文另选阅读字体。 |
| `manhei` | 霞鹜漫黑 | zh | hero / sub | handwritten-sans | comic / creative / handwritten / handwritten-sans / playful / sans / youth | 漫画、轻松和创意短句；不默认用于密集正文。 |
| `mashanzheng` | 钟齐马善政毛笔楷书 | zh | hero / sub | brush-kai | brush / calligraphic / calligraphy / formal / kai / readable / traditional | 传统毛笔楷书，结体端正、起收有法；不强行归入狂放、可爱或清新，适合端正的国风与节庆短标题。 |
| `mengshen_hand` | 萌神手写体 | zh | hero / sub | handwritten | casual / cute / fresh / friendly / handwritten / journal | 自然手写、亲切轻松；适合手账、旅行、日常和情绪短句。 |
| `mengshen_mincho` | 萌神明朝体 | zh | hero / sub / body | serif | editorial / elegant / mincho / retro / serif | 明朝体的古典笔画对比；适合出版、复古、文化和高级编辑。 |
| `mingxin` | 霞鹜铭心宋 | zh | hero / sub / body | serif | distinctive / editorial / literary / serif | 细节有辨识度的宋体候选；小字需实测。 |
| `mist_sans` | 霞鹜975朦胧黑体 | zh | hero / sub | display-sans | creative / display / experimental / retro / sans / soft | 朦胧颗粒和柔化黑体气质；适合复古数字、潮流和实验编辑。 |
| `moda_brush` | 莫大毛笔 | zh | hero | brush | bold / brush / calligraphic / calligraphy / traditional | 毛笔笔势强、适合短句；用于国风、节庆和传统文化主标题。 |
| `movable_fangsong` | 寒蝉活仿楷 | zh | hero / sub / body | fangsong-kai | calligraphy / editorial / fangsong / kai / readable / traditional | 介于仿宋与楷意之间；适合文化、档案、出版和传统信息排版。 |
| `movable_kai` | 寒蝉活楷体 | zh | hero / sub / body | kai | calligraphy / handwritten / kai / literary / readable / retro | 活字感楷体，兼具书写与编辑气质；适合文艺、复古和手作主题。 |
| `movable_sans` | 寒蝉活黑体 | zh | hero / sub | handwritten-sans | creative / handwritten / playful / sans / street / youth | 黑体骨架带不规则手作感；适合街头、手账、青年和创意封面。 |
| `movable_serif` | 寒蝉活宋体 | zh | hero / sub | display-serif | creative / display / editorial / print / retro / serif | 宋体结构带活字印刷的不规则感；适合复古、出版和旧报刊标题。 |
| `muyao` | 沐瑶软笔手写体 | zh | hero / sub | brush | brush / calligraphy / cute / handwritten / soft-brush / traditional / warm | 圆钝转折、稚拙错落与亲切手作感，适合可爱软笔主标题；不因 brush 或主标题角色判为狂放。当前同文字样支持 cute；fresh 尚无充分证据，不按清新毛笔默认召回。 |
| `nanshen` | 胡晓波男神体 | zh | hero / sub | display-sans | bold / commercial / creative / display / power / sans | 醒目的商业展示字；实际视觉重量需试排。 |
| `new_sans` | 霞鹜新晰黑 | zh | hero / sub / body / meta | sans | business / modern / neutral / readable / sans | 清晰现代的阅读黑体；用于替代单一思源黑体的通用信息层。 |
| `new_serif` | 霞鹜新致宋 | zh | hero / sub / body | serif | editorial / elegant / literary / readable / serif | 更具设计细节的中文宋体；适合高级编辑、文学、复古和美妆。 |
| `organic` | 寒蝉有机体 | zh | hero / sub | organic-display | creative / display / experimental / organic / street / y2k | 有机曲线和不规则结构突出；适合实验、Y2K、潮流和怪诞标题。 |
| `oswald` | Oswald | en | hero / sub | condensed-sans | condensed-sans | 窄长、紧凑的英文栏目或海报标题；与正文拉开尺度。目录绑定可变字体包，使用前验证轴和真实字重，不选同名 ExtraLight 冒充 Bold。 |
| `pixel` | 寒蝉点阵体 | zh | hero / sub | pixel | creative / digital / game / pixel / retro | 像素、游戏、复古数字标题；不用于正文、价格或事实信息。 |
| `pixel11` | 俐方體11号 | zh | hero / sub | pixel | creative / digital / game / pixel / retro | 点阵方向，适合游戏标题与数字复古。 |
| `pixel9` | 精品点阵体9×9 | zh | hero / sub | pixel | creative / digital / game / pixel / retro | 高识别度像素点阵；适合游戏、数字复古和像素主题标题。 |
| `platform-3` | 清松手寫體3 | zh | hero | handwritten | casual / fresh / handwritten | 中文细圆笔画略有摆动，结体松散，呈硬笔手写感，无明显毛笔提按。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 本轮使用繁体字样，简体样句有缺字，不能默认简体全覆盖。 |
| `platform-alegreya` | Alegreya | en | hero / sub / body / meta | serif | serif | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-allison` | Allison | en | hero | script | calligraphy / elegant / handwritten / literary / script | 拉丁字母右倾连写，细线带粗细变化，大写与数字有舒展回环；属西文书写形态。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-arial` | Arial | en | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-barriecito` | Barriecito | en | hero | display-sans | casual / creative / display-sans / handwritten / playful | 拉丁无衬线字形粗细交替，字宽与轮廓不规则，带手绘拼贴感。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-barrio` | Barrio | en | hero | display-sans | creative / display-sans / experimental / handwritten / playful | 拉丁全大写采用细线与厚块混排，字腔和笔画比例夸张，轮廓略带手绘偏斜。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-blackout` | Blackout | en | hero | display | creative / display / power | 拉丁粗体大写以连续黑块中的白色负形呈现，部分字腔封实，块面感强。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-1-6` | 精品点阵体9×9 1.6 | zh | hero | pixel | creative / pixel / retro / tech | 中文由方格笔画构成，斜线呈阶梯状，具有低分辨率栅格特征。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-3d` | BoutiqueBitmap9x9 3D | zh | hero | pixel | creative / pixel / playful / retro | 中文像素骨架带空心轮廓和偏移侧面，字形自身呈立体块状结构。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-blur` | BoutiqueBitmap9x9 Blur | zh | hero | pixel | creative / pixel / playful / retro | 中文栅格骨架由密集圆珠状单元组成，笔画边缘呈连续波点状。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-circle-dot` | BoutiqueBitmap9x9 Circle Dot | zh | hero | pixel | creative / pixel / retro / tech | 中文笔画拆为等距独立圆点，横竖与斜线均遵循点阵网格。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-gradient` | BoutiqueBitmap9x9 Gradient | zh | hero | pixel | creative / experimental / pixel / tech | 中文阶梯状骨架由水平细条分割，上浅下深，呈扫描线式字形纹理。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-boutiquebitmap9x9-square-dot` | BoutiqueBitmap9x9 Square Dot | zh | hero | pixel | creative / pixel / retro / tech | 中文由间隔均匀的小方点排列，转折和撇捺均呈规则栅格。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-coiny` | Coiny | en | hero | display-sans | creative / cute / display-sans / playful / warm | 拉丁笔画厚实膨圆，端点柔软，字腔紧凑，整体呈饱满软糖状。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-helvetica-neue` | Helvetica | en | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-lobster` | Lobster | en | hero | script | calligraphy / elegant / handwritten / retro / script | 拉丁粗体右倾连写，粗细对比明显，首字母回卷且下伸笔画弯曲，具西文招牌书写感。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-maokenassortedsans-lite` | 猫啃什锦黑-轻量版 | zh | hero | display-sans | creative / display-sans / playful / power | 中文粗黑笔画，字面倾斜与重心错落，切角和不规则轮廓明显。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-matrix-sans` | Matrix Sans | en | hero | pixel | creative / pixel / retro / tech | 拉丁笔画由方块构成，曲线转为直角阶梯，数字零带栅格斜划。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-montserrat` | Montserrat | en | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-ostrich-sans-inline` | Ostrich Sans Inline | en | hero | display-sans | creative / display-sans / elegant / retro | 拉丁大写高瘦窄长，笔画内部留白形成双线轮廓，整体匀整纤细。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-pingfang-sc` | 苹方 | zh | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-pro` | 寒蝉锦书宋Pro | zh | hero / sub / body / meta | serif | serif | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-rubik-bubbles` | Rubik Bubbles | en | hero | display | creative / cute / display / playful | 拉丁厚字形由团簇圆泡构成，外缘密集起伏，呈蓬松颗粒状轮廓。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `platform-s-core-dream` | S-Core Dream | ko | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-source-han-serif-cn` | 思源宋体 CN | zh | hero / sub | serif | serif | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `platform-story-script` | Story Script | en | hero | script | calligraphy / casual / handwritten / script / warm | 拉丁字形右倾，弧线流畅并有书写式收笔，连接较松，呈自然西文手写感。 仅作为所示语种的短主标题候选；不证明正文适配、目标文案覆盖或浏览器加载。 |
| `playfair` | Playfair Display | en | hero / sub | display-serif | creative / display-serif / elegant | 高反差英文衬线，适合杂志、优雅与浪漫标题；细线须在目标尺寸验证，不把参考中另一款 DEMO 字体的造型归给它。目录包实际为可变字体，Regular 实例需核验。 |
| `printer` | 香萃打印机 | zh | hero / sub | typewriter | creative / editorial / handcraft / print / retro / typewriter | 打印机与打字机质感；适合档案、旧报刊、复古和手工拼贴。 |
| `puhui` | 阿里巴巴普惠体 | zh | hero / sub / body / meta | sans | business / friendly / modern / readable / sans | 亲和商务无衬线；目录仅有 Regular，不能假设附带粗体。 |
| `qiji` | 黄令东齐伋复刻体 | zh | hero / sub | antique-serif | antique-serif | 古籍刻本、金石古雅方向，短标题候选；不用于密集正文。 |
| `qiji_fallback` | 凌东齐伋体 | zh | hero / sub | antique-serif | antique-serif | 齐伋系列另一目录版本；不可因 fallback 文件名假定覆盖或效果相同。 |
| `qijic` | QIJIC | zh | hero / sub | antique-serif | antique-serif | 古籍刻本方向，短标题候选；与齐伋其他包分别核对字形及覆盖。 |
| `qingsong_hand` | 清松手写体1 | zh | hero / sub | handwritten | casual / fresh / friendly / handwritten / journal | 自然日常手写感；适合 Plog、手账、旅行与生活方式注释标题。 |
| `relaxed_sans` | 香萃自在舒畅黑 | zh | hero / sub / body | humanist-sans | fresh / friendly / humanist / readable / sans | 松弛的人文黑体；适合生活方式、清新内容和亲和品牌。 |
| `reunion` | 寒蝉团圆体 | zh | hero / sub | rounded | cute / festival / friendly / rounded | 圆润团聚语义，适合节庆与餐饮。 |
| `rounded` | 资源圆体 | zh | hero / sub / body / meta | rounded | cute / friendly / readable / rounded | 圆润中性字体；可爱场景的正文基准。 |
| `sans` | 思源黑体 | zh | hero / sub / body / meta | sans | sans | 依据已有平台说明与阅读角色补充的候选；列出的字重和样式不是任意组合，目标文案仍须实测。 |
| `saobao` | 胡晓波骚包体 | zh | hero / sub | display | creative / display / playful / street / youth | 个性展示标题候选；用于青年活动和品牌口号，需字样试排。 |
| `serif` | 思源宋体 | zh | hero / sub / body / meta | serif | editorial / elegant / literary / readable / serif | 正文宋体与编辑式标题；使用简体字形，不自动映射其他同名 CN/TW 条目。 |
| `sharp_square` | 有爱锐方 | zh | hero / sub | display-sans | creative / display / sans / sharp / sporty / tech | 锐利方整的展示黑体；适合科技、电竞、运动和硬朗标题。 |
| `shuheiti` | 阿里妈妈数黑体 | zh | hero / sub | display-sans | creative / display-sans / geometric / numeric / sans / tech | 几何、数字科技、强视觉标题；确认真实文件和许可后使用。 |
| `slippery` | WD-XL 滑油字 | zh | hero / sub | display | creative / display / experimental / playful / youth | 独特展示方向，适合年轻品牌和活动短标题。 |
| `smiley` | 优设得意黑 | zh | hero / sub | display-sans | condensed / creative / display-sans / oblique / sans / sharp / slanted / sporty / youth | 自带倾斜的展示黑体；运动、青年、短促口号，不重复叠加伪斜体。 |
| `sprout` | 逐浪萌芽字 | zh | hero / sub | display-rounded | creative / cute / display / food / playful / rounded | 活泼萌趣、字形跳跃；适合亲子、零食、活动和可爱封面。 |
| `star` | 解星 | zh | hero / sub | display | art / creative / display / experimental | 实验展示候选；样张与目标文案试排后才确定风格。 |
| `sugar_round` | 猫啃网糖圆体 | zh | hero / sub / body / meta | rounded | cute / food / readable / rounded / soft | 甜润圆体且保持正文可读性；适合亲子、食品、美妆和生活方式。 |
| `tall_sans` | 寒蝉高黑体 | zh | hero / sub | condensed-sans | condensed / creative / display / editorial / sans | 高窄字面方向；实际文件决定宽窄，禁止横向压缩。 |
| `unified_round` | 金字社统圆体 | zh | hero / sub / body | rounded | friendly / modern / readable / rounded | 统一字面配合圆润转角；适合消费品牌、亲和信息和轻松编辑。 |
| `unified_square` | 金字社统方体 | zh | hero / sub | display-sans | bold / creative / display / modern / power / sans / square / tech | 方整统一、字面醒目；适合现代编辑、品牌、科技和力量标题。 |
| `wavy_round` | 大波浪圆体 | zh | hero / sub | display-rounded | creative / cute / display / playful / rounded / street | 字面圆润且节奏夸张；适合零食、亲子、潮流和趣味封面。 |
| `wenkai` | 霞鹜文楷 | zh | hero / sub / body | kai | calligraphy / fresh / humanist / kai / literary / readable | 人文楷体；文艺、阅读和自然生活方式。 |
| `wide` | 寒蝉宽黑体 | zh | hero / sub | display-sans | bold / creative / display-sans / power / sans / sporty / street / wide | 宽体量感；适合横向标题、街头和力量主题，长标题先测宽度。 |
| `xiaowei` | 站酷小薇LOGO体 | zh | hero / sub | display-serif | creative / editorial / elegant / logo / serif | 有个性的衬线展示；适合品牌与文化标题。 |
| `yuwen` | 宇文天穹 | zh | hero / sub | decorative | creative / decorative / display / experimental / fantasy / horror | 强装饰与奇异结构；适合暗黑、奇幻、潮流和实验封面。 |
| `zcool_art` | 站酷文艺体 | zh | hero / sub | display-sans | art / creative / editorial / geometric / literary / sans | 文艺几何展示方向；短标题先比较字腔。 |
| `zen_antique` | Zen Antique | ja | hero / sub | serif | serif | 复古明朝方向的补充候选；未确认等同参考图“Zen 老式明朝”，中文覆盖须逐字验证。 |
| `zen_dots` | Zen Dots | en | hero / sub | geometric-display | creative / geometric-display / tech | 科技、未来英文短标题候选；不替代中文或密集正文，按目标文案核对字腔、间距与数字。 |
| `zhenkai` | 霞鹜臻楷 | zh | hero / sub / body | kai | calligraphy / elegant / fresh / kai / literary / readable / traditional | 结构精致的楷体；适合文化、书卷、清新和传统内容。 |
| `zhenshuai` | 胡晓波真帅体 | zh | hero / sub | display-sans | bold / commercial / creative / display / power / sans | 厚重标题候选；避免与另一强展示体争抢。 |
<!-- END GENERATED:FONT_RECOMMENDATIONS -->

## 维护

字体候选、语言、角色、形态、标签和设计说明只在结构化 JSON 中维护。修改后运行生成器更新本页，再以 `--check` 验证无差异。资源身份、文件、许可线索和精确 face 继续由 Catalog、manifest 与 Resolver 管理；本页不复制动态资源事实。

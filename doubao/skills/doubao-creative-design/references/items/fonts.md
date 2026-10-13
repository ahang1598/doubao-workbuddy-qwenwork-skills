# 可用字体白名单

当前清单登记 **70 个字体族**，白名单仅约束实际 Canvas Item 协议中明确引用本表的字体字段，例如 [TEXT](text.md) 的 `font_family` 和 `font_weight`，不泛指所有 XML 或 HTML。HTML Item 内的 DOM 文字遵循 [HTML 协议](../html/coding-rendering.md)，不能仅因 family 未列本表而拒绝；仍须遵守行内视觉样式及目标环境加载验证要求；远程字体唯一例外遵循 [Web 字体契约](../rendering/web-font-contract.md)。清单登记不等于本次目标环境已经加载并通过真实文案核验。

推荐、协议登记与运行时可用性必须分开判断。视觉选型统一从 [字体推荐入口](../rendering/font-recommendation-list.md) 开始：清单是精选入口而非封闭白名单，`select_fonts.py` 只返回候选、缺口和诊断，最终选择仍须用真实文案试排。候选用于正式 HTML 时，再按 [资源契约](../rendering/font-family-library.md) 核验实际 family、face、weight／style、许可、目标字形覆盖和 Web 加载；用户锁定精确字体而门禁失败时，必须请求确认，不得静默替换。pure-image 只借用视觉建议，不进入 HTML 资源门禁。扩展视觉候选不会自动扩大本表；只有实际平台注册证据才能增加 Item 可填的 family 或字重。JSON 的 `platform_fonts` 是本表的查询镜像，更新时须一起核对。

## 选择规则

- 引用本表的 Item `font_family` 字段使用表中的精确值，不用显示名称或 CSS 字体栈。
- 对应 `font_weight` 使用表内已注册的字重；normal/italic 列表示已注册的原生字体样式，具体提交方式遵循该 Item 协议。
- `Songti SC`、`Georgia`、`Inter` 不在此表，不可填入受本表约束的字体字段；这不是 HTML DOM 的字体禁用名单。
- 系统字体依赖设备安装，远程字体需要加载；若目标画布提供其他可用字体表，以实际清单为准。本地资源存在或推荐命中均不能替代平台注册与本次目标环境核验。

## 常用选择与简述

| 字体 | 简述与使用建议 | 建议起点 |
|---|---|---|
| `Source Han Sans SC VF` | 中文黑体，适合正文和说明 | 正文 400、标题 700，normal |
| `寒蝉锦书宋Pro` | 中文宋体，可用于宋体风格的正文或标题 | 正文 400、标题 700；600 仅支持 italic |
| `Source Han Serif CN` | 中文宋体，当前仅提供较粗字重，可用于标题 | 600 normal，不填 400 |
| `Montserrat` | 拉丁无衬线，适合英文标题、标签及常规/斜体混排 | 400 normal/italic |
| `Alegreya` | 拉丁衬线，可作为英文衬线文本候选 | 400 normal，无 italic |
| `PingFang SC` / `Arial` / `Helvetica Neue` | 系统字体，使用前确认目标设备可用 | 400/500/600/700 normal |

## 完整白名单

| 显示名称 | font_family | normal 字重 | italic 字重 | 来源 |
|---|---|---|---|---|
| 苹方 | `PingFang SC` | 400, 500, 600, 700 | — | 系统 |
| Arial | `Arial` | 400, 500, 600, 700 | — | 系统 |
| Helvetica | `Helvetica Neue` | 400, 500, 600, 700 | — | 系统 |
| 思源黑体 VF | `Source Han Sans SC VF` | 250, 300, 350, 400, 500, 700, 900 | — | 远程 |
| QIJIC | `QIJIC` | 400 | — | 远程 |
| Resource Han Rounded CN | `Resource Han Rounded CN` | 500 | — | 远程 |
| 思源宋体 CN | `Source Han Serif CN` | 600 | — | 远程 |
| Muyao-Softbrush | `Muyao-Softbrush` | 400 | — | 远程 |
| 抖音美好体 | `DouyinSans` | 700 | — | 远程 |
| QIJIFALLBACK | `QIJIFALLBACK` | 400 | — | 远程 |
| 得意黑 | `Smiley Sans` | — | 400 | 远程 |
| 寒蝉宽黑体 | `Chill K Sans` | 500 | — | 远程 |
| 标小智无界黑 | `LogoSC Unbounded Sans` | 400 | — | 远程 |
| 猫啃什锦黑 | `MaokenAssortedSans` | 400 | — | 远程 |
| 猫啃什锦黑-轻量版 | `MaokenAssortedSans-Lite` | 400 | — | 远程 |
| 寒蝉锦书宋Pro | `寒蝉锦书宋Pro` | 400, 700 | 600 | 远程 |
| 荆南缘默体 | `Kingnamype Yuanmo SC` | 400 | — | 远程 |
| 荆南缘默体 | `KN Yuanmo SC` | 400 | — | 远程 |
| 辰宇落雁體 | `Chenyuluoyan` | 100 | — | 远程 |
| 清松手写体1 | `JasonHandwriting1` | 400 | — | 远程 |
| 清松手寫體3 | `清松手寫體3` | 400 | — | 远程 |
| 宇文天穹 | `UoqMunThenKhung` | 700 | — | 远程 |
| 精品点阵体9×9 1.6 | `BoutiqueBitmap9x9 1.6` | 400, 700 | — | 远程 |
| BoutiqueBitmap9x9 3D | `BoutiqueBitmap9x9 3D` | 400 | — | 远程 |
| BoutiqueBitmap9x9 Blur | `BoutiqueBitmap9x9 Blur` | 400 | — | 远程 |
| BoutiqueBitmap9x9 Circle Dot | `BoutiqueBitmap9x9 Circle Dot` | 400 | — | 远程 |
| BoutiqueBitmap9x9 Gradient | `BoutiqueBitmap9x9 Gradient` | 400 | — | 远程 |
| BoutiqueBitmap9x9 Square Dot | `BoutiqueBitmap9x9 Square Dot` | 400 | — | 远程 |
| 俐方体11号 | `Cubic 11` | 400 | — | 远程 |
| Aboreto | `Aboreto` | 400 | — | 远程 |
| Affigere | `Affigere` | 400 | — | 远程 |
| Alegreya | `Alegreya` | 400, 500, 700, 800, 900 | — | 远程 |
| Aleo | `Aleo` | 300, 400 | 100, 200, 300, 400, 500, 600, 700, 800, 900 | 远程 |
| Alex Brush | `Alex Brush` | 400 | — | 远程 |
| Alfa Slab One | `Alfa Slab One` | 400 | — | 远程 |
| Allison | `Allison` | 400 | — | 远程 |
| Amatic SC | `Amatic SC` | 400, 700 | — | 远程 |
| Analogue OS | `Analogue OS` | 400 | — | 远程 |
| Anticva | `Anticva` | 400 | — | 远程 |
| Archivo Narrow | `Archivo Narrow` | 400, 500, 600, 700 | — | 远程 |
| Asap | `Asap` | 100, 200, 300, 400, 500, 600, 700, 800, 900 | — | 远程 |
| Baloo 2 | `Baloo 2` | 400 | — | 远程 |
| Barlow | `Barlow` | 100, 200, 300, 400, 500, 600, 700, 800, 900 | 200, 300, 400, 500, 600, 700, 800, 900 | 远程 |
| Barriecito | `Barriecito` | 400 | — | 远程 |
| Barrio | `Barrio` | 400 | — | 远程 |
| Blackout | `Blackout` | 400 | — | 远程 |
| Coiny | `Coiny` | 400 | — | 远程 |
| Creative Zoo Sans | `Creative Zoo Sans` | 900 | — | 远程 |
| DynaPuff | `DynaPuff` | 400, 500, 600, 700 | — | 远程 |
| Familjen Grotesk | `Familjen Grotesk` | — | 600 | 远程 |
| Fivo Sans Modern | `Fivo Sans Modern` | 400 | — | 远程 |
| Fragment Mono | `Fragment Mono` | 400 | — | 远程 |
| Gidole | `Gidole` | 400 | — | 远程 |
| Gloock | `Gloock` | 400 | — | 远程 |
| Imbue | `Imbue` | 100, 200, 300, 400, 500, 600, 700, 800, 900 | — | 远程 |
| Lobster | `Lobster` | 400 | — | 远程 |
| Matrix Sans | `Matrix Sans` | 400 | — | 远程 |
| Montagu Slab | `Montagu Slab` | 100, 200, 300, 400, 500, 600, 700 | — | 远程 |
| Montserrat | `Montserrat` | 100, 200, 300, 400, 500, 600, 700, 800, 900 | 100, 200, 300, 400, 500, 600, 700, 800, 900 | 远程 |
| Montserrat Alternates | `Montserrat Alternates` | 400 | 900 | 远程 |
| Ostrich Sans Inline | `Ostrich Sans Inline` | 400 | — | 远程 |
| Paragon | `Paragon` | 400 | — | 远程 |
| Poppins | `Poppins` | 700 | — | 远程 |
| Post No Bills Colombo | `Post No Bills Colombo` | 700 | — | 远程 |
| Rubik Bubbles | `Rubik Bubbles` | 400 | — | 远程 |
| Solway | `Solway` | 300 | — | 远程 |
| Squatina | `Squatina` | 400 | — | 远程 |
| Story Script | `Story Script` | — | 400 | 远程 |
| Tonnelier | `Tonnelier` | 400 | — | 远程 |
| S-Core Dream | `S-Core Dream` | 300 | — | 远程 |

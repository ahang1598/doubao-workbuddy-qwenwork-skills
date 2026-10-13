---
name: doubao-ui-design
description: "豆包官方 UI 设计：用于可评审网页或移动端界面，并交付设计说明与可运行原型。覆盖官网、Landing、Dashboard、B 端后台、App、小程序、H5、活动页、设计展板、数据大屏的设计、改版、还原。海报/配图交 doubao-creative-design；完整应用交 doubao-app-builder；只编辑飞书文档交 lark-doc。"
---

# UI 设计

**设计权在你手里。** 这个包没有生成器，不会替你产出成品。

| 谁 | 负责什么 |
|---|---|
| **你** | 看参考、采素材、定四组数值、**亲手写 HTML/CSS/JS**、看自己的截图、改稿 |
| **脚本** | 交付合同、风格签名、真值门、素材采集、截图、飞书发布与字节对账、交付参数 |

骨架（`skeletons/`）只保证「装得下、不溢出、可读」。**好不好看是你的责任。**

---

## 第一件事

```bash
python3 <本文件所在目录>/scripts/ui.py brief --query "<当前请求原文，一个字都别改写>"
```

**在它之前不要做别的。** 它 5 秒钟给你：交付合同、工作目录、风格签名、成品骨架、
必读工艺清单、**这一稿的对手**（对口金标准的三段源码）、素材计划、
以及后面每一条完整命令。

**后面的命令一律从它的输出里复制**（都带 `--run <绝对路径>`）。
不要凭记忆敲，不要 `cd` 进包目录 —— 产物不落在这个包里。

| 命令 | 它做完什么 |
|---|---|
| `brief` | 合同 + 签名 + 骨架 + 必读工艺 + 对手 + 素材计划 |
| `review` | 截图 + 真值门 + 看图回执。**它自己认阶段**：成品页没看够两轮就看成品页，看够了转去做 doc 的画布与封面 |
| `ship` | 关键屏自动写进画布 + 补跑门 + 发布 + 字节级回读 + 封面三级重试 + 出交付参数 |

每条命令的**开头和结尾**各重印一次合同横幅，末行只有**一个** NEXT。
**横幅要看，别靠记。** 上下文会被压缩，压缩会丢掉几何与数字 ——
横幅里那几行（形态、风格签名、版心上限、两档取景、必交件、当前请求原文、盘在哪）
就是被丢掉的那一类。每次读到横幅，用它校对一遍自己手上的方向。

---

## 主链路的工具（照着调，不要自己试）

下面每一条都在真实运行里验证过。**不在这张表里的做法一律不要发明。**

| 要做的事 | 用哪个工具 | 怎么调 |
|---|---|---|
| 跑这个包的命令 | `Bash` | 超过 15 秒会**自动转后台**并返回 `task_id` —— 那不是失败。用 `TaskOutput(task_id, block=true, timeout=180000)` 读结果 |
| 看自己的产物 | `Bash` 跑 `ui.py review` | **它是一条命令**。一条做完：起服务器 → 整页与逐状态截图 → 跑门 → 写看图回执。**不要**自己 `open_url_in_browser` / `take_screenshot` / `python3 -m http.server` |
| 生图 | `image_gen` | 返回里带 `<uri>` 短链；用 `curl -L -o assets/<名字>.jpg "<uri>"` 下到成品页旁边，再按相对路径引用 |
| 素材上公网 | `FileBatchUpload` | `path_list` 传**绝对路径数组**；返回里每项含 `path` 与 `uri`，整段喂给 `deliver.py --upload-map` |
| 交设计方案 Doc | `NotifyHuman` | `attachments=[{attachment_name, attachment_source}]`，`attachment_source` 是飞书 URL |
| 交界面卡 | `app_builder_agent` | `user_prompt` = **HTML 全文**。传文件路径它读不到，会照描述重画（图会全丢） |
| 两张卡的顺序 | — | **先 `NotifyHuman` 交 Doc，再 `app_builder_agent` 交卡**，参数都由 `ui.py ship` 产出 |

**产物只有两件，格式是固定的：**

| | 是什么 | 格式 | 谁交 |
|---|---|---|---|
| 交件① | 可运行的成品页 | 单文件 HTML（形态见文末的表） | `app_builder_agent` |
| 交件② | 设计方案 Doc | 画布 HTML + 封面 + `proposal.xml` → 飞书文档 | `NotifyHuman` |

**不要用 `file://` 链接交付**，那不是产物。

---

## 一、看：先看到好东西，才做得出好东西

**顺序是硬的：看完再动手。** 写第一行 CSS 之前，这四件事必须发生。

### 1　看这一稿的对手

`brief` 已经把对口的金标准连**三段源码**一起印出来了。打开它，看那三段。

| 你这一稿 | 对手 | 它证明了什么 |
|---|---|---|
| 产品界面 | `gold/app-home/` | 能用的产品原型：tab 真的切、卡片真的展开、底栏真的留了位置 |
| 单向叙事 | `gold/h5-qq2026/` | 十屏复古风，**零 `<img>`**，全部 SVG/CSS 手绘 |
| 互动生成器 | `gold/h5-cycle/` | 满版照片 + 暗场 + 文字压上面，结果卡是整个 H5 的产品 |
| 宽屏站点 | `gold/web-pulse/` | 17 张实拍 + 可用购物车，首屏影像占比 100% |
| 控制台 | `gold/console-api/` | **亮场**工作台：一个数配一个环比，四种状态齐全，满屏是图反而错 |
| 数据大屏 | `gold/screen-hotan/` | **深场** 4001×2251：地图是唯一主角，红只给预警 |
| 设计展板 | `gold/board-flow/` | 5 帧横排：编号 + 中文步骤标签 + 箭头，帧内浅、帧外深 |
| 活动长图 | `gold/longimg-summit/` | 750×N：首段能单独当封面，段与段之间四种换气交替 |
| 文档画布 | `gold/doc-canvas/`、`gold/doc-cycle/` | 同一套七节结构，**三种完全不同的视觉人格** |

`gold/console-api/` 与 `gold/screen-hotan/` 各带一份 `rubric.md` ——
那是当初给它打分用的**真实评分细则**（六个维度，满分标准 + 扣分判断）。
**从"扣分判断"那一列读起：知道会怎么扣分，比知道满分长什么样更有用。**

**规矩（`gold/README.md`）：学机制，不抄版式。**

- 允许学：为什么章节用一条墨线分隔、为什么商品缝隙只留一线、为什么砍掉装饰气泡。
- 禁止抄：四宫格的具体排法、章节编号的具体样式、关键屏网格的具体结构。
- **产物和 gold 在版式上一眼能认出是同一套模板，就是抄了。**

三份 doc 的七节结构一字不差，视觉人格没有一处相同 ——
白纸编辑体 / 微黄档案纸衬线体 / 沙色圆润体。
**结构可以共享，人格不能共享。**

### 2　看外部锚点

`reference/fingerprints/index.json` 是 4 个获奖站在真实浏览器里的**实测数值**
（不是估计值），每个站带一句读法：

> cowboy：满版真实照片 + 巨字标题 + 单个胶囊 CTA + 近单色深场。
> 字阶 4.5 · display 72 · 首屏图占比 100% · 面色 3 种。

`brief` 会印其中三个。`review` 全绿时还会印一张**三列并排对照板**
（你这一稿 / 对口 gold / 获奖库区间）。
**那张板不是门，一条都不阻断** —— 它只回答一个问题：离好还差多远。怎么补是你的事。

`reference/fingerprints/thumbs/` 里有三张缩略图，直接读进上下文看。
`reference/scale-atlas.json` 是数值区间的原始分布；
`reference/competitor-evidence.md` 是竞品证据怎么记。

### 3　看竞品

至少 3 个同类站点，真的点进去，看图、看排版、看动效。
用户给了参考图或参考视频就先看它：视频用 ffmpeg 按 1–2fps 抽帧，拼联络表一次看完。

### 4　读必读工艺

**这几份在动手之前读完，不是"按需"。** 每份 1–2 秒。

| 文件 | 它回答什么 | 什么时候必须读完 |
|---|---|---|
| [craft/award-mechanisms.md](craft/award-mechanisms.md) | **什么叫得奖级**：M1–M6 / N1–N6，带案例与反例 | 开始定风格之前 |
| [craft/scale-atlas.md](craft/scale-atlas.md) | **12 份获奖稿的数值区间**：字阶断崖 / 圆角 / 强调色饱和度 | 定字阶和圆角之前 |
| [craft/composition-motion.md](craft/composition-motion.md) | **构图四条关系 + 滚动驱动 vs 入场揭示 + H5 的两条形态** | 决定首屏长什么样之前 |
| [craft/aesthetic-baseline.md](craft/aesthetic-baseline.md) | 四组数值的判据与参考站实测区间 | 写 `:root` 之前 |
| [craft/page-grammar.md](craft/page-grammar.md) | 每一段先答 `job` / `proof` / `geometry` / `move` 再决定形状 | 排第一段版之前 |
| [craft/interaction-contract.md](craft/interaction-contract.md) | **九条交互机制**，按形态各给一种落法 | 写第一个按钮之前（移动端） |
| `method/04-build-{web,h5,doc}.md` | 这个载体怎么做、哪些做法会出错 | 拷骨架之前 |
| [reference/image-direction.md](reference/image-direction.md) | 生图门 A 八项自检 | 采素材之前 |

**先读 `award-mechanisms.md`（做什么），再读
[craft/anti-patterns.md](craft/anti-patterns.md)（别做什么）。**
顺序反了，你会得到一稿"什么都没做错、但也什么都不出彩"的东西。

按题材再挑：
[craft/product-palettes.md](craft/product-palettes.md)
（dashboard / 后台 / 工作台 / SaaS 配色，**写 B 端界面配色前必读**）、
[craft/composition-mechanisms.md](craft/composition-mechanisms.md)（构图机制）、
[craft/motion-patterns.md](craft/motion-patterns.md) 与
[craft/motion-engines.md](craft/motion-engines.md)（挑一个 signature motion）、
[craft/motion-quality.md](craft/motion-quality.md)（动效服务叙事与状态，不是效果计数）、
[craft/completeness.md](craft/completeness.md)（做没做完）、
[craft/phosphor-icons.md](craft/phosphor-icons.md)（图标库怎么用）。

**动手之前写下 3 条：这一稿要在哪一维超过它们。** 每条指到具体机制，不许写"更好看"。
详见 [method/01-look.md](method/01-look.md)。

---

## 二、采：素材落地，再排版式

合同里的 `assetPlan` 已经按题材列好角色。三条路通常混用：

| 路 | 什么时候 |
|---|---|
| `image_gen` / `image_edit` | 品牌主视觉、产品英雄图、场景、氛围 |
| `text_to_video` / `image_to_video` | query 明确要动态影像。5–8 秒，必须留 poster 降级 |
|  `<本文件所在目录>/scripts/fetch_photos.py` | 真实世界的照片：人像、场景、材质 |

**生图的两条硬约束（绕不过去）：**

1. **只能出矩形，没有透明底。** 生图唯一正确的角色是**满版背景**：
   主体在画面里，文字用 HTML 压在上面。当浮动元素贴上去必然带一圈白边。
   异形、图标、圆头像一律走 SVG / `clip-path` / `border-radius`。
2. **画不了精确中文。** 分工是：**生图负责背景与氛围，HTML 负责所有要读的字。**

**图标不要手搓，更不要用 emoji。** 包里有 Phosphor 全套（1512 个，MIT，
`fill=currentColor`，`viewBox 0 0 256 256`）：

```bash
python3 <本文件所在目录>/scripts/icons.py find 搜索 消息 发布 我的
```

直接打印可内联的 `<svg>`。**一稿只用一种字重**
（`--weight regular|bold|fill|light|thin|duotone`）—— 混用是图标不统一的头号成因。

**成品页最终要有 ≥8 个真实视觉资产**（产品界面形态 ≥5）。
它会被逐张数，数不够会写进交付前的披露清单。
详见 [method/02-source.md](method/02-source.md)。

---

## 三、定：四组数值 + 一份拒绝清单

- **色板**：底色不停在纯白/纯黑；强调色只给一个角色用；同一块面积里只允许一个强调色
- **字阶**：要有断崖，标题不能只是"大一点的正文"
- **圆角**：3 个角色值；建议「只有可点的东西才是圆的」
- **栅格**：留白跟视口走；卡片缝隙可以小到一线让图连成一片
- **拒绝清单**：把你决定不做的模板写下来。**它是内部方法，不进文档**

**机箱可以复用，人格不可以。** 分屏、安全区、取景框、状态栏可以照搬；
配色、字体、构图必须按 `style.json` 的六维签名重新长一遍。
要查的时候单跑：`python3 <本文件所在目录>/scripts/style.py --diverge A B`，要 ≤0.55。

判据见 [craft/aesthetic-baseline.md](craft/aesthetic-baseline.md)、
[craft/anti-patterns.md](craft/anti-patterns.md)。

---

## 四、做

`brief` 已经按形态把骨架拷到位了。**直接改它**，所有 `TODO` 和占位值都要换掉。

**统一走 HTML，没有"要不要生图"的分叉。** 画面由素材层承担：
满版底图 + 可控暗场 + 文字压在上面（`h5.html` 的 `.art` / `.scrim` / `.content` 三层）。

**每一段先答四个问题再决定形状**：`job` / `proof` / `geometry` / `move`
（[craft/page-grammar.md](craft/page-grammar.md)）。
**不要让所有段共用一个骨架** —— 十屏一个模子是最容易犯的错。

**改稿只用 Grep 定位 + Edit 改那一段。**
不要为了找上下文整份重读成品页；doc 画布和封面**不要整份 Write 覆盖** ——
骨架的 CSS 就是它保证「装得下、不溢出、可读」的全部内容，
飞书块宽会浮动，那些 `clamp`/`min` 是踩出来的。

[method/04-build-web.md](method/04-build-web.md)｜
[method/04-build-h5.md](method/04-build-h5.md)｜
[method/04-build-doc.md](method/04-build-doc.md)

---

## 五、review：看自己的产物

```bash
python3 <…>/scripts/ui.py review --run <…>
```

一条命令做完：整页截图 + 逐个**真实界面状态**截图 + 联络表 + 按合同选 profile
跑真值门 + 把 `observed.json` 连量值一起写好。传本地路径就行，它自己起服务器。

**它自己认阶段，认到的印在横幅第 4 行。** 你不用记现在该跑哪一条。

### 把图读进上下文，真的看

然后编辑 `observed-*.json`。`selector` 和 `measure` 已经量好了，你补判断那几栏：

```json
[{"where":"会员区左右分界","selector":".join-media",
  "what":"左侧强调色与右图背景橙相邻，两块橙打架",
  "measure":{"hex":"#FF3B14"},
  "fix":"换成高调黑白人像并锁 grayscale"}]
```

改完跑**同一条命令**，它会把你说的每个坐标、颜色、字号去页面上量一遍。
**编不出来的东西编了会被戳穿。**

**看两轮**：看 → 改 → 再看。第二轮的条目带 `"resolved": true`，
量值按改完之后的新数值写 —— "改了"这件事也是量出来的。

### 移动端量两档取景

390×844 是真机；**1440×900 是卡片被用户打开的宽度**。
后者只量一条 `frame-intact`：**版心必须 ≤520px**。
用取景框、`max-width`、还是 `margin:auto` 都行，它不问实现，只量几何。

状态栏 / 顶栏 / 底栏一律 `position:absolute` 放在取景框里，**不要 `fixed`** ——
`fixed` 会脱出取景框贴到视口上，桌面宽度下横贯 1440px。

### 关键屏是「真实界面状态」，不是「滚 N 次」

骨架里预填了 `window.__UI_CAPTURE__`（首页 / 展开 / 弹层 / 各个 tab），
截图器只**枚举**它，一个按钮都不猜。

**改稿时要跟着改这份清单**：删了 tab 就删掉对应的 state，
加了筛选 / 详情 / 空态就加进来。截出来的图两两比 sha256，**全都一样也算 FAIL**。

详见 [method/05-review.md](method/05-review.md)。

---

## 六、doc：review 的第二个阶段

```bash
python3 <…>/scripts/ui.py review --run <…> --persona "paper=…,ink=…,…"
```

成品页看够两轮之后，**同一条命令**自己转到这一半：建两块画布 + 封面 +
`proposal.xml` 骨架；写完再跑一次，它出封面图、给画布截 698 宽、跑 doc 门。

`--persona` 是 11 个视觉角色，**没有默认值** ——
它是唯一能阻止"所有人的文档长得一样"的地方。
`brief` 已经按 `style.json` 的签名把方向印给你了。

**关键界面那一节不用你贴图。** 画布骨架里有 `<!-- KEY-SCREENS-START -->` 标记块，
`ship` 会拿成品页现截的真机屏，压好、转成 data URI、**原地写进去**。
你只要把 figcaption 换成你的话。
**顺序因此是物理的：先做完成品页，再写 doc。**

**画布里的图不要自己搓压缩命令。** `pack_img.py` 的宽度和质量各有下限，
会自己协商并把退让原因打出来；长图自动切段，出的就是能直接贴的 data URI。
自己 `sips -Z` 降尺寸会把竖着的手机截图压到 185px 宽，贴进 795px 版心就是糊的。

**doc 是给客户看的汇报。** 七节：我们怎么理解这件事 / 我们看到的机会 /
设计主张 / 视觉语言 / 关键界面 / 为什么这对你有效 / 下一步。
详见 [method/04-build-doc.md](method/04-build-doc.md)。

---

## 七、ship：交付

```bash
python3 <…>/scripts/ui.py ship --run <…>
```

关键屏自动进画布 + 补跑门 + 发布 + 字节级回读对账 + **封面三级重试** + 出交付参数。
**发过一次之后重跑会改成重发同一篇**，不会给同一份稿产出两个链接。

`ship` 只在一种情况下拒绝：**盘上没有可发的东西**。
其余全部发完再披露，写进收据由 `deliver.py` 再印一遍。

### 两张卡，顺序是硬约束

**① 先 `NotifyHuman` 交 Doc URL　② 再调 `app_builder_agent` 出网页/H5 卡。**
换顺序会丢卡，原因见 [delivery/host-contract.md](delivery/host-contract.md)。

**两张卡都要交，一张都不能少。** 只交 Doc = 用户拿不到设计说明；
只交卡片 = 用户点不开你的界面。`ship` 的最后一段会把两张卡的参数一起打印出来。

网页类产物**不能**走 `NotifyHuman`，只能经 `app_builder_agent`。
所以第二张卡的质量，全部取决于**递给它的那份 prompt 是什么形态**。

### 交卡四步

> **一句规则：正文内嵌，图片外链。**
> **HTML 正文**整段进 `user_prompt` —— 宽屏和移动端一视同仁，没有例外。
> **图片**必须是公网 URL，不要以 data URI 内嵌进 HTML。
> 两条做反的样子：图片撑爆 HTML → prompt 大到发不出去 → 退化成传一行路径 → 图全丢。

```
① 图片上公网    FileBatchUpload(path_list = 成品页 assets/ 下的全部图片)
② 生成 prompt   deliver.py --run <run.json> --upload-map "<FileBatchUpload 返回原文>"
                → 相对路径就地换成公网 URL，写出 deliver/app-prompt.txt
③ 交卡          Read deliver/app-prompt.txt → 整段作为 user_prompt
                ✗ 不传文件路径　✗ 不写功能摘要　✗ 不按自己的理解重述
④ 回读核对      拿返回的 app_id 再调一次，问首屏有几个 <img>、src 是什么
```

第③步为什么必须是正文：`app_builder_agent` 只收一个纯文本参数，
它的沙箱与本机不共享文件系统。**递路径 = 递了一句它读不到的话**，
它只能照剩下的描述重画一遍，照片会变成色块。

第④步是唯一能证明「卡片里是这一稿」的动作。`<img>` 数量对不上就把
`deliver/app-prompt.txt` 整段重发一次（带同一个 `app_id`）。

**不要手抄 URL。** `deliver.py` 出参数，`deliver.py --confirm "<返回原文>"` 回来对账。

---

## 交付形态：两件必交，成品有多种形态

产物 ① 永远是**设计方案 Doc**（窄栏排版画布 + 封面）。
产物 ② 是可运行的成品页，形态按需求分：

| 需求 | `--surface` | 产物 ② |
|---|---|---|
| App / 小程序 / 界面改版 / 首页 / 列表 / 详情 | `mobile-app` | **能用的产品界面原型**：首屏就是产品首页本身，≥2 个点了会变的真实状态 |
| 年度报告 / 盘点 / 品牌活动页 / 营销专题 / 测测你的… | `mobile-h5` | 分屏叙事 H5，或钩子 → 选择 → **专属结果卡** → 分享 |
| 官网 / Landing / 品牌站 / 作品集 | `web-site` | 宽屏可运行网页 1440×900 |
| Dashboard / B 端后台 / 监控台 / 工作台 | `web-console` | 1440 与 1920 两档；**表格、筛选、弹窗、空/异常状态都要有**；B 端满屏是图就是设计错误 |
| 设计展板 / 交互流程图 / 图层拆解 | `spec-board` | 横向多帧 + 箭头 + 中文步骤标签，一张给人看的方案图 |
| 数据大屏 / 指挥中心 | `big-screen` | 按 query 给的尺寸（如 4001×2251），不滚动、不触控 |
| 活动分享长图 | `long-image` | 750×N 单栏纵向 |

**形态判错了整份稿就是错的。** 用户点名了就照他说的：
`ui.py brief --surface <id> --query "…"`；判错了重冻：`--force --surface <id>`。

`brief` 还会判另外三件事，一起印在横幅上：

- `operation`：`create` 新建 / `revise` 按用户给的旧版改 / `restore` 按参考图还原 /
  `amend` **就地改这一稿已经交出去的产物**（带 `--run` 指向那次 run，不重出、不重发新链接）
- `deliverables`：交什么（默认 `{html, doc}`）
- `count`：用户点名的数量（「恰好 5 屏」是硬的，脚本推导出来的只提示不阻断）

Doc 里放的是设计思路、设计想法、设计语言、为什么这么设计；
Doc 的 HTML 以**排版**为主（窄栏，像一份印出来的专题），
成品网页/H5 才是**画面与时间**。两者好看的机制完全不同，不要用同一套判断。

---

## 需求账本：用户点名的东西，一条都不许丢

`brief` 会从 query 里抽出**用户逐字点名**的东西 —— 文案、数量、色值、尺寸、
必须有的模块、必须避开的东西 —— 列成一份账本印出来。

**文案要 100% 匹配原文。** 用户写「立即预约」，页面上就得是「立即预约」，
不是「马上预约」。`ship` 会逐条对账，缺项会夺走 NEXT。

---

## 门的立场

真值门全部在真实浏览器里量，全部是「看图看不出、但读者受损」的项。
BLOCK 只有 14 条，其余全是 REPORT。**七种载体共用同一套门码**，分化靠「关掉不适用的那几条」，不靠加门。

1. **门守下限，抬不高上限。** 上限靠 `review` 的看图闭环、`gold/` 和
   `craft/award-mechanisms.md`。**不要把设计规则化** ——
   门告诉你哪里坏了，不告诉你该长什么样。
2. **任何门在"目标集合为空"时必须 FAIL。** 对偶：**目标集合全都一样也必须 FAIL。**
3. **门守的是下限，不是品味。** 门告诉你哪里坏了，不告诉你该长什么样。
4. **能阻断交付的判据只剩一种形态：可证伪的产物存在性。**

审美判据（`--aesthetic`）只有四条，每一条都拿参照案例验过不会判死好稿。
它们是 REPORT，不阻断 —— 因为"平庸 vs 优秀"不是"能不能读"。

---

## 预算

单任务 ≤35 分钟 / ≤120 次工具调用。**脚本命令只占 5 条**：
`brief` 1 + `review` 3（成品页两轮 + 文档一轮）+ `ship` 1。
剩下的全是你的工作 —— 看参考、采素材、写 HTML、读自己的截图、改稿。

> 一次任务里「看自己产物」的动作少于 2 次，这一稿多半是丑的。

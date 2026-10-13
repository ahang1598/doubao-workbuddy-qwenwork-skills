# CSS 配方库｜直接读分类内容

本库按布局、形状、材质、配色与组合职责组织，参数与实现保存在各分类正文。新建／整体重做在 Brief 冻结前先比较组合并适配设计方向，再选择必要原子；冻结后读取实现并绑定 HTML。Brief 用自然语言写设计，另留简短 CSS 采用记录；不复制 CSS 参数，具体筛选见 [组合参考筛选](#brief-combination-match)。

## 按品类 Ref 读取

1. 先从 [`../ref-bindings.json`](../ref-bindings.json) 的 `category_refs` 确定当前品类的稳定 `ref_key`，并读取该键指向的 Spec 与 Visual System。
2. 用 `ref_key` 取得 CSS 候选：先应用 `css.entry_overrides`，未列出的条目继承 `css.default_ref_keys`。默认关联只代表可以进入候选集，不代表必须采用。
3. 再从 [`../../svg/catalog.json`](../../svg/catalog.json) 读取 SVG 的稳定 ID、真实文件、CSS 消费者和适用品类。不得凭文件名猜资源职责。
4. Brief 冻结后先读取选中实现及依赖，再在最终 HTML 记录实际采用的 CSS／SVG ID、作用对象、依赖、覆盖值与未采用原因，并展开为行内样式；素材就绪组装时校核实际绑定。Brief 保留设计说明与短采用记录，不复制实现参数。
5. 从 Skill 根目录运行 `python3 scripts/maintenance/check-template-ref-bindings.py`，校验品类键、CSS 条目、SVG 文件、消费者与覆盖完整性；需要把品类解析成带名称的候选清单时运行 `python3 scripts/maintenance/check-template-ref-bindings.py --ref-key <ref_key>`。

| 想改什么 | 直接读取 | 文件内实际内容 |
|---|---|---|
| 组件留白、字体、行高、错位 | [组件布局与字体](layouts/layout-and-type.md) | 参数表、文字 CSS、紧凑／宽松密度；页面布局见下方分类 |
| 连续微距感官长图 | [微距叙事长图](layouts/continuous-flow.md#layout.sensory-macro-longpage) | 独立全页布局；只有材质局部两列，配色与素材另选 |
| 圆角、页签、文件夹轮廓 | [容器形状](shapes/containers.md) | 几何参数、HTML 骨架、完整 mask 与轮廓代码 |
| 字体／卡片／背景质感 | [按作用对象选择](#effect-object-routing) | 类型共用一份实现；按对象读取适配方式，再进入参数正文 |
| 主色、表面色、文字色 | [全部配色入口](colors/palettes.md#palette-directory) | 所有已登记配色的直达链接；参数留在对应正文 |
| 直接拿组件或快速搭配 | [组合配方](combinations/recipes.md) | 六个 recipe、章节组合与短引用源模板 |

<a id="effect-object-routing"></a>

## 质感分类与作用对象入口

**按类型维护唯一实现，按作用对象选择用法，按风格筛选组合。** 下表只是指向现有实现的入口，不创建“字体版纸纹／卡片版纸纹／背景版纸纹”三份代码。不移动已有文件、ID或资源；文字裁切等适配器仍在文字正文维护。

类型归为纸张印刷、玻璃塑料、金属浮雕、织物编织、柔焦光照、渐变色场、字形填充及字形轮廓。catalog 的 `effect_type` 表示机制类型，`effect_targets` 使用 `text`（字体）、`card`（卡片）、`background`（背景）；这些是支持对象，不是风格标签，也不是运行时自动应用命令。未填此字段的布局、配色或组合继续按原有入口检索，不因此视为不可用。

| 作用对象 | 目标效果 → 唯一实现 | 应用方式与边界 |
|---|---|---|
| 字体 | [渐变／纹理填字](layouts/layout-and-type.md#text.paint)＋[渐变](colors/palettes.md#color.gradient)／[纸纹](surfaces/paper-and-print.md#surface.light-paper) | 字形裁切由text.paint承担，只取所需纹理资源或paint，不复制纸张卡片结构；透明纹理需实色底填充，避免缺字 |
| 字体 | [金属反光带](surfaces/metal-and-relief.md#surface.metal-bands)＋[填字](layouts/layout-and-type.md#text.paint) | 反光色标唯一维护，裁切到标题字形；不把整块矩形背景称为金属字 |
| 字体 | [描边](layouts/layout-and-type.md#text.outline)、[发光](surfaces/diffuse-light.md#surface.neon-edge)、[浮雕](surfaces/metal-and-relief.md#surface.type-relief) | 分别使用字形描边、文字发光分支或文字挤出；正文独立，描边不能堵塞字腔 |
| 卡片 | [纸张](surfaces/materials.md#material.paper)、[玻璃](surfaces/materials.md#material.glass)、[塑料](surfaces/plastic-and-gel.md#material.plastic) | 所选形状＋共用表面＋材质覆盖；内容层独立，表面alpha／模糊不作用于正文 |
| 卡片 | [柔焦与薄雾](surfaces/diffuse-light.md#surface.soft-focus-mist) | 仅卡片内图像／装饰层使用filter:blur；限制区域、预留边缘，内容与主体保持清晰；不复制一份“卡片柔焦” |
| 卡片 | [织纹](surfaces/textile-and-craft.md#surface.woven-grid)、[金属带](surfaces/metal-and-relief.md#surface.metal-bands)、[霓虹边](surfaces/diffuse-light.md#surface.neon-edge) | 面纹理放表面层，发光框放不被mask裁剪的外层；亮边和文字发光不能误用同一选择器 |
| 背景 | [轻纸纹](surfaces/paper-and-print.md#surface.light-paper)、[屏幕颗粒](surfaces/paper-and-print.md#surface.screen-grain)、[网点](surfaces/paper-and-print.md#surface.dot-pattern)、[织纹](surfaces/textile-and-craft.md#surface.woven-grid) | 明确整页／章节／局部范围、尺度、强度和混合方式；纹理在文字与主体下，不继承卡片页签或投影 |
| 背景 | [弥散光晕](surfaces/diffuse-light.md#surface.diffuse-field)、[柔焦与薄雾](surfaces/diffuse-light.md#surface.soft-focus-mist) | 柔焦仍引用同一ID；背景范围可以更大，blur与边缘外扩按画幅调整，照片已有光影不重复叠加 |
| 背景 | [渐变色场](colors/palettes.md#color.gradient)、[图片渐隐](surfaces/diffuse-light.md#surface.image-fade) | 前者绘制颜色，后者修改图片alpha；绑定不同图层，渐隐不能抹掉文字或产品 |

### 柔焦与毛玻璃不能因名称接近而合并

- `surface.soft-focus-mist`：模糊选中的图像自身，使用filter；适用卡片局部或背景。卡片／背景两条引用共用一份实现，仅改变范围和参数。
- `material.glass`：透过半透明表面模糊后方内容，使用backdrop-filter及现有表面结构。默认按面板调用，必须有合适后景；不把一层透明白色称为已经实现毛玻璃。
- 字体的“柔光”通常先查文字发光分支；只有明确的艺术字需求才允许模糊装饰字层，清晰文字本体保留。不要让柔焦默认影响正文。

局部原子补充或明确局部编辑时：确定承载对象→按效果类型与具体tags找候选→读取唯一实现及依赖→绑定到HTML的真实图层、范围和参数→渲染检查。对象字段只帮助定位，不替代素材、层级与可见性判断；特殊适配只有实现或参考有依据才做，不因检索表为空自动否定效果。

## 风格标签：一级、二级与通用

本库保留布局／形状／质感／配色／组合目录；风格是交叉检索维度。同一原子只维护一份实现，不因适配多个风格复制文件。

- `通用`：可跨风格调用的结构或机制；不表示无需调参，也不表示每张页面都要使用。
- `一级：大类`：当前预设自身具有该大类的明确视觉特征，但不足以确定二级分支。
- `二级：大类 / 分支`：当前预设的构图、配色、字体或装饰关系共同支持该分支，检索时同时归入父级，无需重复登记一级。
- **没有明确风格属性，只标 `通用`，不同时挂一级／二级标签。** “能用于”“常见于”不是归属依据；不要用可搭配范围、参考图整体风格、预设名称或单一颜色替代当前实现的证据。
- 几何形状、材质、光效、排版机制和单独配色通常按通用处理；组合也不自动获得风格属性。只有组合本身形成可识别的视觉关系时才标风格，并在正文简述依据；以后新增条目沿用此标准。
- 具体正文是标签维护源；catalog 的 `style_tags` 同步这些标签，原 `tags` 保留形状、材质、颜色等效果词。默认值、依赖和代码仍只在正文维护。

### 布局的适配风格

`style_tags` 描述当前实现的风格归属；`style_affinities` 描述结构可以承载的风格，两者不可混用。通用布局可以保留 `style_tags: ["通用"]`，同时具备适配风格。适配元数据仅在 `catalog.json` 对应条目维护，正文不复制另一份表。

每项包含 `style`（风格家族／分支）、`terms`（自然查询词）、`level`（`strong` 或 `adaptable`）、`reason`（结构依据与必要调整）。强适配应由现有图文结构支持；可适配需要说明调整，不把任意换色视为适配证据。颜色不自动扩展为风格，不把容量、打印或 ATS 合格当风格标签。`related_combinations` 只关联真实使用该布局的组合，不新增实现依赖或复制代码。

检索按直接／扩展／弱命中区分证据，同等命中阶段优先强适配，再比较可适配与其他元数据；别名重复不累加适配权重。`style_matches` 返回命中词、程度、依据，`describe` 返回完整适配信息及关联组合。标签帮助召回，不代替内容、阅读路径和视觉核验。

简历按风格选型时，依[简历 Visual](../../../references/style/coding/systems/resume-visual-system.md)先检索整页布局，再比较其关联组合和采用范围，随后才补局部原子；这是下方公共组合流程的品类入口。局部修改或用户指定完整组合仍直接沿原选择处理。

| 一级大类 | 二级分支 |
|---|---|
| 理性信息风 | 极简理性、瑞士网格、企业宣讲<br>数据图解：可参考 [蓝白科研信息组合](combinations/recipes.md#combination.science-blue-white) |
| 杂志编辑风 | 时尚杂志、人文出版、人物专题、复古报刊 |
| 自然质朴风 | 清雅自然、北欧生活、侘寂质朴、田园森系 |
| 新中式风 | 当代东方、宋韵留白、水墨意境、金石古雅 |
| 国潮装饰风 | 年画民俗、工笔重彩、传统纹样、潮流国风 |
| 诗性浪漫风 | 情绪影像、柔光花艺、书信叙事、梦幻意境 |
| 感官生活风 | 滋养疗愈：可参考 [植萃绿金感官组合](combinations/recipes.md#combination.botanical-green-gold)<br>微醺生活、肌肤触感、居家仪式 |
| 复古商业风 | 美式餐饮广告、昭和商店招贴、海派月份牌、怀旧商品目录 |
| 手账拼贴风 | 旅行手账、票据档案、照片剪贴、杂志剪报 |
| 波普撞色风 | 漫画波普、复古波普、波普拼贴、孟菲斯几何 |
| 趣味创意风 | 童趣绘本、涂鸦手作、清新轻艺术、趣味拟物 |
| 都市潮流风 | 街头文化、字体潮流、音乐现场、复古数码 |
| 未来科技风 | 产品科技、工业科技、赛博未来、Y2K 千禧、复古未来 |
| 抽象光感风 | 柔雾弥散、颗粒渐变、全息虹彩、抽象光场 |
| 奢雅精致风 | 极简精品、古典雅奢、装饰艺术、时装雅致 |
| 先锋实验风 | 解构排版、平面粗野、酸性设计、超现实拼接 |
| [材质肌理风](../../../references/style/coding/systems/social-visual-system.md#social-style-17) | 纸墨版画、颗粒印刷、织物纤维、陶土手作、金属压印、透明薄膜 |

分类词汇覆盖 17 类，不代表每个分支已有专属组合。已登记条目的风格归属以正文与 catalog 为准；有明确组合依据才设置风格标签，其余保留通用。检索不到二级预设时，先扩展到适用的父级与同品类组合，评估可调整关系后再选择通用原子，保留摄影、插画、字体等资产需求；不得把纸纹说成完整水墨风，把玻璃或金属单独当作完整 Y2K 风。

分支下的名称是便捷链接，不是完整候选清单。适用分支与筛选条件统一在 catalog 的 candidate_contexts 维护，不等于 style_tags 的风格归属；命中分支后还需核对 use_when。新增候选关联先更新目录，不在各入口重复写条件。参数、素材要求与依赖仍只在组合正文维护。

### 按风格读取

1. Spec 形成内容骨架，Visual 提出可调整的风格和阅读关系。新建／整体重做先按品类、作用范围与用户效果词限量查找组合；已知候选用 `describe`，未知候选先 `search` 再 `describe`。不先把“卡片式”等开放要求收窄成模型自选的圆角、单栏或薄边，再只搜索对应原子。
2. 按用户锁定项、真实内容、画幅和素材职责比较组合的整体信息层级、图文关系与视觉语言。摘要不足以判断可调整范围时，对相关候选用 `get --prose` 补读；示例配色、人物、文案、栏目数量和暂缺素材本身不是排除依据。先判断换色、换内容、调整比例或局部结构后是否仍贴合，再决定取舍；首次比较与依赖其结果的实现读取保持先后顺序。
3. 贴合的组合在原结构内适配真实内容量：保留主次、对齐轴、阅读顺序和核心跨区关系，调整卡片、图窗、内容区的宽高与占比，以及内外间距、字号和行距。内容偏少时主动分配剩余空间，不让模块全部挤在顶部，也不只拉高空卡片；卡片尺寸与内部内容分布同步调整，图片保持比例并保护主体。留白应服务焦点与阅读节奏，不以填满率或所有模块等高为目标；不因内容偏少直接改栏数、搬移核心模块或重做整体构图。未覆盖的箭头、分隔、局部容器或材质再用原子补足，局部不适合优先替换局部。只有同范围组合经适配仍与用户要求或内容结构冲突，或确无候选，才转原子组装／自主实现；不能以模型预选布局为硬约束排除组合。适配后的可见结果写入最终 Brief，选中 ID、源路径和版本进入短采用记录，不复制参数，不修改用户事实与锁定项。
4. Brief 冻结并开始 HTML 细化后，才用 `get <ID> --dependencies` 读取选中实现及依赖，必要结构用 `template` 精确提取；把真实引用、参数、作用范围与消费者写入 HTML。素材就绪并组装 HTML 时校核实际绑定，后续变动只重查受影响部分。

按需检索工具为 [`scripts/runtime/query-css-library.py`](../../../scripts/runtime/query-css-library.py)：

```bash
# Spec 内容与 Visual 草案形成后，已知组合先比较摘要；未知时先 search，优先 describe 返回的少量组合候选
python3 scripts/runtime/query-css-library.py search "纸本 拼贴 照片 容器" --style "手账拼贴风" --ref-key social-long-image --kind combination --limit 5
python3 scripts/runtime/query-css-library.py describe combination.retro-pop-collage layout.collage
# 最终 Brief 冻结、选型确定后再读取实现
python3 scripts/runtime/query-css-library.py get combination.retro-pop-collage --dependencies --read-state /任务目录/css-read-state.json
```

`search` 做元数据召回，不给视觉适配分。除精确词外，检索器会将常用设计意图扩成边界明确的候选集：`图文关系` 召回主图、错位、拼贴、标注与图像衔接；`背景／氛围` 召回纸纹、织物、颗粒、柔焦与背景承托；`质感` 召回纸、玻璃、塑料、金属与纹理；`装饰／点缀` 召回背页、夹子、绳线、边框与图形细节；`有趣／创意／排版` 优先召回拼贴、路径、错落和非标准图窗；`特效` 召回文字描边、填字、立体字和受控边光；`配色／色彩` 召回色板。它们只扩大候选与排序，不能取代 Brief 对对象、用途和禁止项的约束。

泛化“卡片／容器／面板”查询会先列出文件夹、票券、撕纸、档案页、卷纸、切角框等结构型轮廓，并降低中性圆角容器；明确写“圆角／毛玻璃／塑料”时才恢复圆角候选优先。组合评估后补充局部容器时使用 `--kind shape`，再按已选轮廓分别查询材质、背页、胶带、夹具或阴影，不用“高级卡片”一词让圆角配方占满候选。`describe` 返回有限设计证据，不展开代码；`get --prose` 只补设计说明；`get --dependencies` 返回选中正文与声明依赖；`template` 只提取明确采用的结构节点。任务内可用 `--read-state` 去重已返回且未变化的段落，该状态必须放在任务目录，不写入 Skill，也不代表视觉验证通过。

### 依赖、结构与读取预算

`--dependencies` 展开正文明确依赖，以及 catalog `reading_contracts` 中标记为 required 的链接；optional 仅在采用对应效果时读取，reference 只作参考。未分类链接须结合实际采用范围确认，不能静默忽略后声称实现齐全。模板载体按正文或 `template_sources` 定位；只有采用该结构时才读取对应节点与必要样式，不加载同文件其他变体。

`describe` 缺少关键证据时，用 `get ID --prose` 补读设计说明；摘要未摘录不等于能力不存在。`template ID --block N` 读取选中的内嵌结构，外部模板可用 `--selector` 提取唯一节点。任务内 `--read-state` 按根目录、内容哈希与读取视图去重；换任务或上下文丢失后不用旧状态冒充已读。正文预算默认 30000 字符，超限时先缩小采用范围，确需完整大模板时显式调整，不截断实现或分批读完整库。

组合摘要可同时返回按实际语种与文字角色筛选的字体候选；`describe --font-language zh|en|ko|ja` 指定语种。字体候选、历史 CDN 记录和平台名单均不证明当前渲染可用，最终仍需核验真实文案、字形、字重及字面。

例如：波普拼贴优先定位 `combination.retro-pop-collage`，再按需补撕边／网点；音乐现场可检索电光青、霓虹和颗粒，是否使用由参考决定；产品科技仍可采用通用网格和主场，不能被标签强制加玻璃或赛博光效。

<a id="brief-combination-match"></a>

## Visual 草案 → Brief → HTML 的组合参考筛选

Visual 先比较同品类、同作用范围的组合关系，再确定适配方案与局部原子需求；模型提出的方向草案在该比较中完善，最终 Brief 只描述可见关系与效果。编译 HTML 时区分三种匹配，不另建平行清单：

| 匹配对象 | 记录内容 | 能说明什么 |
|---|---|---|
| Visual 的 R 类视觉组合 | Brief 记录参考名称、采用的图文／构图关系、适用段落与舍弃项 | 设计关系有参考依据，不表示已有 CSS 实现 |
| 本库 CSS 组合 | 实际组合 ID、正文、采用范围、覆盖参数及依赖 | 可复用该组件或章节的实现，不自动等于整页模板 |
| 本库局部原子 | 所选布局、形状、材质、颜色等引用与承载对象 | 局部效果有实现依据，余下构图与素材仍需落实 |

先检查视觉关系候选，再按本库规则判断实际可复用内容；不因未命中同名风格模板而跳过 Visual 中相关构图。前期比较结论写入同一 Brief 的短采用记录，包含采用依据、范围、内容映射和必要降级；随后由 HTML 记录真实实现引用。无需逐一列出无关候选，也不以“未匹配”概括三种结果。

适用于 HTML 创建／整体重做路线；已明确选定配方的任务或仅修改现有局部时，沿有效选型读取对应实现，不重复全页选型。新建／整体重做先理解用户参考和内容，由 Spec／Visual 提出方向草案，再按上方顺序比较组合、评估适配、补充原子，最后冻结 Brief。比较时按需读设计正文，冻结后才展开选中实现、依赖与结构；pure-image 不因命中组合转为 HTML。

- 比较整体构图与章节关系、视觉语言与质感、图像及文字的分工、内容密度与画幅。**适配度估计达到约 70%，且只需改部分参数、替换同职责素材与真实文案时**，在 Brief 短采用记录保留候选依据；编写 HTML 时把实际组合 ID、采用范围、真实消费者和覆盖参数直接落实到源码，Brief 保留人类可读的视觉关系和短采用记录，素材清单仍只记录图片生产。
- 70% 是基于参考的判断阈值，不是关键词命中率或自动相似度。可写“约 75%，结构与图文分工一致，调整配色和标题尺度”；不能只凭同色、同题材或同风格标签给高分。若要重做主要构图、叙事或素材关系，即使颜色相近也不算达标。
- 区分“组件／局部章节匹配”和“整页方向匹配”：现有六个材质卡片不能仅凭卡片相似就作为整页模板。局部匹配只引用到 Brief 的相应部分。
- 约 70% 的适配判断沿用上项标准，不要求精确同名或示例完全相同。依据不足先补读相关设计正文；经适配仍未达标或确无候选时，在 Brief 短采用记录简记具体冲突及“未采用现有组合”，再转原子组装。不得凑评分、牺牲用户参考或要求用户替模型筛库。
- 匹配只提供复用起点，不能替代原 Brief、视觉系统、KV、字体或素材要求。HTML 细化时展开被选组合及其依赖，并落实补充／替换的原子，HTML 完成／素材就绪后仍执行 CSS 复核；本步骤不代替最终绑定和渲染验证。

## 调用

已知候选先用 `query-css-library.py describe` 比较；未知候选才用 `search` 限量召回。选定后使用 `get --dependencies` 读取对应正文、共用层与依赖，不能只复制覆盖段；需要 HTML／SVG 结构时再按返回的 selector 使用 `template`，不加载同文件无关变体。

复用现成组件时从组合配方定位 [行内源模板](combinations/material-recipes.html)，读取所选配色和布局覆盖值后调整。需要改原子实现时，读取相应 CSS 代码块；原子组装方式见组合配方正文：圆角依赖文件夹共用结构，材质依赖共用表面／纹理／光照层与配色默认值；这些依赖不意味着新作品必须使用文件夹或玻璃。

## 当前已实现的范围

| 分类 | 已入库能力与入口 |
|---|---|
| 布局与字体 | 原有网格、阅读栏、主场、拼贴与连续流动；新增[通知／邀请函](layouts/notice-and-invitation.md)、[简历整页](layouts/resume-full-page.md)、[折页整版](layouts/fold-full-page.md)、[画册布局](layouts/brochure-and-booklet-layouts.md)与[跨版关系](layouts/spread-relations.md) |
| 形状 | 文件夹、票券、衬纸、卷纸、档案页、拱窗、胶带、夹具及信封折片等；同一机制按内容职责使用 |
| 材质与光照 | 纸张、玻璃、塑料、织物、光场与金属；新增[纸张、印花与贴布](surfaces/craft-detail.md)，生成器与局限见正文 |
| 配色与组合 | 分类色板、材质组件、邀请函、13 套简历组合、折页组合、蓝银演出与粉色派对等整页／章节组合，按[配方](combinations/recipes.md)与索引定位 |

组件、章节与整页模板分别标明采用范围，局部相似不表示整页匹配。库中存在实现不代表已通过当前目标平台渲染；按真实文案、素材与画幅调整后仍须检查。匹配标准继续遵循上方约 70% 原则。

## 路径与维护

- catalog 的 documents.path 相对 Skill 根目录（SKILL.md 所在目录）；Markdown 链接相对当前文件。组合记录的 template 相对组合配方文件。
- 各分类正文中的 CSS 代码块是原子实现源，HTML 模板是带资源短引用的组装源。更新原子后同步受影响模板，并检查样式、文字与遮罩。
- 索引只维护名称、标签、文件与 anchor；默认值、参数说明、依赖和覆盖值都维护在对应正文。同结构的变体不复制 SVG。
- 保留原品类路线、字体、固定画布与交付协议；正式 HTML 只保留实际节点、行内样式和内嵌 SVG，无本地路径或索引运行时依赖。

## 按视觉分类直接读取

| 类别 | 本批已填充文件 | 内容 |
|---|---|---|
| 配色 | [淡雅](colors/soft-and-muted.md)、[自然](colors/fresh-and-natural.md)、[理性](colors/calm-and-rational.md)、[复古](colors/rich-and-retro.md)、[撞色](colors/high-contrast-pop.md)、[明快](colors/bright-and-playful.md) | 共用语义变量的配色覆盖 |
| 布局 | [规整](layouts/grid-and-alignment.md)、[疏朗](layouts/airy-and-spacious.md)、[错落](layouts/asymmetric-balance.md)、[主场](layouts/hero-focus.md)、[连续](layouts/continuous-flow.md)、[拼贴](layouts/overlap-and-collage.md) | 各自的参数表、CSS 与 HTML 骨架；字体源文件另含填字／描边与弧形排字 |
| 质感 | [纸张](surfaces/paper-and-print.md)、[弥散](surfaces/diffuse-light.md)、[织物](surfaces/textile-and-craft.md)、[玻璃](surfaces/glass-and-frost.md)、[浮雕](surfaces/metal-and-relief.md) | 纸纹／颗粒、光场／霓虹、球面玻璃、浮雕／反光带、经纬／绳 |
| 形状 | [面板](shapes/cards-and-panels.md)、[徽章](shapes/capsules-and-badges.md)、[纸边](shapes/tickets-and-notches.md)、[衬纸／卷纸／档案页](shapes/notes-and-paper.md)、[拱顶／星芒](shapes/organic-shapes.md) | 圆角、阶梯框、徽章、纸边、卷边公告面、不规则档案纸、缝线、胶带、夹子、拱窗／拱顶、星芒与对话框 |

本批参数为参考图视觉近似，具体节点和覆盖关系见 [章节组合](combinations/recipes.md#页面章节的组合参考)。是否可用以具体正文的实现、依赖及状态为准；只有占位标题而无实现的条目不计入能力。旧玻璃、塑料、纸张和文件夹实现继续从上方通用正文读取。

<a id="svg-assets"></a>

## SVG 随包资源与交付内嵌

所有可复用 SVG 存在 Skill 的 [assets/svg](../../svg) 中，每份资源只存一次。正文与源模板只保留短引用；普通 CSS 渐变、经纬织纹不需要转成 SVG。引用 `asset:svg/paper-fiber.svg` 对应 Skill 根目录下的 `assets/svg/paper-fiber.svg`，不随任务工作目录改变。

```css
--vl-texture: url("asset:svg/paper-fiber.svg");
--vl-grain: .12;
--vl-texture-size: 256px;
```

生成时读取选中原子的参数与代码，保留短引用；完成节点展开和样式行内化后，使用 [内嵌脚本](../../../scripts/runtime/inline-svg-assets.py) 输出正式 HTML。下例从 Skill 根目录执行，输入和输出改成实际任务路径：

```bash
python3 scripts/runtime/inline-svg-assets.py --input draft.html --output final.html
```

脚本按自身位置找到 assets，不发起网络请求。普通 asset: URL 内嵌保留原 SVG；含 CSS 时使用 tinycss2 校验解析副本中的引用，不改写源内容，允许原样保留自包含条件样式；svg-inline 的 CSS 属性使用 tinycss2 解析 URL（包括转义及百分号编码的内部引用）；静态内部样式通过 tinycss2／cssselect2 按层叠优先级落实为节点 style，移除内部 style 元素后再改写实例 ID 与引用。脚本不负责整页 HTML 的 CSS 行内化；支持 CSS url 和 HTML src/href 中的短引用，包括行内属性里的转义引号。源模板直接打开不会加载短引用，先通过此步骤生成预览。

运行环境先安装 [素材工具依赖](../../../scripts/runtime/requirements-assets.txt)：`python3 -m pip install -r scripts/runtime/requirements-assets.txt`。不在生成过程中自动安装或静默跳过依赖。svg-inline DOM 转换的条件规则、动态伪类、伪元素及无法解析的样式明确报错，不能返回成功却丢失效果；转换失败时输入和已有输出保持不变。

最终 HTML 中，纹理／遮罩以 data URI 内嵌，可编辑路径文字以实际 SVG DOM 插入，均不再依赖 Skill、资源文件或脚本。脚本只打印资源数量与输出位置；不要把内嵌后的长串或整个最终 HTML 回读进模型上下文，验证时使用渲染结果与摘要。

新增 SVG 继续存入 `assets/svg`，同步登记到 [`../../svg/catalog.json`](../../svg/catalog.json)，并在所属分类正文写资源 ID、文件引用和参数；不在 Markdown、CSS catalog 或源模板中重复编码后的 SVG。只有修改 SVG 内部几何或滤镜时才按需读取那一份源码。项目独有变体放到任务 assets 副本，通过 `--asset-root` 指定副本；布局、颜色、grain 等外层 CSS 参数仍按原方式修改。

资源不存在、路径越界、SVG 自带外部依赖时，脚本报错且不写入成品。已有输出默认不覆盖，需要明确重建时使用 `--force`；输入文件始终保持独立。

<a id="brief-routing"></a>

## Brief → HTML → CSS 的读取顺序

目录供查询脚本按名称／标签限量召回，不执行适配评分，也不保存视觉决策。按 [组合参考筛选](#brief-combination-match) 先比较整体可复用关系，再检索局部实现；最终 Brief 保留适配后的可见目标，HTML 记录真实实现。

“复古高饱和拼贴”可先查 [对应组合](combinations/recipes.md#combination.retro-pop-collage)：高饱和指向明快或撞色配色，拼贴指向布局，复古还需纸面／字体与照片关系的证据；不只搜索“复古”颜色分类。命中只产生候选，按内容、画幅和素材选择后，直接读取被选原子的正文、共用层与依赖，不加载全库或 SVG 原文。

沿现有 HTML 记录：全局容器和元素的行内样式保存 palette、实际色值、网格、实例角度、层级和允许遮挡区；对应 DOM 节点记录 shape／surface 引用、资源短引用与局部参数；字体走原字体协议。不新增 `container_layout`、`assembly_relations` 或其他平行 schema。仅记录“复古”“拼贴”等标签不足以实现。

组装按所选引用展开 HTML 节点与行内样式，再内嵌所用 SVG，最后渲染核对。优先级保持：用户锁定项与参考约束 → 已确认的元素局部决策 → 全局参数 → 配方默认值。经组合适配评估后仍无适用候选时组合原子，并明确剩余素材／实现需求，不因目录里有某种效果就自动叠加。

文字质感先读 [填字、描边、路径排字](layouts/layout-and-type.md#text.paint)，再按需选 [文字挤出](surfaces/metal-and-relief.md#surface.type-relief)。通用渐变在 [配色参数](colors/palettes.md#color.gradient)，覆盖任意数量色标和逐色标透明度。参考效果的近似与素材边界见 [组合说明](combinations/recipes.md#补查后的覆盖边界)。

## 可编辑 SVG 文字的插入

纹理和 mask 继续使用 asset: URL 内嵌。需要继承页面字体／颜色并保留 textPath 的 SVG，先用 [生成器](../../../scripts/runtime/make-text-arc.py) 写到任务资产副本，再用 `<!-- svg-inline:svg/title.svg -->` 标记交给原内嵌脚本。脚本将其插入为实际 SVG DOM，并按实例重命名内部 ID。标记不是最终 HTML 的运行时组件，不在模型上下文中展开 SVG 源码。


## 明确风格组合的覆盖情况

下表仅列部分明确风格组合入口，不维护风格缺口结论；完整候选以当前 catalog 和下方脚本维护的组合目录为准。通用原子、场景参考标签以及单独配色不代表完整风格覆盖。先核对候选品类及组件／章节／整页范围，再按约 70% 的视觉适配原则比较组合；存在候选不等于必须采用，也不能因本表未列出而跳过组合比较、直接转入原子。

| 大类 | 当前组合或缺口 |
|---|---|
| 理性信息风 | [蓝白科研信息组合](combinations/recipes.md#combination.science-blue-white) |
| 杂志编辑风 | [牛皮纸时尚编辑战报](combinations/recipes.md#combination.kraft-editorial-report)、[古典插画人文长页](combinations/recipes.md#combination.antique-illustrated-story) |
| 自然质朴风 | [木质香氛编辑长页](combinations/recipes.md#combination.woody-scent-editorial) |
| 新中式风 | [古画游园长卷](combinations/recipes.md#combination.oriental-garden-scroll)、[朱砂墨底东方香叙](combinations/recipes.md#combination.oriental-vermilion-scent)、[东方家族影像册](combinations/recipes.md#combination.oriental-family-album) |
| 国潮装饰风 | [朱红民艺图文长页](combinations/recipes.md#combination.minnan-folk-editorial) |
| 诗性浪漫风 | [桂花柔光香叙](combinations/recipes.md#combination.osmanthus-poetic-light) |
| 感官生活风 | [暖烘焙食品长页](combinations/recipes.md#combination.warm-bakery-story-longpage)：食品长页候选，按整页关系评估 |
| 复古商业风 | [街景酒馆目录长页](combinations/recipes.md#combination.tavern-directory-longpage)：酒馆目录长页候选；[搁板摄影目录](combinations/recipes.md#combination.tavern-shelf-directory)、[出纸槽垂纸说明组](combinations/recipes.md#combination.tavern-paper-dispenser)：局部章节候选 |
| 手账拼贴风 | [撕纸票签人物战报](combinations/recipes.md#combination.torn-paper-report) |
| 波普撞色风 | [复古高饱和拼贴](combinations/recipes.md#combination.retro-pop-collage) |
| 趣味创意风 | [手绘涂鸦知识长页](combinations/recipes.md#combination.doodle-learning-guide)、[潮玩拟物产品长页](combinations/recipes.md#combination.playful-product-editorial) |
| 都市潮流风 | [黑粉巨字电影专题](combinations/recipes.md#combination.urban-pink-cinema)、[蓝银演出与磁带专题](combinations/recipes.md#combination.urban-blue-concert) |
| 未来科技风 | [银灰工业科技面板](combinations/recipes.md#combination.industrial-silver-panel) |
| 抽象光感风 | [冰蓝虹彩科技邀请函](combinations/recipes.md#combination.invitation-holographic-blue)：全息虹彩邀请函整页候选，不自动适用于其他品类或范围 |
| 奢雅精致风 | [象牙白人物雅致战报](combinations/recipes.md#combination.ivory-portrait-report) |
| 先锋实验风 | [回转蓝带与圆形人像简历](combinations/recipes.md#combination.resume-07)、[橙色颗粒与书写网格简历](combinations/recipes.md#combination.resume-13)：解构排版简历整页候选，按实际内容与范围评估 |
| 材质肌理风 | 按当前 catalog 检索同品类、同范围组合并核对正文；通用材质原子仅作局部补充，不单独证明整页风格覆盖 |

本批三组展示图保留 8 个组合、9 个画面分支：古典插画的赭黄／灰蓝共用结构，其余按实际视觉分别编排。不能用一个组合强行套整张展示板。

<!-- css-extraction-directory -->
## 脚本维护的组合目录

以下按实际 catalog 更新；标签表示归属，不表示所有分支完整覆盖。

| 组合 | 风格标签 |
|---|---|
| [清透光感面板](combinations/recipes.md#combination.clear-light) | 通用 |
| [暖纸编辑面板](combinations/recipes.md#combination.paper-editorial) | 通用 |
| [柔色纸本文件夹](combinations/recipes.md#combination.soft-paper-folder) | 通用 |
| [复古高饱和拼贴](combinations/recipes.md#combination.retro-pop-collage) | 二级：波普撞色风 / 波普拼贴 |
| [球面玻璃与立体字](combinations/recipes.md#combination.luminous-sphere) | 通用 |
| [蓝白科研信息组合](combinations/recipes.md#combination.science-blue-white) | 一级：理性信息风 |
| [植萃绿金感官组合](combinations/recipes.md#combination.botanical-green-gold) | 通用 |
| [黑粉巨字电影专题](combinations/recipes.md#combination.urban-pink-cinema) | 二级：都市潮流风 / 字体潮流 |
| [蓝银演出与磁带专题](combinations/recipes.md#combination.urban-blue-concert) | 二级：都市潮流风 / 音乐现场 |
| [银灰工业科技面板](combinations/recipes.md#combination.industrial-silver-panel) | 二级：未来科技风 / 工业科技 |
| [象牙白人物雅致战报](combinations/recipes.md#combination.ivory-portrait-report) | 二级：奢雅精致风 / 极简精品 |
| [牛皮纸时尚编辑战报](combinations/recipes.md#combination.kraft-editorial-report) | 二级：杂志编辑风 / 时尚杂志 |
| [撕纸票签人物战报](combinations/recipes.md#combination.torn-paper-report) | 二级：手账拼贴风 / 票据档案 |
| [古典插画人文长页](combinations/recipes.md#combination.antique-illustrated-story) | 二级：杂志编辑风 / 人文出版 |
| [朱红民艺图文长页](combinations/recipes.md#combination.minnan-folk-editorial) | 二级：国潮装饰风 / 传统纹样 |
| [古画游园长卷](combinations/recipes.md#combination.oriental-garden-scroll) | 一级：新中式风 |
| [朱砂墨底东方香叙](combinations/recipes.md#combination.oriental-vermilion-scent) | 二级：新中式风 / 当代东方 |
| [东方家族影像册](combinations/recipes.md#combination.oriental-family-album) | 二级：新中式风 / 当代东方 |
| [手绘涂鸦知识长页](combinations/recipes.md#combination.doodle-learning-guide) | 二级：趣味创意风 / 涂鸦手作 |
| [潮玩拟物产品长页](combinations/recipes.md#combination.playful-product-editorial) | 二级：趣味创意风 / 趣味拟物 |
| [桂花柔光香叙](combinations/recipes.md#combination.osmanthus-poetic-light) | 二级：诗性浪漫风 / 情绪影像 |
| [木质香氛编辑长页](combinations/recipes.md#combination.woody-scent-editorial) | 二级：自然质朴风 / 侘寂质朴 |
| [相机界面与蓝白说明长页](combinations/recipes.md#combination.camera-ui-explainer) | 二级：未来科技风 / 产品科技 |
| [海洋星球与地点卡活动](combinations/recipes.md#combination.ocean-orbit-campaign) | 二级：趣味创意风 / 趣味拟物 |
| [舞台剪贴与图解导览](combinations/recipes.md#combination.theatre-collage-guide) | 二级：趣味创意风 / 清新轻艺术 |
| [手作事务所与活页说明卡](combinations/recipes.md#combination.clay-craft-office) | 二级：趣味创意风 / 趣味拟物 |
| [育儿玩具与照片拼贴活动](combinations/recipes.md#combination.clay-parenting-collage) | 二级：趣味创意风 / 趣味拟物 |
| [拟物时装舞台与身份标签](combinations/recipes.md#combination.personified-fashion-stage) | 二级：趣味创意风 / 趣味拟物 |
| [波普活动排行与人像矩阵](combinations/recipes.md#combination.pop-campaign-ranking) | 二级：波普撞色风 / 波普拼贴 |
| [净白青蓝功效说明](combinations/recipes.md#combination.clinical-cyan-evidence) | 二级：理性信息风 / 数据图解 |
| [黑橙光场与产品功能矩阵](combinations/recipes.md#combination.black-orange-product-stage) | 二级：未来科技风 / 产品科技 |
| [布艺字组合 · 丹宁蓝 × 可可格纹](surfaces/craft-detail.md#combination.craft-denim-cocoa) | 通用 |
| [布艺字组合 · 奶油黄 × 玫瑰粉](surfaces/craft-detail.md#combination.craft-butter-rose) | 通用 |
| [布艺字组合 · 樱花粉 × 深巧克力](surfaces/craft-detail.md#combination.craft-pink-cocoa) | 通用 |
| [布艺字组合 · 象牙白 × 草莓红](surfaces/craft-detail.md#combination.craft-ivory-red) | 通用 |
| [牛皮纸手绘菜品拼贴菜单](combinations/recipes.md#combination.menu-kraft-doodle) | 一级：手账拼贴风 |
| [复古餐馆交错图注菜单](combinations/recipes.md#combination.menu-retro-diner) | 一级：杂志编辑风 |
| [橙色主推与套餐矩阵菜单](combinations/recipes.md#combination.menu-orange-combo) | 一级：国潮装饰风 |
| [柔色甜品异形卡片与双语价目菜单](combinations/recipes.md#combination.menu-pastel-dessert) | 一级：趣味创意风 |
| [暖木招牌与交错分类菜单](combinations/recipes.md#combination.menu-warm-korean) | 一级：自然质朴风 |
| [四区影像组合](combinations/recipes.md#combination.four-zone-imagery) | 二级：杂志编辑风 / 时尚杂志 |
| [错层切角组合](combinations/recipes.md#combination.offset-cut-window) | 二级：奢雅精致风 / 极简精品 |
| [竖题留白组合](combinations/recipes.md#combination.vertical-title-whitespace) | 二级：新中式风 / 当代东方 |
| [暗调编辑组合](combinations/recipes.md#combination.dark-editorial) | 二级：奢雅精致风 / 古典雅奢 |
| [跨列大字组合](combinations/recipes.md#combination.spanning-display-title) | 二级：理性信息风 / 企业宣讲 |
| [曲带图组组合](combinations/recipes.md#combination.ribbon-image-group) | 二级：理性信息风 / 企业宣讲 |
| [米色纤维纸三分类咖啡菜单](combinations/recipes.md#combination.menu-paper-hot-cold) | 一级：杂志编辑风 |
| [双页纸感咖啡茶饮价目单](combinations/recipes.md#combination.menu-minimal-coffee-spread) | 一级：杂志编辑风 |
| [春绿水彩信封邀请函](combinations/recipes.md#combination.invitation-spring-envelope) | 二级：诗性浪漫风 / 书信叙事 |
| [蓝纸双语公告](combinations/recipes.md#combination.notice-cobalt-paper) | 一级：手账拼贴风 |
| [校园装订通知](combinations/recipes.md#combination.notice-school-notebook) | 二级：趣味创意风 / 趣味拟物 |
| [荧光信纸公告](combinations/recipes.md#combination.notice-lime-letter) | 二级：都市潮流风 / 音乐现场 |
| [波普晋升喜报](combinations/recipes.md#combination.notice-pop-promotion) | 二级：波普撞色风 / 波普拼贴 |
| [薄荷编辑公告](combinations/recipes.md#combination.notice-mint-editorial) | 二级：杂志编辑风 / 时尚杂志 |
| [蓝白曲带展会邀请函](combinations/recipes.md#combination.invitation-expo-wave) | 二级：理性信息风 / 企业宣讲 |
| [红金多弧信笺邀请函](combinations/recipes.md#combination.invitation-ceremony-red) | 二级：国潮装饰风 / 传统纹样 |
| [冰蓝虹彩科技邀请函](combinations/recipes.md#combination.invitation-holographic-blue) | 二级：抽象光感风 / 全息虹彩 |
| [深蓝金光私享会邀请函](combinations/recipes.md#combination.invitation-nocturne-gold) | 二级：奢雅精致风 / 极简精品 |
| [蓝色悬挂票据公告](combinations/recipes.md#combination.notice-blue-ticket) | 一级：理性信息风 |
| [暑假装订纸通知](combinations/recipes.md#combination.notice-summer-notebook) | 二级：趣味创意风 / 趣味拟物 |
| [竹韵东方·开放留白长页](combinations/recipes.md#combination.bamboo-open-scroll) | 二级：新中式风 / 当代东方 |
| [木作人文·疏朗工艺长页](combinations/recipes.md#combination.woodcraft-airy-scroll) | 二级：杂志编辑风 / 人文出版 |
| [蓝白身份双栏简历](combinations/recipes.md#combination.resume-01) | 二级：理性信息风 / 极简理性；二级：杂志编辑风 / 人物专题 |
| [黑蓝人物侧栏与竖排导航简历](combinations/recipes.md#combination.resume-02) | 二级：杂志编辑风 / 人物专题 |
| [绿橙跨区人物编辑简历](combinations/recipes.md#combination.resume-03) | 二级：杂志编辑风 / 人物专题 |
| [红色巨字与书写穿插简历](combinations/recipes.md#combination.resume-04) | 二级：都市潮流风 / 字体潮流；二级：杂志编辑风 / 时尚杂志 |
| [极细字体与窄黑侧栏简历](combinations/recipes.md#combination.resume-05) | 二级：理性信息风 / 极简理性 |
| [黑色栏目带与灰色贯穿侧栏简历](combinations/recipes.md#combination.resume-06) | 二级：理性信息风 / 极简理性 |
| [回转蓝带与圆形人像简历](combinations/recipes.md#combination.resume-07) | 二级：先锋实验风 / 解构排版 |
| [群青贯穿网格与纸纹简历](combinations/recipes.md#combination.resume-08) | 二级：理性信息风 / 瑞士网格 |
| [云天纸张与实物夹具拼贴简历](combinations/recipes.md#combination.resume-09) | 二级：手账拼贴风 / 照片剪贴；二级：手账拼贴风 / 票据档案 |
| [蓝色拍立得与技能贴纸简历](combinations/recipes.md#combination.resume-10) | 二级：手账拼贴风 / 照片剪贴；二级：波普撞色风 / 波普拼贴 |
| [巨型窄体与红色技能区简历](combinations/recipes.md#combination.resume-11) | 二级：都市潮流风 / 字体潮流；二级：杂志编辑风 / 人物专题 |
| [蓝色编辑选框与时间轴简历](combinations/recipes.md#combination.resume-12) | 二级：理性信息风 / 瑞士网格 |
| [橙色颗粒与书写网格简历](combinations/recipes.md#combination.resume-13) | 二级：都市潮流风 / 字体潮流；二级：先锋实验风 / 解构排版 |
| [冷蓝终端章节组](combinations/recipes.md#combination.cold-blue-terminal-chapters) | 二级：未来科技风 / 赛博未来 |
| [搁板摄影目录](combinations/recipes.md#combination.tavern-shelf-directory) | 二级：复古商业风 / 怀旧商品目录 |
| [出纸槽垂纸说明组](combinations/recipes.md#combination.tavern-paper-dispenser) | 二级：复古商业风 / 怀旧商品目录 |
| [夹持剪报阅读组](combinations/recipes.md#combination.clipped-archive-reading) | 二级：手账拼贴风 / 票据档案 |
| [银底优惠票阵](combinations/recipes.md#combination.silver-coupon-grid) | 一级：未来科技风 |
| [警戒现场档案长卷](combinations/recipes.md#combination.warning-archive-longpage) | 二级：手账拼贴风 / 票据档案 |
| [连续银底星光促销长页](combinations/recipes.md#combination.silver-starlight-longpage) | 一级：未来科技风 |
| [街景酒馆目录长页](combinations/recipes.md#combination.tavern-directory-longpage) | 二级：复古商业风 / 怀旧商品目录 |
| [蓝银卷槽名单票券](combinations/recipes.md#combination.blue-silver-roster-ticket) | 二级：都市潮流风 / 音乐现场 |
| [蓝银抽奖设备组](combinations/recipes.md#combination.blue-silver-prize-console) | 二级：都市潮流风 / 音乐现场 |
| [蓝银演出活动长页](combinations/recipes.md#combination.blue-silver-concert-longpage) | 二级：都市潮流风 / 音乐现场 |
| [粉色派对说明窗口](combinations/recipes.md#combination.pink-party-window) | 一级：都市潮流风 |
| [粉色关卡标题与胶囊](combinations/recipes.md#combination.pink-party-level-heading) | 一级：都市潮流风 |
| [粉色连续步骤导轨](combinations/recipes.md#combination.pink-party-linked-stages) | 一级：都市潮流风 |
| [粉色派对关卡长页](combinations/recipes.md#combination.pink-party-longpage) | 一级：都市潮流风 |
| [雾绿性能跑鞋长页](combinations/recipes.md#combination.mist-green-performance-longpage) | 二级：未来科技风 / 产品科技 |
| [奶油复古穿搭长页](combinations/recipes.md#combination.cream-sport-editorial-longpage) | 二级：杂志编辑风 / 时尚杂志 |
| [暖烘焙食品长页](combinations/recipes.md#combination.warm-bakery-story-longpage) | 一级：感官生活风 |
| [蓝色散字侧轨与局部方格简历](combinations/recipes.md#combination.resume-letter-rail) | 二级：都市潮流风 / 字体潮流 |
| [圆肖像与胶囊履历编辑简历](combinations/recipes.md#combination.resume-circle-editorial) | 二级：杂志编辑风 / 人物专题 |
| [双色姓名粉带与情境照片简历](combinations/recipes.md#combination.resume-pink-name-collage) | 二级：波普撞色风 / 波普拼贴 |
| [清透饮品摄影叙事长页](combinations/recipes.md#combination.beverage-sensory-longpage) | 二级：自然质朴风 / 清雅自然 |
| [3D趣味粘土活动导览长页](combinations/recipes.md#combination.clay-citywalk-longpage) | 二级：趣味创意风 / 趣味拟物 |
<!-- /css-extraction-directory -->

运动商品长页：独立布局见 [性能递进](layouts/continuous-flow.md#layout.product-performance-longpage)、[摄影分章](layouts/continuous-flow.md#layout.editorial-lookbook-longpage)；组合见 [雾绿性能](combinations/recipes.md#combination.mist-green-performance-longpage)、[奶油复古穿搭](combinations/recipes.md#combination.cream-sport-editorial-longpage)。使用当前品类 ref-key 过滤，布局与皮肤分别选择。

简历局部组合：独立读取[散字侧轨](layouts/asymmetric-balance.md#layout.scattered-letter-rail)、[标签上置细轨](layouts/grid-and-alignment.md#layout.stacked-label-track)、[成组履历行](layouts/grid-and-alignment.md#layout.grouped-record-row)。三者可与已有网格、胶囊、拼贴原子组合；整页方案见上方新增三条简历。


### 渐进召回与字体绑定诊断

`search` 默认返回 5 条，中文复合词按库词表拆解；先给精确效果，再在不足时做受控相关词扩展，最后标记仅品类命中的弱结果。`ref_key`、kind、artifact 和 layout_scope 始终是硬过滤，不通过扩展绕开。阅读 `query_analysis`、`recall_stage`、`relevance`、`unmatched_terms` 判断不足；未知 Visual 编号不能当作组合 ID，弱命中不代表视觉已满足。需要材质、文字或色板时可分别用 `--kind surface/text/palette`。未覆盖的用户要求继续补查或自主实现，并记明原因。

组合字体统一由 `font-curated-pool.json` 的 `combinations` 按组合 ID 直接维护，不再使用 catalog 的 font_profile 与共享 profiles。新增组合必须补齐主题、四语言和四角色的明确映射，并经 `check-template-ref-bindings.py` 校验字体目录引用。`describe` 的 `font_status=blocked` 与 `font_errors` 只阻止字体采用，CSS 摘要仍可检查；未知组合、缺映射、无效角色或字体引用均明确报错，不自动补默认字体。推荐结果不证明字体已加载或字形覆盖；HTML 通过 Resolver 的 Web 字体通道及实际渲染继续验证。

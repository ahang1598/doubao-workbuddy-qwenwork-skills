# 电商详情页配色候选扩展设计

## 目标

在不改变详情页 `ai-coding` 路线、内容结构、构图策略、效果策略或现有 `EC01–EC08` 编号的前提下，利用已有 CSS 色板扩大电商详情页的冷色、深色、高对比、自然色和品牌色候选，并阻止暖浅中性色因品类或“高级、柔和、洁净”等描述自动成为大面积背景。

## 变更范围

生产规则只修改 `references/style/coding/systems/ecommerce-visual-system.md`。已有 CSS 色板实现、社媒 Visual、主 `SKILL.md`、KV 工作流和素材 Prompt 工作流保持不变。

设计说明文件保留本次边界和验收依据，不参与运行时路由。

## 规则设计

### 1. 暖浅中性色

电商 Visual 只保留一句约束：奶油白、米白等暖浅中性色，仅在用户、确认参考或品牌／商品本身有明确依据时才作为大面积底色，不因品类或“柔和、高级”等气质词自动选用。其余判断继续沿用现有取色优先级，不增加独立门禁或解锁流程。

### 2. EC 与 CSS 色板分层

`EC01–EC08` 继续表达配色职责，CSS `palette.*` 只提供已实现的具体候选。不能因为 CSS 库存在某个色板就反向改变品类、构图、素材或效果决策，也不能把色板名称当作采用理由。

每个 EC 只列少量代表性 CSS 候选，选定前按现有流程使用 `describe` 比较设计正文，冻结后再读取实现。一个 CSS 色板可以在不同 EC 中承担不同职责，但必须保持其实际文字、背景、强调色和明暗关系。

建议映射：

| EC | CSS 色板候选 | 边界 |
|---|---|---|
| EC01 临床白＋冷灰＋验证蓝 | `palette.clinical-cyan`、`palette.science-blue-orange` | 验证色只标证据，不覆盖肤色和商品色 |
| EC02 奶油中性＋材质本色 | `palette.cream-pink`、`palette.osmanthus-cream`、`palette.burgundy-cream` | 遵守上方暖浅中性色规则，避免全页同明度 |
| EC03 黑白＋单一行动色 | `palette.charcoal-rose`、`palette.industrial-silver-lime`、`palette.cobalt-acid` | 只保留一个主行动色；荧光色不承载细正文 |
| EC04 暖纸＋两色套印 | `palette.warm-paper`、`palette.pastry-gold`、`palette.antique-ochre`、`palette.oxide-blue-paper` | 暖纸底遵守上方规则；色版关系不能退化成统一暖滤镜 |
| EC05 自然低饱和 | `palette.bamboo-olive`、`palette.moss-letter`、`palette.botanical-green-gold`、`palette.oxide-blue-paper` | 自然色来自商品、材料、环境或主题，不用“天然”替代事实 |
| EC06 冷白银蓝＋性能色 | `palette.clinical-cyan`、`palette.science-blue-orange`、`palette.silver-cyan-mono`、`palette.aqua-lime` | 性能色只编码一个主要证据或状态 |
| EC07 深色奢华＋材质高光 | `palette.charcoal-rose`、`palette.industrial-silver-lime`、`palette.botanical-green-gold` 的深色分支 | 价值感由商品与材质建立，不自动使用黑金 |
| EC08 品牌撞色＋稳定事实底 | `palette.primary-pop`、`palette.sky-lime`、`palette.cobalt-acid`、`palette.coral-paper-ink`、`palette.neon-cyan` | 品牌色与商品色优先；高饱和色按角色限量使用 |

### 3. 社媒配色的迁移边界

只迁移可跨品类成立的颜色关系，不复制社媒任务的固定面积、平台氛围或具体 HEX：

- Social `C03` 的“黑白中性轴＋单一荧光”补强 EC03。
- Social `C05` 的“冷白银蓝＋单一证据色”补强 EC01／EC06。
- Social `C07` 的企业高对比关系补强 EC06／EC08。
- Social `C11` 的有限色版关系补强 EC04／EC08。
- Social `C12` 的颜料撞色和 `C14` 的商业波普关系补强 EC08。
- Social `C09` 只迁移“从真实摄影季节与光线取色”的原则，不复制固定季节色板。
- Social `C13` 只用于确需连续弥散色域的抽象光感任务，并先确定稳定文字区。

Social `C01`、`C02`、`C04`、`C06`、`C08`、`C10` 中包含暖纸、奶油或暖浅大底的分支，不因迁移成为电商默认值。

## 数据流

商品、品牌、参考和主题事实 → 选择 EC 配色职责 → 比较少量 CSS palette 候选 → 将可见颜色职责写入 Brief → KV 验证实际方向 → 冻结后读取所选 CSS 实现 → HTML 实际渲染验收。

## 验收

1. 无用户、品牌或参考暖浅依据的美妆／家居／母婴任务，EC02 及其暖浅 CSS 色板不得自动进入候选。
2. 用户或参考明确要求奶油色时，EC02 和对应 CSS 色板仍可正常使用。
3. 至少能为常见详情页比较一个冷白／理性、一个深色／高对比或品牌主导方向，不强制生成多个 KV。
4. CSS 引用均能通过 `check-references.py`，映射中的已知 palette ID 均能被 `describe` 读取。
5. 不修改路由、屏幕职责、构图、素材生产、字体、KV 数量或交付协议。

## 边缘情况

- 商品本身是米白包装，只保证商品身份色，不自动把整页背景扩展为奶油色；确需同类背景时须说明品牌或参考依据。
- 暖色食品、复古印刷与纸张题材可以使用暖纸或焦糖，但仍需由商品、参考或已选风格提供依据，不能仅凭“食品”解锁整页奶油底。
- 深色配色不等于高端；没有真实材质、商品轮廓和可读层级时不能用 EC07 掩盖构图问题。
- 同一 CSS palette 在不同章节切换明暗分支时，文字色、次级文字和标签色必须成对切换。

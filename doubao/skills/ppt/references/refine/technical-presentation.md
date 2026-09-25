# technical-presentation · Refine Handbook

技术工程场景的 refine 手册。当内容页需要 refine 时,**判断这页缺什么(缺内容 / 缺表达 / 缺视觉),补什么**。三种动作平权,不排序。

## 一、气质定位

**母题特征**:
- palette 冷科技:深靛蓝 / 松绿 / 蓝宝石 / 终端霓虹绿(深底)· 主色永远冷调
- 左侧刻度尺(12 格 · 04/08/12 数字 · mono)· 4 角 L 型工程角标(hairline)· 图纸网格底(20×20 极浅方格)
- 尺寸引线(accent 横线 + 三角箭头 + 数字标签)· 右侧 ADR 索引条(12 段 · primary_dark)· ADR 顶标 mono ADR-NNN
- 底部 dashboard 状态灯带(6 圆点 · 绿黄红三色)· `>` 光标 · `[NN]` 中括号编号(mono · 命令行/SRE 感)
- mono 引用块(灰底 · code 感)· 等宽字体是灵魂
- **图片策略**:技术要真不要氛围。架构图 / 时序图 / 流程图 SVG 手绘极高频 · 代码 block 极高频 · 生图 / image_edit 少用
- **语义色约定**:P0 红 = critical / P1 琥珀 = warn / P2 绿 = ok —— refine 时按此三色映射 alarms/thresholds/健康矩阵,和 style 里的故障复盘朱红 #C9302C 系一致

## 二、什么样的页需要 refine

**必 refine**:
- `refine_triggers.should_refine=true`(命中任一信号)

**主观 refine**(截图检查):
- 缺内容:整页一句话 + 几段简介 · 无技术细节
- 缺表达:3 段纯文字堆砌 / 架构描述没画图 / 步骤散在段落
- 缺视觉:一角挤另一角空 / 缺 hero 锚 / 无 mono 字号 / 装饰母题全缺
- 以上 3 点有任意可以进一步优化的地方

## 三、Refine 三类动作(平权 · 缺什么补什么)

三类动作**没有先后**,一页可能同时缺内容 + 缺视觉,那就 enrich + decorate 一起做;也可能只缺表达,那就只 reframe。

### 3.1 · Enrich · 补内容(缺 payload 时用)

**技术风重架构 / 重 benchmark / 重 ADR · 少氛围**。

**A · 用户已给附件/原稿**(`is_manuscript_apply=true`):
- Read 原稿相关章节 · 挖这页可加的**次要信息层**:
  - hero 之外的**分组件性能 / 分场景 SLA / 分版本兼容**数据
  - **技术选型对比 / 已有 ADR 归属**(相关 2-3 条)
  - **依赖清单 / SBOM / 版本号 / license**(具体到 patch 号)
  - **架构决策上下文**(context / decision / consequences 三段)
- 按重要性分层塞进页(hero 架构图 + 支撑数据 + ADR 归属 + 依赖脚注)

**B · 用户只给主题**(`is_manuscript_apply=false`):
- **搜索方向 · 优先真实来源**:
  - 官方文档(K8s / AWS / TensorFlow / React / Postgres)
  - Benchmark(MLPerf / ImageNet / GLUE / SPEC · effect size 带 CI)
  - Arxiv 顶会顶刊高被引
  - 架构最佳实践(AWS Well-Architected · 12-Factor · CNCF Landscape)
  - ADR 参考模板
- **搜索关键词模式**:
  - "\<技术\> official documentation / best practices"
  - "\<模型\> benchmark result 2024"
  - "\<架构\> case study" / "\<问题\> ADR template"
  - "\<组件\> SLA availability"
- **搜完必须标 Source**:官方文档挂 URL · benchmark 挂论文名 · ADR 挂编号 · 版本号必带

**图片策略**:
- **SVG 手绘架构图 / 时序图 / 流程图 极高频**:组件方块 + 连线 + 数据流箭头
- **原生 chart 中度**:benchmark 对比柱 / 性能曲线 / SLA 达成率
- **代码 block 极高频**:mono shape · 灰底 · mac 3 灯
- **IconPark 中度**:服务图标 · 状态图标 · SRE 语义色 · 克制
- **image_search 少用**:硬件实物 · 数据中心才用
- **生图 / image_edit 默认不用**:技术要真

**enrich 后的产物**:一份"内容清单"(hero 架构图 + benchmark + ADR 归属 + 依赖脚注)· 直接塞进本页

---

### 3.2 · Reframe · 换表达形式(有内容但表达弱时用)

把已有内容**换更强视觉表达**。技术风常用替换:

- **段落描述 → 架构图**(组件方块 + 连线 · 微服务 · 数据流方向箭头)
- **调用描述 → 时序图**(用户 → 前端 → 后端 → DB · 竖向 lifeline)
- **发布步骤 → CI/CD 管线**(6-8 步方块链)
- **技术规格 → 技术栈矩阵**(每格一个技术 + 具体版本号 · mono)
- **接口对比 → API diff**(左 v1 · 右 v2 · 高亮变更行 · 红/绿语义色)
- **设计决策 → ADR 条目**(context / decision / consequences · ADR-NNN)
- **性能对比 → benchmark 柱状**(自己 vs 竞品 · 带 CI · 单位标清)
- **服务状态 → 健康矩阵 4×3**([HEALTHY]/[WARN]/[CRITICAL])
- **告警时间线 → 时序告警带**(时间轴 + P0/P1/P2 语义色)
- **兼容说明 → 版本兼容矩阵**
- **依赖列表 → SBOM 清单**(mono · 组件+版本+license)
- **趋势数字 → Sparkline**(4 联 · 8 竖条 · 数字+变化率 %)
- **代码片段 → 代码 block**(mac 3 灯 · 灰底 · mono)
- **On-Call → 4-6 人卡阵**(头像+名字+值班时段)
- **SLO → 燃尽带**(进度条 · 剩余错误预算)

**reframe 时的技术风原则**:
- 架构图纵向分层 · 上层调下层 · 不允许箭头交叉
- 时序图 lifeline 顶部标参与者 · 竖虚线到底 · 消息带序号
- mono 只用于 code / ADR / 版本号 / 命令行 / 编号 chip · 正文别混
- 语义色三段固定不能反用:P0 红 · P1 琥珀 · P2 绿
- accent 色仅用于"关键组件 / hero 数字 / status pill"· 一页至多 2-3 处
- benchmark 数据必带单位(ms/QPS/GB)和 CI (± n)

---

### 3.3 · Decorate · 加视觉锚点(缺视觉时用)

**装饰母题库**:
1. 左侧刻度尺(12 格 · 04/08/12 数字 · mono)
2. 4 角 L 型工程角标(hairline)
3. 图纸网格底(20×20 极浅 hairline)
4. 尺寸引线(accent 横线 + 三角箭头 + 数字标签)
5. 右侧 ADR 索引条(12 段 · primary_dark · ADR 顶标 mono ADR-NNN)
6. 底部 dashboard 状态灯带(6 圆点 · 绿黄红)
7. 顶部 status 灯 8 方块 · 告警语义色带(P0 红 / P1 琥珀 / P2 绿)
8. `>` 光标 · `[NN]` 中括号编号 signature(mono · SRE 感)
9. mono 引用块(灰底 · 命令行 / 配置片段)
10. signature 竖装饰条(3×80 主色 · 卡内侧)
11. 编号方块(20-30px · 主色底白字 · ADR-001 / STEP-01)
12. hairline 分割线(1px · 极浅主色)· 双线边框主锚模块(2px · 强调 hero)

**视觉锚点升级库**(把已有元素做大做强):
- hero benchmark 数字 60pt+(主色重块底 · 带单位 · 如 "3x faster")
- 架构图中央组件 hero(白底 + primary 2px 边框 + 大字号 title)
- ADR-NNN 编号 mono chip(每 shape 挂归属 · 顶标位)
- 语义色 status pill([HEALTHY] 绿 · [WARN] 琥珀 · [CRITICAL] 红 · mono)
- 代码 block hero(mac 3 灯 · 灰底 · mono · 上下 hairline 夹)

**布局重构库**(修视觉塌陷 · 每次 refine 最多挑 1 个):
- 中央架构图 60% + 四周 4 段组件说明
- 左侧代码 block 60% + 右侧解释 40% · 中间 hairline
- 上 hero benchmark + 下 3 段对比(方法 A · B · C)
- 全页 dashboard(12 服务 · 4×3 · 每格 status pill)
- 全页 CI/CD 管线(水平横条 · 6-8 步 + 连线 + 状态灯)

---

## 四、使用规则

**判断这页缺什么的信号(每类独立触发 · 不排序)**:
- `total_text_chars < 60` 或整页几句话就完 → 3.1 enrich 补内容
- 文字够但堆砌成段落 / 架构描述没画图 → 3.2 reframe 换表达
- `visual_elements ≤ 12` 或装饰全缺 / 无 mono 字号 → 3.3 decorate 加视觉锚
- **一页可能同时缺 2 类 / 3 类**,那就多类一起做

**气质一致性**(每次 refine 后过):
- 技术感是否到位:mono · 语义色 · 状态灯 · 架构图 · 不用花体不用氛围图
- 数据是否精确:数据带 CI · 服务带 SLA · 版本带具体号 · 依赖带 license
- 结构化是否清晰:架构图有层次 · 数据流有方向 · 时序图有 lifeline
- 语义色是否用对:P0 红 · P1 琥珀 · P2 绿 · 不能反用
- ADR 是否挂归属:架构决策类 shape 必挂 ADR-NNN

**不要做的事**:
- 不要动 brand_assets(背景 / 页眉 / 页脚 / 装饰线 · 只加不删)
- 不要用氛围图代替架构图 · 不要用花体字(mono 是灵魂)
- 不要用 gradient(技术风扁平直角 · flat 派 · 阴影渐变禁)
- 不要滥用 IconPark(style 一致 · 混用 filled/outline 会乱)
- 不要编造数据:benchmark / 版本号必真实 · 带 Source 脚注
- 不要跳过 enrich 只做 decorate 凑数(架构不清时装饰只让页更乱)

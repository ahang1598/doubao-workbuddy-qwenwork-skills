<p align="center">
  <img src="assets/readme/hero.svg" width="100%" alt="Teachable figures：通过预测、操作与解释来学习的交互教学技能。">
</p>

# Teachable figures · 交互教学图解

[English](README.md) · [简体中文](README.zh-CN.md) · **[在线体验 →](https://ywedai.github.io/teachable-figures/)**

把课文中的一个结论变成学习者可以操作的实验：先预测，改变一个条件，观察结果，再解释一个新情境。

这是一个 **agent skill（智能体技能）**，包含渲染示例与验证工具。既能生成独立 HTML 图解，也能适配已有应用的课程结构。

## 快速安装

**Claude Code**（个人全局可用）：

```sh
git clone https://github.com/ywEdAi/teachable-figures.git ~/.claude/skills/teachable-figures
```

只想在某个项目里使用，就克隆到该项目的 `.claude/skills/teachable-figures`。重启 Claude Code 后，输入 `/teachable-figures` 调用，或直接描述教学需求让它自动匹配。

**Codex**：

```sh
git clone https://github.com/ywEdAi/teachable-figures.git ~/.codex/skills/teachable-figures
```

在提示词里用 `$teachable-figures` 调用。

**其他智能体或手动安装**：下载 [仓库 ZIP](https://github.com/ywEdAi/teachable-figures/archive/refs/heads/main.zip) 或 [最新 Release](https://github.com/ywEdAi/teachable-figures/releases/latest) 中的 `.skill` 文件（一个 ZIP 包），解压到该智能体的技能目录；没有技能目录的智能体，让它先读取 `SKILL.md`。

通过 Git 克隆安装的，在安装目录运行 `git pull` 更新。通过 ZIP 或 `.skill` 安装的，下载新版压缩包并替换已安装的技能文件夹；替换前先保留自己的本地修改。

## 两种使用方式

**引导模式（默认）**：如果项目里有学习者工作区（见下文），技能会先读它，已经写明的就不再问。然后问一轮问题，最多五个，每个都附推荐答案，可以直接回“好”：
- 使用对象（老师或家长讲解，还是自学者）以及学习者是谁；
- 要理解的结论与常见误解；
- 输出为独立 HTML 还是接入已有应用；
- 需要示意图、细节还是 3D；
- 计划使用的控件。

如果是自学者，还会加 2–4 个简短的诊断题，了解先修知识和可能的误解，并可以建议一个小的知识点计划。确认方案后才开始生成。

```text
/teachable-figures 我想给初中生讲：为什么加一个惰轮不会改变传动比的大小。
```

**直接模式**：说“直接生成”或“跳过提问”，或者在请求里已写清结论、学习者、输出形式与细节程度，技能就用默认值直接制作（除非工作区另有说明，默认按自学者设计），并在交付说明里列出所有假设，包括对先修知识的假设。

```text
/teachable-figures 直接生成。解释为什么加入惰轮不会改变最终传动比的大小。
误解：每多一个齿轮，输出就一定更慢。独立 HTML，包含预测、一圈输入计数、原生控件、重置与解释问题。
```

## 适合做什么，不适合做什么

| 适合 | 不适合 |
| --- | --- |
| 学习者可以**动手改变一个原因**、观察结果的机制，例如传动比、注意力遮罩、截面积 | 没有可预测内容的数据图表、仪表盘或报告配图 |
| 需要剖开、拆解或旋转才能看懂的结构，例如火箭剖面、胸腔器官、衣服的褶裥 | 幻灯片、海报、信息图或静态插画 |
| 一段课文中的某一个结论，每个机制做一个图解 | 一次生成整门课程；可以先挑出最值得做成图解的几个机制 |
| 明确标注假设的教学模型 | 临床解剖、工程仿真、CAD 或物理引擎级别的精度；把示意重建当作史实 |

生成的图解是教学设计，不代表已经验证了学习效果。

## 是学习，不是讲授

这个技能做的是**学习练习和图解**。讲授，也就是讲解或演示一套解释，仍然由老师、家长或课文承担。图解支持的是学习者自己做的事：预测、动手改变原因、注意结果、解释原因。

**使用对象不同，做法也不同。**

| | 老师或家长（讲解者） | 自学者 |
| --- | --- | --- |
| 谁来搭支架 | 你本人，现场：讲解、提问、指给学生看 | 图解本身 |
| 默认做法 | 大图、少文字、给全班的预测题、可开关的聚焦引导、讲解时逐步点亮的有序高亮 | 先修知识诊断、针对误解的反馈、撤掉支架后的独立练习、迁移题 |

只有你希望图解自己来讲解时，才需要加**讲解层**：一组有顺序的“先看这里 → 你会看到……；再看那里 → ……”，并联系学习者已有的知识。

**学习者工作区**：在项目的 `teachable-figures/` 文件夹里放三个 Markdown 文件。任何编程 agent 在每节课前都会先读它们，课后再更新：
- `LESSONS.md`：做过的所有课程。
- `LEARNER.md`：学习者或班级档案，包括先修知识和观察到的误解，每条都附证据。
- `LEARNING-PLAN.md`：知识点、先修关系和掌握状态。

可以从[模板](assets/templates/)开始，把[给 agent 的说明片段](assets/templates/agents-snippet.md)贴进 `AGENTS.md` 或 `CLAUDE.md`。[填好的示例](assets/templates/sample/)展示了一位自学者学完三节课后的样子。文件里不记录姓名，也不保存原始录音，你可以随时修改或删除任何内容。详见[学习者工作区](references/learner-workspace.md)。

**学习科学依据**：每份教学规格都要回答一张清单，涵盖：
- 图式：联系已有图式，并说明要改变什么；
- 支架与撤除；
- 认知负荷：先只改一个变量、分步呈现、预测阶段不露出答案；
- 注意与提示：每一步的聚焦引导和有序高亮；
- 双重编码：文字术语、图例与图中部件在悬停或聚焦时互相联动；
- 针对误解的反馈。

原则与文献出处（Sweller、Mayer、Paivio、Wood、Bruner 与 Ross、Kalyuga、Chi 等）见[学习设计](references/learning-design.md)。它们是设计原则，不能保证一定学会。

## 在线体验十五个完整示例

![六个示例的实际截图：圆锥截面、胸腔示意、火箭发射、Transformer 数据流、明代曳撒与齿轮传动](assets/readme/examples.png)

**[打开示例目录 →](https://ywedai.github.io/teachable-figures/)** 无需安装。每页都有预测、操作、读数、重置、解释与迁移问题；下载 [examples 目录](examples/) 后，也可以直接打开 HTML 离线运行。每页都可在中英文之间切换，图在左、步骤在右。

第一次用？先看 **[工作原理](https://ywedai.github.io/teachable-figures/how-it-works.html)**：用这个 skill 讲它自己。交给它几个请求，看哪些会被拒绝；再拿掉一步，看哪些失败在截图里根本看不出来。

| 在线示例 | 可以探索什么 |
| --- | --- |
| [圆锥截面 · 3D](https://ywedai.github.io/teachable-figures/geometry-slices.html) | 旋转立体、调整截面高度，比较半径的线性变化与面积的平方变化。 |
| [人体胸腔 · 3D](https://ywedai.github.io/teachable-figures/human-anatomy.html) | 旋转图谱来源的人体网格、打开胸腔观察窗，检查肺、心脏、气道与单独标注的示意膈肌。 |
| [火箭发射模拟](https://ywedai.github.io/teachable-figures/rocket-launch.html) | 检查有实体结构的火箭剖面与组件拆解，再比较推力、起飞、燃尽与滑行。 |
| [Transformer 数据流](https://ywedai.github.io/teachable-figures/transformer-flow.html) | 逐步查看示例向量、Q/K/V、因果遮罩、注意力、残差归一化与 FFN。 |
| [明代曳撒结构](https://ywedai.github.io/teachable-figures/chinese-clothing.html) | 依据一件博物馆藏品，检查交叠衣襟、有明暗面的褶层与折返剖面。 |
| [齿轮传动比](https://ywedai.github.io/teachable-figures/gear-ratio.html) | 加入惰轮，区分输出转数的大小与旋转方向。 |
| [忒修斯之船 · 哲学](https://ywedai.github.io/teachable-figures/ship-of-theseus.html) | 逐块换板、用旧板重拼一艘船，看物质、连续性、形式、名义四条标准如何给出不同答案；再看复制的复制如何丢失设计信息。 |
| [信息熵 · 信息论](https://ywedai.github.io/teachable-figures/information-entropy.html) | 搭建是/否提问树，比较平均提问数与熵；把几次报告打包一起问，平均可降到一个问题以下。 |
| [贝叶斯与基础比率 · 概率](https://ywedai.github.io/teachable-figures/bayes-base-rate.html) | 在 1000 人点阵里只看阳性者，数出其中真正患病的比例；再测一次，看先验如何更新。 |
| [四季成因 · 地球科学](https://ywedai.github.io/teachable-figures/seasons.html) | 拖动日期和纬度，比较正午太阳高度、日照时长与每日日照量；转动三维轨道，看地轴方向始终不变；把地轴倾角调成 0，季节就消失。 |
| [月相 · 天文，三维](https://ywedai.github.io/teachable-figures/moon-phases.html) | 转动三维日地月模型，对照地球上看到的月亮：月亮永远半边亮，月相取决于角度；5° 的轨道倾角解释了月食为什么不是每月都有。 |
| [四冲程发动机 · 机械，三维](https://ywedai.github.io/teachable-figures/four-stroke-engine.html) | 转动三维剖面的曲轴：气门、火花塞和正时皮带说明为什么曲轴转两圈才点一次火，凸轮轴只转半速。 |
| [动态平衡 · 化学](https://ywedai.github.io/teachable-figures/dynamic-equilibrium.html) | 看正逆反应速率趋于相等却都不为零；用同位素标记证明平衡时反应仍在进行，再从速率推出勒夏特列原理。 |
| [自然选择 · 生物](https://ywedai.github.io/teachable-figures/natural-selection.html) | 扮演捕食的鸟，看桦尺蛾黑色型频率跨代变化；没有变异，选择就无从发生。 |
| [价格上限 · 经济](https://ywedai.github.io/teachable-figures/price-ceiling.html) | 拖动房租上限，看短缺与无谓损失；比较价高者得、抽签、排队三种分配的额外损失。 |

圆锥与胸腔使用空间坐标、旋转、投影和深度排序。胸腔采用 Human Reference Atlas 网格，另有明确标注的示意膈肌与检查用观察窗；火箭是一维理想模型；Transformer 使用公开说明的简化参数；服饰图把史料事实与示意重建分开标注。忒修斯之船不判定哪个答案正确，只展示各条标准的论证结构；信息熵页的数值都按精确公式计算。所有示例都有中英文切换。

<details>
<summary>查看最初的齿轮教学实验</summary>

加入一个惰轮，输出就会变慢吗？在 12 齿主动轮与 24 齿输出轮的例子中，输入一圈，输出仍为半圈；惰轮改变旋转方向，不改变传动比的大小。

![两次齿轮实验的截图：输出都是半圈，惰轮改变方向；原生控件和计数器展示结果](assets/readme/gear-ratio.png)

这是理想模型的示意图，不模拟真实齿面接触。

</details>

## 先明确机制，再选择画法

教学规格先写清结论、误解、可改变的原因、可观察的结果与计算依据。一份模型共同驱动画面、读数、无障碍摘要和解释。

| 模式 | 适合表达 |
| --- | --- |
| 2D SVG | 分布、曲线、状态变化与短流程。 |
| 轻量等轴 SVG | 可以操作的按键、开关、抽屉与屏幕。 |
| 机械 SVG | 支架、关节、管线、剖面与拆解结构。 |
| 可旋转 3D | 需要通过旋转和遮挡变化理解的空间关系。 |
| 可选 WebGL | 确实需要它的波、热、光等场景。 |

先确定主体形态和用户要求的细节，再选能完成交互的渲染器。[渲染选择指南](references/rendering-selection.md) 将功能设备交给 iso-figure，将刚性机械结构交给 Anatomy，将有机形态和布料交给合适的参考网格或插图。画法仍服务于教学机制，例如解释传动比并不需要强制使用 3D。

## 评审与验证

[渲染融合评审](reviews/rendering-fusion-audit.md) 记录了最初示例的视觉缺陷，以及 v0.3.0 如何分别验收主体形态与教学交互。[v0.2.0 迭代报告](reviews/v0.2.0.md) 保留此前的几何修复、五个新增示例与检查结果。此前的 [UI/UX 评审](reviews/uiux.md) 和 [教学设计评审](reviews/pedagogy.md) 也保留供追溯。

轻量示例已修复输入框被快捷键拦截的问题，并加入原生控件与实时读数。合成器还增加了重置、静音、输入归属管理，以及闲置、页面隐藏、离屏或减少动态效果时停止的示波器。

turning-dial 的四项 3D 拥挤问题通过调整真实端子、连接点与插座盖几何修复。完整配置的 3D 审计中，各失败类别均为零；渲染引擎、审计阈值与排除规则保持不变。见 [完整原始输出](reviews/turning-dial-full-audit-v0.2.0.txt)。

```sh
npm ci
npm test
npm run test:browser
```

v0.3.0 的 4 项模型/规格检查与 21 项浏览器用例均通过；两个新几何准备脚本也已重建验证。此前 12 项上游明暗主题构建结果保留在 v0.2.0 报告中。浏览器检查使用已安装的 Google Chrome；如已安装 Playwright Chromium，可设置 `BROWSER_CHANNEL=chromium`。构建在临时副本中运行，不修改内置源文件。

较慢的完整 turning-dial 几何审计：

```sh
npm run audit:3d
```

检查范围包括模型、明暗主题构建、键盘输入隔离、原生控件、重置、移动端布局、减少动态效果及新增课程的交互。具体范围与缺口见 [当前评审](reviews/v0.2.0.md)。

## 来源、融合方式与许可证

这个技能以原有 **teachable-figures** 为教学基础，融合了两个上游渲染技能。原有部分提供结论与误解分析、预测 → 操作 → 解释流程、可复用配置、语言框架和 AI English Shift 宿主适配。

| 上游技能 | 融合的内容 | 固定版本 | 许可证 |
| --- | --- | --- | --- |
| [Anatomy · wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) | 机械实体、关节与管线、剖面与爆炸图、相机控制、3D/WebGL 技术及几何验证工具。内置于 `assets/anatomy/`。 | [`454a0ef`](https://github.com/wheresryan22/anatomy/tree/454a0ef801b6d9b905f08309d094491c7085b3dd) | [MIT · Ryan](assets/anatomy/LICENSE) |
| [iso-figure · MrBongoC/ai-iso-skill](https://github.com/MrBongoC/ai-iso-skill) | 等轴 SVG 投影、可用的按键/开关/显示屏、共享状态与渲染流程、便携 HTML 示例。内置于 `assets/iso-figure/`，工作流适配见 `references/simple-iso.md`。 | [`44b4da7`](https://github.com/MrBongoC/ai-iso-skill/tree/44b4da7714148eef547cc1b102e433472dfe3531) | [MIT · Tolga Cohce](assets/iso-figure/LICENSE) |

上游实际名称是 **Anatomy**；这里指解释性物体的渲染工具包，不是医学解剖图谱。本项目根据教学需要调整了上游约定：不强制零件数量，预测前不自动巡游，允许清晰的标签，提供原生控件与减少动态效果支持，并让画面与解释共用同一份模型。仓库还包含本地几何修复、无障碍改进、十五个完整课程示例和评审工具。

[来源与融合决策](references/sources-and-fusion.md) 说明各部分的贡献边界；[来源清单](references/source-manifest.json) 记录完整提交号与本地改动。每个课程页面另列其科学或历史依据。

README 的设计工作流使用了 [oil-oil/beautify-github-readme](https://github.com/oil-oil/beautify-github-readme)。它用于文档呈现，与上述内置渲染技能分别列示。

人体胸腔还使用了 **[Human Reference Atlas / HuBMAP 参考网格](https://humanatlas.io/3d-reference-library)**，许可证为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。它是领域数据来源，与渲染技能分别列示。[数据来源记录](assets/hra/provenance.json) 包含固定版本、原文件哈希、裁切、压缩与改色说明；另附 [重建方法](assets/hra/README.md)。

两个上游的完整 MIT 声明保留在 [Anatomy LICENSE](assets/anatomy/LICENSE) 和 [iso-figure LICENSE](assets/iso-figure/LICENSE)。这些许可适用于对应的上游贡献。

**本仓库自己的内容**采用双许可：原创代码（脚本、测试，以及各课程页面的 HTML/CSS/JavaScript）使用 [MIT 许可证](LICENSE)；原创课程内容（文字、插图、图示、预览图，以及 `SKILL.md` 和 `references/` 中的写作指导）使用 [CC BY 4.0](LICENSE-CONTENT)。两者都可以复用和改编，包括商业用途：代码请保留 MIT 声明，内容请注明“Teachable Figures by ywEdAi”。随附的第三方材料仍按上文所列各自的许可证。

## 已知局限

- 上游 Anatomy 示例主要展示渲染技术。接入课程前，需要关闭启动及闲置后恢复的自动巡游；十五个完整课程不自动播放。
- AI English Shift 适配面向特定宿主，使用前应核对宿主当前代码、注册结构与语言要求。
- 模型和浏览器检查通过，不等同于已证明学习效果。本次评审没有开展新手学习者实验或屏幕阅读器实测。
- 完整机械审计覆盖配置的 turning-dial 场景。圆锥和胸腔使用独立检查与选定视角检查，没有进行穷尽的网格相交证明。

## 示例部署

[GitHub Pages](https://ywedai.github.io/teachable-figures/) 发布 `gh-pages` 分支。从干净的 `main` 工作区更新在线示例：

```sh
git subtree push --prefix examples origin gh-pages
```

该命令把当前 `examples/` 目录发布到 `gh-pages`，分支更新后 Pages 会重新部署。示例没有运行时包依赖；`.nojekyll` 让 HTML 按原样发布。

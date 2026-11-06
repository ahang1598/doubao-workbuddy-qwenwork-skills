---
name: xiaoyi-vlog-gen-win
description: 一键成片、vlog制作，支持批量导入多张图片，智能画面编排、自动匹配氛围感BGM、添加流畅转场与创意特效，一键渲染生成精美vlog短片。触发词：一键成片、vlog、照片剪辑、多图成片、图库生成视频。
---

> **桌面接入说明（小艺 Work Desktop）**
> 
> 本技能**自身不发起任何业务 API 网络调用**：技能的 4 个脚本（`check-init.sh` / `detect-resolution.sh` / `prepare-project.sh` / `render-video.sh`）均为纯本地编排与 Remotion 渲染工具，不访问 `np://claw-skill` 管道，也不需要 `CLAW_SKILL_TOKEN`。
> 
> 涉及业务能力的部分**全部委托给兄弟技能**（由模型/Agent 在流程中分别调用，各自已完成桌面管道转换，与本技能解耦）：
> 
> - 图像理解 → `图像理解` 相关技能（必需）
> - 封面/片尾生图 → `seedream-image_gen`（可选）
> - BGM 生成 → `minimax-music-gen-win`（可选）
> - 技能安装 → `find-skills`
> 
> Remotion/React 依赖由小艺 Work 根据 Skill 根目录的 `package-lock.json` 在登录后后台安装，调用过程中不执行 `npm install`。浏览器优先复用系统 Chrome/Chromium；缺失时按 setup.md 提示用户配置，不在任务中静默下载大型浏览器。

# 小艺一键成片

传入一组图片，按序执行 **初始化与能力预检 → 图像理解 → 创作简报确认 → 资产并行生成 → 智能编排 → 项目准备 → 渲染输出 → 发送给用户**。每个步骤都必须按序评估并汇报进度；用户提供、复用或明确选择降级的资产可跳过对应生成任务。

`$XIAOYI_VLOG_DIR` 表示本 Skill 根目录（即本 `SKILL.md` 所在目录，由运行环境注入）。

---

## 一键成片完整流程

### 第0步：初始化与能力预检

#### 0.1 初始化状态

每次生成视频前，先检查初始化状态：

```bash
bash "$XIAOYI_VLOG_DIR/scripts/check-init.sh"
```

- 退出码 0 → 已初始化，继续下一步
- 退出码 1 → 执行 [docs/setup.md](docs/setup.md) 重新初始化

#### 0.2 前置技能检查

在图像分析、创作简报和任何扣点提示前，检查以下技能：

| 能力        | 依赖工具/技能              | 缺失时处理                                       |
| --------- | -------------------- | ------------------------------------------- |
| 图片理解（必需）  | `图像理解`相关工具或技能        | 提示用户使用 `find-skills` 安装；未安装则终止              |
| 图片生成（可降级） | `seedream-image_gen` | 让用户选择使用 `find-skills` 安装，或使用纯文字封面/片尾        |
| 音乐生成（可降级） | `minimax-music-gen-win` | 让用户选择使用 `find-skills` 安装，或使用用户提供/复用音乐/无 BGM |

一次列出所有本次任务需要但未安装的技能及可选方案，然后停止等待用户选择。

1. 图片理解没有降级路径；用户拒绝安装或安装失败时终止。
2. 图片和音乐生成只能在用户明确选择后降级，不得自动降级。
3. 用户选择安装后，调用 **find-skills** 完成安装，再重新执行本检查。
4. 用户已明确不要音乐或已经提供/复用音乐时，音乐生成技能记为本次“不需要”，无需强制安装。
5. 第0步发现技能未安装不属于生成失败，不得直接进入第3步的运行时失败分支。

### 第1步：图像理解

使用第0步已确认安装的 **图像理解** 技能分析理解图片内容。

**要点：**

- ⚡ **多张图片可并行理解，显著缩短分析耗时**
- 对每张图片都要调用，收集完整的视觉信息
- prompt 应引导模型输出适合视频脚本创作的描述：场景、人物、物体、情绪、色彩、构图、光线
- 特别关注图片间的**关联性**（同一场景？时间顺序？主题递进？），为后续编排提供依据
- 将所有图片的理解结果汇总，作为脚本创作的素材

### 第2步：创作简报与统一确认

根据第1步的图像理解结果拟定完整创作方案，但本步**禁止调用图片或音乐生成接口**。全新项目无论用户是否已提供明确主题，都必须展示一次最终创作简报并等待确认，避免未经确认的标题、主题或视觉方向被直接写入封面图。

纯重排或重渲染可复用此前已确认的简报和资产，无需再次确认；只要修改 `title`/`subtitle`/`endText`、视觉方向、封面/片尾概念或重新生成 BGM，就必须重新进入本步。

#### 2.1 顶层信息

先确定不依赖场景排序的 `title`/`subtitle`/`endText`、`theme`、`resolution`。其中 `resolution` 需提前检测（生图画幅约束依赖它）：

```bash
RESOLUTION=$(bash "$XIAOYI_VLOG_DIR/scripts/detect-resolution.sh" <用户图片目录>)
```

输出 `landscape`/`portrait`，在第4步写入 `script.json`。

标题要求：`title` ≤8 字、`endText` ≤6 字，避免生僻字、异体字和特殊符号；`subtitle` 应补充主题而非重复标题。

**主题配色（根据内容自选或自定义，下表仅供参考）：**

| 预设名    | bgColor   | textColor | accentColor | 适用风格       |
| ------ | --------- | --------- | ----------- | ---------- |
| 暗金（默认） | `#1a1a2e` | `#e8d5b7` | `#a89070`   | 复古、经典、婚礼   |
| 纯白     | `#ffffff` | `#1a1a2e` | `#666666`   | 简约、商务、产品   |
| 暖橙     | `#2d1b0e` | `#ff9f43` | `#c4762c`   | 旅行、美食、生活   |
| 冷蓝     | `#0a1628` | `#74b9ff` | `#4a8bc2`   | 科技、城市、夜景   |
| 莫兰迪    | `#3c3c3c` | `#d4c5b9` | `#9e8e7e`   | 文艺、胶片、安静   |
| 森绿     | `#0d2818` | `#a8e6cf` | `#6bae8f`   | 自然、风景、户外   |
| 粉红     | `#2d0a1e` | `#ffb6c1` | `#c97b8b`   | 浪漫、可爱、少女   |
| 赛博     | `#0a0a0a` | `#00ff88` | `#00cc6a`   | 赛博朋克、电子、潮流 |

#### 2.2 封面与片尾方案

根据第0步确定的首尾方式处理：

- `coverMode=generated`：使用 **seedream-image_gen** 生成封面图（首帧）和片尾图（末帧），文字直接生成在图中，Remotion 端不再叠加。本步只准备方案和 prompt；第2步取得确认并进入第3步后才实际生图。
- `coverMode=text`：不准备生图 prompt 和参考图，不展示无法执行的生图概念；后续省略 `titleImage` 和 `endImage`，使用 Remotion 纯文字卡片。

以下共享视觉锚点、prompt、正反例和参考图规则仅适用于 `coverMode=generated`。

**共享视觉锚点（封面/片尾强制逐字复用）：**

封面与片尾必须**共享同一套色调、光影质感、美学风格**，只在场景构图上区分。先撰写一个共享视觉锚点，两个 prompt 都**逐字嵌入**，不得改写：

| 栏目   | 要求                                             | 示例                                   |
| ---- | ---------------------------------------------- | ------------------------------------ |
| 色调   | 具体色相+明度+饱和度，不用"暖色/冷色"                          | 暖金 #D4A24A 主调，暗部偏青 #2A3B4A，高光泛橙，中高饱和 |
| 光影质感 | 光源方向+硬度+颗粒/干净度+对比度                             | 侧逆光，硬光比，胶片颗粒，对比度偏高，高光溢出              |
| 美学风格 | 精准风格词（电影感/胶片/editorial/莫兰迪/青橙调/暗金/日系/赛博/极简/油画） | 35mm 胶片质感，电影感青橙对比，editorial 构图       |

#### Prompt 骨架（锚点 + 场景 两段式）

```
[画幅] 居中构图留安全边距，只参考传入图的色调氛围不复制人物面部/服装/具体场景，[场景描述] + [共享视觉锚点逐字复用]，画面中央渲染[标题/片尾]"<文字>"，标题清晰醒目但不过大、颜色与画面色调协调
```

- 画幅：`landscape`→16:9，`portrait`→9:16
- **场景描述**：封面偏开场感（延伸的公路/远眺），片尾偏结束感（渐远的脚印/回望的背影），首尾不重复；不复制人脸/服装/可识别地标
- **文字防错别字**：双引号包裹；标题 ≤8 字、片尾 ≤6 字（长文字错字率显著上升，必要时拆主副行）；避生僻字/异体字/特殊符号；含引号或特殊符号时用 Here String 存 prompt 再传参

**正例（封面 / 片尾，同锚点不同场景）**：

```
封面：16:9 横构图，居中构图留安全边距，只参考传入图的色调氛围不复制具体场景，黄昏空无一人的海岸公路向远方延伸，暖金 #D4A24A 主调，暗部偏青 #2A3B4A，高光泛橙，中高饱和，侧逆光，硬光比，胶片颗粒，对比度偏高，高光溢出，35mm 胶片质感，电影感青橙对比，editorial 构图，画面中央渲染标题"夏日旅行"，标题清晰醒目但不过大、颜色与画面色调协调
片尾：16:9 横构图，居中构图留安全边距，只参考传入图的色调氛围不复制具体场景，清晨空旷沙滩上一串渐远的脚印通向海平线，暖金 #D4A24A 主调，暗部偏青 #2A3B4A，高光泛橙，中高饱和，侧逆光，硬光比，胶片颗粒，对比度偏高，高光溢出，35mm 胶片质感，电影感青橙对比，editorial 构图，画面中央渲染片尾"旅途终章"，标题清晰醒目但不过大、颜色与画面色调协调
```

→ 只有"场景描述"和"文字"不同，色调/光影/美学逐字一致。

**反例**：

- ❌ 首尾割裂：封面"暖金胶片" vs 片尾"冷蓝干净"——色调/光影不一致
- ❌ 锚点模糊："暖色调，电影感"——无具体色相和质感，模型发挥方向不可控

#### 参考图与生成准备

**参考图**：从用户图选 1-3 张代表主题/色调/情绪的图（避免纯特写、纯文字截图），封面/片尾用**同一组**作调性锚。

本步只记录参考图、封面 prompt 和片尾 prompt，不执行命令。实际调用见第3步。

#### 2.3 BGM 方案

根据同一创作主题拟定 BGM 来源、类型和 prompt。Vlog 背景音乐默认使用**纯音乐（无人声）**，除非用户明确要求歌曲或人声。

**BGM 来源：**

- 用户提供 → 记录文件路径，设置 `bgmMode=provided`
- 重排/重渲染 → 复用已有 BGM，设置 `bgmMode=reused`
- 全新视频且音乐技能可用 → 拟定新 BGM prompt，设置 `bgmMode=generated`，确认后生成（约5分钟，exec timeout 设 600 秒）
- 用户不要音乐或主动选择降级 → 设置 `bgmMode=none`

只有 `bgmMode=generated` 且 **minimax-music-gen-win** 已安装时，确认卡才展示类型、语言、完整 prompt，以及“将扣除 20 AI 点”。`provided`、`reused`、`none` 均不显示 20 点付费提醒。

**BGM 风格参考：**

| 视频风格    | BGM 描述示例          |
| ------- | ----------------- |
| 旅行 vlog | 轻快吉他、民谣风、公路旅行感    |
| 浪漫/婚礼   | 钢琴、弦乐、温柔抒情        |
| 复古/胶片   | Lo-fi、爵士、怀旧黑胶感    |
| 都市/街拍   | 电子节拍、Hip-hop、都市氛围 |
| 自然/风景   | 环境音乐、空灵钢琴、自然音效    |
| 美食/生活   | 轻快爵士、法式手风琴、温馨感    |
| 运动/冒险   | 摇滚、电子、节奏感强        |

#### 2.4 统一确认闸门

确认前只拟定一句高层图片叙事摘要（例如“按清晨出发、白天游览、黄昏收束的时间线推进”），不得提前生成或展示逐图顺序、文件名、时长、动画、转场、特效或 `scenes[]`。详细图片编排属于第4步，只有确认后才能生成。

确认卡必须按以下层级独占一条消息，所有适用字段不得遗漏。不要展示冗长的封面/片尾完整 prompt，只展示用户能判断方向是否合适的摘要；BGM prompt 因付费确认要求必须完整展示。新生成 BGM 时，付费提醒必须同时出现在卡片开头和末尾授权摘要中：

```markdown
> **付费提醒：本方案包含一次 BGM 生成，将扣除 20 AI 点。**
> <仅新生成 BGM 时显示；用户提供、复用已有或无 BGM 时省略>

## 创作简报（待确认）

**核心文案**
- 标题：<title>
- 副标题：<subtitle>
- 片尾：<endText>

**整体方向**
- 主题：<一句话主题总结>
- 画幅：<16:9 横屏 / 9:16 竖屏>
- 视觉：<一句话概括色调、光影质感和美学风格>
- 图片叙事：<一句话高层摘要，禁止逐图展开>

**封面与片尾**
- 方式：<AI 图片生成 / 纯文字卡片>
- 封面：<生图时展示一句场景构想；纯文字时写“不生成封面图”>
- 片尾：<生图时展示一句场景构想；纯文字时写“不生成片尾图”>
- 生图配置：<仅当用户指定参数与推荐不一致时展示推荐配置及影响；纯文字时省略>

**BGM 方案与专项点数**
- 来源：<新生成 / 用户提供 / 复用已有 / 无 BGM>
- 类型：<新生成时写“纯音乐（无人声）/人声音乐”；其他来源写“不适用”>
- 语言：<新生成时填写 BGM prompt 使用的中文/英文，纯音乐也必须填写；其他来源写“不适用”>
- Prompt：<新生成时展示完整 prompt；其他来源展示“不生成”>
- **BGM 专项点数：<新生成时写“将扣除 20 AI 点”；其他来源写“不产生 BGM 生成的 20 AI 点”>**

## 最终授权摘要
- 标题：**「<title>」**
- 片尾：**「<endText>」**
- 首尾方式：**<生成封面和片尾图片 / 使用纯文字卡片>**
- BGM 授权：**<新生成时写“生成一次 BGM，并扣除 20 AI 点”；其他来源写实际来源及“不产生 BGM 生成的 20 AI 点”>**

回复「确认」后，我会按上述文案和授权准备所需资产，并继续完成视频。
如需调整，请直接说明要修改的字段。
```

**确认状态规则：**

1. 只有用户明确同意且回复中包含独立的“确认”二字，才可进入第3步；否定、疑问、修改请求或“可以”“继续”“没问题”等模糊表达均不构成确认。
2. 用户修改任何方案后，更新相关字段并重新展示完整确认卡；修改阶段不算重复确认，最终只经过一次有效确认。
3. 对于新生成 BGM，本统一确认即满足 **minimax-music-gen-win** 的生成确认要求；确认卡已完整展示类型、语言、prompt 和 20 点消耗时，第3步不得再次询问。
4. 一次确认只授权简报中的一次 BGM 生成，不授权自动重试或生成多个版本。
5. 若用户指定的生图模型或参数与 **seedream-image_gen** 的推荐不一致，把推荐配置及影响合并进本确认卡，不得增加第二个确认回合。
6. 确认卡必须独占一条消息；发出后立即停止执行并等待用户回复，不得追加图片编排、逐图分析、进度、解释或建议，确认前禁止资产生成和详细智能编排。
7. 标题、片尾、首尾方式和 BGM 授权必须在“最终授权摘要”中再次出现，不能被视觉方案或图片叙事信息替代。
8. 用户提供、复用或不要 BGM 时，不显示 20 点付费提醒，并在费用与最终授权中明确“不产生 BGM 生成的 20 AI 点”。

### 第3步：资产并行生成

收到第2步的有效确认后，不再重复检查技能，直接按已确认的资产模式并行启动适用任务，以最长任务耗时为总等待时间：

- `coverMode=generated` → 并行启动封面图和片尾图生成；`coverMode=text` → 不启动图片生成。
- `bgmMode=generated` → 启动 BGM 生成；`provided`、`reused`、`none` → 不启动音乐生成。

#### 3.1 封面/片尾图生成

`coverMode=text` 时跳过本节。`coverMode=generated` 时，使用第2步已确认的同一组参考图和 prompt，并行调用 **seedream-image_gen**：

```bash
python3 ~/.openclaw/workspace/skills/seedream-image_gen/scripts/generate_seedream.py \
  --model Pro --size 1K \
  --image <代表图1.jpg> [--image <代表图2.jpg>] \
  --prompt '<prompt 见上>'
```

**生成后**：捕获路径（`💾 Images Saved to: ...`）→ 重命名拷贝为 `cover.jpg`/`end.jpg` 备用。实际调用后出现超时、API 报错、退出码非 0 或无有效输出时属于运行时失败；只省略失败任务对应的 `titleImage` 或 `endImage` 字段，第6步对该卡片自动回退纯文字，不影响另一张已成功图片。

#### 3.2 BGM 生成

`bgmMode=provided`、`reused` 或 `none` 时跳过本节。`bgmMode=generated` 时，使用 **minimax-music-gen-win** 严格按第2步确认卡中的类型、语言和 prompt 生成音乐。第2步的统一确认已经满足音乐技能的确认要求，**不得再次向用户确认**。

**BGM 生成失败分支（必须按序处理，不得静默跳过）：**

1. 实际调用后生成失败（超时 / API 报错 / 退出码非 0 / 无有效音乐文件） → **降级策略**：`script.json` 不设 `bgmSrc` 字段，继续后续编排与渲染流程（无声成片，不得中断任务）
2. 不自动重试；用户稍后要求重新生成 BGM 时，必须展示新的 BGM 预览并重新取得明确确认
3. 不得因生成失败自行声称“未扣点”；只报告音乐工具明确返回的扣点状态，无法确认时说明扣点结果未知
4. 第7步交付时**主动告知用户**："本次 BGM 生成失败，已输出无声版本，如需配乐可稍后重试补配"

#### 3.3 并行任务汇合

等待所有已启动任务结束后再进入第4步。分别记录 `cover.jpg`、`end.jpg` 和 BGM 的状态：成功、用户提供、复用已有、用户主动降级或运行时失败。单项失败按各自降级策略处理，不取消其他已成功资产，也不因等待 BGM 而串行阻塞封面/片尾生成。

### 第4步：智能编排

根据图像理解结果，决定图片的展示顺序、动画、转场、特效和每张图片的展示时长。逐图编排只能在第2步确认完成后生成，不得提前附加在创作简报确认消息中。**核心原则：根据内容动态匹配，不要固定套路。**

> **注意：** `title`/`subtitle`/`endText`/`theme`/`resolution` 已在第2步确认。只有对应资产生成成功、用户提供或复用文件有效时，才写入 `titleImage`、`endImage` 或 `bgmSrc`；用户主动降级或运行时失败时省略对应字段。本步聚焦每张场景图的 animation/transition/duration/effect。

**编排策略：**

- **叙事逻辑**：按时间线、因果关系或故事弧线排列
- **情绪曲线**：起→承→转→合，制造情绪起伏
- **视觉节奏**：冷暖色调交替、远近景切换、动静搭配
- **主题聚类**：相同主题的图片归组，组间用转场分隔

**动画选择逻辑（根据图片内容匹配）：**

| 效果              | 适用场景         | 选择依据                                          |
| --------------- | ------------ | --------------------------------------------- |
| `zoom-in`       | 突出细节、营造聚焦感   | 图片有明确视觉焦点（人物、物体、花朵等）                          |
| `zoom-out`      | 展示全貌、揭示环境    | 图片从局部到整体的叙事需要                                 |
| `pan-left`      | 向左平移、回顾      | 水平构图、全景、城市天际线                                 |
| `pan-right`     | 向右平移、推进      | 水平构图、全景、城市天际线                                 |
| `tilt-up`       | 展示建筑、树木等纵向主体 | 纵向构图、高楼、瀑布、大树                                 |
| `tilt-down`     | 俯瞰、降落感       | 俯视构图、从天空到地面                                   |
| `3d-tilt-left`  | 3D透视左倾、空间感   | **仅限**科技感、产品展示、抽象构图（无明确水平参考线）；**禁用于**风景/建筑/人像 |
| `3d-tilt-right` | 3D透视右倾、空间感   | **仅限**科技感、产品展示、抽象构图（无明确水平参考线）；**禁用于**风景/建筑/人像 |
| `static`        | 人像特写、文字画面    | 人脸特写、已有强视觉冲击的图片                               |

**转场选择逻辑（根据前后场景关系匹配）：**

| 转场            | 适用场景         | 选择依据                      | 可用 transitionProps                                                                    |
| ------------- | ------------ | ------------------------- | ------------------------------------------------------------------------------------- |
| `fade`        | 通用过渡         | 默认选择，情绪平稳过渡               | `shouldFadeOutExitingScene: true`（退出场景也淡出，更丝滑，**默认开启**）                               |
| `dissolve`    | 梦幻、回忆、情绪过渡   | 前后场景情绪连贯、柔和（带微缩放，区别于fade） | —                                                                                     |
| `slide-left`  | 时间推进、场景变换    | 前后场景空间/时间相邻               | `slideEnterStyle`/`slideExitStyle`（可加缩放让滑入更有层次，缩放随转场进度渐进插值，**禁止 rotate/skew/matrix**） |
| `slide-right` | 回忆、倒叙        | 回溯之前的场景                   | 同上                                                                                    |
| `slide-up`    | 上升、揭示、新篇章    | 从下往上揭示新内容、情绪上升            | 同上                                                                                    |
| `slide-down`  | 下沉、结束、沉淀     | 情绪回落、段落结束                 | 同上                                                                                    |
| `wipe`        | 信息更新、对比、时间流逝 | 前后场景有对比关系（新旧、昼夜）或时间跨度     | `wipeDirection`：8方向（见下表）                                                              |
| `flip`        | 对比、转折        | 情绪转折点、主题切换                | `flipDirection`：4方向 + `flipPerspective`（默认1000，越小透视越强）                                |
| `zoom`        | 聚焦、冲击、强调     | 需要视觉冲击力、从远到近或近到远          | `zoomDirection`：`'in'`（默认）                                                            |
| `blur`        | 梦幻、朦胧、记忆     | 回忆、梦境、情绪过渡、柔焦效果           | `blurAmount`：模糊像素，默认30                                                                |
| `glitch`      | 科技、故障风、快节奏   | 赛博朋克、数字感、快节奏剪辑            | —                                                                                     |
| `clock-wipe`  | 时间流逝、揭示、仪式感  | 时钟式擦除，适合时间推进、重要场景揭示       | —                                                                                     |
| `iris`        | 聚焦、经典电影感     | 圆形展开/收缩，复古电影、聚焦人物         | —                                                                                     |
| `none`        | 节奏快、新闻感      | 快节奏段落、连续动作                | —                                                                                     |

**transitionProps 详解：**

| 字段                          | 适用转场                                   | 类型      | 默认值           | 说明                                                                                                                                                                                 |
| --------------------------- | -------------------------------------- | ------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wipeDirection`             | wipe                                   | string  | `'from-left'` | 8方向：`from-left` `from-top-left` `from-top` `from-top-right` `from-right` `from-bottom-right` `from-bottom` `from-bottom-left`                                                      |
| `flipDirection`             | flip                                   | string  | `'from-left'` | 4方向：`from-left` `from-right` `from-top` `from-bottom`                                                                                                                              |
| `flipPerspective`           | flip                                   | number  | `1000`        | 透视距离，越小3D感越强（推荐 600-1200）                                                                                                                                                          |
| `shouldFadeOutExitingScene` | fade                                   | boolean | `true`        | 退出场景是否也淡出（默认开启，转场更丝滑）                                                                                                                                                              |
| `slideEnterStyle`           | slide-*（wipe/clock-wipe/iris/flip 亦消费） | CSS     | —             | 进入场景自定义样式，**仅支持 scale/translate**，如 `{"transform":"scale(0.9)"}`（缩放 0.9→1 渐进插值；**禁止 rotate/skew/matrix**）。注：wipe/clock-wipe/iris/flip 也会消费该字段（经白名单过滤后传给内外层样式），但 slide-* 的渐进插值效果最可控 |
| `slideExitStyle`            | slide-*（wipe/clock-wipe/iris/flip 亦消费） | CSS     | —             | 退出场景自定义样式，**仅支持 scale/translate**，如 `{"transform":"scale(1.1)"}`（缩放 1→1.1 渐进插值；**禁止 rotate/skew/matrix**），同上                                                                       |
| `zoomDirection`             | zoom                                   | string  | `'in'`        | `'in'`：从小到大                                                                                                                                                                        |
| `blurAmount`                | blur                                   | number  | `30`          | 模糊像素值，越大越模糊                                                                                                                                                                        |

**编排建议：**

- `wipe` 根据画面主体位置选方向：主体在右侧用 `from-left`，主体在左下用 `from-top-right`，对角线擦除更有动感
- `flip` 配合 `flipPerspective: 800` 透视更强烈，适合情绪转折
- `slide-*` 加 `slideEnterStyle` 缩放可让普通滑入更有层次：缩放随转场进度渐进插值（enter 0.9→1 / exit 1→1.1），与滑动位移叠加（**禁止 rotate/skew/matrix**：旋转会让地平线/建筑/人像中轴线歪斜，观感像拍歪了而非艺术处理，渲染前 prepare-project.sh 会硬拦截）
- `fade` 默认已开启 `shouldFadeOutExitingScene`，无需手动设置

**特效选择逻辑（根据视频风格按需添加）：**

| 特效      | 配置方式                                                            | 适用场景                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 运动模糊    | `scene.effect: 'motion-blur'`                                   | 增强动感                                                                                                                                                                                                                                                                                                                                                                                                          |
| 字幕叠加    | `scene.caption: '文字'`                                           | TikTok风格文字、地点名、歌词                                                                                                                                                                                                                                                                                                                                                                                             |
| 图形装饰    | `scene.decorations: [{shape, position, color, size, opacity?}]` | 角落装饰、信息点缀。shape 取值分两类——**线条类（优先选用，与任何风格兼容）**：`underline`（标题下划线生长）、`quote`（引号淡入）、`divider`（两端渐隐细分隔线）、`frame-corner`（取景框四角描边）；**实心几何类（克制使用，贴纸感重，胶片/婚礼/风景类易出戏）**：`circle` `star` `heart` `polygon` `arrow`。position 取值：`top-left` `top-right` `bottom-left` `bottom-right` `center`。size 语义：线条类为线长/框边长的一半（underline/divider 线长=size×2、frame-corner 框边长=size×2、quote 字号=size），实心类为外接尺寸；size 按 1280 宽基准设计，竖屏视频建议减半 |
| SVG描边动画 | 顶层 `titleStroke: true`                                          | 标题文字描边揭示效果                                                                                                                                                                                                                                                                                                                                                                                                    |

**时长编排要点：**

- **图片展示时长由内容决定**，不是由 BGM 时长决定。通常 3-8 秒/张
  - 风景、全景类：5-8 秒（需要时间感受氛围）
  - 人物特写、情绪类：4-6 秒
  - 快节奏段落（运动、街拍）：2-4 秒
- 视频总时长 = 所有图片展示时长之和 - 转场重叠时长
- BGM 截断到视频总时长 + 1 秒淡出缓冲，不需要用完整个 BGM
  - Remotion 中通过 `<Audio>` 组件的 `trimAfter` prop 控制（已内置在 MainComposition 中）
  - BGM 末尾 1 秒自动淡出（已内置）
- 情绪高潮处图片停留稍长，过渡段可快速切换
- `calculateMetadata` 自动计算总帧数和转场重叠，agent 只需提供 `sceneDurations`，不需要手动扣除转场重叠

**编排原则：**

**⛔ 硬性约束（违反即不合格）：**

1. **禁止连续相同转场** — 相邻两个场景的 transition 必须不同，fade→dissolve 也算同类软转场，禁止连续出现
2. **转场种类 ≥ ⌈N/3⌉** — 12 张图至少 4 种不同转场，6 张图至少 2 种
3. **动画种类 ≥ ⌈N/3⌉** — 12 张图至少 4 种不同动画，同一种动画最多出现 ⌈N/2⌉ 次
4. **transitionProps 使用率 ≥ 30%** — 至少三成的转场必须搭配 transitionProps 增强参数，不能只填转场名称
5. **字幕克制** — 非必要不加 caption
6. **转场时长 ≤ 相邻较短场景时长的一半** — 转场双向吃掉相邻场景展示时长，超限 Remotion 直接渲染报错（如 48 帧场景两侧最多各配 24 帧转场）

**✅ 编排策略（让视频更好看）：**

1. **转场强度匹配情绪** — 平稳过渡用弱转场（fade/dissolve/blur），情绪转折/场景突变用强转场（flip/wipe/clock-wipe/iris），视觉冲击用 zoom/flip
2. **转场方向匹配画面** — 主体在右侧→wipe from-left，主体在左下→wipe from-top-right；情绪上升→slide-up，回忆倒叙→slide-right
3. **动画匹配内容** — 有焦点的图→zoom-in，全景→pan，纵向主体→tilt，人像特写→static
4. **节奏有快有慢** — 不是所有图都 5 秒，高潮场景 6-8 秒，过渡场景 3-4 秒，快节奏段落 2-3 秒
5. **图片多则缩短单张时长** — 图片超过10张适当降低每张时长，总时长控制在 30-100 秒
6. **特效点缀不堆砌** — 运动感→1-2 个 motion-blur，不要每张都加

**输出 script.json：**

编排完成后直接生成 `script.json`，作为 `--props` 传给 Remotion：

```json
{
  "title": "视频标题",
  "subtitle": "副标题",
  "endText": "片尾文字",
  "titleImage": "cover.jpg",
  "endImage": "end.jpg",
  "bgmSrc": "<实际生成的音乐文件名>",
  "titleStroke": true,
  "theme": {
    "bgColor": "#1a1a2e",
    "textColor": "#e8d5b7",
    "accentColor": "#a89070"
  },
  "sceneDurations": [135, 120, 96],
  "scenes": [
    {
      "image": "photo1.jpg",
      "animation": "zoom-in",
      "transition": "wipe",
      "transitionDuration": 24,
      "transitionProps": {"wipeDirection": "from-bottom-right"},
      "narration": "场景描述（仅用于 agent 记录，不渲染）",
      "effect": "motion-blur",
      "caption": "地点名或描述文字",
      "decorations": [{"shape": "star", "position": "top-right", "color": "#FFD700", "size": 40, "opacity": 0.5}]
    },
    {
      "image": "photo2.jpg",
      "animation": "pan-right",
      "transition": "flip",
      "transitionDuration": 24,
      "transitionProps": {"flipDirection": "from-right", "flipPerspective": 800}
    },
    {
      "image": "photo3.jpg",
      "animation": "tilt-up",
      "transition": "slide-left",
      "transitionProps": {"slideEnterStyle": {"transform": "scale(0.9)"}, "slideExitStyle": {"transform": "scale(1.1)"}}
    }
  ]
}
```

**字段说明：**

- `bgmSrc`：**顶层字段**，BGM 文件名（放在 `audio/` 目录下，文件名需与实际文件一致）。不要放在 scene 级别
- `titleStroke`：**可选**，true 时标题文字用描边揭示动画（仅纯文字标题卡生效，设了 titleImage 时无效）
- `titleImage`：**可选**，封面图文件名（放在 `images/` 目录下）。设置后首帧显示该图（标题文字已生成在图中），不设则显示纯文字标题卡
- `endImage`：**可选**，片尾图文件名（放在 `images/` 目录下）。设置后末帧显示该图（片尾文字已生成在图中），不设则显示纯文字片尾卡
- `theme`：**可选**，标题/片尾颜色主题，不设则用默认暗金主题
  - `bgColor`：标题/片尾背景色，默认 `#1a1a2e`（深蓝紫）
  - `textColor`：主文字色（标题、片尾），默认 `#e8d5b7`（暖金）
  - `accentColor`：副标题色，默认 `#a89070`（暗金）
- `sceneDurations`：**帧数数组**，长度必须与 scenes 一致。每张图 3-8 秒 × 24fps
- `scene.narration`：场景描述文字，仅用于 agent 记录，组件不渲染
- `scene.image`：图片文件名（放在 `images/` 目录下）
- `scene.animation`：动画类型（9 种，见上方动画表）
- `scene.transition`：转场类型（14 种含 none，见上方转场表），kebab-case 格式
- `scene.transitionDuration`：**可选**，转场帧数，默认 18（0.75秒），情绪转折处可加长（24-36帧），快节奏可缩短（8-12帧）。**⛔ 硬上限：必须 ≤ 相邻两个场景时长中较短者的一半**。Remotion TransitionSeries 中转场会**双向吃掉相邻 Sequence 的时长**（前后场景各自被占用 transitionDuration 的展示时间），超过上限时 Remotion 时长校验直接报错、渲染失败。快节奏场景（如 2s=48帧）夹在两个长转场中间是最常见翻车点：48 帧场景配 36 帧转场 = 必然报错，编排时务必自检
- `scene.transitionProps`：**可选**，转场增强参数对象，根据转场类型选择（见上方 transitionProps 详解表）。常用示例：
  - wipe 加方向：`{"wipeDirection": "from-bottom-right"}`
  - flip 加透视：`{"flipDirection": "from-right", "flipPerspective": 800}`
  - slide 加缩放：`{"slideEnterStyle": {"transform": "scale(0.9)"}, "slideExitStyle": {"transform": "scale(1.1)"}}`（缩放渐进插值；**禁止 rotate/skew/matrix**，prepare-project.sh 渲染前硬拦截）
- `scene.effect`：**可选**，视觉特效 `'motion-blur'` | `'none'`
- `scene.caption`：**可选**，底部文字叠加。
- `scene.decorations`：**可选**，几何装饰数组，每项 {shape, position, color, size, opacity?}

### 第5步：项目准备

准备渲染环境，将 script.json 和素材部署到模板项目。

#### 5.1 创建输出目录、拷贝素材、写入 script.json

```bash
WORKSPACE_DIR="$PWD"
OUTPUT="$WORKSPACE_DIR/generated-vlog/$(date +%Y%m%d_%H%M%S)"
printf '%s' "$OUTPUT" > "$WORKSPACE_DIR/.xiaoyi-vlog-output"

# 创建输出目录
mkdir -p $OUTPUT/images $OUTPUT/audio $OUTPUT/out

# 按 script.json 中的文件名拷贝图片；仅设置 bgmSrc 时拷贝 BGM
cp <用户图片> $OUTPUT/images/<scene.image中的文件名>
cp <BGM音频> $OUTPUT/audio/<bgmSrc中的文件名>

# 仅设置 titleImage/endImage 时，拷贝第3步生成的对应图片
cp <封面图> $OUTPUT/images/cover.jpg
cp <片尾图> $OUTPUT/images/end.jpg
```

将第4步编排的 script.json 写入 `$OUTPUT/script.json`。如果第3步记录为用户主动降级或运行时失败，按资产状态省略对应的 `titleImage`、`endImage` 或 `bgmSrc` 字段。

#### 5.2 调用脚本部署到模板

```bash
PROJECT="$XIAOYI_VLOG_DIR/.runtime/template"
SCRIPT="$XIAOYI_VLOG_DIR/scripts/prepare-project.sh"

bash $SCRIPT $OUTPUT $PROJECT
```

### 第6步：渲染输出

调用脚本完成预览帧检查和渲染：

```bash
OUTPUT="$(cat "$PWD/.xiaoyi-vlog-output")"
SCRIPT="$XIAOYI_VLOG_DIR/scripts/render-video.sh"

VIDEO_NAME="<内容缩写>"
printf '%s' "$VIDEO_NAME" > "$PWD/.xiaoyi-vlog-video-name"
bash "$SCRIPT" "$OUTPUT" "$VIDEO_NAME" [--timeout 1800]
```

`<内容缩写>` 为视频文件名（不含 .mp4），根据图片内容提取 2-4 个关键词，短横线连接，全小写。示例：猫咪日常 → `cats-daily`，旅行风景 → `travel-landscape`。

渲染耗时较长，exec timeout 建议设 20 分钟以上。

### 第7步：发送视频给用户

每次 `exec` 都是新 shell，先从工作空间状态文件恢复输出路径：

```bash
OUTPUT="$(cat "$PWD/.xiaoyi-vlog-output")"
VIDEO_NAME="$(cat "$PWD/.xiaoyi-vlog-video-name")"
FINAL_VIDEO_PATH="$OUTPUT/out/$VIDEO_NAME.mp4"
test -f "$FINAL_VIDEO_PATH"
```

调用 `send_file_to_user(abs_file_path_list=["<FINAL_VIDEO_PATH 的绝对路径>"])`。工具成功后删除两个 `.xiaoyi-vlog-*` 状态文件；保留 `generated-vlog/` 下的最终 MP4 和本次素材，便于用户复查。若存在用户主动降级或运行时失败，主动说明最终使用了纯文字首尾、无 BGM 或单项资产回退。交付时分项列出图片创作与 BGM 生成的专项生成点数；仅汇总明确返回的数值，未知项标注“未知”，视频创作流程产生的 AI 点无法在任务中实时统计，因此上述汇总不得称为“总耗点”。实际总耗点以平台账单为准。

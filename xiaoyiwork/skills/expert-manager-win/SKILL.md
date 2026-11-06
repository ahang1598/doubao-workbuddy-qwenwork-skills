---
name: expert-manager-win
description: |
  创建或更新 jiuwenswarm 专家/专家团文件包。当用户想要一个具备特定专长的 agent（例如"文案专家"、"数据分析专家"），或希望把现成材料改造成可复用的专家包时使用。触发词：创建专家、创建专家团、转化专家、生成专家包、导入专家、修改专家、检查专家包、专家合规。
description_cn: 创建或更新专家/专家团文件包。
allowed_tools: [bash, read_file, write_file, image_gen]
---

# 专家包构建与维护手册

> **阅读要求**：本文件是执行本技能的唯一作业依据。动手之前，先把全文（含各节规则、操作命令与文末参考资料清单）完整读一遍并照此执行；不允许只浏览个别小节就开工。

在本技能下，你的任务是产出和维护符合 jiuwenswarm 规范的专家文件包，并保证最终产物能被 `expert.load` 正常加载、进入 `experts.list`。

## 0. 基本概念

### 0.1 包的两种形态

| 形态 | 判定依据 | 结构 |
|---|---|---|
| 单专家 | 顶层无 `package_type` 键，成员 manifest 写 `packageType: "agent_template"` | 一个 agent |
| 专家团 | 顶层写 `package_type: "agent_group"` | leader + 多个 member |

形态由包的实际结构决定：单角色即单专家，多角色协作即专家团。不要按用户口头要求强行指定形态。

### 0.2 包必须落在哪里

专家包只能放在"专家根目录"下，否则 `expert.load` 扫不到。根目录按以下优先级解析：

```
JIUWEN_EXPERTS_DIR  >  JIUWENSWARM_DATA_DIR  >  ~/.jiuwenswarm
```

完整位置为 `<专家根目录>/<expert-id>`。该解析对应 jiuwenswarm 的 `common.utils.get_agent_experts_dir()`，即 `LocalDirExpertPackageSource` 的扫描根。桌面端（小艺Work）按用户隔离数据根，`JIUWENSWARM_DATA_DIR` 由桌面端注入 jiuwen 子进程，脚本会自动跟随，无需手动指定。

**因此：任何情况下都不得把包写到专家根目录之外。** 用户要求换路径时，先说明"包放在别处将无法被发现"，然后仍在专家根目录内完成操作。

### 0.3 persona 目录约定

- 单专家：目录名固定为 `"agents"`，persona 位于 `agents/<expert_id>.md`；
- 专家团成员：目录名固定为 `"persona"`，persona 位于 `agents/<member>/persona/<member_id>.md`。

## 1. 展示信息与包字段的映射

`experts.list` 里看到的每一条信息都来自下表字段。无论新建、移植还是迭代，凡涉及展示信息的改动，一律按此表执行。

| 界面呈现 | 单专家取值 | 专家团取值 | 改动权限 |
|---|---|---|---|
| 包名/id | `agentCard.id`（= 目录名） | 顶层 `name`（= 目录名） | **锁定**，改名等于重建 |
| 形态标签 | 无 `package_type` 键 + `packageType:"agent_template"` | 顶层 `package_type:"agent_group"` | 随结构而定，禁止人为指定 |
| 展示名 | `agentCard.name` | `metadata.displayName` | 自由修改 |
| 简介 | `agentCard.description` | `metadata.description` | 自由修改，写清核心能力 |
| 头像 | `metadata.avatar`（声明式，如 `"avatars/expert.png"`） | 同左 | 可替换图片文件 |
| 擅长领域 | `metadata.tags`（字符串列表，3 个） | 同左 | 可改；已满 3 个时先提示删除/替换，再新增 |
| 试试这样问我 | `metadata.quickPrompts`（固定 3 条，第 1 条兼作 `defaultInitPrompt`） | 同左 | 可改 |
| 职业定位 | `metadata.profession`（单字符串，如 `"后端架构师"`、`"专家团"`） | 同左 | 可改 |
| 行业分类 | `metadata.categoryId`（单字符串，取值规则见 §4.1） | 同左 | 可改 |

## 2. 任务入口

用户请求落到以下三类之一。三类入口只在"信息收集"方式上不同，收集完毕后统一进入第 3 节的机械环节。

### 入口 A：对话式新建

开工前必须问清两件事：

1. 形态：单专家还是专家团（按 §0.1 判定，不要让用户随意定）；
2. 领域：这个专家擅长什么。

**单专家还需收集**：名字、职业头衔、能力详述、persona 正文素材（身份设定、核心能力、工作流程、输出规范、注意事项）、是否挂载 skills/tools。

**专家团还需收集**：团队名、leader（主理人）人选及职责、每位团员的名字/头衔/职责、团队 SOP、全员协作契约（写入顶层 `instruction`）。

**定名查重（必做，且必须在初始化目录之前）：**

拟出 `agentCard.id`（= 目录名，kebab-case）和展示名后，先跑：

```
python3 scripts/check_conflict.py --id <expert_id> --name <展示名>
```

- 退出码 1：同 id 包已存在（本地或云端）。必须换 id 重查，直至通过——沿用重复 id 会让本地包悄悄遮蔽既有包，云端更新链路也随之断掉；
- 退出码 0 但带警告：展示名撞名。建议换名；用户坚持时，讲明"列表里会出现两个同名专家"，然后按其意愿继续。

### 入口 B：既有材料移植

用户给了文件路径或直接粘贴内容时：

1. 通读材料，抽取其中的身份设定、能力清单、SOP、输出规范、约束条件、脚本、参考资料与角色分工；
2. 据此判定形态（单角色→单专家，多角色→专家团），并向用户交代判定依据；
3. 与用户核对推断结论及各展示字段，缺失项当场补齐；
4. 先按入口 A 的"定名查重"过一遍（id 撞名必须换），再进入初始化与填充。

### 入口 C：迭代既有包

用户要修改/编辑/更新某个已有专家时：

1. 到专家根目录下按名字找到对应包目录（例：`backend-dev`），通读 `manifest.json` 与 `agents/*.md`，摸清现状；
2. 和用户确认本次改动面（persona 正文、展示字段、tags、头像、增删团员等）；
3. 做最小化编辑，文风与原文件保持一致；
4. 跑校验（§3 环节 ⑤）；
5. 无论改了什么，都要重跑一次可发现性确认（§3 环节 ⑥）。

**迭代守则：**
- 改前把目标文件完整读入，防止内容丢失；
- 只动用户点名的部分，不整篇重写；
- 包不存在时，引导用户先确认专家根目录里是否真有它。

**允许改动的字段**：`agentCard.name`、`agentCard.description`、persona 正文、`metadata.tags`、单专家的 `metadata.avatar`、专家团的 `metadata.displayName`/`metadata.description`、团员 persona、leader 的 `AGENT.md` 正文等。

**一律禁止触碰（它们是包的身份标识，动了包就"丢"了）：**
- `manifest.json` 的 `agentCard.id`（单专家）/ 顶层 `name`（专家团）——必须与目录名一致；
- 包目录名、成员目录名、leader 固定名；
- `agents/*.md` 文件名：`persona.dir` 指向的是目录，改文件名虽不报错，但会打乱排序拼接，确需改名请重建包；
- 成员 manifest 的 `packageType`；
- 用户要求改 id/目录名时，答复口径：改名需重建，不支持原地改。

## 3. 机械环节（初始化 → 打包）

以下环节编号对应流水线顺序：

```
信息收集(§2) → ② init_expert.py → ③ 内容填充 → ④ 头像(可选) → ⑤ validate_expert.py → ⑥ register_expert.py → ⑦ package_expert.py(可选)
```

需要批量建包时，逐个包完整走完 ②→⑥（见 §6 约束 9）。

### 环节 ②：初始化目录

```bash
python3 scripts/init_expert.py <expert-name> --type agent|team \
  [--path "$JIUWEN_EXPERTS_DIR"] [--members member-a,member-b]
```

- `--path` 省略时默认专家根目录；`--members` 仅专家团使用，列出成员 id（leader 不写，脚本自动创建）。
- 模板文件以 `[TODO]` 占位，内容随后由你填充。
- **⚠ 模板已写盘：填充前必须先 Read 目标文件，再 Write/Edit。** 写入工具对"本会话未读过且已存在"的文件会拒绝写入，报错 `Read it before attempting to write it`——manifest / persona / AGENT.md / README 一律如此。推荐逐文件 Read → 用 Edit 替换 `[TODO]`，不要对未读文件直接 Write。

### 环节 ③：内容填充

按下列参考资料逐文件撰写：

- `@references/manifest-spec.md` — 两种形态的 manifest.json 字段定义与样例
- `@references/persona-md-spec.md` — persona 正文写法（普通 agent / leader / 团员）
- `@references/team-spec.md` — 专家团协作约束、命名规则与 SOP 搭配
- `@references/avatar-spec.md` — 头像规格与绘图提示词写法

### 环节 ④：头像（可选）

依据 `@references/avatar-spec.md`，用 `image_gen` 给每个角色出一张头像放进 `avatars/`：单专家经 `metadata.avatar` 引用；专家团依赖 `avatars/<id>.png` 隐式扫描。

**头像可缺席，失败不拦路**：`image_gen` 因网络、插件缺失、WinError 等原因失败时，在 `README.md` 记一笔"待补头像 + 推荐 prompt"，直接进入环节 ⑤/⑥。运行期只核对 `metadata.avatar` 声明的文件是否存在（专家团为隐式扫描，缺图不报错），`expert.load` 不会因缺头像而失败。用户事后自行补 PNG 到 `avatars/` 即可。

### 环节 ⑤：校验

```bash
python3 scripts/validate_expert.py <path/to/expert-dir>
```

脚本优先调用 jiuwenswarm 自带的 `validate_expert_package`；环境里没有 jiuwenswarm 包时，退回到内置的等价实现。任何一项校验不过，整个包终止。

### 环节 ⑥：可发现性确认

```bash
python3 scripts/register_expert.py <path/to/expert-dir>
```

该脚本做四件事：

1. 与云端及本地既有包比对 id 和展示名（同 id 直接阻断）；
2. 复查关键字段里是否残留 `[TODO]`；
3. 确认包确实位于专家根目录；
4. 报告本地专家源的开关状态（默认开启，只有显式设 `JIUWEN_EXPERT_LOCAL_DIRS=0` 才会关闭）。

查重不过或 `[TODO]` 未清空时，脚本报错拒绝确认。

注意：jiuwenswarm 本身没有 marketplace 注册表，此脚本不写任何注册文件——所谓"确认可发现性"，就是终检 + 路径核对 + 环境变量报告。

### 环节 ⑦：打包（可选）

```bash
python3 scripts/package_expert.py <path/to/expert-dir> [output-dir]
```

产出 `<expert_id>.zip`，供手动分发，或留待将来接入包仓库（现阶段没有上架 API）。

## 4. categoryId 与 tags 生成规范

两者都是 `metadata` 下的产品层自由字符串：包校验与 `expert.load` 不做枚举检查，随 `experts.list` 原样透出，由宿主产品按需消费。

### 4.1 categoryId（行业分类）生成规则

- 单字符串，语义是"该专家属于哪个行业领域"。按专家的核心能力领域归一个分类，不按用户口头偏好随意填。
- **定类先查重（与入口 A 的定名查重同批做）**：收集现有专家包在用的 categoryId（本地专家根目录已装包 + 云端在架专家），有与领域相符的就**原样复用**；确无贴切项时，才按 `<两位序号>-英文驼峰` 风格新拟（如 `04-DataAI`）。
- 同一领域的取值必须**逐字符稳定**：该值是包对外透出的分类依据，同域不同写法会让下游消费方把同一领域拆成多份。

### 4.2 tags（擅长领域）选取建议

- `metadata.tags` 是字符串列表（建议 3 条），会被 `experts.list` 透传展示。
- 以能力词为主（如"数据分析"），可搭配一个具体工具或场景词（如"Excel 建模"）；避免与 profession 重复的空泛大词。
- 示例：`数据分析 / Excel建模 / 可视化`、`数值计算 / MATLAB编程 / 工程建模`、`内容策略 / 多平台创作 / 品牌叙事`。

## 5. 材料到包结构的移植映射

入口 B 拿到材料后，按下表决定每块内容最终落在包里什么位置：

| 材料里是什么 | 转成什么 | 落到哪 |
|---|---|---|
| 角色设定、专家人设 | persona 正文的身份与能力段落 | 单专家 `persona/<name>.md`；专家团 `agents/<m>/persona/<m>.md` |
| 操作步骤、业务流程 | persona 正文的工作流程段落 | persona 正文 |
| 输出格式约定 | persona 正文的输出规范段落 | persona 正文 |
| 接口文档、字段说明 | 技能参考文档 | `skills/<name>/references/` |
| 可运行脚本 | 技能脚本 | `skills/<name>/scripts/` |
| 单据/报告模板 | 技能模板 | `skills/<name>/templates/` |
| 多角色分工说明 | leader + 各成员 persona | `agents/<member>/persona/<member>.md` |
| 阶段式 SOP | leader persona 的 SOP 段落 | `agents/leader/persona/leader-persona.md` |
| 协作契约 | 顶层 `instruction` + leader `AGENT.md` | `manifest.json` / `agents/leader/AGENT.md` |

移植质量底线：

1. 材料中每条有价值的信息都必须在包里有着落，不允许静默丢弃；
2. 碎片化内容按包结构重新归位，而不是原样堆砌；
3. 术语照原样保留，不得擅自简化；
4. 大段资料一律放 `skills/<name>/references/`，persona 正文只留提纲挈领的部分。

## 6. 硬性约束（违反即产出无效）

1. 目录名即 id：单专家 `agentCard.id`、专家团顶层 `name`、各成员 `agentCard.id`，三者都必须与所在目录同名；
2. leader 位固定：专家团 `agents` 列表必须含 `"leader"`；leader 子包必有 `AGENT.md`，其余成员**不得**携带 `AGENT.md`（职责写进 persona）；
3. `persona.dir` 必填：写相对路径，目录里至少要有一个 `*.md`；多个文件按文件名排序后拼接进 identity 段；
4. 路径一律包内相对：`persona.dir`、`tools[].file`、`skills[].dir`、`metadata.avatar` 既不许绝对路径，也不许 `..` 越界；
5. `rails`、`subagents` 两个字段本期不支持，禁止出现；
6. 根模板的 `model` 字段不生效，校验会告警，建议直接删掉；
7. 包必须落在 §0.2 定义的专家根目录，否则 `expert.load` 发现不了；
8. 本地专家源默认开启，`LocalDirExpertPackageSource` 扫描根目录并把包送进 `experts.list`；只有显式设 `JIUWEN_EXPERT_LOCAL_DIRS=0` 才关闭；
9. 批量建包必须逐个串行走完 `init → validate → register`，不许只写文件跳过校验/确认（参考 `scripts/batch_create.py`），核心模式：
    ```python
    for pkg in packages:
        run init_expert.py                  # ② 建目录骨架
        fill manifest / persona / avatars   # ③ AI 逐文件填充
        run validate_expert.py              # ⑤ 不过即中止
        run register_expert.py              # ⑥ 校验通过才执行
    ```
10. 目标位置已有同名包、且本次无需重建内容时，仍要补跑校验 + 可发现性确认，确保包处于可用状态；
11. 专家团任一成员校验失败，整包加载随之终止；
12. persona 会被原文塞进系统提示词——请按"写给 LLM 的人设指令"来写，不要写成 README 式的说明书。

## 7. 收尾交付

包生成后，向用户交代：

1. 头像已由 `image_gen` 放入 `avatars/`（PNG/JPG，512×512，≤500KB），可自行替换；
2. 需要分发时：`python3 scripts/package_expert.py <expert-dir>`；
3. 请用户复核内容准确性；
4. 本地专家源默认处于开启状态。

## References

- `references/manifest-spec.md` — 两种形态的 manifest.json 字段定义与样例
- `references/persona-md-spec.md` — persona 正文写法（普通 agent / leader / 团员）
- `references/team-spec.md` — 专家团协作约束、命名规则与 SOP 搭配
- `references/avatar-spec.md` — 头像规格与绘图提示词写法

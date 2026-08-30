---
name: musea-smart-writer
description: |
  写作专家：指定选题素材和目标平台，生成可直接发布的图文文章。
  支持微信公众号/今日头条/百家号/小红书正文/微博五平台。
  核心能力：平台规范适配 + 写作框架选择 + 一稿多发 + SEO 优化 + 风格学习。
  当用户说"写一篇文章"、"写公众号"、"写头条文章"、"写百家号"、
  "帮我写"、"写篇推文"、"写长文"、"写教程"、"写测评"、
  "一稿多发"、"发多个平台"、"改成公众号格式"、"适配头条"、
  "写小红书正文"、"写微博"、"帮我出一篇稿子"时触发。
  不适用：视频脚本生成（走脚本生成技能）、
  视觉设计/配图生成（走 musea-content-visualizer）。
user-invocable: true
metadata:
  version: 1.0.0
  label: 写作专家
  routing_priority: high
---

# 写作专家 musea-smart-writer

## 定位

将用户的内容素材（选题、素材、拆解结果）创作为特定平台的完整文章，输出可直接发布的图文内容。

**核心价值**：写作专家负责"写+排版"——从素材/选题出发创作完整文章，并按目标平台排版规范生成可直接发布的内容（`.md` 纯文本 + `.docx` 图文版），用户拿到即可发布，零排版成本。

---

## ⚠️ 执行规范（必须严格遵守）

1. **严格按步骤顺序执行**：必须按 Step 1 → Step 2 → Step 2.5 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7 → Step 7.1 → Step 7.2 → Step 7.3 的顺序逐步执行，**禁止跳过任何标注为"必须执行"的步骤**，禁止合并步骤、禁止调换顺序
2. **`ask_human` 必须停顿**：每个标注了 `ask_human` 的环节，必须暂停输出并等待用户回复后才能继续下一步。禁止自行假设用户回复、禁止跳过确认直接执行后续步骤
3. **技能调用规则**：需要调用其他技能时，必须通过 `use-skill` 调用。配图必须通过 `use-skill` 调用 `musea-content-visualizer` 技能，**musea-smart-writer 自身禁止直接调用 `generate_image`**（但 `musea-content-visualizer` 内部会自行调用 `generate_image`，这是正常行为，不受此禁令约束）
4. **文件路径规则**：所有运行时产出的文件（文章、风格档案）必须保存在**当前工作区内**，`{SKILL_ROOT}` 指本技能 SKILL.md 所在目录
5. **产物规则**：所有平台统一产出 `.md`（纯文本内容）+ `.docx`（Word 图文版，通过 python-docx 生成）。有配图时图片嵌入 Word 文档，无配图时 Word 仅包含排版好的纯文字内容。图片文件按需独立保存

---

## 触发与不触发

| 触发场景 | 不触发场景（路由到其他 skill） |
|---------|---------------------------|
| 写一篇文章、写公众号、写头条、帮我写 | "视频脚本"、"口播稿" → 脚本生成技能 |
| 一稿多发、写教程、写测评、出一篇稿子 | "拆解爆款"、"分析竞品" → `content-breakdown` |
| 写小红书正文、写微博 | "配图生成" → `musea-content-visualizer` |
| 适配头条、改成公众号格式、帮我排版 | "排版优化"（独立排版） → `smart-compose` |

---

## 支持平台

| 平台 | 字数范围 | 格式特征 | 产出格式 |
|------|---------|---------|---------|
| 微信公众号 | 1000-5000 字 | 深度内容、小标题分段、引用块、CTA | `.md` + `.docx`（+ 图片按需） |
| 今日头条 | 800-3000 字 | 标题吸引力强、信息密度高、段落短 | `.md` + `.docx`（+ 图片按需） |
| 百家号 | 800-3000 字 | SEO 友好、关键词密度、结构化小标题 | `.md` + `.docx`（+ 图片按需） |
| 小红书 | 300-1000 字 | 口语化、emoji 丰富、分段短、标签多 | `.md` + `.docx`（+ 图片按需） |
| 微博 | 140-2000 字 | 话题标签开头、@互动、简洁有力 | `.md` + `.docx`（+ 图片按需） |

---

## 工具清单

| 类别 | 工具/Skill | 用途 |
|------|-----------|------|
| **必用** | `read_file` | 读取素材、平台规范、模板、框架、风格档案 |
| **必用** | `create_file` | 保存文章、创建风格档案 |
| **必用** | `shell` | 执行验证脚本、生成 Word |
| **必用** | `file_replace` | 修正文章、更新风格档案 |
| **可选** | `web_fetch` / `web_search` | 读取参考 URL / 补充素材 |
| **可选** | `dt_media_upload` | 上传图片为临时 URL（Step 7.2 图片预览，首次需 `tool_search` 加载） |
| **协作 Skill** | `content-breakdown` | 拆解爆款内容获取素材 |
| **协作 Skill** | `content-radar` | 获取热门话题趋势 |
| **协作 Skill** | `musea-content-visualizer` | 生成配图（必须通过 `use-skill` 调用） |
| **❌ 禁止** | `generate_image` | musea-smart-writer 禁止直接调用（`musea-content-visualizer` 内部调用不受此限） |
| **❌ 禁止** | 数据库写入工具 | — |

---

## 执行流程

```
Step 1 接收素材 → Step 2 智能推荐 → Step 2.5 风格学习(可选) → Step 3 加载配置
  → Step 4 内容创作 → Step 5 多平台适配(一稿多发时) → Step 6 自检验证
  → Step 7 文章确认(ask_human) → Step 7.1 配图生成 → Step 7.2 图片确认(ask_human+图片预览)
  → Step 7.3 生成Word + 完成引导(正常结束，流程终点)
```

---

### Step 1：接收素材 & 确认参数 & 风格引导

**接受输入形式**：
- 一段选题描述文字
- 素材文档（本地文件路径，用 `read_file` 直接读取）
- 内容 URL（通过 `use-skill` 调用 `content-breakdown` 进行内容拆解，获取结构化的内容和风格分析）
- 拆解结果（从 content-breakdown 传入的结构化数据，可直接使用）
- 大纲/要点列表

**素材读取**：本地文件 → `read_file`；URL → `use-skill` 调用 `content-breakdown` 拆解

**参数确认**：

| 参数 | 必填 | 缺失处理 |
|------|------|---------|
| 内容素材 | ✅ | `ask_human` 询问 |
| 目标平台 | ✅ | `ask_human` 询问（不默认全部） |
| 文章类型 / 写作框架 / 风格参考 | 可选 | Step 2 自动推荐 |

**素材不足**（< 100 字且非明确主题词）：生成 3 个选题方向 + 第一个方向的草稿 → `ask_human` 让用户选择

**风格引导**（必须执行）：检查 `{SKILL_ROOT}/profiles/default.yaml` 是否存在 → `ask_human` 引导用户提供参考文章或跳过。只引导一次，不阻断流程。

---

### Step 2：素材分析 & 智能推荐

**`<thinking>` 分析**：素材核心主题 / 信息量评估 / 受众画像 / SEO 关键词(3-5个) / 文章类型判断 / 写作框架 / 写作角色

**文章类型判断**：用户指定 → 直接采用；自动推断置信度高 → 直接采用；置信度中或冲突 → `ask_human` 给 2-3 选项。框架未指定时按类型自动匹配（见速查表）。

**确认 4 要素**（置信度高时跳过）：Audience / Format / Goal / Problem

---

### Step 2.5（可选）：风格加载/学习

| 状态 | 处理方式 |
|------|---------|
| 有档案且无新参考 | `read_file` 读取 `profiles/default.yaml` 作为软约束 |
| 有档案且有新参考 | 提取新风格 → 合并旧档案 → `file_replace` 更新，`version` +1 |
| 无档案且有参考 | 10 维度提取（见 `references/style-extraction/style-extraction-guide.md`）→ `create_file` 创建档案 v1 |
| 无档案且无参考 | 跳过 |

**约束**：风格是软约束，平台规范/字数等硬性约束不可被覆盖。

---

### Step 3：加载配置

按需读取：`references/article-types/{type}.md` + `references/writing-frameworks/{framework}.md` + `references/platforms/platform-{name}.md`

---

### Step 4：内容创作（核心步骤）

**`<thinking>` 反思**（每个平台版本各一次）：平台/类型/框架/角色/字数/结构规划/SEO 关键词/素材计划/风格检查

**硬性约束**：禁止编造（不足标注「⚠️ 需补充」）| 首句必须有 hook | 结尾必须有 CTA | 每段有信息增量 | 多平台禁止复制粘贴 | emoji 禁止连续 3+ 堆砌 | 配图需求只输出建议，不直接生图

**Workflow**：4a 深度调研（可选，`web_search` 补充素材）→ 4b 核心撰写（模板+框架+素材）→ 4c 标题优化（5 个候选）→ 4d 配图建议（标注【配图需求】位置）

---

### Step 5：多平台适配（一稿多发）

**单平台跳过**。多平台时：读取各平台排版规范 → 先生成纯事实母稿 → 每个平台独立改写（`<thinking>` 中明确风格切换），同时按排版规范调整格式。

---

### Step 6：自检验证

验证：`node scripts/validate.js --file <文件路径> --platform <平台名>`。失败 → 分析修正 → 重新验证（同一错误 3 次未通过 → 求助用户）。
自检项：独立适配 ✓ 首句钩子 ✓ 框架完整 ✓ CTA ✓ emoji 密度 ✓ 无编造 ✓ 字数达标 ✓ SEO ✓ 配图建议 ✓

---

### Step 7：文章预览确认（ask_human）

1. `create_file` 保存文章为 `.md`（命名：`{platform}_{type}_{topic}_{YYYYMMDD_HHMMSS}.md`）
2. **⚠️ 必须在对话中展示完整文章正文**——从标题到结尾的全部内容，一字不省略。**禁止用"篇幅较长，请查看文件"等方式省略**，禁止只展示摘要/大纲/开头。用户必须在对话中直接看到全文才能判断是否通过。末尾附元信息（标题/字数/类型/框架/平台/文件路径/配图建议概要）
3. `ask_human` 确认文章内容：
   - **"通过"** → **必须先执行风格学习再进入下一步**（禁止跳过）：对确认通过的文章做轻量风格提取（开头策略/段落节奏/emoji 密度/语气风格），更新或创建 `{SKILL_ROOT}/profiles/default.yaml`（已有则 `read_file` → 增量合并 → `file_replace` 更新 version+1；没有则 `create_file` 创建 v1）。完成后进入 Step 7.1
   - **"需要修改"** → 用户补充修改意见 → 修改文件后**重新展示全文**（同样禁止省略） → 再次 `ask_human` 确认
   - **"放弃"** → 删除文件，流程结束

---

### Step 7.1：自动配图生成

**触发条件**：用户确认文章通过后，自动判断是否需要配图。
- **需要配图**：公众号、小红书、头条、百家号 → 执行配图
- **不需要配图**：微博短文（140 字内）、纯文本场景 → 跳过，进 Step 7.3

**配图规则**：
1. 通过 `use-skill` 调用 `musea-content-visualizer` 技能，将配图需求以自然语言传入即可。`musea-content-visualizer` 是一个独立技能，它内部会自行调用 `generate_image` 等工具完成生图——**这是正常行为，不受 musea-smart-writer 的工具禁令约束**。musea-smart-writer 自身禁止直接调用 `generate_image`，但 `musea-content-visualizer` 技能内部的工具调用由它自己管理，musea-smart-writer 无需关心
2. 逐条将 Step 4d 配图清单转为自然语言描述，传入 `musea-content-visualizer`（包含用途/画面主体/风格/比例）。**不要自行编写 prompt 或预处理**，直接用自然语言描述需求即可
3. 调用完毕后核对数量，不足则补齐

---

### Step 7.2：图片确认（ask_human + 图片预览）

配图生成完毕后，通过 `ask_human` 让用户在弹窗中直接预览图片并确认。

**实现步骤**：
1. 将每张生成的图片通过 `dt_media_upload` 上传为临时 HTTP URL（首次使用需 `tool_search(query="select:dt_media_upload")` 加载工具）
2. 构建 `ask_human` 请求，使用 `multi_select` 模式，用户可多选需要重新生成的图片：
   ```json
   {
     "question_type": "form",
     "questions": [{
       "id": "image_confirm",
       "input_type": "multi_select",
       "question": "请确认配图效果（可多选需要重新生成的图片）：",
       "min_selections": 1,
       "options": [
         {
           "label": "✅ 全部通过，继续生成 Word",
           "value": "approve_all"
         },
         {
           "label": "图1：封面图 — {描述}",
           "value": "regenerate_1",
           "media": { "type": "image", "url": "{dt_media_upload返回的URL}" }
         },
         {
           "label": "图2：{用途} — {描述}",
           "value": "regenerate_2",
           "media": { "type": "image", "url": "{dt_media_upload返回的URL}" }
         },
         {
           "label": "❌ 放弃配图，保留纯文本版本",
           "value": "skip_images"
         }
       ]
     }]
   }
   ```
   > 返回值为数组，如 `["regenerate_1", "regenerate_3"]` 表示需要重新生成第 1、3 张
3. 根据用户选择继续流程：
   - **包含 "approve_all"** → 进入 Step 7.3（Word 含图片）
   - **包含 "regenerate_N"** → 批量重新调用 `musea-content-visualizer` 生成选中的图片 → 再次 `ask_human` 展示更新后的图片
   - **包含 "skip_images"** → 进入 Step 7.3（Word 不含图片）

---

### Step 7.3：生成 Word 图文版（最终产物）

将文章内容生成 **Word (.docx) 文件**。有配图时将图片嵌入文档，无配图时仅包含排版好的纯文字内容。

**产出文件说明**：

| 文件类型 | 说明 | 是否必出 |
|---------|------|---------|
| `.md` | 纯文本内容（Step 7 已生成） | ✅ 必出 |
| `.docx` | Word 图文版（排版好的文档，有图片则嵌入） | ✅ 必出 |
| 图片文件 | 独立的配图文件（`.png`） | 按需（有配图需求时） |

**生成步骤**：

1. 读取 Step 7 保存的 `.md` 文章文件内容
2. 使用 `{SKILL_ROOT}/scripts/md_to_docx.py` 脚本生成 Word 文档（经过验证的模板脚本，直接调用即可）：
   - **有配图**：`python3 {SKILL_ROOT}/scripts/md_to_docx.py --md <md路径> --docx <docx路径> --images cover:<封面图路径> <关键词1>:<插图1路径> ...`
   - **无配图**：`python3 {SKILL_ROOT}/scripts/md_to_docx.py --md <md路径> --docx <docx路径>`
   - 图片映射的 key 为小标题中的关键词（脚本按关键词匹配插入位置），`cover` 为封面图（插在主标题下方）
3. ⚠️ **如需自行编写脚本而非使用模板**，必须遵守：图片通过 `run.add_picture()` 插入（不要用 `doc.add_picture()`），否则图片不显示
4. 在对话中展示产物清单 + 后续引导，**正常结束回复**（不使用 `ask_human`）：
   ```
   🎉 文章产物已全部生成！

   📄 Markdown 文本版：{md文件路径}
   📄 Word 图文版：{docx文件路径}
   🖼️ 配图文件：{图片路径列表}（如有）

   👉 如需调整 Word 排版，请回复具体修改需求
   👉 如需发布到其他平台（一稿多发），请告诉我目标平台
   👉 如对写作风格有反馈（如 emoji 偏多/语气太正式），请告诉我，我会记住你的偏好

   [当前流程：musea-smart-writer Step 7.3 任务完成]
   ```
5. **用户回复后恢复流程**（用户不回复 = 流程自然结束，无需强制交互）：
   - **调整 Word** → 修改后重新生成 Word → 重新展示上述产物清单和引导选项（循环，直到用户满意或不再回复）
   - **一稿多发** → 回到 Step 5 为新平台适配，完成后再次回到 Step 7.3 生成新平台的产物
   - **风格反馈** → 读取 `{SKILL_ROOT}/profiles/default.yaml` → 追加到 `user_adjustments` → `version` +1，告知用户已记录
   - **不回复** → 流程自然结束 ✅

---

## 风格档案机制

**存储**：`{SKILL_ROOT}/profiles/default.yaml`（模板见 `profiles/default.yaml.template`）

**迭代触发**（权重从高到低）：用户修改后确认 > 用户主动反馈 > 文章确认通过 > 参考文章提取

**合并策略**：`user_adjustments` > 新提取 > 旧规则。风格是"软约束"，平台规范/字数等硬性约束不可被覆盖。

---

## 文章类型速查

| 文章类型 | 模板文件 | 默认框架 | 写作角色 |
|---------|---------|---------|---------|
| 深度教程 | `article-types/deep-tutorial.md` | PAS | Tech Writer |
| 产品测评 | `article-types/product-review.md` | FAB | Tech Writer |
| 清单盘点 | `article-types/listicle.md` | 无特定 | Tech Writer |
| 资讯快评 | `article-types/news-commentary.md` | AIDA | Journalist |
| 品牌推广 | `article-types/brand-promotion.md` | 4P | Copywriter |
| 个人观点 | `article-types/opinion-piece.md` | PAS | Essayist |
| 高流量爆款 | `article-types/viral-explainer.md` | AIDA | Storyteller |
| 资源盘点 | `article-types/resource-roundup.md` | FAB(每项) | Tech Writer |
| 身份逆袭 | `article-types/personal-story.md` | BAB | Storyteller |
| 情感故事 | `article-types/emotional-narrative.md` | BAB | Storyteller |

---

## 写作框架速查

| 框架 | 全称 | 段落结构 | 文件 |
|------|------|---------|------|
| AIDA | Attention→Interest→Desire→Action | 注意→兴趣→欲望→行动 | `writing-frameworks/aida.md` |
| PAS | Problem→Agitate→Solution | 问题→激化→解决 | `writing-frameworks/pas.md` |
| 4P | Picture→Promise→Prove→Push | 描绘→承诺→证明→推动 | `writing-frameworks/four-p.md` |
| FAB | Feature→Advantage→Benefit | 特点→优势→利益 | `writing-frameworks/fab.md` |
| BAB | Before→After→Bridge | 前→后→桥梁 | `writing-frameworks/bab.md` |
| ACCA | Awareness→Comprehension→Conviction→Action | 认知→理解→信念→行动 | `writing-frameworks/acca.md` |

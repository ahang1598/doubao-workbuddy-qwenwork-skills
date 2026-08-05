# 下一步推荐 · 共享算法与 Handoff 模板规范

> **本文件是 27 个 Skill「Handoff 提示」段的共享逻辑定义**。每个 SKILL.md 末尾不再各自手写「下一步推荐」清单，而是按本文档约定生成。
>
> 单一来源：`_shared/skill-graph.json`。本文档 + dashboard-template.html + validate-chain.py 都从那里读。

---

## 一、算法（next-skill ready set）

**输入**：
- `done = { 已写入 spark-output/context/*.json 的 skill ID 集合 }`（去 `.json` 后缀；首次跑则 `done = { 本 skill }`）
- `skills = _shared/skill-graph.json` 的 `skills[]`

**Ready 判定**（每个候选 `s` 满足，**v0.5.8 修正语义**）：

```
s.id ∉ done                                    # 自己还没跑
AND s.required.every(r => r ∈ done)            # 显式硬依赖全在 done 中
```

**字段语义**：
- `required: []`（空数组）= **明确声明无硬依赖**，恒满足判定，下游软依赖跑不跑都能 ready
- `required: [a, b]` = a 和 b 都必须在 done 中
- `reads` 字段保留为**信息字段**（dashboard 渲染依赖线 + fan-out 排序权重），**不参与 ready 判定**

**历史修正**：v0.5.5 ~ v0.5.7 算法用三元式 `required.length > 0 ? required.every : reads.every`，导致 `required: []` 被回落到 `reads` 严格匹配——Brief / 8 个 entry-level 永远等不到所有 reads 跑完，`Frame.next_hint.preferred = ['brief']` 永远无法触发。v0.5.8 `dist/test-next-skill.py` 自测发现并修正为单条 required.every。

**排序**（决定推荐顺序前 5 名）：

1. **当前 Skill 的 `next_hint.preferred` 内的 Skill 排最前**（保留语境化优先建议）
2. **当前 Skill 的 `next_hint.alternatives` 内的 Skill 次之**
3. **同阶段 / 下一阶段 Skill 优先**（`s.phase >= current.phase`，且 `s.phase - current.phase` 小的靠前）
4. **`anchor: true` 的 Skill 加权**（Brief / Journey / Pitch / PRD / Retro 这 5 个核心交付物自动靠前）
5. **fan-out 高的 Skill 优先**（被更多下游引用的 Skill）

**输出**：候选 Skill ID 数组（取前 5 个；不足 5 个则取全部；为空则视为终端节点）。

---

## 二、Handoff 三层结构模板（27 Skill 统一）

每个 Skill 在「更新链路面板」之后、Skill 结束之前，必须以下列三层结构输出（**独立段落**，不与其他内容混合）：

```
✅ {SkillName} 已完成{可选: 1-2 项关键产物简述，如 "5 段 IA + 23 个页面节点"}。

📊 下一步可走：`/{a}` · `/{b}` · `/{c}` · `/{d}` · `/{e}`

{emoji} **本 Skill 后通常优先 `/{preferred[0]}`**（{reason}）；想 {alternatives[0].reason} 走 `/{alternatives[0].id}`；想 {alternatives[1].reason} 走 `/{alternatives[1].id}`。

说"进入 {a}" / "进入 {b}" / "进入 {c}" 选下一步。
```

### 各层职责

| 层 | 内容 | 来源 |
|---|---|---|
| **第 1 行** | `✅ {Skill} 已完成` + 关键产物简述（≤ 30 字） | 各 Skill 自定，但格式固定 |
| **第 2 行** | `📊 下一步可走：` + 算法算出的前 5 候选 Skill ID | **完全自动**（来自上述算法） |
| **第 3 段** | `{emoji} **本 Skill 后通常优先 /{preferred[0]}**` + 1-2 句理由 + 1-3 条 alternative | **来自 skill-graph.json `next_hint`**（语境化优先建议 + 备选） |
| **第 4 行** | `说"进入 X" / "进入 Y" / "进入 Z"` | 自动复制第 2 行的前 3 个 ID |

### 终端节点（`preferred = []`）

如 Retro，候选可能为空。此时第 2 行改为 `📊 下一步可走：（已到链路终端，无后续 Skill）`，第 3 段直接输出 `reason`（不带 alternatives）。

---

## 三、规则与红线

- ✅ **禁止手写候选清单**：第 2 行必须由算法生成。Skill 完成时若发现实际 ready set 与 `next_hint` 不符（如 `preferred` 中的 Skill 不在 ready set 内），以**算法结果为准**，第 3 段降级为「本 Skill 完成。下一步参见上面候选清单。」
- ✅ **第 3 段允许 1-2 句点拨**：保留 `next_hint.reason` 的语境化建议，不要硬干掉。
- ✅ **首行简述限 30 字**：避免 handoff 变长篇大论，关键产物挑 1-2 项即可。
- ❌ **禁止把候选清单按场景再分类**（不要再写「文档类 / 视觉类 / 决策类」三段）——分类已折叠进 `next_hint`。
- ❌ **禁止与「更新链路面板」段合并**：链路面板独立段、Handoff 独立段，中间空一行。
- ❌ **禁止漏第 2 行**：即使候选只有 1 个也要写出来。

---

## 四、示例：Brief 完成时的实际输出

`done = { brief }`，按算法 ready set = {journey, stories, sitemap, pitch, frame? no（done）...} → 经排序前 5 = `[journey, stories, sitemap, pitch, flow-web]`。

输出：

```
✅ Brief 已完成，上下文已写入 spark-output/context/brief.json。

📊 下一步可走：`/journey` · `/stories` · `/sitemap` · `/pitch` · `/flow-web`

🎨 **本 Skill 后通常优先 `/journey`**（用户视角可视化，含情感曲线 + dropout-risk 标注，把抽象策略变成可视的体验断点）；想做工程拆解走 `/stories`；想先对齐决策者走 `/pitch`；想直接搭 IA 走 `/sitemap`。

说"进入 journey" / "进入 stories" / "进入 pitch" 选下一步。
```

---

## 五、SKILL.md 各文件如何引用本文档

每个 SKILL.md 末尾「Handoff 提示」段不再手写完整模板，而是写：

```markdown
### Handoff 提示（**完成本 Skill 后必输出**）

> 按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出，前 5 候选由算法从 `_shared/skill-graph.json` 计算，本 Skill 的 `next_hint` 已登记在 skill-graph.json 中（preferred / reason / alternatives / emoji）。

**首行模板**：`✅ {本 Skill 中文名} 已完成，{关键产物：1-2 项简述}。`

（其余三层由 AI 按算法 + skill-graph.json 实时生成，禁止在 SKILL.md 内硬编码候选清单。）
```

这样：
- **依赖图改了** → 改 skill-graph.json 一处即可
- **语境化建议改了** → 改 skill-graph.json 的 `next_hint` 即可
- **24 个 SKILL.md 不再各自维护候选清单**，避免 Bug 3 那种「Sitemap 完成后才推荐 Journey」的顺序错乱

---

## 六、对 v0.5.4 Bug 3 的解药

Bug 3 现场：用户跑完 Brief → Sitemap，对话中 AI 在 Sitemap 完成后才推荐 Journey。

**原因**：Brief 旧 handoff 把 Stories / Journey / Sitemap / Pitch 并列散在 3 个分类段落，AI 没有强势点拨。

**本文档的解**：
- Brief 在 skill-graph.json 的 `next_hint.preferred = ["journey"]`，**强制 AI 在 Brief 完成后第 3 段第一句必说「通常优先 /journey」**
- 不再让分类标签淡化指引强度
- alternatives 列 stories / pitch / sitemap，**让用户知道可走但不喧宾夺主**

---

## 七、Compaction 容错：`_session-state.json` 协议

> **问题**：Conversation Compaction 会清除会话中的 marker（渠道 1 失效），若同时路径记忆丢失（渠道 2 的路径拼不出来），AI 会陷入"找不到 context"的死循环。

### 写入时机

每个 Skill 在**下游输出 Step 1（写盘 `<skill>.json`）之后**，同步写入或更新 `spark-output/context/_session-state.json`：

```json
{
  "current_skill": "<刚完成的 skill id>",
  "workspace_path": "<当前 pwd 的绝对路径>",
  "original_workspace_path": "<最初的项目根目录（如 Flow Web Phase A 创建新目录前的 pwd）>",
  "completed_skills": ["brief", "sitemap", "stories", "flow-web"],
  "current_phase": "<当前执行阶段，如 Phase B / 完成>",
  "updated_at": "<ISO8601>"
}
```

**更新规则**：

- `completed_skills`：读取已有文件的数组 → 追加当前 skill id（去重）
- `workspace_path`：始终写当前 `pwd`
- `original_workspace_path`：仅在文件不存在时写入，已有则保留原值

### 读取时机

每个 Skill 的 Step 0 上游读取应在**渠道 1（会话 marker）和渠道 2（`spark-output/context/*.json`）都失败后**，尝试读取 `_session-state.json`：

1. 从 `workspace_path` 和 `original_workspace_path` 获取两个候选路径
2. 分别在这两个路径下尝试读取 `spark-output/context/*.json`
3. 读取成功则恢复上下文，告知用户："⚠️ 检测到 Compaction 后的上下文恢复——从 `_session-state.json` 恢复了 {completed_skills.length} 个已完成 Skill 的上下文。"

### 红线

- ❌ `_session-state.json` 不替代 `<skill>.json`——它只是路径索引，不存储 context 正文
- ❌ 不因 `_session-state.json` 写入失败而阻断 Skill 完成——写入失败静默跳过

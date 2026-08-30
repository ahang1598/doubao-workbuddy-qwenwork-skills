# 知识管家 · 排错手册

> 本文档记录知识管家 skill 运行时的典型故障和解决方案。
> 按故障现象查找，而不是按原因查找。

---

## 现象 1：AI 说找不到"知识管家" skill / 走了 `dingtalk-workspace`

### 识别方法

- AI 在对话里说"我没找到知识管家 skill"或"使用通用工具帮你"
- 对话日志里出现：`execute_skill_id=dingtalk-workspace`（而不是 `knowledge-butler`）
- AI 开始直接敲 `dws minutes list` 命令

### 可能原因（按常见度排序）

#### 1.1 钉钉悟空的 skill 索引没刷新（最常见）

**症状**：刚跑完 `setup.sh`，文件已经在 `~/.real/users/user-*/.skills/*/SKILL.md`，但 AI 仍然搜不到。

**解决**：
1. **完全退出钉钉**（右键任务栏图标 → 退出，不是关闭窗口）
2. 重新打开钉钉
3. 进入悟空任务，输入"用知识管家 skill"——AI 能识别即索引已刷新

**验证命令**（mac）：
```bash
ls ~/Library/Application\ Support/dingtalk-rewind-server/users/user-*/\.skills/*/SKILL.md 2>/dev/null | head
# 或直接看文件内容里有没有 name: knowledge-butler
grep -l "name: knowledge-butler" ~/.real/users/user-*/.skills/*/SKILL.md 2>/dev/null
```

#### 1.2 触发词不在 frontmatter 里

**症状**：用户说的话和 frontmatter 的触发词不匹配。例如用户说"获取听记的内容"但 skill 只识别"整理听记"。

**解决**：编辑 SKILL.md frontmatter 的 description 区，加入用户的新说法，重跑 setup.sh。

#### 1.3 Skill 注册到了错的 user

**症状**：钉钉登录了多个账号，skill 装到了一个账号下，但任务在另一个账号执行。

**解决**：
```bash
# 找出当前活跃 user
ls -lat ~/.real/users/user-*/sessions/ | head
# 确认 .skills 目录里有 knowledge-butler
ls ~/.real/users/<active-user>/.skills/*/SKILL.md | xargs grep -l "knowledge-butler"
```

---

## 现象 2：AI 绕过脚本直接调 `dws minutes`

### 识别方法

- 钉钉悟空任务日志里出现 `command=dws minutes list` / `command=dws minutes get transcription`
- 没有出现 `command=.venv/bin/python scripts/wukong_minutes_to_md.py` 这一行

### 原因

Skill 没被正确加载（见现象 1），AI 看不到 SKILL.md 的禁令 0，于是去摸通用 DWS CLI。

### 解决

1. 先按现象 1 修复 skill 发现
2. **v1.2 起**，`batch` 必须带 `--session-id`——即使 AI 绕过脚本直接调 `dws`，也无法完成整理（没落地）。用户可以通过以下命令**机械验证**本次任务是否走了脚本：
   ```bash
   # 最近的整理文件如果 generator 字段存在 = 走了脚本
   # 在 workspace 根下（也就是 $PWD，悟空 project 目录）跑：
   grep -l "^generator: wukong_minutes_to_md.py" 1-素材/录音/*.md | wc -l
   ```

---

## 现象 3：AI 偷偷拉了原文但没告诉用户

### 识别方法

- 钉钉悟空任务日志里有 `dws minutes get transcription --uuid ...` 的调用
- 但用户收到的对话里只看到"请确认怎么处理"之类的问句
- 任务耗时显著长于列表操作（> 1 分钟），但输出看似只是列表

### 原因

违反了 SKILL.md 的「执行态透明度规则」——AI 静默调用工具，不向用户播报。

### 解决

- v1.2 SKILL.md 已加入透明度禁令（`禁止静默执行超过 30 秒`），新安装后 AI 会被指令约束
- 临时缓解：用户明确说"每调一个工具都告诉我"，AI 会 fallback 到有声执行

---

## 现象 4：Preflight 报 "session 未找到"

### 识别方法

脚本输出：
```
❌ session 未找到。请先运行 preflight 生成 session
```

### 原因

- session TTL 5 分钟，过期自动失效
- session 文件被系统清 `~/.cache`

### 解决

重新跑 `preflight` 拿新 session_id。

---

## 真实故障案例

### 2026-04-24 09:36 · skill 发现失败 + 脚本绕过（v1.2 的动因）

- **症状**：用户输入"获取听记的内容"，AI 耗时 2分38秒只返回 5 条列表
- **根因**：`search_skills` 两次返回空，AI fallback 到 `dingtalk-workspace`，直接调 `dws minutes list` 共 10 次，并偷偷拉了 4 条转写原文但没告诉用户
- **修复**：
  - SKILL.md 加「获取听记的内容」等触发词
  - Fix 2（本文件）记录"重启钉钉刷索引"FAQ
  - 脚本加 `preflight --session-id` 硬约束（v1.2）
  - SKILL.md 加「执行态透明度规则」
- **日志位置**：`~/Library/Application Support/dingtalk-rewind-server/logs/app/application.2026-04-24.log` conversation `b9e85fef...1b57`

### 2026-04-23 · AI 用 `get summary` 代替 `get transcription`

- **症状**：整理文件内容是 AI 摘要，不是原文逐字稿
- **根因**：AI 图省事用 `dws minutes get summary`（已被 AI 压缩过）代替 `get transcription`
- **修复**：SKILL.md 禁令 2 明文禁止 summary 代替 transcription；Phase 7 水印验证抓漏网之鱼

---

## 2026-04-25 · Karpathy 三层架构升级后的常见问题

### Fix 9：「为什么我的概念都跑到专题里去了？」

**症状**：升级到新版后，发现原来的 `2-AI知识库/概念/` 目录消失了，里面的方法论页面（如"复利效应"、"飞轮"）都跑到了 `2-AI知识库/专题/` 下。

**这不是 bug，是有意改动**。原因：

- 老版本把"概念"和"专题"分两个目录——但普通用户分不清"复利效应"该建在哪边
- 新版用 frontmatter `entity_kind` 字段区分类型：
  - `entity_kind: person/org/project/product/topic` —— 具体对象
  - `entity_kind: method` —— **方法论 / 抽象概念（取代旧概念页）**
- 用户在悟空 UI 看到的是一个扁平专题列表，不需要懂 entity_kind 的细分
- 双链零迁移成本：`[[复利效应]]` 不论文件在 `概念/` 还是 `专题/` 都成立

**确认升级生效的方法**：
```bash
# 应该看到新文件在专题/下
ls $HOME/Desktop/知识管家/2-AI知识库/专题/

# 应该看到旧概念目录有 .archived 标记（1 周后下次升级清空）
ls -la $HOME/Desktop/知识管家/2-AI知识库/概念/.archived 2>/dev/null
```

如果旧目录还在但内容已迁走，那是正常的——保留 1 周作为回滚窗口。

### Fix 10：「我改了规则手册.md，AI 没按我说的做」

**症状**：你在 `~/Desktop/知识管家/规则手册.md` 写了"摘要长度 ≤100 字"，但 AI 跑投喂任务后摘要还是 200 字+。

**可能的原因**（按优先级排）：

1. **AI 没读取**：Phase -1 环境自检时 AI 必须读规则手册，但旧 SKILL.md 没这步——**重启钉钉刷新 skill 索引**让新规则生效。
2. **规则写得太模糊**：AI 解析不到"≤100 字"这个阈值。改成更明确："摘要长度严格不超过 100 字，超过的截断"。
3. **AI 在硬约束和你的偏好之间冲突**：SKILL.md 内置的"摘要必含核心观点 3 条"如果你的"≤100 字"装不下 3 条，AI 会优先满足硬约束。这种情况告诉 AI："允许只列 1-2 条核心观点"。

**验证 AI 读到了规则手册**：
```bash
# 看悟空日志最新一次任务的环境自检输出
tail -100 ~/Library/Application\ Support/dingtalk-rewind-server/logs/app/application.$(date +%Y-%m-%d).log \
    | grep "已加载规则手册"
```
应该看到 `📖 已加载规则手册：/Users/xxx/Desktop/知识管家/规则手册.md`。没看到 = AI 跳过了 Phase -1 步骤 4。

### Fix 11：「洞察文件越来越多怎么办？」

**症状**：跑了几次批量整理后，`2-AI知识库/洞察/` 下积累了几十篇 `kind: synthesis` 的综合洞察，看着乱。

**预期行为**：批量任务（Workflow 5/6）会在反链阈值（≥3 反链 + ≥2 专题）触发时自动起草综合洞察——这是 Karpathy "kept current" 持续编译机制的产物。

**清理方法**：

1. **任务完成时主动删**：每次批量任务完成回执的"跨听记发现"段会列出新建洞察清单，不需要的回 `删 1` / `删 1、3、5` —— AI 即时删除
2. **事后批量清**：
   - 用 Finder / 悟空 UI 直接进 `2-AI知识库/洞察/` 删不要的文件
   - 跑 Workflow 3（说"整理一下"），AI 会扫孤儿洞察 + 没反链的洞察，列出建议清理清单
3. **调高触发阈值**：在 `规则手册.md` 加："洞察生成偏好：阈值 ≥5 反链 + ≥3 专题（更严格）"——AI 下次任务遵守

**为什么不用 status: draft 状态机**：那是早期方案，过度复杂（参考 gbrain 项目设计）——**创建即真实，用户主动删**比"半成品标记+定期清理"心智负担更轻。

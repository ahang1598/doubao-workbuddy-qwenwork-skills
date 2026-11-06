---
name: minimax-music-gen-win
description: >
  基于 MiniMax Music3.0 的音乐生成技能。当用户想要生成音乐、歌曲、音频时使用。
  触发词包括："生成歌曲"、"写首歌"、"创作音乐"、"来一首歌"、"帮我做首歌"、
  "生成歌词"、"写歌词" 等任何与音乐创作相关的请求。
  也适用于用户已有歌词希望将其转化为歌曲，或描述场景/情绪想要背景音乐的场景。
  即使是随意的请求如 "给我来点音乐" 或 "I want a chill beat" 也应触发此技能。
  不用于：播放已有音乐文件、音乐理论问题、不涉及生成的音乐推荐。
---

# ⚠️ 重要：确认机制

**音乐生成需消耗 20 AI 点，每次生成必须获得用户明确确认。**

- 用户未明确确认→ **禁止生成**
- 无论之前是否生成过，**每次生成前都必须重新确认**
- 确认状态不保留，每次生成为独立事件
- 若存在`ask_user`工具，先以普通聊天文本完整展示要确认的内容，再调用 `ask_user`，每次确认都必须调用此工具；若不存在`ask_user`工具，直接文本展示和询问
---

# MiniMax 音乐生成技能

使用 MiniMax Music3.0 生成歌曲（人声或器乐）。支持两种创建模式：
**基础模式**（一句话输入，输出歌曲）和**高级控制模式**（编辑歌词、优化提示词、生成前规划）。

## 产物存储路径

生成的文件用户未指定时使用默认路径，指定时按指定路径输出

## 产物命名规则

- 音乐文件：`YYYYMMDD_HHMMSS_SSS_XX_generated.mp3`
- 歌词文件：`YYYYMMDD_HHMMSS_SSS_XX_lyrics.json`

---

## 脚本说明

### 1. 歌词生成脚本

`scripts/generate_lyrics.py` — 根据提示词生成完整歌词

```bash
# 生成完整歌曲歌词，指定输出路径
python3 scripts/generate_lyrics.py --prompt "Indie folk, melancholic, introspective, longing" --output-path /path/to/output

# 编辑/续写已有歌词
python3 scripts/generate_lyrics.py --prompt "make it more upbeat" --mode edit --lyrics "[Verse] 原有歌词..."

# 从 JSON 文件读取现有歌词进行编辑/续写
python3 scripts/generate_lyrics.py --prompt "make it more upbeat" --mode edit --lyrics /path/to/lyrics.json
```

### 2. 音乐生成脚本

`scripts/generate_music.py` — 根据提示词和歌词生成音乐

⚠️ 音乐生成耗时较长，exec 调用时 timeout 设为 600（10分钟）

```bash
# 使用已有歌词生成音乐（直接传入歌词文本）
python3 scripts/generate_music.py --prompt "Mandopop, Festive, Upbeat" --lyrics "[Verse] 歌词内容..."

# 使用 JSON 歌词文件生成音乐
python3 scripts/generate_music.py --prompt "Pop, Romantic" --lyrics /path/to/lyrics.json

# 自动生成歌词并生成音乐
python3 scripts/generate_music.py --prompt "Electronic, Ambient" --lyrics-optimizer

# 生成纯音乐（无人声），指定输出路径
python3 scripts/generate_music.py --prompt "Electronic, Ambient" --instrumental --output-path /path/to/output
```

---

## 工作流程

### 第0步：检测用户意图与语言

1. **歌曲类别**：人声（人声音乐）、器乐（纯音乐）
2. **创作模式偏好**：他们是否提供了详细要求（→ 高级）或随意的一句话（→ 基础）？
3. **语言检测**：检测用户输入的语言
   - 🇨🇳 **中文输入** → 生成**中文提示词**，歌词为**中文**
   - 🇺🇸 **英文输入** → 生成**英文提示词**，歌词为**英文**
   - 🌐 **其他语言** → **需向用户强调确认**："检测到您使用非中英语言，将使用英文生成提示词，是否继续？"

如果不确定，使用此决策树提问：

```
Q1：你想要哪种类型？
  - 🎤 人声音乐（有歌词演唱）
  - 🎵 纯音乐（无人声）

Q2: 你想要哪种创作模式？
  - ⚡ 基础版 — 一句话描述，自动搞定
  - 🎛️ 高级模式 — 自己调歌词、prompt、风格
```

如果用户给出清晰的一句话如"帮我生成一首悲伤的钢琴曲"，跳过问题 —— 推断器乐 + 基础模式并继续。

---

### 第1步：基础模式

**目标**：用户提供简短描述 → 自动生成歌词 → 生成音乐

1. **将描述扩展为提示词（语言匹配规则）**：

   **🇨🇳 中文输入（如"下班快乐的歌"）**：
   - 用**中文**扩展提示词，例如：
   ```
   一首欢快轻快的华语流行歌曲，庆祝下班时刻的自由，
   节奏轻快充满活力，描述离开办公室、拥抱个人时间的喜悦，
   傍晚城市灯光的氛围，轻松愉悦。
   ```

   **🇺🇸 英文输入（如"a happy after work song"）**：
   - 用**英文**扩展提示词，例如：
   ```
   An upbeat and cheerful Mandopop song celebrating the end of a workday,
   with energetic rhythms and optimistic melodies,
   capturing the joy of leaving the office and embracing personal time,
   evening city lights vibe.
   ```

   **🌐 其他语言**：
   - **必须向用户强调**："检测到非中英输入，将使用英文生成提示词和歌词，是否继续？"
   - 用户确认后继续，或询问是否需要翻译

2. **⚠️ 必须等待用户明确确认后才可生成音乐**：

   向用户展示预览并等待确认：
   ```
   🎵 **即将为你生成**：

   **类    型**：人声音乐 / 纯音乐
   **语    言**：🇨🇳 中文 / 🇺🇸 英文
   **Prompt**：[根据输入语言生成的提示词]
   **歌    词**：自动生成（中文/英文）
   **AI 点数**：将扣除 20 点

   ⚠️ 如需生成，请确认。
   ```

   **重要规则**：
   - 必须等待用户回复，**不可主动调用生成脚本**
   - 只有收到明确的确认才可执行生成
   - 收到确认后才继续下一步；否则停止并告知用户已取消

3. **收到确认后，执行生成**

   **歌词语言规则**：用户输入为中文 → 生成**中文歌词**，输入英文 → 生成**英文歌词**。

   自动生成歌词（带人声）：
   ```bash
   python3 scripts/generate_music.py --prompt "<提示词>" --lyrics-optimizer
   ```

   或者生成纯音乐（无人声）：
   ```bash
   python3 scripts/generate_music.py --prompt "<提示词>" --instrumental
   ```

---

### 第2步：高级模式

**目标**：用户对每个参数有完全控制权

1. **歌词阶段**
   - 如果用户提供了歌词：显示带分段标记的格式化歌词，请求编辑。
   - 用户有主题但无歌词：用 generate_lyrics.py 生成，支持迭代修改
   - 支持 edit 模式局部修改："第二段副歌改一下"

2. **提示词阶段**
   - 根据歌词情绪生成推荐提示词
   - 以可编辑标签形式呈现，用户可增删改

3. **高级规划**（可选，提供但不强制）：
   - 歌曲结构：verse-chorus-verse-chorus-bridge-chorus 或自定义
   - BPM 建议（编码为提示词中的速度描述符）
   - 参考风格："类似某种风格" → 映射到提示词标签
   - 人声特性描述

4. **最终确认**：

   向用户展示预览并等待确认：
   ```
   🎵 **即将为你生成**：

   **类    型**：人声音乐 / 纯音乐
   **语    言**：🇨🇳 中文 / 🇺🇸 英文
   **Prompt**：[根据输入语言生成的提示词]
   **歌    词**：[展示最终歌词]
   **AI 点数**：将扣除 20 点

   ⚠️ 如需生成，请明确回复「确认」。
   ```

   **重要规则**：
   - 必须等待用户回复，**不可主动调用生成脚本**
   - 只有收到明确确认才可执行生成
   - 收到确认后才继续下一步；否则停止并告知用户已取消

   **歌词语言规则**：用户输入为中文 → 生成**中文歌词**，输入英文 → 生成**英文歌词**。

   执行生成：
   ```bash
   python3 scripts/generate_music.py --prompt "<最终提示词>" --lyrics "/path/to/final_lyrics.json"
   ```

---

### 第3步： 裁切音乐时长

若用户在要求中指定了音乐时长，自主编写裁切脚本用ffmpeg按用户要求时长对生成的音乐进行裁切。

### 第4步： 结果与发送

生成完成后告知用户并将音乐文件发送给用户：

必须调用 `send_file_to_user(abs_file_path_list=["<音乐文件绝对路径>"])` 发送最终音乐文件，不得只返回 URL 或本地路径文本。用户指定时长时只发送裁切后的文件；未指定时发送完整音乐。

```
🎵 音乐已生成
📁 文件路径： 默认输出路径or用户指定路径
```

---

## 歌词格式

使用段落标记结构化歌词：
- `[Intro]` — 前奏
- `[Verse]` — 主歌
- `[Chorus]` — 副歌
- `[Bridge]` — 桥段
- `[Outro]` — 尾奏

示例：
```
[Verse]
第一行歌词
第二行歌词

[Chorus]
副歌部分
重复演唱的内容
```

---

## 提示词写作指南

**基本结构**：
```
一首 [情绪/情感] [BPM 可选] [流派+子流派] 歌曲.
[人声描述].
[叙事/主题].
[氛围/场景].
[关键乐器和制作元素].
```

**关键要点**：
1. **写完整句子** — "一首忧郁的节奏布鲁斯歌曲，关于……" 而非 "节奏布鲁斯、悲伤、慢速、钢琴"
2. **具体生动** — "在时空中打捞记忆碎片" 比 "悲伤回忆" 更有感染力

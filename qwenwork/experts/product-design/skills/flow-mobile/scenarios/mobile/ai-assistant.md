# Scenario: Mobile AI Assistant（移动端 AI 助手）

> **研究来源**：基于对 Kin、Google Gemini、Grok、Chance AI、Raycast、Pi、Dot、Rewind 等 8 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以自然语言对话为核心交互方式的移动端 AI 助手应用，用户通过文字或语音与 AI 进行多轮对话，获取问答、内容生成、分析等服务，历史对话可保存和检索。

**Canonical Examples**: ChatGPT iOS、Claude iOS、Google Gemini iOS

**Not this scenario if**:
- 以特定垂直任务嵌入 AI（如 AI 图片生成工具、AI 写作插件），AI 是辅助功能而非核心体验
- 客服/支持机器人（嵌在其他 App 内的 Bot，如 Intercom Chat）
- 以语音助手形式工作（如 Siri、Alexa，无可见对话 UI）
- 主要在 Web 端使用（改用 web/ai-product）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 问答用户（查信息/解释概念）/ 创作助手用户（写作/改写）/ 效率工具用户（总结/翻译）|
| **核心目标** | 快速得到高质量答案 / 完成某项具体任务（写一段 bio / 翻译邮件） |
| **心智模型** | 与真人对话的感受：期待流式输出（而非等待）、期待即时反应、可随时打断 |
| **使用频率** | 中-高频（多次/天）；每次使用时间较短（1-10 分钟），移动场景为主（通勤/碎片时间）|
| **决策模式** | 任务驱动型：有明确问题需要解答；偶有探索型（想看 AI 怎么回答）|
| **容错期望** | 可以重新生成（Regenerate）/ 提前停止（Stop）/ 复制内容 / 分享；误删对话通常不可恢复（需 Dialog 确认）|

---

## IA Template

**导航模式**: 两种主流模式（AI 助手类 App 差异较大）

**模式 A：侧边抽屉（主流）**
```
主视图: 当前对话界面
左侧 Drawer: 历史对话列表（侧滑手势 / 左上角 ☰ 按钮打开）
底部 Toolbar: 模型选择 / 新建对话 / 设置
```

**模式 B：Tab Bar（Gemini / 部分 AI 应用）**
```
Tab 1: 主页 / Home   — 欢迎界面 + 快速开始提示
Tab 2: 对话 / Chat   — 对话界面
Tab 3: 历史 / Library — 过往对话列表
Tab 4: 我的 / Profile — 账户 + 模型设置
```

**选择建议**: 功能单一（纯聊天）→ 模式 A；功能多元（聊天+工具+历史）→ 模式 B

**页面层级**: 2-3 级
```
L1: 对话界面（Chat View）
L2: 历史对话列表（Conversations List）→ 某条历史对话（reopen）
L3: 笔记/保存内容 / 设置页（部分产品）
```

**权限流结构**（较轻量）:
```
Microphone（语音输入）:
  → 首次点击麦克风 → 自定义说明页 → 浏览器/系统麦克风权限弹窗
  
Camera（多模态图片附件）:
  → 首次点击附件 → 系统/浏览器 Camera/Photos 权限

Speech Recognition（STT）:
  → 与 Microphone 同步请求（通常连续触发）
  
Notifications（对话完成 / 提醒）:
  → onboarding 完成后单独询问（非强制）
```

**数据密度**: 低（单列对话气泡；历史列表简单行）
- 核心视图：滚动容器（`ScrollView` / `FlatList`）+ 消息气泡列表（自动滚到底部）
- 辅助视图：`List`（历史对话记录）
- 特殊元素：Markdown 渲染（代码块、粗体、列表）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 历史对话列表 | Stack Push 或 Bottom Sheet |
| 模型选择 | Bottom Sheet（medium 高度）或 Action Sheet |
| 对话操作菜单（复制/分享/重新生成）| 长按气泡 Context Menu |
| 删除对话确认 | Dialog |
| 附件来源选择（相机/相册/文件）| Action Sheet |

**导航骨架图（ASCII，模式 A）**:
```
┌────────────────────────────────────┐
│  Status Bar                         │
├────────────────────────────────────┤
│ ☰ 历史  [New Chat 模型名 ▾]  [···] │  ← Toolbar
├────────────────────────────────────┤
│                                    │
│  🤖 你好！我是 AI 助手，有什么我     │
│     可以帮助你的？                  │  ← AI 气泡（左对齐）
│                                    │
│  今天怎么用 Python 处理 CSV？ [User] │  ← 用户气泡（右对齐）
│                                    │
│  🤖 [流式输出...光标闪烁]           │  ← 生成中
│                                    │
│    [▋ 停止生成]                     │  ← 生成中 Stop Button
│                                    │
├────────────────────────────────────┤
│ [📎] [      输入消息...     ] [🎤🚀]│  ← Composer
└────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **Composer 必须锚定在视口底部，不可内嵌入页面流** — 移动端 AI 助手的 Composer 必须固定在屏幕底部（键盘弹起时随之上移），而非随消息列表内容滚动——H5 可用 `position: fixed` + `env(safe-area-inset-bottom)` 处理底部安全区；React Native 可用 `KeyboardAvoidingView` + SafeAreaView。所有 AI 助手（Grok、Gemini、ChatGPT）均采用此架构；Composer 的输入框必须支持自动扩展高度（H5：`textarea` + auto-resize；RN：`TextInput` multiline + `onContentSizeChange`），最多展示 6-8 行后出现内部滚动。

2. **流式输出必须配合自动追踪底部机制，不可依赖容器默认行为** — 消息气泡列表追加新内容时，需要自动将视图滚到最新消息位置。H5 使用 `scrollIntoView` 或监听消息数量变化后调用 `scrollTo`；RN 使用 `FlatList` 的 `scrollToEnd`，让用户始终看到最新生成的文字——若不实现此机制，用户需手动向下滚动跟上流式输出，严重破坏「与真人对话」的沉浸感。发送按钮在生成过程中必须变为 Stop Button，完成后恢复为发送（Grok flow 6093 + Rewind 截图均确认）。

3. **麦克风权限必须先展示自定义说明页，移动端权限拒绝后恢复路径复杂** — 移动端（无论 H5 或 RN）麦克风权限一旦被拒绝，用户需要手动进入系统设置开启，恢复成本极高。因此首次请求前必须展示自定义说明页（「语音输入用于实时转录，不存储原始音频」），用价值说服用户授权后再触发系统弹窗——说明页是提升移动端麦克风授权率的关键手段（Kin flow 5431 / Gemini flow 3207 均有完整实现）。

4. **历史对话列表必须用「今天/本周/更早」分组 + 左滑删除（含二次确认）** — AI 助手每日产生 5-10 条新对话，无分组的平铺时间序列在 30 条后完全无法使用。分组（「今天/本周/更早」）帮助用户快速定位历史话题；左滑删除（附 Dialog 二次确认）是移动端原生交互共识，不应替换为 Web 风格的 Dialog 或全页确认——对话一旦删除不可恢复，二次确认是必要保护。

5. **纯聊天类 AI 助手应使用 Drawer 模式而非 Tab Bar，最大化对话区域** — AI 助手的绝对主视图是对话气泡 + Composer，历史对话列表是辅助视图。Tab Bar（底部固定高度）会持续挤压对话展示高度，在历史列表仅为「偶尔翻查」的场景中得不偿失。侧边 Drawer（左上角 ☰ 按钮或左滑手势打开）让对话视图占据全屏宽高，符合 ChatGPT iOS / Claude iOS / Grok 的架构选择；Tab Bar 模式（如 Gemini）适合功能多元（聊天+工具+图片生成）的产品，纯聊天场景下 Drawer 是行业共识。

---

## Canonical Flows

> 以下 flow 基于 8 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Start New Chat & Receive Streaming Response（新建对话 + 流式输出）

**在此场景的特殊性**: AI 助手的对话界面与普通 DM 的最大区别是**流式输出**（Streaming）——AI 回答不是一次性呈现，而是像打字机一样逐字显示。发送按钮在生成过程中变为 Stop 按钮（Grok flow 6093 + Rewind 截图均确认），让用户可以随时打断。「快速开始提示」（Suggested Prompts）是 AI 助手特有的空状态 UI，帮助用户找到切入点（Gemini、Kin 均有）——这与普通 IM 的空状态（「暂无消息」）截然不同。Markdown 渲染（粗体/代码块/列表）是 AI 回复的特有需求，在普通 DM 中不需要。

**行业共识**：Grok（flow 6093）、Gemini（flow 3207）、Chance AI（flow 7359）均确认：发送后按钮变 Stop → 流式文字出现 → 完成后显示 Response Actions。

**Entry**: App 主页 / 点击「新建对话」

```
Screen 1: Chat Home（空状态 / 欢迎页）
  主操作: 输入第一条消息 / 点击 Suggested Prompt
  关键组件:
    - Text（欢迎标题 + 副标题：「有什么我可以帮你的？」）
    - [可选] Suggested Prompt Chips（3-6 个快速入门提示，横向可滚动）:
        如「翻译一段文字」「帮我写一封邮件」「解释一个概念」
    - 底部 Composer（固定在视口底部）:
        Button（📎 附件）
        TextArea（"输入消息..."，多行自动扩展）
        Button（🎤 语音）
        Button（发送 ↑，disabled 状态直至有输入）
  → 输入文字: 发送按钮从 disabled → 激活
  → 点击 Suggested Prompt: 自动填入输入框
  → 点击「发送」: Screen 2

Screen 2: 对话进行中（Streaming）
  主操作: 等待 AI 响应 / 随时停止
  关键组件:
    - FlatList / ScrollView（消息气泡列表，新消息自动 scrollToEnd）
    - 消息气泡列表:
        用户气泡（右侧，accent color，圆角矩形）
        AI 气泡（左侧，灰色/白色，左上角 AI Avatar）
        生成中 AI 气泡: 打字机效果文字 + 末尾光标 `▋` 闪烁
    - 生成状态 Composer:
        发送按钮 → 变为 Stop Button（⏹ 方形图标）
        输入框: disabled（生成中禁止输入）
    - [可选] Thinking 状态: 小圆点 ···（三个跳动点，Loading 前置状态）
  → AI 流式输出中: 文字逐字追加
  → 点击 Stop: 流式输出停止，响应截断，Stop Button 恢复为发送
  → 生成完成: 进入 Screen 3

Screen 3: 响应完成（Response Complete）
  主操作: 阅读响应 / 追加问题 / 使用操作
  关键组件:
    - 完整 AI 响应（支持 Markdown 渲染: 粗体/代码块/有序列表/链接）
    - Response Actions（AI 气泡下方小图标栏）:
        Button(复制)
        Button(分享)
        Button(👍)（Thumbs Up）
        Button(👎)（Thumbs Down）
        [可选] Button(重新生成)
    - [可选] Follow-up Suggestion Chips（AI 推荐的追问问题）
    - Composer（恢复可输入状态）
  → 长按 AI 气泡: Context Menu（复制 / 分享 / 保存为笔记 / 重新生成 / 举报）
  → 输入追问 + 发送: 重复 Screen 2-3 循环
```

**Exit State**:
- ✅ 成功生成：完整响应展示，Response Actions 可用
- ⏹ 用户停止：截断文字 + 提示「已停止生成」+ 操作按钮
- ❌ 网络错误：AI 气泡显示「生成失败，点击重试」+ 重试 Button

---

### Flow 2: Voice Input with Live Transcription（语音输入 + 实时转录）

**在此场景的特殊性**: 移动端的语音输入体验是 AI 助手的核心交互之一——麦克风按钮在所有 AI 助手 App 中均有（Gemini、Pi、Dot、Kin 均如此）。关键设计差异是**实时显示转录文字**（而非盲录），让用户可以纠正识别错误再提交（Gemini flow 3207 展示了「Start Listening → Live Transcript → Full Transcript / Submit」三步）。Google Gemini 还支持语音输出（TTS 播放 AI 回复），需在 AI 气泡旁显示 Speaker 图标 + 进度控制。Kin App（flow 5431）展示了麦克风权限说明页（Pattern G），是行业规范做法。

**行业共识**：Gemini（flow 3207）、Kin（flow 5431）均在首次使用语音时展示说明页再触发系统权限；实时转录文字是 Gemini 确认的行业标准。

**Entry**: 对话界面 → 点击 Composer 中的 🎤 按钮

```
Screen 1: 麦克风权限说明页（首次）
  触发条件: 麦克风权限未授权
  关键组件:
    - 大图标（麦克风图标）
    - Text（标题：「开启语音输入」）
    - Text（说明：「使用麦克风直接说话来输入问题，语音将在本地转录，不会上传原始音频」）
    - Button("开启麦克风", 主色) → 触发系统/浏览器麦克风权限弹窗
    - Button("稍后再说", 次要样式)
  → 授权成功: 进入 Screen 2
  → 已授权: 直接进入 Screen 2（跳过此页）

Screen 2: 聆听中（Listening State）
  主操作: 说话 / 停止
  关键组件:
    - 全屏或半屏覆盖层（Bottom Sheet 或覆盖 Composer 区域）
    - 麦克风动画（声波 / 音量波形动画）
    - Text「正在聆听...」（灰色小字）
    - [动态] 实时转录文字（逐词出现，灰色 / 主色文字）
    - Button（点击停止聆听，圆形大按钮，停止录制图标）
    - Button（取消，次要样式）
  → 停止说话后 1-2 秒: 自动完成，进入 Screen 3
  → 手动点击停止: 进入 Screen 3

Screen 3: 转录确认（Transcription Review）
  主操作: 确认发送 / 编辑文字 / 重新录制
  关键组件:
    - 转录完整文字（可编辑输入框，预填入识别结果）
    - Button("发送", 主色，底部全宽)
    - Button("重新录制", 次要样式)
    - Button("取消", 文字按钮)
  → 点击「发送」: 转录文字填入 Composer，自动触发发送 → 进入 Flow 1 Screen 2
  → 编辑文字后发送: 修正后发送
```

**Exit State**:
- ✅ 成功：转录文字发送，进入流式输出流程
- ❌ 静音超时（3 秒无声音）：回到聆听前状态，Toast「未检测到语音，请重试」
- ↩ 取消：返回对话界面，Composer 不填充任何内容

---

### Flow 3: Manage Conversation History（历史对话管理）

**在此场景的特殊性**: AI 助手的「历史记录」是与 IM 工具最大的差异之一——AI 对话有**明确的主题结构**（每次对话有自动生成的标题），用户需要快速找到上周讨论的某个话题。Kin（flow 5431）展示了「Conversations 列表 + 主页 Dashboard」双视图，说明 AI 助手的历史管理需要比 IM 更完整的上下文信息（标题 + 摘要 + 时间）。Grok 的「Private Chat」模式（flow 6093）是 AI 助手独有的「无历史模式」——明确告知用户本次对话不会保存，是 Web 端无浏览历史模式的移动版对应。左滑删除会话前需要 Dialog 二次确认（对话一旦删除不可恢复）。

**行业共识**：所有 AI 助手 App 均提供「新建对话」入口（通常在导航栏右上角或 + 按钮）；搜索历史对话是 ChatGPT、Claude 等的标准功能。

**Entry**: 侧边抽屉（Drawer）打开 / Conversations Tab

```
Screen 1: 历史对话列表（Conversations List）
  主操作: 查找或开始对话
  关键组件:
    - 页面标题「对话记录」+ 右上角 ✏️ 新建按钮
    - 搜索框（搜索对话标题和内容）
    - List（历史对话列表，下拉刷新）:
        每行: 对话标题（AI 自动生成 or 用户自定义）+ 最近时间 + 摘要（首句）
        分组: 「今天」「本周」「更早」Section Header
        左滑操作: 删除（触发 Dialog 确认）
        右滑操作: Pin 置顶（可选）
    - Empty 空状态（首次使用: 「还没有对话记录」+ 「开始第一次对话」CTA）
  → 点击某条历史对话: Push → Screen 2
  → 点击「✏️ 新建」: 新建空白对话 → 返回 Chat Home
  → 搜索: 列表过滤，高亮匹配关键词

Screen 2: 历史对话（Reopened Chat）
  主操作: 继续对话 / 复制内容 / 分享
  关键组件:
    - 完整历史消息气泡列表（自动滚到最新消息）
    - 页面标题（对话标题，可点击重命名）
    - 右侧菜单: ··· （分享 / 重命名 / 删除 / 导出）
    - 底部 Composer（与新建对话完全相同）
  → 输入并发送: 追加到历史对话继续聊天
  → 长按气泡: Context Menu（复制 / 分享 / 保存）
  → 点击 ···「删除」: Dialog 确认 → 删除并返回列表

[可选] Screen 3: 对话重命名
  主操作: 修改标题
  关键组件:
    - Dialog 样式的行内编辑（含 TextField）
    - Button("保存"), Button("取消")
```

**Exit State**:
- ✅ 正常查看：历史消息完整展示，可继续追问
- ✅ 删除成功：列表即时移除，Toast「对话已删除」
- ↩ 取消删除：Dialog 选「取消」，对话保留

---

---

### Flow 4: File Upload & Multimodal Chat（文件上传 + 多模态对话）

**在此场景的特殊性**: 多模态输入（图片 + 文件 + 文字）是 AI 助手区别于纯文字 IM 工具的核心能力差异。ChatGPT（flow_id 7017，15 屏）是最完整的参考：用户在 Composer 点击 📎 → 底部来源面板弹出（Camera / Photos / Files 三选项）→ 相机权限说明页 → 拍照 → 预览确认（重拍 / 使用）→ 图片缩略图出现在 Composer 输入框上方（带 × 移除按钮）→ 输入分析指令（如「描述这张图」）→ 发送 → AI 返回图片内容描述。Comet（flow_id 10943，9 屏）展示了**多图上传**的关键状态：选多张图后显示灰色占位缩略图 → 逐个填充真实图片，传达上传进度而无需 Modal 阻塞交互。Grok（flow_id 6083）的附件菜单含 Camera / Photos / Files / Create image 四个选项，并在权限请求前展示 in-app 说明 Modal（两步权限），是 Pattern G 的标准实现。**关键设计约束**：附件缩略图必须在 Composer 内展示（不在消息气泡内），发送前用户可随时点 × 移除，这是「附件与文字一起发送」心智模型的正确实现（ChatGPT flow_id 7028 / 7018 均如此）。Nooka（flow_id 8119）展示了文档（PDF）上传 + **异步 AI 生成**的状态管理：上传完 → 生成中（含思考过程动画）→ 完成后归档到 Library，是处理耗时 AI 任务的标准状态机。

**行业共识**：ChatGPT（flow_id 7017 / 7018 / 7028）/ Grok（flow_id 6083）/ Comet（flow_id 10943）均使用「📎 → 底部 Action Sheet（Camera / Photos / Files）三分支」作为附件来源入口，而不是直接打开系统相册——Action Sheet 让用户明确选择图片来源（拍新的 vs 选已有）；相册权限须先展示 in-app 说明页才触发系统弹窗（ChatGPT flow_id 7017 + Grok flow_id 6083 均验证两步权限模式）。

**Entry**: 对话 Composer 点击 📎 附件图标

```
Screen 1: 附件来源选择（Action Sheet）
  主操作: 选择图片/文件来源
  触发: 点击 Composer 左侧 📎 按钮
  关键组件:
    - Action Sheet（从底部弹出，暗色半透明背景遮罩）:
        Button("📷 相机", 主列表样式) → Screen 2a
        Button("🖼 照片图库", 主列表样式) → Screen 2b
        Button("📄 文件", 主列表样式) → Screen 2c
        Button("取消", 红色/取消样式，Sheet 底部独立分区)
    - [可选，Grok 模式] 额外选项:
        Button("✨ 生成图片"，AI 图像生成入口)

Screen 2a: 相机拍照（Camera）
  触发条件: 相机权限未授权时先插入 Screen 2a-P
  容器: Full-screen Modal（相机界面）
  关键组件（权限说明页 Screen 2a-P）:
    - 相机图标（大，居中）
    - Text「允许使用相机」（标题）
    - Text「拍摄照片后发送给 AI 分析，照片不会在本地永久存储」（说明）
    - Button("允许使用相机", 主色) → 触发系统 Camera 权限弹窗
    - Button("稍后再说", 次要)
  相机界面（授权后）:
    - 全屏相机预览
    - 底部: 大圆形快门按钮
    - 顶部: 「✕」关闭 + 翻转摄像头图标
  拍照预览确认:
    - 预览图（全屏显示）
    - Button("重拍", 左下角，次要) → 返回相机
    - Button("使用照片", 右下角，主色) → 返回 Composer

Screen 2b: 照片图库选择（Photos Picker）
  触发条件: Photos 权限未授权时先展示说明页（同 Pattern G）
  容器: 系统原生 Photo Picker（iOS PHPickerViewController）
  关键组件:
    - 系统 Photos 选择器界面（不可自定义）:
        支持多选（上限：默认 5 张，可配置）
        右上角「选择 X 项」计数实时更新
        Button("添加", 主色，右上角，选中后激活)
  → 选完点「添加」: 返回 Composer，缩略图显示在输入框上方

Screen 2c: 文件选择（Files Picker）
  容器: 系统原生 Files Picker（iOS UIDocumentPickerViewController）
  关键组件:
    - 系统 Files 界面（不可自定义）:
        支持路径: Recents / iCloud Drive / On My iPhone / Third-party
        文件格式过滤: PDF / DOC / DOCX / TXT / XLSX（AI 可分析的格式）
        单选（一次一个文件）
    - 选中文件: 文件名 + 大小（如「报告.pdf · 2.3MB」）

Screen 3: Composer 附件预览（发送前）
  主操作: 确认附件 + 输入提示词 + 发送
  容器: 对话页面（Chat Thread）+ Composer 已扩展
  关键组件:
    - Composer 附件区（输入框上方，独立 ScrollView 横向排列）:
        图片缩略图（每个约 80×80pt，圆角）:
          右上角「×」关闭按钮（点击移除该附件）
          上传状态: 灰色占位（Skeleton）→ 真实缩略图填充（Comet 模式）
        文件 Card（比图片更宽）:
          文件图标（PDF/DOC 类型图标）
          文件名（单行截断）+ 文件大小
          右上角「×」移除按钮
        多图时: 横向 ScrollView，超出屏幕宽度时左右可滚动
    - TextArea（照常显示，可输入提示词）:
        Placeholder 变化: 「描述这张图片...」（有图片时）/ 「问一个关于这份文件的问题...」（有文件时）
    - 发送按钮（所有附件上传完成 + TextArea 有内容时激活）

    [可选 Suggested Prompts 区域，出现在附件区下方]:
        「总结这份文档」/ 「翻译这张图片的文字」/ 「这张图片里有什么？」

  → 输入提示词 + 点击发送: Screen 4

Screen 4: AI 多模态响应（Multimodal Response）
  主操作: 查看 AI 对图片/文件的分析结果 / 继续追问
  关键组件:
    用户消息气泡（含附件）:
      - 图片类: 小缩略图（约 200pt 宽，圆角，点击 → Full-screen 查看）+ 提示文字（若有）
      - 文件类: 文件 Card（文件名 + 大小 + 页数，点击 → App 内预览或系统查看器）
      - 多附件: 网格排列（2 列，超出可展开）

    AI 分析中状态:
      - AI 气泡区: 「正在分析...」+ 三点 Loading 动画 ···
      - [可选，Chance AI 模式] 分阶段进度文字:
          「正在识别图片内容」→「正在生成分析」→「完成」（逐步流式切换）

    AI 分析结果气泡:
      - 内容引用 Header（图片时）: 小缩略图图标 + 「基于您分享的图片」
      - 分析正文（Markdown 渲染，支持：引用块 / 标题 / 列表 / 加粗）
      - Response Actions（气泡下方小图标栏）:
          Button(复制) + Button(分享) + Button(👍) + Button(👎) + Button(重新生成)

    Follow-up Suggestions（AI 响应后推荐）:
      - Chip 横排: 「请详细解释第二点」/ 「翻译成中文」/ 「还有其他问题吗？」

    Composer（常驻，可继续追问）:
      - 📎 图标（可追加新附件到本次多轮对话）
      - TextArea（继续输入追问）
  → 点击图片缩略图: Full-screen 查看（黑色背景 + 下划关闭，同 DM 媒体查看器）
  → 继续输入追问（纯文字或追加新附件）: 循环 Screen 3-4
```

**Exit State**:

- ✅ 图片分析成功：用户消息气泡含图片缩略图，AI 气泡含图片描述/分析，可继续追问
- ✅ 文件分析成功：文件 Card 出现在消息气泡，AI 返回文档摘要/问答
- ❌ 文件过大（> 20MB）：Toast「文件过大，最大支持 20MB，请压缩后重试」，附件从 Composer 移除
- ❌ 文件格式不支持：Toast「不支持该格式，支持 PDF / DOC / DOCX / TXT」
- ❌ 相机权限被拒绝：Toast「需要相机权限，可在系统设置中开启」+ Button「打开设置」；Action Sheet 其他选项（照片/文件）仍可用
- ↩ 移除附件：点击缩略图右上角 × → 附件从 Composer 移除，TextArea Placeholder 恢复默认

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `TextArea` + auto-resize | `TextInput` multiline + `onContentSizeChange` | 对话输入框（多行自动扩展）|
| ★★★ | `List` / `VirtualList` | `FlatList` + `scrollToEnd` | 消息气泡列表（懒加载 + 自动滚底）|
| ★★★ | `NavBar` + Drawer | `DrawerLayout` / `react-navigation Drawer` | 对话列表侧边抽屉导航 |
| ★★★ | `Button`（状态切换）| `Pressable` / `Button` | 发送 → Stop 生成状态切换 |
| ★★ | 长按 `Popover` / `ActionSheet` | `ContextMenu` (RN) | 长按气泡: 复制/分享/重新生成 |
| ★★ | `SwipeAction` | `Swipeable`（react-native-gesture-handler）| 历史对话列表左滑删除 |
| ★★ | `SearchBar` | `SearchBar` / `TextInput` | 历史对话标题 + 内容全文搜索 |
| ★★ | `Dialog` | `AlertDialog` / `Modal` | 删除对话二次确认 |
| ★★ | 浏览器 Web Speech API / Expo Speech | `expo-speech` / `@react-native-voice/voice` | 语音输入录制 + STT 实时转录 |
| ★ | `List` + Section Header | `SectionList` | 历史对话记录（今天/本周/更早分组）|
| ★ | Empty `Result` 组件 | `Empty` / 自定义空状态 | 空状态（首次使用 / 搜索无结果）|
| ★ | `ImageUploader` / `input[type=file]` | `expo-image-picker` | 多模态附件（图片/文件）来源选择 |
| ★ | `Toast` | `Toast` / `Snackbar` | 操作反馈提示（已删除/已复制等）|
| ★ | `react-markdown` / 自定义渲染 | `react-native-markdown-display` | AI 响应中 Markdown 粗体/代码块渲染 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **发送按钮在 AI 生成期间不变为 Stop 按钮**：用户发送后无法停止生成，被迫等待长达数十秒的完整响应。→ 正确做法：发送后按钮立即变为 Stop Button（停止图标），点击停止流式输出，按钮恢复为发送（Grok / Rewind 均如此）。

- **AI 气泡不支持 Markdown 渲染**：代码、标题、列表以纯文本方式呈现（`###`、`**`、`-` 等 Markdown 符号直接显示），严重降低可读性。→ 正确做法：AI 响应用 Markdown 解析器渲染，至少支持粗体、代码块（monospace 字体）、有序/无序列表。

- **Chat Home 空状态只显示「输入框 + 空白」**：新用户不知道从哪里开始，放弃率高。→ 正确做法：空状态展示 3-6 个 Suggested Prompt Chips（横向可滚动），点击直接填入 Composer，降低冷启动摩擦（Gemini、Grok 均有此设计）。

- **语音输入不显示实时转录**：用户录完音后看到一段无法确认的文字，不确定 AI 是否听清楚了什么。→ 正确做法：聆听状态下实时显示识别中的文字（Live Transcription），让用户知道转录进展；完成后有确认/编辑/重录步骤（Gemini flow 3207 三步确认模式）。

- **历史对话列表只按时间排序，无搜索**：用户有 50+ 条对话时找不到上周讨论的某个主题。→ 正确做法：支持全文搜索（标题 + 内容），历史对话按「今天/本周/更早」分组，对话标题自动生成（取前几个词或 AI 生成摘要）。

- **删除历史对话无二次确认**：左滑即删除，用户误操作后无法恢复。→ 正确做法：左滑触发 Dialog（「删除后无法恢复，确认删除？」），两个操作：「删除」(danger 样式) / 「取消」。

- **Composer 输入框不支持多行输入**：单行输入框中输入长 Prompt 时无法换行，超出时被截断或水平滚动，体验极差。→ 正确做法：TextArea / TextInput multiline 自动扩展高度，最多 6-8 行后出现内部滚动效果（所有研究样本均采用此方案）。

- **没有语音权限说明页，直接弹系统麦克风权限弹窗**：用户在不了解用途时拒绝麦克风权限，此后即使想使用也不方便开启。→ 正确做法：自定义说明页（「语音输入用于转录，不存储原始音频」），说服用户理解价值后再触发系统弹窗（Kin flow 5431 中有完整实现）。

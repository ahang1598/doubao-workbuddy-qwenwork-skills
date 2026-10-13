# 宿主交付合同

> 这一份是包里最不该被重写的东西：它记录的是**宿主的事实**，不是我们的偏好。
> 每一条都有 trace 证据。

## 1. 两张卡，顺序不可换

宿主 system prompt 原文（三条 trace 逐字相同）：

```
4. 【非常重要】当调用"app_builder_agent"工具生成应用类产物时，严谨再使用 NotifyHuman 工具进行产物交付
5. 注意：图片类的产物，禁止用 NotifyHuman 进行交付，在回复中直接输出图片即可
6. 注意：网页类产物，HTML/JS 等，严禁使用 NotifyHuman 工具进行产物交付
```

（注意第 4 条宿主自己有错字，"严谨"应为"严禁/无需"。flash 档会把它读成
"整轮都不要再用 NotifyHuman"。我们改不了宿主，只能让顺序天然规避它。）

**后果逐案对上：**

| 案例 | 模型实际动作 | 结果 |
|---|---|---|
| 洛丽塔官网 | 上传 site.html 拿到 CDN 地址 → 推理"网页类产物严禁 NotifyHuman" → 把地址写进正文纯文本 | 只有 Doc 一张卡 |
| QQ H5 | 同上 | 只有 Doc 一张卡 |
| 运动官网 | 调了 app_builder_agent（出网页卡）→ 推理"调过 app_builder 就不该再 NotifyHuman" → 直接文字回复 | 只有网页一张卡 |

**反证**：产物正确的那一轮顺序是
`… → app_builder_agent → NotifyHuman(doc)` —— 先 app 后 doc 也能出两张卡，
说明这不是硬拦截，是**模型的解读**。

**所以修法是把顺序固定成"先 Doc 卡、后 app"**，
让"调过 app_builder"这件事在 NotifyHuman 之后才发生，那条推理就不可能被触发。

| # | 卡 | 谁生成 | 怎么交 |
|---|---|---|---|
| ① | 设计方案 Doc | 本包 `publish.py` | `NotifyHuman(attachments=[飞书 URL])`　**必须最先** |
| ② | 可运行网页 / H5 | `app_builder_agent` | 它自己上屏出卡，不再 NotifyHuman，不把地址写进正文 |

## 2. HTML 文件永远不是卡片

上传 `site.html` 拿到的 CDN 地址只会变成正文里一行纯文本。
`site.html` 要保留，但它的身份是**截图源与规格源**，不是交付物。

**不要造"上传网页拿地址当卡片"的通道**——宿主上不存在这条通道。
曾经为它写过一条 `register-site` 命令、一套收据、一段说明，
而那条命令打印的「PASS 官网卡片已登记」是假的：它什么都没登记。

## 3. app_builder_agent 的合同

（来自宿主自带的 `doubao-app-builder` skill，逐行核对过）

- 本地图片/文件**必须先 FileBatchUpload 上传获取远程链接，
  然后把远程链接写进 `app_builder_agent` 的 user_prompt 文本里**
- **严禁在 prompt 里使用本地文件路径**
- **禁止替 app_builder_agent 做技术选型**（框架/库/组件库）
- **禁止输出应用地址**：系统会通过单独的卡片自动展示
- `arch_type`：默认 `jspage`；3D/游戏用 `html`；需要持久化才 `fullstack`

**0 个公网图片 URL 的 prompt 会产出一整页纯色块**——实测。
「运动官网没有图片」那一轮，12 张图已上传拿到地址，
但交给 app_builder 的是一段 600 字的裸文本 prompt，一个 URL 都没有。

### 有一条宿主口径在本包里**必须反过来**

宿主 skill 原文写的是：

> 图片链接嵌入：**仅为最关键的 2–3 个页面**附带已有的图片链接和描述，
> 同时告知它可自行搜索补充。

**那条口径的场景是「从零写一个应用」**——那时让 app_builder 自己发挥是对的。
**本包的场景相反：界面已经设计完了。**
`app_builder_agent` 在这里的唯一职责是**把定稿的 HTML 原样上屏**。

所以本包的口径是：

| | 宿主 app-builder 的场景 | 本包的场景 |
|---|---|---|
| prompt 内容 | 需求描述 + 2–3 个页面的图链 | **成品 HTML 全文，一字不改** |
| 图片 | 附几个，其余让它自己搜 | **全部替换成已上传的公网 URL，不许它搜** |
| 措辞 | 描述你想要什么 | 「请直接使用提供的 HTML 代码，不要做任何修改」 |

**这一步不要手写。** `deliver.py` 会读成品 HTML、替换素材 URL、
写出 `deliver/app-prompt.txt`，并做一次对账：
**prompt 短于成品 HTML 的 90% 就拒绝交付。**

实测（三条真实 trace）：

| trace | prompt | 结果 |
|---|---:|---|
| 62 空气传感器官网 | 28,727 字（贴了完整 HTML） | 卡片就是设计稿 ✅ |
| 64 咖啡小程序 | 20,043 字（贴了完整 HTML） | 卡片就是设计稿 ✅ |
| **63 校园论坛 App** | **359 字（一段功能描述）** | **卡片是另一个模型重画的** ❌ |

第三条里 `site/index.html` 一个字节都没进 prompt——它被 FileBatchUpload
上传了，然后被丢下。用户的反馈是「整个 doc 的设计和 h5 设计风格不一致」
和「交互细节比较简陋」。**两条都是必然结果，不是巧合。**

## 4. 工具可用性看哪个字段

**`meta.tool_list` 是"本轮调用过的工具"，不是"可用工具"。**
真值在 `mainagent.agent_runtime.tools`（三条 trace 各 61 项）。

读错这一个字段的代价：会据此判定 `app_builder_agent` 不稳定存在，
默认走那条宿主上不存在的上传通道，三个案例全部形态错误。

`image_to_video` / `text_to_video` / `app_builder_agent` 在真实 tool_list 里都有。
不确定时**运行时探测**，不要写死。

## 5. 发布后必须字节对账

见 [../method/06-deliver.md](../method/06-deliver.md)。
一句话：**脚本自己打印的 PASS 不是证据。**

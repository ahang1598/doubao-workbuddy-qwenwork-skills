---
name: html
version: 1.0.76
description: 专门设计、生成和修改可直接在浏览器中打开的 HTML 页面或已发布的 doubao-html 链接。交付物以独立 .html 文件为主，可包含内联或本地 CSS、JavaScript，支持页面布局、视觉样式、交互效果、响应式适配、组件设计和内容展示。适用于静态网页、单页展示、活动页、原型页、HTML 模板及页面片段。不处理前后端工程、应用框架、服务端接口、数据库、用户系统、构建部署或运营数据。
---

# 单页 HTML 交付与发布

## 交付与发布规范

- **单文件自包含**：一个 `.html` 文件到手就可用。
  - CSS 写在 `<style>`、JS 写在 `<script>` 内联块里，**不拆出** `.js` **/** `.css` **/ 额外 HTML 文件**。
  - 多「页面」用页内 hash 路由切换视图，大段代码用分段注释组织（`<!-- ===== 视图：xxx ===== -->`）。
  - **原生 JS**：不用 React / Vue / JSX / Babel / 任何构建工具。状态管理用普通对象 + 重渲染函数。
  - **静态资源引用**：
    > 运行环境：云电脑 / 本地电脑，按下述顺序判定。
    > 1. SystemPrompt 中的 `Computer OS` 字段：值为 `Windows` 或 `Mac` 判为本地电脑；值为其他判为云电脑。
    > 2. SystemPrompt 未包含 `Computer OS` 字段时：`<system-reminder>` 包裹的内容中出现 `Runtime: local_pc` 判为本地电脑，出现 `Runtime: cloud_vm` 判为云电脑。
    - 图片、音视频等**由元素 `src` 或 CSS `url()` 加载**的素材，先下载到 `assets/`；生图搜图返回的 URL 会过期，不能直接写进 html，下载后按运行环境选引用方式：
      - **本地电脑**：用相对路径，如 `<img src="assets/hero.png">`，不写绝对路径。省掉上传这一步，交付更快。
      - **云电脑**：
        - 每张图跑一次 `lark-cli drive +html-image-upload --file assets/hero.png`，取返回里 `data.url` 写进 `<img src>`。这个链接不会过期；而搜图、生图得到的 URL 会过期，不能直接放到 html 中。
        - 此场景下**严禁使用 `FileBatchUpload` 工具**，必须使用 `lark-cli drive`，否则图片也会过期。
    - **数据文件（JSON / CSV / TXT）不适用**：`file://` 页面不能依赖 `fetch` 或 `XMLHttpRequest` 读取本地数据文件。固定数据内联进 JS；用户要求更新时，按数据源选择可访问的 URL 或文件选择入口。
    - **图片路径只能写在 `src` 属性或 CSS `url()` 里**：推荐 `<img src="assets/img1.jpg">`。发布链路只静态扫描这两个位置——写在 JS 代码里的任何形式（含 `const imgs = ['assets/a.jpg']` 这样的常量数组）、以及 `data-src` / `srcset` / `poster` 等其它属性，发布后都会裂图。

- **交付与发布**：
  - 当用户没有明确的发布需求时：用 `present_files` 交付任务目录中的最终 `.html` 文件，**`artifacts[].name` 写产物文件名，不要另起标题**（`销售仪表盘.html`，不是「销售数据看板」）。**同一个产物只交付一个 `.html` 文件**——按运行环境选定一种图片引用方式就够了，不要再额外附一份「以防万一」的备份版或压缩包，用户拿到两份不知道该打开哪个。交付说明如实写清：没实现的功能、用的是示例数据、做不了的能力。**`present_files` 的 `artifacts` 只包含最终 HTML 文件，不单独交付 `assets/` 等依赖目录。依赖目录保留在本地原位置，需要转发时，仅在回复中提醒用户连同目录一起发送。**
  
  - **`present_files` 调用后会直接向用户展示产物卡片，禁止在最终回复正文中输出任何链接**（包括发布返回的 `online_url` 如 `doubao.link` / `feishu.link`，以及 `present_files` 回执中的 `aka.doubaocdn.com` 等临时 CDN 地址），也不使用回执中的临时 CDN 地址再次调用交付工具或冒充网页链接。

  - 当用户想要「发布」、「可访问的链接」、「给我链接」时：将你的 html 文件发布成一个 doubao-html 网页，此时无需交付 html 文件，仅需使用 `present_files` 交付发布接口返回的 `online_url`（卡片会自动展示，**不在回复正文里再贴一次链接**）。用户在文件交付后追加「链接发我」等要求时，同样先发布，再用 `present_files` 交付 `online_url`，不拿临时 CDN 地址代替发布。未发布时用 `present_files` 交付最终 `.html` 文件。
  
  - **发布接口确认成功后，直接用 `present_files` 交付返回的 `online_url`，禁止再访问该链接做检查**，避免检查环境缺少用户登录态而把登录页当成产物。
  - **最终给用户的回复不要过长**：最重要的产物是你最终生成的 html 产物，而不是给用户的最终回复，所以在交付了 html 产物后的最终回复不应该太长，**不能超过300字，也不能超过 8 行**，只需要简单介绍一下你生成的 html 产物即可

- **修改、参考已发布的 doubao-html 网页**：
  - 当用户给你提供了一个 doubao-html 链接（形如 `https://{xxx}.doubao.link/app/app_{xxxxxxx}/`），并希望基于此修改或新建时，先用 `lark-cli apps +get --app-id <id>` 看 `app_type`：`html` / `modern_html` 是单页 HTML，下载源码、修改、重新发布即可；其他类型使用 `doubao-app-builder` 技能。
  

## 外部资源

**JS 库统一走 jsDelivr**：`https://fastly.jsdelivr.net/npm/<包名>@<版本>/…`。故障时的备用镜像是 **cdnjs**（`https://cdnjs.cloudflare.com/ajax/libs/<lib>/<ver>/…`，Cloudflare 官方运营，同版本文件字节一致）。**禁止** bootcdn、staticfile、polyfill.io（均有供应链投毒历史），unpkg 不作首选。

**字体走自托管镜像** `https://miaoda.feishu.cn/fonts/css2?family=…`：查询语法与 Google Fonts 的 `css2` 端点完全一致，返回的 `@font-face` 也指向自托管 CDN，两跳都不经过 Google。**不直连** `fonts.googleapis.com` **/** `fonts.gstatic.com`（部分地区不可达）。多字族就重复写多个 `family=`，例如 `<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">`。每个 `font-family` 都要带完整的系统字体 fallback 栈，字体加载失败时页面仍然成立。


---

# doubao-html · 发布 HTML 与下载代码

## 术语与前提

- **app_id**：`app_` 开头，doubao-html 网页唯一标识（服务端把 html 应用的 `app_type` 归一为 `modern_html`）。
- **meta_token**：豆包网页分享链接 `/page/<token>` 的最后一段。
- 所有 `--file-path` / `--dir` / `--output` 路径**只接受相对当前目录的相对路径**，传绝对路径会被拒——先 `cd` 到产物目录。
- **`cd` 和 `lark-cli` 必须写在同一条命令里**（`cd <产物目录> && lark-cli apps …`）。每次执行命令的工作目录不保证沿用上一次，分两次执行时 `./x.html` 会按另一个目录解析，报 `--file-path … does not exist`。
- **用 PowerShell 工具执行时**（Windows 本地）：
  - 用 `Set-Location -LiteralPath "<产物目录>"; lark-cli apps …` 代替 `cd … &&`，Windows 自带的 PowerShell 5.1 不支持 `&&`。
  - **不要加 `2>&1` 等重定向**。lark-cli 的进度信息写在 stderr，PowerShell 5.1 会把重定向进来的 stderr 当成错误（输出里出现 `lark-cli : publishing to app …`），整条命令被标为失败，实际发布却已成功。成败只看返回 JSON 的 `ok`。

---

## §1 发布：`+deploy`

`+deploy` 既能首发建应用，也能复发布更新已有应用。

```bash
cd <产物目录> && ls ./<file_name>.html && lark-cli apps +deploy --file-path ./<file_name>.html                    # 首发，自动建应用
cd <产物目录> && ls ./<file_name>.html && lark-cli apps +deploy --file-path ./<file_name>.html --app-id app_xxx   # 复发到同一应用
```

- 发布前用 `ls` 确认入口文件就在当前目录；`ls` 找不到就先修正目录或文件名，不要直接发布。
- 只使用本文列出的参数。`+deploy` 没有 `--yes`，加了会报 `unknown flag`。不要改用 `--dir` 或 `+html-publish`：它们要求目录里有 `index.html`，本 skill 的产物通常没有。

- **单文件（`--file-path`）是本 skill 的唯一主路径。** 该文件即入口，产物里恒为 `index.html`。**会自动爬取页面引用的本地依赖**（`<img src|srcset>`、`<link rel>`、`<script src>`、CSS 的 `url()` / `@import` 等），一并打包——页面引用了同目录 `assets/` 的素材也能正常渲染。

### app_id 怎么定

- **更新已有应用时，默认带上上次返回的 `--app-id`**，无需做幂等查询，直接更新同一应用。**首次返回的 app_id 必须记住并复用。**
- 不带 `--app-id` 时，入口文件的绝对路径是幂等标识——同一路径复发落回同一应用；改名 / 搬目录 / 换 cwd 会**新建**一个应用。
- stderr 回显 `publishing to app <app_id> (from --app-id|has_html_app_created|+create)`，据此确认发到了哪个应用。`app_id` 不是本会话拿到的（来自历史/他人）时先与用户确认——发布会覆盖该应用线上内容。

### 输出契约
- **判断成败看返回 JSON 的 `ok` 字段，不要看 exit code。** 参数校验失败时返回 `{"ok": false, "error": {...}}`，而包裹命令的工具层仍可能显示 `Exit code 0`。`error.hint` 一般给出了正确改法，优先照做并转述。
- 发布单受理后命令**立即返回、不原地等待**：发布中返回 `data.release_id` + `data.poll_hint`，同步完成则直接返回 `data.online_url`。
- 用 `+release-get --app-id <app_id> --release-id <release_id>` 轮询到 `status=finished` 再读 `online_url`（间隔 ≥3s，整体约 5 分钟上限；超时未完成就停下、报当前 status 和 release_id）。
- 流水线失败 = 发布失败（`ok:false`，message 含各 step 的 `error_logs` 摘要）；产物已上传，修复后重新 `+deploy` 即可。
- **命令被转到后台时不要重新发布**。工具返回「moved to the background」「Started background command」之类的提示时，发布可能已经受理：先等这个后台任务结束并读取它的输出；拿到 `release_id` 就用 `+release-get` 查结果。直接重发会报 `发布任务已存在`，或者新建出另一个应用。
- **发布单还在处理时不要重复 `+deploy`**。返回 `发布任务已存在`（错误码 `400002553`）说明上一次发布还没结束，用 `+release-get` 查到 `finished` 或失败后再决定是否重发。
- 按 `error.type` 区分处理，不要把所有失败都当作命令写错：
  - `validation`：参数或路径问题，按 `error.hint` 修正后重试。
  - `network`（如 `TOS upload failed`、`server time out`、HTTP 502/503）：同一条命令间隔几秒重试，最多 2 次；重试报 `发布任务已存在` 时改为 `+release-get` 查询。
  - `internal`（如 `pre_release … no artifact_url`）：服务端问题，同一条命令重试 1 次，仍失败就停下，向用户报告 `error.message` 和 `app_id`，不要换参数反复尝试。
- **只通过 `present_files` 交付 `online_url`，禁止在回复正文中输出链接**：调用 `present_files` 后客户端会直接渲染网页卡片，**最终回复正文中禁止再贴出 `online_url`（`doubao.link` / `feishu.link`）或 `aka.doubaocdn.com` 等临时 CDN 地址**。`present_files` 回执中的 CDN 地址是临时文件下载地址，不是发布链接，不作为预览、分享或下载入口再次交付。
- **发布成功后直接交付**：发布接口确认完成并返回 `online_url` 后，直接通过 `present_files` 交付，**禁止再用 `curl`、浏览器或自写脚本访问链接检查可用性或渲染效果**。检查环境可能没有用户登录态，打开的是登录页；不要据此判断发布失败，或在交付名称、说明中添加“手机登录豆包后打开”等提示。

### 会拦截的两件事

- **凭证扫描**：按文件名扫 `.env` / 私钥 / `credentials` 等，命中即拒绝。默认动作是**把这些文件移出发布范围**，不要习惯性加 `--allow-sensitive`（那会跳过整道扫描，而产物是公网可访问链接）。
- **体积**：单个 `.html` ≤ 20 MiB、打包前原始总量 ≤ 200 MiB、打包后 zip ≤ 50 MiB。超限只能收窄产物范围，没有放开参数。产物里有大量图片或视频时，发布前先看产物目录大小，接近限制就先压缩图片或移走没被页面引用的文件，否则会报 `packed zip is … MiB, exceeding the 50.0 MiB limit`。

---

## §2 下载已发布应用的源码：`+export`

用户给了 doubao-html 链接、本地又没有原文件时，用它把应用代码打成 zip 取回本地。

```bash
lark-cli apps +export --app-id app_xxx --output ./src.zip
lark-cli apps +export --app-id app_xxx                     # 省略 --output 则存成 ./app_xxx.zip
```

- `--app-id`（自己的应用）与 `--meta-token`（分享链接的 token）**恰传其一**，两者都只收**裸标识符**——整条 URL 会被本地拦下。
- **导出的是最后一次提交 / 检查点，不是沙箱当前状态。** 改了没发布的代码不在归档里；看起来「少了刚写的代码」时先确认是否已发布，而不是重试导出。
- 取不到源码的几种情况——**都不要反复重试**，直接告知用户取不到、请他提供原文件：权限不足（403，持有分享 token ≠ 有下载权限）、代码不在归档（422）、归档过大（413）、应用不存在（404，用 `+list --keyword <name>` 核对 app_id）。

---

## §3 定位与收尾

- **定位应用**：有 app_id 用 `+get --app-id app_xxx`；只有应用名用 `+list --keyword "名字"`。
- **`is_published=true` 只代表历史上发布过，不代表最新代码已部署**——必须有本轮 `+release-get` 观察到 `finished`；不要凭 `is_published` 或 `+list` 判定「已上线」。

## Agent 规则速记
1. 路径一律相对 cwd，先 `cd` 到产物目录；绝对路径会被拒。PowerShell 下用 `Set-Location …;`，不加 `2>&1`。
2. 判断成败看返回里的 `ok`，不看 exit code。
3. 转后台或 `发布任务已存在` 时等待和查询，不要重发。
4. 发布是异步的，`+release-get` 到 `finished` 才算成。
5. 复发布带上一次的 `--app-id`；不是本会话拿到的 app_id，覆盖前先与用户确认。
6. `+export` 导出的是最后提交 / 检查点，不是沙箱当前态。

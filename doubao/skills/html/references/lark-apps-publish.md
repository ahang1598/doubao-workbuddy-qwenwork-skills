# lark-apps · 发布 HTML 与下载代码

面向 agent 的操作指南，默认 `--as user`。认证 / 权限 / exit-10 高风险确认等通用规则不在此重复。

## 术语与前提

- **app_id**：`app_` 开头，doubao-html 网页唯一标识（服务端把 html 应用的 `app_type` 归一为 `modern_html`）。
- **meta_token**：创意应用分享链接 `/page/<token>` 的最后一段。
- 所有 `--file-path` / `--dir` / `--output` 路径**只接受相对当前目录的相对路径**，传绝对路径会被拒——先 `cd` 到产物目录。

---

## §1 发布：`+deploy`

`+deploy` 既能首发建应用，也能复发布更新已有应用。

```bash
lark-cli apps +deploy --file-path ./index.html                    # 首发，自动建应用
lark-cli apps +deploy --file-path ./index.html --app-id app_xxx   # 复发到同一应用
```

- **单文件（`--file-path`）是本 skill 的唯一主路径。** 该文件即入口，产物里恒为 `index.html`。**会自动爬取页面引用的本地依赖**（`<img src|srcset>`、`<link rel>`、`<script src>`、CSS 的 `url()` / `@import` 等），一并打包——页面引用了同目录 `assets/` 的素材也能正常渲染。

### app_id 怎么定

- **复发布带上一次返回的 `--app-id` 是常态主路径**，跳过幂等查询直接更新同一应用。**首次返回的 app_id 必须记住并复用。**
- 不带 `--app-id` 时，入口文件的绝对路径是幂等标识——同一路径复发落回同一应用；改名 / 搬目录 / 换 cwd 会**新建**一个应用。
- stderr 回显 `publishing to app <app_id> (from --app-id|has_html_app_created|+create)`，据此确认发到了哪个应用。`app_id` 不是本会话拿到的（来自历史/他人）时先与用户确认——发布会覆盖该应用线上内容。

### 输出契约
- **判断成败看返回 JSON 的 `ok` 字段，不要看 exit code。** 参数校验失败时返回 `{"ok": false, "error": {...}}`，而包裹命令的工具层仍可能显示 `Exit code 0`。`error.hint` 一般给出了正确改法，优先照做并转述。
- 发布单受理后命令**立即返回、不原地等待**：发布中返回 `data.release_id` + `data.poll_hint`，同步完成则直接返回 `data.online_url`。
- 用 `+release-get --app-id <app_id> --release-id <release_id>` 轮询到 `status=finished` 再读 `online_url`（间隔 ≥3s，整体约 5 分钟上限；超时未完成就停下、报当前 status 和 release_id）。
- 流水线失败 = 发布失败（`ok:false`，message 含各 step 的 `error_logs` 摘要）；产物已上传，修复后重新 `+deploy` 即可。
- **发布成功后直接交付**：发布接口确认完成并返回 `online_url` 后，直接交付该链接，**禁止再用 `curl`、浏览器或自写脚本访问链接检查可用性或渲染效果**。检查环境可能没有用户登录态，打开的是登录页；不要据此判断发布失败，或在交付名称、说明中添加“手机登录豆包后打开”等提示。

### 会拦截的两件事

- **凭证扫描**：按文件名扫 `.env` / 私钥 / `credentials` 等，命中即拒绝。默认动作是**把这些文件移出发布范围**，不要习惯性加 `--allow-sensitive`（那会跳过整道扫描，而产物是公网可访问链接）。
- **体积**：单个 `.html` ≤ 20 MiB、打包前原始总量 ≤ 200 MiB、打包后 zip ≤ 50 MiB。超限只能收窄产物范围，没有放开参数。

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
1. 路径一律相对 cwd，先 `cd` 到产物目录；绝对路径会被拒。
2. 判断成败看返回里的 `ok`，不看 exit code。
3. 发布是异步的，`+release-get` 到 `finished` 才算成。
4. 复发布带上一次的 `--app-id`；不是本会话拿到的 app_id，覆盖前先与用户确认。
5. `+export` 导出的是最后提交 / 检查点，不是沙箱当前态。

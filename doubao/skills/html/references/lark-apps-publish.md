# lark-apps · 用 +deploy 发布 HTML 与下载代码
面向 agent 的操作指南，只覆盖 **`+deploy` 裸 HTML 发布**这一条链路。默认 `--as user`。认证/权限/exit-10 高风险确认等通用规则不在此重复。
## 术语与前提
- **app_id**：`app_` 开头，妙搭应用唯一标识（服务端把 html 应用的 `app_type` 归一为 `modern_html`）。
- **meta_token**：创意应用分享链接 `/page/<token>` 的最后一段，指向**别人**的应用。
- 所有 `--file-path` / `--dir` / `--output` 路径**只接受相对当前目录的相对路径**，传绝对路径会被拒——产物不在 cwd 下时先 `cd` 过去。
## 整体链路
```
（可选）+create 命名建应用 ──┐
                            ├─→ +deploy --file-path/--dir ──→ +release-get 轮询到 finished ──→ online_url
   直接 +deploy 自动建应用 ──┘
                                            └─→ 需要代码快照时 +export 下载 zip
```
`+deploy` 不需要仓库、不构建、不落任何本地文件：把指定文件/目录打包发布成一个 html 应用，拿到可分享链接。既能首发建应用，也能复发布更新已有应用。
---
## §1 发布：`+deploy --file-path` / `--dir`
### 命令骨架
- **单文件**：`lark-cli apps +deploy --file-path ./report.html`
  该文件即入口，产物里恒为 `index.html`。**会自动爬取页面引用的本地依赖**（css/js/图片/字体，含 `<link rel=…>`/`<script src>`/`<img src|srcset>`/内联与外链 CSS 的 `url()`·`@import`/JS 的 `import`·`fetch()`·`new Worker`·`new URL(…, import.meta.url)`/JSON 里的资源路径等），一并打包——发一个引用了同目录资源的页面也能正常渲染。
- **目录**：`lark-cli apps +deploy --dir ./site`
  目录下所有普通文件随包上传（跳过 `.git` 子树，不跟随符号链接），入口默认取目录**根**的 `index.html`；不爬依赖、原样打包整个目录。
- **指定入口**：`lark-cli apps +deploy --dir ./site --entry-file page.html`
  `--entry-file` 只接受 `--dir` 的**直接子文件名**（不含 `/`、须 `.html`）；发布产物里被改名为 `index.html`（只改产物、不动磁盘原文件）。入口在子目录里时把 `--dir` 直接指到那一层，不要在 `--entry-file` 写路径。
- **互斥**：`--file-path` 与 `--dir` 二选一；`--entry-file` 只在 `--dir` 下有意义。
### `--dir` 入口判定
| 给了 `--entry-file` | 目录根有 `index.html` | 结果 |
|---|---|---|
| 否 | 是 | `index.html` 即入口，直接发布 |
| 否 | 否 | 报错 `no entry file`：加 `--entry-file` 或放一个 `index.html` |
| 是 | 否 | 发布，该文件在产物里改名为 `index.html` |
| 是 | 是 | 报错 `entry conflict`：去掉 `--entry-file` 或移走 `index.html` |
### 首发 vs 复发布（app_id 怎么定）
- **复发布带上一次返回的 `--app-id` 是常态主路径**：`+deploy --dir ./site --app-id app_xxx` 跳过幂等查询，直接更新同一应用。**首次返回的 app_id 必须记住并复用。**
- **不带 `--app-id`**：入口文件的绝对路径（按当前用户隔离）是幂等标识——同一路径复发落回同一应用；改名/搬目录/换 cwd 会**新建**一个应用。要继续更新已有应用就带 `--app-id`。
- 查不到已有应用时自动创建；应用名取入口文件名去扩展名（`report.html`→`report`；入口是 `index.html` 时取父目录名；都取不到用 `html-app`）。要**自定义名字**就先 `lark-cli apps +create --name <name> --app-type html`，再用返回的 app_id 发布。
- stderr 回显 `publishing to app <app_id> (from --app-id|has_html_app_created|+create)`，据此确认发到了哪个应用。`app_id` 不是本会话拿到的（来自历史/他人）时先与用户确认——发布会覆盖该应用线上内容。
### 凭证扫描与体积上限（会拦截，别绕）
- 默认按文件名扫凭证类文件（`.env` / `.env.*`、`.npmrc`、`.netrc`、`id_rsa` 等私钥、`*.pem` / `*.p12` / `*.pfx` / `*.keystore`、`credentials`、`service-account.json`，大小写不敏感），命中即拒绝并列出。默认动作是**把这些文件移出发布范围**（删掉或把 `--dir` 收窄到只含站点那层）。只有确认本就是要公开的页面内容才加 `--allow-sensitive`（跳过整道扫描，产物是公网可分享链接，误放行=把凭证发上公网）。`--dry-run` 命中同样非零退出，不能用它绕过。
- 体积：单个 `.html` ≤ 20 MiB、打包前原始总量 ≤ 200 MiB、打包后 zip ≤ 50 MiB。超限只能收窄产物范围，没有放开参数。
### 示例
```bash
lark-cli apps +deploy --file-path ./report.html                    # 首发单文件，自动建应用
lark-cli apps +deploy --file-path ./report.html --app-id app_xxx   # 复发到同一应用
lark-cli apps +deploy --dir ./site                                 # 目录，入口 ./site/index.html
lark-cli apps +deploy --dir ./site --entry-file home.html          # 目录无 index.html 时指定入口
lark-cli apps +deploy --dir ./site --dry-run                       # 只看计划与实际外发文件列表，不发任何写请求
```
`--dry-run` 会打出实际外发的 `idempotent_key`（本机绝对路径，含用户名与目录结构）、待发文件清单、contentHash——需要判断是否可接受时先跑它。
### 输出契约
- 发布单受理后命令**立即返回、不原地等待**：发布中时返回 `data.release_id` + `data.poll_hint`（可直接执行），同步完成时直接返回 `data.online_url`。
- 用 `+release-get --app-id <app_id> --release-id <release_id>` 轮询到 `status=finished` 再读 `online_url`（间隔 ≥3s，整体约 5 分钟上限；超时仍未完成就停下、报当前 status 和 release_id）。
- 裸 HTML 发布 `data.built` 恒为 `false`；`online_url` 不回写任何本地文件。
- 流水线失败 = 发布失败（exit 非 0，message 含各 step 的 error_logs 摘要）；产物已上传，修复后重新 `+deploy` 即可。业务失败通常带 `error.hint`，优先转述；5xx 带 `retryable` 可稍后重试。
---
## §2 下载应用代码：`+export`
把应用代码打成 zip 下载到本地。**跨应用是它的核心价值**——分享链接指向别人的应用、你对其没有开发权限时，`+export` 只要求你对该应用有**下载权限**。
### 命令骨架
- `--app-id` 与 `--meta-token` **恰传其一**：前者自己的应用，后者分享链接 `/page/<token>` 的 token。两者都只收**裸标识符**——整条 URL 传进来会被本地拦下（不会变成看起来像"应用不存在"的 404）。
- `--checkpoint-id` 可选，**正整数**，导出某检查点；省略取默认分支最新提交（不要显式传 `0`）。
- `--output` 可选，相对当前目录；省略存成 `./<app_id>.zip`。
```bash
lark-cli apps +export --app-id app_xxx --output ./src.zip
lark-cli apps +export --app-id app_xxx                      # 存成 ./app_xxx.zip
lark-cli apps +export --meta-token <share-token>            # 别人分享给你的应用（仍需下载权限）
lark-cli apps +export --app-id app_xxx --checkpoint-id 42
lark-cli apps +export --app-id app_xxx --dry-run
```
### 关键语义与输出
- **导出的是"最后一次提交/检查点"，不是沙箱当前状态**：服务端对远端产物跑归档，从不读沙箱文件系统。改了没触发 checkpoint 或没发布的代码**不在归档里**。看起来"少了刚写的代码"时先确认是否已发布/存档，而不是重试导出。
- 成功 stdout 是 JSON envelope，含 `output`（落盘绝对路径）与 `size_bytes`；传 `--app-id` 时回显 `app_id`。流式写盘，大仓库安全；失败不留半个文件。
### 错误处理
| 情况 | 怎么办 |
|---|---|
| 代码不在归档（422） | 该应用产物存在文件存储、不在可归档产物里 → 改用 `+file-list` / `+file-download`，重试无用 |
| 权限不足（403） | 需要该应用的下载权限；**持有分享 token ≠ 有权限** |
| 应用不存在（404） | `+list --keyword <name>` 核对 app_id |
| 归档过大（413） | 超导出体积上限，改用 `+file-download` 逐文件取 |
| 参数报错 | `--app-id`/`--meta-token` 恰给一个、都要裸标识符；`--checkpoint-id` 要正整数 |
---
## §3 定位与收尾
- **定位应用**：有 app_id 用 `+get --app-id app_xxx`；只有应用名用 `+list --keyword "名字"`。只接受 `app_` 开头，不要把 `cli_` 开头的飞书应用 ID 传进来。
- **`is_published=true` 只代表历史上发布过，不代表最新代码已部署**——必须有本轮 `+release-get` 观察到 `finished`；不要凭 `is_published` 或 `+list` 判定"已上线"。

## Agent 规则速记
1. 有现成 HTML/静态站、只要可分享链接 → `+deploy --file-path`（单文件）或 `--dir`（目录）；要拿代码快照 → `+export`。
2. 路径一律相对 cwd，先 `cd` 到产物目录；绝对路径会被拒。
3. 复发布带上一次的 `--app-id`，别靠幂等 key 猜；要自定义应用名先 `+create` 再用返回的 app_id 发。
4. 凭证文件命中先移出发布范围，不要习惯性加 `--allow-sensitive`。
5. 发布是异步的，`+release-get` 到 `finished` 才算成。
6. `+export` 导出的是最后提交/检查点、不是沙箱当前态。
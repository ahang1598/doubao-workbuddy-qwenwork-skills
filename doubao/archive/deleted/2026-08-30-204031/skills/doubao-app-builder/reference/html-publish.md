# html-publish 敏捷发布链路

把本地已有的 HTML 文件 / 静态产物目录用 `lark-cli` 发布为可访问应用。本链路只负责上传与发布，不生成、不改写 HTML 内容。应用属于用户资产，命令默认用 `--as user`。运行时命令事实以 `lark-cli apps +<cmd> --help` 为准。

## 何时用

**仅当用户需求里明确说要由你（Agent）发布为 HTML 应用时使用**（如「你直接帮我发布成应用」「用命令把这个页面发布上线」）。可发布的对象：

- 本地开发链路自产的产物（任务目录里的 `index.html`）。
- 用户提供的完整 HTML 成品 / 静态资源目录（原样发布，不改写内容）。

以下情形**不走本链路**：

- 用户只泛泛提出发布 / 托管 / 拿可访问链接诉求、没有明确要你执行发布：按原有交付步骤引导用户**点击预览后，通过预览界面的发布按钮自行发布**。
- 非纯 HTML + CSS + JS 产物（React / Vue 等框架项目、构建工具项目、SPA、全栈应用）。
- 当前环境不提供 `lark-cli`：如实告知，退回上述发布按钮引导。

## 发布前置门（第一步，先于任何其他动作）

命中本链路后，第一个动作是量三个尺寸，不是读文件内容、不是打包：

1. 单个 `.html` ≤ 10MB / 打包后 tar.gz ≤ 20MB / 未压缩候选文件总量 ≤ 200MB（客户端硬限制，任一超限即被拒绝上传）。
2. 任一超限 → 立即停止，把超限数字转述给用户，交还决定权。
3. 三项都通过 → 直接进入下面的 Workflow（命中本链路即代表用户已明确要求发布，无需再次向用户确认）。

## Workflow

```text
lark-cli apps +create --name <name> --app-type html
-> lark-cli apps +html-publish --app-id <app_id> --path <html_path>
-> lark-cli apps +release-get --app-id <app_id> --release-id <release_id from html-publish>
```

以下 `+<cmd>` 均为 `lark-cli apps +<cmd>` 的简写。

- `+create` 必填 `--name`、`--app-type html`，可选 `--description`。应用名可从页面 / 站点主题生成简洁名称，不要让用户手动提供。从输出 `data.app.app_id` 读取 app_id（需要取值时用 JSON 或 `--jq '.data.app.app_id'`）。
- `+html-publish` 必填 `--app-id`、`--path`；可选 `--allow-sensitive`（跳过凭据文件扫描）。输出含 `data.release_id`。
- `+release-get` 必填 `--app-id`、`--release-id`，轮询发布状态直到 `finished` / `failed`。

## app_id 规则

- `app_id` 必须是 `app_` 开头的应用 ID；`cli_` 开头的是飞书应用 ID，绝不能传入。
- 用户给出 `app_xxx` 或应用链接（如 `/app/app_xxx`）时直接提取。
- 重新发布同一个应用时复用原 `app_id`，重新执行 `+html-publish` 并用新的 `release_id` 查询状态；没有 app_id 才 `+create` 新建。

## 路径规则

- `--path` 只接受当前工作目录内的相对路径，可以是单个文件或目录；入口必须是 `index.html`。
- 单文件传 `./index.html`（文件名必须是 `index.html`）；目录传 `./site`（目录根下必须有 `index.html`）；已在产物目录内可传 `.`。
- 不要在工作区根目录、用户主目录、仓库根目录等上层目录使用 `--path .`。
- 不要为了发布重复创建目录或复制文件；直接传已有的 HTML 文件或目录。
- 传绝对路径会报 `--path must be a relative path within the current directory`；先 `cd` 到目标目录再传相对路径，例如 `cd /target/dir && lark-cli apps +html-publish --path .`。

## 静态资源

本链路自产产物按 html-develop.md 资源已上传 CDN、无本地路径引用，无需处理本节。发布用户提供的成品时，如 HTML / CSS / JS 引用了本地图片、视频、音频、字体等静态资源：

- 发布前逐个用 `lark-cli apps +file-upload --app-id <app_id> --file <相对路径>` 上传（单文件上限 100MB），把代码里的本地引用替换为返回的 `download_url`，替换时保持原语义（`<img src>`、`<video src>`、CSS `url(...)`）。不要替换成 `+file-sign` 返回的 `signed_url`，签名链接有有效期。
- 只处理被 HTML / CSS / JS 引用的静态资源：不上传 `index.html` 主入口本身，不上传 `.env`、密钥、凭证、配置文件。
- `--file` 用执行命令时所在目录内的相对路径；文件在别处时先 `cd` 到其所在目录上传，上传完再回产物目录继续替换和发布。
- 每个文件上传一次即可，记录本地路径 → `download_url` 的映射（如 `file_map.json`），不要重复上传。
- 静态资源链接按 `app_id` 隔离：不要跨应用复用 `download_url`；为不同应用发布时，同一个本地文件也要用当前 `app_id` 重新上传替换。
- 发布前检查传给 `--path` 的内容：已替换为 `download_url` 的本地资源和 `file_map.json` 都不属于上传内容，直接从待发布文件 / 目录里清理，不要为"保持目录干净"另建目录或复制文件。

## 安全规则

`+html-publish` 默认拦截 `.env`、`.npmrc`、`.aws/credentials` 等凭据文件。只有用户明确要发布凭据示例文件或教程内容时才追加 `--allow-sensitive`，追加前先说明将包含哪些敏感候选文件。

## 发布状态查询

- 拿到 `release_id` 后用 `+release-get` 轮询，间隔不超过 3s，不要长时间静默等待。
- `status=publishing`：继续轮询。不要拿其它链接冒充"本轮发布的访问链接"。
- `status=finished`：发布成功，只回报发布状态和 `app_id`；不要自行拼接或输出链接（与「禁止输出应用地址」一致，系统会单独展示）。
- `status=failed`：输出已含 `error_logs`（`step` / `error_log`），据此向用户转述关键失败步骤和可行动的修复建议。
- 这里的「发布状态」仅指本链路刚发起的这次 release 的进度，是「你无法查询产物的发布状态」规则的唯一例外；app_builder_agent 产物的发布状态查询仍走「网页应用感知 / 问答」路由，其余发布状态一律如实说明无法查询。
- 命令失败时把 `error.hint` 转述给用户，不要原样甩 envelope JSON。

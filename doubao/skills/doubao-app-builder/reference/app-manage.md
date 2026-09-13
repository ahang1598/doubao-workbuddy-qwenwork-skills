# 已发布应用的管理

发布之外的应用操作：**改谁能打开、把代码导出来、查应用信息**。这些都不是发布动作，`+deploy` 一概不碰，[`publish.md`](publish.md) 也不覆盖。

什么时候读本文：

- 用户说「改可用范围 / 访问权限」「设成公开 / 组织内 / 只给某几个人」「别人能不能打开」「把链接发出去安全吗」
- 用户要「把这个应用的代码下下来」「导出源码」，包括别人分享给他的应用
- 你需要拿某个应用的 `meta_token`、`online_url` 或确认它存不存在

> 运行时命令事实以 `lark-cli apps <命令> --help` 为准。

---

## 一、先定位应用

| 手上有什么 | 怎么查 |
|---|---|
| `app_id` | `lark-cli apps +get --app-id app_xxx` |
| 只有应用名 | `lark-cli apps +list --keyword "名字"` |
| 分享链接 `/page/<token>` | 最后那段就是 `meta_token`，直接用它 |

- 只认 `app_` 开头的 ID。`cli_` 开头的是飞书应用 ID，**绝不能**传给 `apps +*` 命令。
- `+get` 的返回里除了 `app_id` 还有 **`meta_token`**——下面改权限要用它。

---

## 二、访问权限

🔴 **权限统一走 `drive` 域 + `meta_token` + `--type apps`。** 妙搭应用在飞书这边就是一种 Drive 资源，拿到它的 `meta_token` 之后，Drive 那整套权限命令都能用在它身上。**不要在 `apps` 域里找权限命令**——那下面没有，`apps +permission-get-setting` 这种是拼出来的，不存在。

第一步永远是拿 token：

```bash
lark-cli apps +get --app-id app_xxx      # 返回里的 meta_token 就是下面所有命令的 --token
```

拿到之后：

| 要做什么 | 命令 |
|---|---|
| 查权限设置（链接分享、复制下载、协作者管理） | `drive +permission-get-setting --token <meta_token> --type apps` |
| 查协作者 | `drive +member-list --token <meta_token> --type apps` |
| 加 / 移除协作者 | `drive +member-add` / `drive +member-remove`，同样 `--token` + `--type apps`；**高风险写操作，真实执行要 `--yes`** |
| 替用户向 owner 申请权限 | `drive +apply-permission --token <meta_token> --type apps` |

⚠️ **裸 token 必须显式带 `--type apps`**，省了会报参数错误（`--token` 也收完整 URL，那种情况才自动推断类型）。

🔴 **通用规则读 `lark-drive` skill**——档位怎么选、`91009`/`91010`/`91011`/`91012` 这些错误码怎么读、高风险写操作要确认到什么程度，那边是权威来源，别在这儿凭记忆拼：

```bash
lark-cli skills read lark-drive references/lark-drive-permission-guide.md
```

### 改公开权限：typed 命令用不了，走 v2

查是 shortcut 命令（支持 apps），**改却不行**：`lark-cli drive permission.public patch` 走 v1 接口，它的 `--type` 枚举只有 doc / sheet / file / wiki / bitable / docx / mindnote / minutes / slides，**没有 `apps`**（`permission.members create` 同理）。别在这条路上反复试，改要走 v2 的原始接口：

```bash
lark-cli api PATCH /open-apis/drive/v2/permissions/<meta_token>/public \
  --params '{"type":"apps"}' \
  --data '{"link_share_entity":"<档位>"}'
```

发之前先 `--dry-run`。`link_share_entity` 就是「谁能通过链接打开」这一档，五个取值：

| 取值 | 含义 |
|---|---|
| `closed` | 关闭链接分享，只有协作者能进 |
| `tenant_readable` / `tenant_editable` | 组织内获得链接的人可阅读 / 可编辑 |
| `anyone_readable` / `anyone_editable` | **互联网上**获得链接的人可阅读 / 可编辑 |

两个常见目标：

```bash
# 改成互联网可见（任何拿到链接的人可读）
--data '{"link_share_entity":"anyone_readable"}'

# 改成仅自己可见（关链接分享，顺带收掉复制下载）
--data '{"link_share_entity":"closed","security_entity":"only_full_access"}'
```

`security_entity` 管的是「谁能复制、创建副本、打印、下载」（`only_full_access` / `anyone_can_view` / `anyone_can_edit`）——放开链接分享时它不会自动跟着放开，用户要的话一起传。

v2 对 apps 有两处收窄，照 v1 档位填会被拒：

- `share_entity` **只认 `anyone` / `same_tenant`**，v1 那个 `only_full_access` 不行
- `external_access` **这个字段它不认**，别传。⚠️ 它在 v1 里管的是「是否允许内容被分享到组织外」——**往互联网方向放开时如果被拦（`91009` / `91010`），根因通常就在这个开关或租户策略上，不是你命令写错了**，照下面的错误码处置，别反复重试。

🔴 **raw api 没有确认门。** typed 命令把公开权限修改列为高风险、要 `--yes` 拦一道，`lark-cli api` 是 escape hatch，**这道门不存在**——「档位必须由用户选」只能靠你自己守。用户说「开放一下」「让大家能看」只是目标状态，没说组织内还是互联网、可读还是可编辑，**先把档位列给他选再动手**。

**改失败时先看错误码**，这几个不是缺 scope，重试也没用（详见 `lark-drive` skill）：`91009` 对外分享被租户安全策略管控（要管理员改组织级策略）、`91010` 该文档对外分享未打开、`91011` / `91012` 被密级策略拦截（让用户去页面做密级豁免或降级，**回复里要带上目标 URL**）。

改完再跑一次 `drive +permission-get-setting` 确认生效，**别拿命令返回成功当结果**。

## 三、导出应用代码：`+export`

用户要「把这个应用的代码下下来」时用它。**跨应用是它的核心价值**——别人分享给他的应用，对它没有开发权限也能导出，只要有下载权限。

```bash
lark-cli apps +export --app-id app_xxx --output ./src.zip
lark-cli apps +export --app-id app_xxx                 # 省略 --output，存成 ./<app_id>.zip
lark-cli apps +export --meta-token <share-token>       # 别人分享的应用
```

- `--app-id` 与 `--meta-token` **二选一**，且都只收**裸标识符**：`--meta-token` 取分享链接 `/page/<token>` 的最后一段，**整条 URL 传进去会被拒**。
- `--output` **必须是相对当前目录的路径**。
- `--checkpoint-id` 可选，正整数，导某个检查点；省略取默认分支最新提交（不要显式传 `0`）。

🔴 **导出的是默认分支上的最后一次提交，不是沙箱里的当前状态**——没提交、没发布的改动不在包里。发现「少了刚写的代码」时先确认那部分有没有发布过，**重试导出没有用**。

### 导不出来时

| 情况 | 怎么办 |
|---|---|
| 422 代码不在归档里 | 该应用产物在文件存储、不在可归档产物里 → 改用 `+file-list` / `+file-download`，重试无用 |
| 403 权限不足 | 需要该应用的下载权限；**持有分享 token ≠ 有权限** |
| 404 应用不存在 | `+list --keyword <name>` 核对 app_id |
| 413 归档过大 | 超导出体积上限，改用 `+file-download` 逐文件取 |

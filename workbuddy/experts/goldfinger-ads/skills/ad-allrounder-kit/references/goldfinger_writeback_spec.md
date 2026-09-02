# 金手指回灌规范（艾投 · 复盘产物写回金手指）

> **状态：✅ 已打通并自动化**。2026-08-25 实测 `tools/list` + 真实写入 + 回读校验全链路通过。
> **默认执行方式：直接跑 `scripts/goldfinger_sync.py`**（已封装鉴权/建项目/分片/回读校验），不要手写 curl。
> 本文件说明「艾投产出的复盘文档如何回灌金手指」，供主线四（复盘）与操作日志纪律引用。

---

## 〇、⚡ 标准做法：一条命令完成同步（优先用这个）

```bash
python3 scripts/goldfinger_sync.py \
  --project "踏雪香薰" \
  --md 复盘.md \
  --html 完整报告.html \
  --title "艾投·投放结案复盘_踏雪香薰_20260825" \
  --metrics '{"cost":72230,"orders":598,"cpa":120.79,"target_cpa":110,"roi":2.33}' \
  --intent '{"goal":"结案复盘","targetCpa":110,"actualCpa":120.79}' \
  --cron "0 21 * * *"
```

脚本已内建全部踩坑对策，输出 JSON 含 `written[]`（各 artifact id）、`verified{parsable/truncated/html_md5_match}`、`view_api`。
**判成功的唯一标准：`verified.truncated == 0` 且（有 HTML 时）`html_md5_match == true`。**

### ⚠️ 2026-08-25/26/27 破坏性变更（老调用方式会直接失败）

1. **MCP 强制鉴权（08-25 起）**：无凭证调用返回 `401 missing_bearer_token`；
   ⚠️ 也可能以 **JSON-RPC error（HTTP 200 + `code:-32001`）** 形式返回 —— 判失效要**两种都识别**。
2. **🔐 鉴权改为 OAuth 授权（08-27 起，当前方案）**：
   - **接入方式改为「连接器依赖」（08-31 起）**：专家包**不再自带 `.mcp.json`**，
     改为在 `plugin.json` 声明 `dependencies.connectors: ["jinshouzhi"]`，
     引用 WorkBuddy 已上架的**金手指连接器**；连接器卡片的名称/描述/图标由连接器自身提供，
     服务地址与 OAuth 配置也由连接器侧维护，**专家包内不重复声明**。
   - 连接器侧配置（供排查参考，不在专家包内）：服务名 `jinshouzhi`，`type: streamableHttp`，
     `x-workbuddy.auth.type = "oauth"`；**不再有 `headers`，不再有 tokenSchema 表单**。
   - 用户操作从「复制粘贴 Token」变为 **连接器 →「金手指 MCP」→ 点「连接」→ 跳转金手指授权**。
   - 授权后 `accessToken`/`refreshToken` 存平台**加密凭证库**（`.credentials.v3.json` 的 `mcpOAuth` 节点，
     AES-256-GCM），**不会以环境变量下发给脚本** —— 这是与旧 token 模式最本质的区别。
   - 服务端 OAuth 已就绪（实测）：`/.well-known/oauth-authorization-server` 与
     `/.well-known/oauth-protected-resource` 均 200；401 正确返回 `WWW-Authenticate: Bearer resource_metadata=...`；
     支持 `authorization_code` + PKCE `S256` + 动态注册（`/register`），scope `openid profile`。
   - **⚠️ 由此产生的调用优先级（重要）**：
     1. **首选直接调 MCP 工具 `mcp__jinshouzhi__*`** —— 平台自动带 OAuth 凭证，无需拿 token。
     2. 兜底才用 `goldfinger_sync.py` 直连 HTTP，且**仅联调/CI** 场景（须显式提供 `GOLD_FINGER_TOKEN`）。
   - **⛔ 绝不调用 `/api/mcp-personal-token/regenerate`** —— 会让已生效凭证立即失效。
   - 未授权/失效 → 抛 `TokenMissing` 并输出**大白话引导**（去连接器点连接授权），退出码 2；**不打堆栈、不静默失败**。
   - 自检：`python3 scripts/goldfinger_sync.py --check-token`。
   - ⚠️ **不要用 `/api/me` 校验凭证**：FAT 环境该接口**不校验** Bearer，无效凭证也返回 200「本地访客」，
     用它检查等于没检查。**必须打 MCP 通道**（脚本已改用 `list_projects` 探活）。
3. **参数从 `project` 改为 `project_id`**：`upsert_review_artifact` / `upsert_review_intent` / `upsert_review_schedule` / `get_project_context` 全部**只认项目 id，传项目名会报错**
   （报错原文：「请使用 project_id（list_projects 返回的 id），不要传项目名称 project」）。
   - 取 id：**优先 `list_projects()`（MCP 同源）**；`GET /api/projects` 仅供网页端参照，见下条。
   - **建项目**：`POST /api/projects {"name":"<项目名>"}` → 返回 id（金手指侧没有该项目时先建，不要挪用近似的测试项目）。
4. **工具调用失败可能是 HTTP 200 + `result.isError:true`**：须先查 `isError` 再解析 `content[0].text`，
   否则会把中文错误提示当 JSON 解析而崩溃。
5. **⛔⛔ MCP 与 REST 可能是两套数据源（2026-08-27 实测，阻塞级）**：
   - 现象：MCP `list_projects` **只返回 1 个 mock 项目 `proj_test_001`**（内容全空）；
     REST `GET /api/projects` 返回 **18 个真实项目**。双向互不可见：
     · MCP 读真实 id（如 `p45d63d29934e6a1e`）→ 「未找到项目」；
     · REST 读 mock id（`proj_test_001`）→ HTTP 404「项目不存在」。
   - **后果**：若「用 REST 建项目/查 id，再用 MCP 写复盘」，必然报「未找到项目」——
     这是最易踩的错配，旧版脚本正是这样失败的。
   - **对策（脚本已实现）**：`ensure_project()` **以 MCP 侧为准**查项目（写在哪就读在哪，保持同源）；
     检测到「REST 有、MCP 无，且两侧 id 集合无交集」时抛 `ProjectSourceMismatch`，
     输出明确诊断并 **退出码 3**，绝不静默降级、绝不假报成功。回读校验同样改走 MCP（REST 仅兜底）。
   - **根因在服务端**，艾投侧无法绕过：需金手指把 MCP 接到真实项目库。修好后重跑同步即可（复盘本地已留存）。
6. **API Key 读不到明文（安全设计，非缺陷）**：`get_project_context` 不返回 apikey 明文，
   需求单里只有 `apiKeyConfigured` 之类布尔标记。**要真连账户建单时，apikey 仍须用户显式提供**
   （或走 `validate_apikey` 校验连通性），不能指望从项目上下文里读出来。
7. **🛡️ REST 全线 401 与鉴权兜底（2026-08-27 实测，已实现兜底）**：
   - **现象**：外网环境 **REST 全部 401**（`/api/projects`、`/api/projects/{id}`、`/api/me`、`/api/mcp-personal-token`），
     错误原文：**「外网环境不支持企业网关身份，请完成 WorkBuddy 授权」**。
     ⚠️ 且 **REST 不认 MCP Token** —— 带 Bearer 也是 401；MCP 与 REST 是**两套独立鉴权体系**。
   - **好消息**：**MCP 通道带 Token 一切正常**（`list_projects`/`get_project_context`/`upsert_review_*` 均 ✅），
     服务端 401 提示也明确支持三类凭证：个人 MCP Token / OAuth token / 已登录会话（staffname / WorkBuddy Cookie）。
     （实测裸 `staffname` 头**无效**，须走真实登录态。）
   - **✅ 兜底策略（脚本已实现，实测通过）**：
     · **MCP 是唯一必需依赖，REST 降级为"可选增强"**。新增 `RestUnavailable` 异常 + `http_json_safe()`
       （REST 不可用返回 None 而不抛），`ensure_project` / 回读校验 / `--check-token` 全部改为可降级。
     · 实测：REST 全 401 下**完整同步依旧跑通**（11 条可解析 / 0 截断 / HTML MD5 一致），
       `--check-token` 也正常（仅身份展示字段为 null）。输出新增 `auth_mode` 标明当前走的凭证方式。
     · **唯一无法兜底的是"新建项目"** —— 建项目只有 REST 接口、MCP 侧无此工具。
       此时抛 `ProjectSourceMismatch` 并明确告知「请先在金手指网页端手动建好项目」，不假报成功。
     · **同步凭证页**：浏览器直读 REST 会 401 白屏，已加 401/403 拦截 + 降级说明
       （强调「**不代表复盘没同步成功**」，并给出 3 条确认路径：网页端登录查看 / 让艾投用 MCP 回读 / 看本地留存文档）。
   - **结论**：鉴权出问题时**能兜底，主链路（写复盘 + 回读校验）不受影响**；仅"自动建项目"与"凭证页直读"需降级处理。

---

## 一、能力现状（14 个工具，实测）

| 方向 | 接口 | 状态 | 用途 |
|---|---|---|---|
| 写 | `upsert_review_artifact` | ✅ 可用 | **复盘文档/日报/完整报告/操作日志回灌主通道** |
| 写 | `upsert_review_intent` | ✅ 可用 | 复盘意图（本次复盘目标/口径） |
| 写 | `upsert_review_schedule` | ✅ 可用 | 复盘定时（cron，与艾投每日日报自动化对齐） |
| 写 | `upsert_demand_brief` | ✅ 可用 | 需求单/策略产物写回「需求单确认」 |
| 读 | `get_project_context` | ✅ 可用 | 回读校验：`review.artifacts[] / intents[] / schedules[]` |
| 读 | `list_projects` | ✅ 可用 | 取准确 project id（回灌前必做） |
| 读 | `get_project_data` | ✅ 可用 | 拉近 N 天真实投放数据（消耗/曝光/点击/转化/ROI） |
| 读 | `list_creative_examples` | ✅ 可用 | 平台素材范例 |
| 其他 | `validate_apikey` / `open_config` / `adjust_project` / `bind_generated_creatives` / `upsert_copy_asset` / `upsert_brand_assets` | ✅ 可用 | 校验/开台/上线后轻调/素材中转/文案 |
| 读策略单 | `get_strategy` / `list_strategies` | ❌ **未暴露** | 路径B 仍走「用户贴确认单」过渡方案 |

**REST 接口（免鉴权可读，查看页就靠这个）**：
`GET /api/projects` 项目列表 ｜ `GET /api/projects/{id}` **项目全量详情含 review.artifacts** ｜
`POST /api/projects` 建项目 ｜ `GET /api/bootstrap` 五步定义与 agent ｜ `GET /api/me` 当前身份。

> 结论一句话：**复盘往金手指「写」是通的；从金手指「读策略单」还不通。**

---

## 二、回灌调用约定

### 主通道 `upsert_review_artifact`

必填 `project_id`、`title`、`payload`；可选 `kind`、`conversation_id`。

```json
{
  "project_id": "p45d63d29934e6a1e",
  "title": "艾投·投放日报_{offerName}_{YYYYMMDD}",
  "kind": "daily_report",
  "payload": {
    "source": "aitou_daily_review",
    "reportDate": "YYYY-MM-DD",
    "format": "markdown",
    "content_md": "<日报全文 Markdown>",
    "metrics": { "cost": 0, "conversions": 0, "cpa": 0, "target_cpa": 0 },
    "actions": ["<明日盯盘微调动作>"],
    "iterated": false
  }
}
```

**`kind` 取值约定**（艾投自定义，服务端不校验，保持一致便于金手指侧筛选）：

| kind | 对应艾投产物 |
|---|---|
| `daily_report` | 每日日报（唯一复盘报告） |
| `final_review` | 结案复盘（四段式） |
| `playbook` | 《项目打法》沉淀 |
| `operation_log` | 投放操作日志（8 要素） |
| `full_report_html` | 完整 HTML 分析报告（放 `payload.content_html`）**仅限 <60KB；超限必须改用下一行分片** |
| `full_report_html_chunk` | **大 HTML 报告分片**（>60KB 时用，带 chunkIndex/chunkTotal/fullMd5） |
| `deprecated_notice` | 作废标记（无删除接口时用来废弃脏数据） |

### 回读校验（每次回灌后必做）

调 `get_project_context({project})` → 在 `review.artifacts[]` 中按返回的 `id` 找到刚写的那条，**必须对 `payload_json` 执行 `json.loads`**：解析成功才算写入完整；若抛 `Unterminated string` 即为超 65535 字节被静默截断（详见第三节第 1 条）。再核对 `content_md` 长度 / `fullMd5` 等关键字段。

---

## 三、实测边界（重要）

1. **⛔ 单条 payload 硬上限 65535 字节（MySQL TEXT），超出即被服务端「静默截断」** —— **这是本接口最大的坑**：
   - 超限时**接口照样返回成功 + 正常 id，不报任何错**；只有回读 `payload_json` 时才发现 JSON 被砍断、无法 parse。
   - 实测：67.2KB 的 HTML 报告（58053 字符）写入后回读仅剩 65533 字节（保留 93.5%），`json.loads` 直接抛 `Unterminated string`。
   - ⚠️ **绝不可凭"返回成功"就判定回灌成功**——2026-08-25 首轮验证正因只看返回码、未回读，误判 114KB 写入通过。
   - **强制纪律：每次回灌后必须回读并 `json.loads` 解析 `payload_json`，解析通过才算成功。**
2. **超限对策 —— 分片回灌（实测 MD5 完全一致）**：
   - 单片正文按 **utf8 字节 ≤ 40000** 切（预留 JSON 转义膨胀 + 其他字段余量；中文转义后可能翻倍，不要贴着 65535 算）。
   - `kind` 用 `full_report_html_chunk`，payload 带 `chunkIndex` / `chunkTotal` / `fullMd5` / `fullCharLen` / `content_html_chunk` / `reassemble` 说明。
   - 回读时按 `chunkIndex` 升序拼接，用 `fullMd5` 校验。实测 67.2KB 报告切 4 片，拼回后 58053 字符、MD5 与本地文件完全一致 ✅。
   - Markdown 级日报/复盘（1~3KB）远低于上限，**无需分片**。
3. **append 语义，不是 upsert**：接口名叫 upsert，但**同名 title 重复写入会新增一条记录、不覆盖旧的**。
   - 好处：契合艾投「追加式不覆盖」纪律，回灌历史天然留痕。
   - 代价：**重试/重复调用会产生重复记录**。故失败重试前先 `get_project_context` 回读确认是否已写入成功。
4. **⛔ 没有删除接口**：14 个工具中无任何 delete/remove 能力。写错/被截断的脏数据**无法通过 MCP 删除**，只能：
   - 新写一条 `kind="deprecated_notice"` 标记作废（payload 记 `deprecates` 原 id + `reason` + `replacedBy`）；
   - 并告知用户「彻底清理需去金手指页面操作」。**所以宁可先小样试写，别直接灌大批量。**
5. **编码**：中文、Markdown 表格、emoji（🚀🟢🟡🔴）、`¥` 与 `↑↓` 均无损往返。
6. **写入会改项目状态**：写复盘材料后项目 `status` 自动从 `demand_ready` → `reviewing`。属预期行为，但**要提前告知用户**，别让他以为项目被误改。
7. **项目须已存在**：`project` 必须是金手指侧已有项目。回灌前先 `list_projects()` 核对名称，不要凭用户口述的项目名直接写，避免写错项目或报错。
   - 实测踩点：本地报告叫「踏雪香薰」，金手指侧无此项目，须先与用户确认落到哪个项目，**不可自行猜一个近似的就灌**。
8. **`upsert_review_schedule` 的 `enabled` 传 `false`** —— 与艾投「自动化默认不开」纪律一致；回读为 `0`，需用户去页面手动开启。
9. **无鉴权头**：端点当前为 FAT 环境、无 Authorization 即可调用；`list_projects` 返回的是当前用户名下项目。**注意这是测试环境，生产切换后需复验。**

---

## 三·五、标准回灌流程（照此执行）

1. `list_projects()` → 与用户确认落点项目名（不猜）。
2. `get_project_context({project})` → 看该项目已有哪些复盘材料，避免重复灌。
3. 估算体量：payload 序列化后 utf8 字节 > 60000 → 走分片；否则单条写。
4. 调 `upsert_review_artifact` / `upsert_review_intent` / `upsert_review_schedule`。
5. **回读校验（强制）**：`get_project_context` → 逐条 `json.loads(payload_json)` → 解析通过 + 关键字段/MD5 命中，才算成功。
6. 把 artifact id 与校验结论如实报给用户；有截断/失败就说清哪一步断了。

---

## 三·六、打开金手指主台（`open_config`）与页面侧限制

**调用**：`open_config({strategy})`，strategy 为自由结构 object（建议带 offerName / projectId / entryIntent / 关键指标 / 回灌产物 id）。返回：
- `deepLink`：`/pre-launch?session={sessionId}` 短链（推荐给用户，可读性好）
- `inlineDeepLink` / `recommendedLink`：`#s=` 开头的 gzip+base64 内联长链（服务端 message 建议用 recommendedLink）
- `expiresInMinutes: 30` —— **⏱ session 仅 30 分钟有效，过期需重新调用**
- `inlineMode`(lite/full) / `inlineBytes` / `degraded`（策略过大时降级标志）

**⛔ 两个页面侧硬限制（2026-08-25 用真实浏览器实测，前端 v1.0.48）**：

1. **深链不能用 present_files 预览面板打开** —— 金手指是 React SPA，`/pre-launch` 只返回约 945 字节空壳（`<div id="root">`），正文全靠 JS 客户端渲染；内置预览面板不执行 SPA 打包脚本 → **显示空白，用户会以为链接坏了**。
   - ✅ 正确做法：**直接把可点击 URL 写在回复里**，让用户在真实浏览器打开；需要自证页面可用时用 agent-browser 截图给用户看。
   - 排查口径：页面 200 + `/assets/*.js`(327KB) `/assets/*.css`(35KB) 均 200 → 服务端没问题，就是预览面板渲染不了 SPA。
2. **「效果复盘」步骤默认被锁（disabled）** —— 五步导航中「需求单确认」「AI投手准备」可点，**「投放素材准备」「投放执行」「效果复盘」均为 disabled**，须按顺序走完前置步骤才解锁。
   - ⚠️ 即使复盘材料已通过 `upsert_review_artifact` 回灌成功（接口+回读双验证通过），**用户当前也看不到** —— 这是页面流程门禁，不是回灌失败。
   - **必须提前向用户说明这一点**，否则用户点进去找不到复盘内容会认为回灌没成功。

**门禁的确切解锁条件（已反编译前端 `index-*.js` 确认）**：
步骤条 disabled 判断为 `q = E===0 || (E===1 && !!a) || (E>=2 && Ds && E<=ut)`，其中 `Ds = (Ts===100)`，
`Ts` 是「AI投手准备」里信息配置的完成度（API Key + 账户 ID + 各前置项全部填完才 100）。
→ **结论：不填完 API Key／账户 ID，「效果复盘」永远点不开。这是页面死逻辑，外部无法绕过。**

---

## 三·七、✅ 解决「灌了看不到」——同步凭证查看页（标准交付物）

既然页面门禁绕不过，就**不依赖页面**给用户看结果。做法：生成一个自包含 HTML「同步凭证页」，
运行时用 `fetch` 实时读 **免鉴权** 的 `GET /api/projects/{id}`，自动拼分片并渲染。

**要点**：
1. **数据实时来自金手指、不是本地副本** —— 页面顶部写明这一点，页脚再声明一次，避免用户以为是假的。
2. **必带「已同步存储完成」凭证区**：存储平台 / 项目名 / 项目 id / 校验结果（N/N 条完整 · 0 条截断）+ 最近读取时间。
3. **自动拼 HTML 分片**：按 `chunkIndex` 升序合并，显示「已拉取 4/4 片，完整可用」；缺片要标红。
4. **列出全部存储凭证**：逐条列 artifact 的 kind / title / id，能 `JSON.parse` 打 ✓、不能打 ✗，用户可自行核对。
5. **提供四个出口**：从金手指重新拉取 / 打开金手指平台 / 查看原始存储数据（直链 API）/ 打印存 PDF。
6. UI 沿用金手指统一皮（腾讯蓝 `#0052D9` + banner 品牌行 + section 序号），**成本涨标红跌标绿**。
7. 存 `outputs/`，文件名如 `金手指同步凭证_{offerName}复盘_{YYYYMMDD}.html`。

> 参考实现：`outputs/金手指同步凭证_踏雪香薰复盘_20260825.html`（实测可从金手指拉到 5 条材料、4/4 分片完整）。

---

## 三·八、🔁「生成复盘 → 自动同步 → 给链接」标准流程（主线四收尾必走）

复盘一旦产出，**不再问用户要不要同步，直接按下列顺序做完**（这是用户 2026-08-25 明确要求的流程）：

| 步 | 动作 | 说明 |
|---|---|---|
| 0 | **查凭证** | `--check-token`；未配置→**先给引导，别硬跑**（话术见下），配好再继续 |
| 1 | 本地落盘 | 先写 `outputs/投放复盘/…`，本地是唯一真相源 |
| 2 | 确认项目 | `GET /api/projects` 找同名项目；**没有就 `POST /api/projects` 新建**，绝不挪用近似项目 |
| 3 | 自动同步 | 跑 `goldfinger_sync.py`（自动分片/写意图+定时） |
| 4 | 强制回读校验 | 看 `verified.truncated==0` 且 `html_md5_match==true`，否则视为失败 |
| 5 | 生成同步凭证页 | 按 三·七 产出 HTML，`present_files` 打开 |
| 6 | 告知用户 | 明确说**已同步存储好了**，给出：项目名 + 项目 id + 材料条数 + 校验结论 + 凭证页链接 + 平台地址 |
| 7 | 提示门禁 | 顺带说明「平台页面第五步需填完 API Key/账户 ID 才解锁，所以先用凭证页看」 |

**未授权时的大白话话术（照这个说，别甩报错）**：
> 同步到金手指前，得先授权一下——**不用填什么码，点一下跳转同意就行**。授权代表你的账号，连好之后**只会读写你自己的项目**，不会串到别人那儿。
> 三步：① 打开 WorkBuddy →「连接器」→ 找到「金手指 MCP」；② 点「连接」，跳到金手指登录并同意授权；③ 跟我说一声，我立刻重新同步。
> 复盘我已经先存在你本地了，不会丢。

**🔁 兜底指引（上面三步走不通 / 授权失败时，改说这段）**：
> 金手指能力**仅在 WorkBuddy「营销通」应用中可用**。如遇授权失败，请将 WorkBuddy 升级至最新版本后，打开 WorkBuddy 客户端，进入「营销通」应用完成授权。授权成功后将自动继续 MCP 连接。
>
> 复盘/日报我已经先存你本地了，不会丢——授权好跟我说一声，我立刻重新同步。

⚠️ 纪律：连接器里点不到、点了没反应、授权后仍报未授权 → **直接给这段兜底指引**，不要让用户在连接器里反复试、不要甩报错堆栈、不要静默失败。

**失败时**：如实说哪一步断了（未授权/授权过期/项目不存在/内容被截断），不假报成功，不重复灌（append 语义会产生重复）。

---

## 四、艾投执行纪律（回灌也要人在环上）

- **回灌属于「写外部系统」，默认先出清单、经用户确认再写**。与「不擅自动账户」同级：日报/复盘先在对话里给用户看，用户说"灌进金手指"才调接口。
- **本地优先、双写留痕**：先按既有规则写本地 `outputs/投放复盘/日报/`、`outputs/投放操作日志/`，再回灌金手指。本地是唯一真相源，金手指是同步副本。
- **回灌结果如实汇报**：写成功要把返回的 artifact `id` 和项目名报给用户；失败就说失败、说清哪一步断了，不假报成功。
- **不重复灌**：同一份日报只灌一次；确需修订，新灌一条并在 title 标 `_修订N`，靠 append 语义留下版本轨迹。

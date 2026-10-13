# 文件检索

所有命令的 stdout 输出遵循 NDJSON 协议，每行一个 JSON 对象（统一为 `IApiType` 格式）。提示信息输出到 stderr（仅 `--verbose` 模式可见）。

## NDJSON 统一输出格式（IApiType）

所有 stdout 输出行均遵循以下结构：

```typescript
{
  code?: number;       // 状态码，0 为成功，负数为 CLI 错误码（progress 类型不含 code）
  msg: string;         // 状态描述
  action: string;      // 命令名称（如 "search"）
  type: string;        // 输出类型："result" | "progress" | "list" | "artifact"
  data: object;        // 业务数据
}
```

- **`type: "result"`** — 命令最终结果，每个命令的最后一行（降级场景下也是最后一行）
- **`type: "progress"`** — 长任务（上传/下载）的中间进度
- **`type: "list"`** — 列表条目（如 search 的文件列表）
- **`type: "artifact"`** — 副产物指针（如 search 落盘 jsonl 的路径）；`search` 命令落盘成功时追加在 result 行之后

**失败处理**：命令失败时通过 `CliExitError` 抛出（进程退出码 1），顶层 `quark-drive.ts` 的 catch 捕获后输出一行 `IApiType` 格式的错误结果到 stdout：

```jsonl
{"code":<错误码>,"msg":"<错误信息>","data":{},"action":"<命令名>","type":"result"}
```

- **`code`**：来自 `CliExitError.errorCode`，即 `error_constants.ts` 中定义的负数错误码
- **`msg`**：来自 `CliExitError.message`，为 `CLI_ERROR_MAP` 中的默认消息或命令中通过 `customMsg` 覆盖的动态消息
- **`data`**：固定为 `{}`
- **`action`**：来自 `CliExitError.action`，即命令名称
- **`type`**：固定为 `"result"`

---

## 命令

### 搜索文件（search）

在用户网盘中搜索文件。不支持分页，一次最多返回 100 条结果。

#### 适用与分流

用户可以一句话查找网盘里的文件，可以用关键词找文件，可以描述图片画面（比如"咖啡馆里的小猫"），也可以通过时间、地点、人物、场景、物体等多个维度的组合进行搜索（比如"2025年和妈妈在西安大雁塔下拍的合照"），或者根据主题找文件（比如"考研资料"）。

> **搜索 vs AI 助手区分规则**：当用户 query 同时包含位置描述（"网盘里的…文件夹"）和内容理解意图（「总结」「分析」「讲解」等动词 + 具体提问），应走 **AI 助手**流程（search --stdout-only → summary/qa），而非搜索即交付。搜索仅用于「查找文件」本身，不用于「理解文件内容」。
> - ✅ "在夸克网盘的工作文档文件夹里，帮我总结一下上个季度的DAU环比增长是多少" → AI 助手（qa），不是搜索
> - ✅ "网盘里的周报，上季度业务数据表现怎么样" → AI 助手（summary），不是搜索
> - ✅ "找一下网盘里的年终汇报" → 搜索（纯粹查找文件，无内容理解意图）

用户通常这样进行查找：

- 找一下网盘里xxx
- 夸克网盘里三亚日落的照片
- 夸克网盘里的英语四六级报名表
- 我的网盘里存的李永乐真题试卷
- 找一下网盘里我和妈妈的合照
- 找一下夸克网盘我存的易烊千玺的照片
- 我昨天备份的照片帮我找出来
- 查找网盘所有图片和视频

#### 入参

```bash
node scripts/quark-drive.cjs search --keyword <KEYWORD> [--size <NUMBER>] [--category <NUMBER>] [--stdout-only]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--keyword <string>` | string | 必填 | — | 搜索关键词（最大 50 字符） |
| `--size <number>` | number | 选填 | `100` | 返回结果数量（1-100），完整结果请查看落盘 artifact |
| `--category <number>` | number | 选填 | — | 按分类过滤（0:文件夹 1:视频 2:音频 3:图片 4:文档 5:种子 6:其他 7:压缩包 8:应用） |
| `--stdout-only` | string | 选填 | — | 仅输出到标准输出（用于中间步骤，搜索结果不作为最终结果展示） |

> **重要：`--category` 使用规则**
> - keyword 提取必须保留文件类型描述词（如"照片""视频""文档"等），不能只提取主题词而丢弃类型词。搜索 API 会根据 keyword 自动识别并限定返回的文件类型，**绝大多数场景不需要传 `--category`**
> - 仅当用户明确要求搜索单一类型（如"找所有视频"）且 keyword 不足以表达类型意图时，才传 `--category`
> - **禁止**为了搜索多种类型（如"图片和视频"）而拆分成多次调用（分别传 `--category 3` 和 `--category 1`），直接用自然语言 keyword 搜索一次即可
> - 示例：
>   - 用户说"搜索网盘里的康乃馨照片" → `--keyword "康乃馨照片"`，不传 `--category`（保留"照片"类型词）
>   - ❌ 错误：`--keyword "康乃馨"`（丢失了文件类型"照片"）
>   - 用户说"查找网盘所有图片和视频" → `--keyword "图片和视频"`，不传 `--category`
>   - 用户说"查找网盘大海的照片" → `--keyword "大海的照片"`，不传 `--category`

> **重要：搜索无结果时规则（严格执行）**
> - 当搜索返回 `total=0` 时，agent 必须**立即停止**，直接告知用户未找到匹配文件，并建议用户自行调整搜索词或检查网盘中是否存在该文件
> - **绝对禁止 agent 自行更换、缩短、拆分或改写 keyword 后重新调用 search**——即使 agent 认为换词可能找到结果也不允许
> - 每次搜索任务只调用一次 search，无结果即终止，不做任何重试

> **搜索即交付原则（严格执行）**
> - 当用户意图是「查找/搜索/浏览」文件时（"找几张…给我""帮我找出来""搜一下""有没有…的照片"等），**search 执行完毕即为任务完成**——搜索结果卡片会自动呈现给用户，这就是「给用户」的方式
> - "给我""帮我找出来""发给我看看"在搜索语境下等同于"展示搜索结果"，**绝对禁止**将其解读为需要额外执行 share（分享）、download（下载）、organize（整理）等操作
> - search 之后**禁止自行追加任何操作**，除非用户在搜索结果呈现后**明确发出新指令**（如"把这些分享给朋友""整理到一个文件夹""下载到本地"）
> - 判断标准：用户原始 query 中是否包含明确的操作动词（"分享""整理""下载""移动""上传"）或内容理解动词（"总结""分析""讲解""解读"）。仅包含"找""搜""查""看""有没有"等检索意图词时，search 即终止；包含内容理解动词时不适用搜索即交付，应走 AI 助手流程（search --stdout-only → summary/qa）

> **重要：`--stdout-only` 使用规则**
> - 搜索结果需要最终展示给用户时，不传 `--stdout-only`
> - 搜索仅作为中间步骤获取文件 FID 时（如助手场景），传 `--stdout-only`

#### 成功出参

无论搜索是否有结果，**stdout 始终输出 NDJSON `type: "result"` 行**。

##### NDJSON result 输出

每次搜索成功都以标准 NDJSON result 格式输出：

```jsonl
{"code":0,"msg":"成功","data":{"total":2274,"file_list":[...],"check_all_link":"https://pan.quark.cn/skill#/search-result?sp=xxx"},"action":"search","type":"result"}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.total` | number | 搜索结果总数（服务端返回的实际匹配数量） |
| `data.file_list` | array | `BrowseFileItem` 数组，wild 模式**最多输出前 5 条预览**，完整结果见 artifact 落盘文件 |
| `data.check_all_link` | string | **wild 模式特有字段**。当结果多于 5 条（即有记录未在 `file_list` 展示）时提供，指向在网盘中查看全部搜索结果的地址；agent 须在列表展示后透出该链接。结果不超过 5 条时可能不返回该字段 |
| `data.browse_hint` | string | **wild 模式特有字段**。与 `check_all_link` 同时出现，提供在浏览器中查看的提示文案。当该字段存在时，agent **必须**将其文案展示给用户 |

无结果时 `data.total` 为 `0`，`data.file_list` 为空数组 `[]`。

> **agent 须知**：当输出的 `data.total` 为 `0` 且 `data.file_list` 为空数组 `[]` 时，表示用户网盘中**没有找到任何匹配的文件**。agent 应明确告知用户搜索结果为空（如"未在网盘中搜索到与 XXX 相关的文件"），并建议用户自行调整搜索词。禁止将空结果误解为命令执行失败——`code: 0` 表示命令本身执行成功，只是没有匹配项。**禁止 agent 在收到空结果后自行更换 keyword 重新搜索。**

##### 搜索结果展示

> **agent 须知**：搜索完成后，agent 必须将搜索结果以**表格**形式展示给用户。表格列包括：**缩略图**、**文件名**、**大小（或文件数量）**、**类型**、**修改时间**、**查看链接**。同时用 **1-2 句话**简要概括搜索结果的整体情况（如"为你找到了 N 个相关文件，主要是旅行照片"）。
>
> **⚠️ 缩略图列约束（必须遵守）**：「缩略图」是**条件列**——仅当 CLI 返回的展示条目中**存在至少一条带非空 `big_thumbnail`** 时才出现。**若本次展示的所有条目都没有返回 `big_thumbnail`（字段缺失或为空），表格一定不能出现「缩略图」这一列**（整列删除，而非保留空列或填"—"）。**禁止**为没有缩略图的结果（如纯文件夹、无缩略图的文档）虚构、补全或留空占位缩略图列。
>
> **展示按 CLI 返回条数即可**：CLI 的 result 中 `file_list` **最多 5 条预览**，**有几条就在表格中展示几条**；**不要**为了补充展示而去读取 artifact 落盘文件。当 `data.total` 大于实际展示条数时，须注明"共找到 N 个文件，以上为部分结果"，并透出 `check_all_link`。
>
> **落盘文件何时读**：artifact 落盘文件**不用于**搜索结果展示，仅在用户**连续发起新指令**、需对搜索到的全部文件执行后续操作（share / download / organize 等）时才读取以获取全量 FID。例：用户先"搜索 xxx 图片"（仅展示 `file_list`），再说"分享这些图片"——此时才从落盘文件读取全量结果。
>
> **透出查看全部地址与 browse_hint（wild 模式必做）**：列表展示完毕后，当 `data.check_all_link` 存在且非空时，agent **必须**：
> 1. 将该链接以可点击形式展示给用户（如 Markdown `[点击查看全部搜索结果](check_all_link)`）。
> 2. 同时**完整展示该链接的 URL 原文**，方便用户手动复制。
> 3. 如果结果中包含 `browse_hint` 字段（与 `check_all_link` 同时出现），**必须**原样展示 `browse_hint` 的文案给用户（如「当前页面可能无法保持网盘登录状态。建议复制链接，在浏览器中打开，以获得更稳定、完整的浏览体验。」），**禁止省略或改写**。
> `check_all_link` 为空或不存在时省略该提示。

> **搜索后操作强制流程**：仅当用户在搜索结果呈现后连续发起新指令、要对搜索到的文件执行后续操作（share、download、organize 等）时，才需要读取落盘文件；展示搜索结果阶段不需要读。触发后必须按以下步骤执行：
> 1. 从 search 的 stdout 中提取 `type:"artifact"` 行的 `data.file_path`
> 2. 读取该 jsonl 文件，逐行解析获取全量 FID 列表
> 3. 将全量 FID 列表传入后续命令（如 `share <FID1> <FID2> ...`）
>
> 禁止直接使用上下文中至多 5 条的预览 list（`file_list`）作为后续命令的输入，该 list 是截断的预览数据，不代表完整搜索结果。

**表格列与 `BrowseFileItem` 字段映射**（字段值取自 NDJSON result 的 `data.file_list` 条目）：

| 表格列 | 字段 | 展示规则 |
|--------|------|---------|
| 缩略图 | `big_thumbnail` | wild 模式特有字段、**条件列**。当存在缩略图时**尽量以图片形式展示**——表格内用 Markdown 图片语法 `![](big_thumbnail)` 渲染；部分条目 `big_thumbnail` 为空时该格留空或填"—"。**但若展示的全部条目都没有 `big_thumbnail`，则整列不要出现**（见上方「缩略图列约束」） |
| 文件名 | `filename` | 直接展示完整文件名 |
| 大小 / 文件数量 | `size` / `includeItems` | **表头随数据自适应**：① 条目含 `size`（文件类型）→ 将字节数换算为人类可读单位（如 `1572864` → "1.5 MB"）；② 条目含 `includeItems`（文件夹类型，无 `size`）→ 展示「**xx 个文件**」（如 `12 个文件`）。**表头取值规则**：本次结果全部为文件（仅 `size`）→ 表头「大小」；全部为文件夹（仅 `includeItems`）→ 表头「文件数量」；**混合时**统一用表头「文件数量」，各行按自身字段分别展示大小或「xx 个文件」 |
| 类型 | `category` / `obj_category` | 将 `category` 数字映射为中文类型（0:文件夹 1:视频 2:音频 3:图片 4:文档 5:种子 6:其他 7:压缩包 8:应用），或直接使用 `obj_category` 文案 |
| 修改时间 | `updated_at` | 毫秒时间戳，格式化为 `YYYY-MM-DD HH:mm` 等可读时间 |
| 查看链接 | `check_link` | wild 模式特有字段。以可点击链接形式展示（如 Markdown `[查看](check_link)`）；为空时留空或填"—" |

> **⚠️ 注意**：`big_thumbnail` 与 `check_link` 为 **wild 模式特有字段**，千问模式不返回。展示时优先用图片渲染缩略图、用可点击链接渲染查看链接，提升用户浏览体验。

##### 追加 `type: "artifact"` 行

`search` 命令每次成功执行都会把完整搜索结果写入本地 jsonl 文件，并在 stdout 末尾追加一行 `type: "artifact"` NDJSON 回传绝对路径：

```jsonl
{"code":0,"msg":"成功","data":{"file_path":"/Users/x/.quarkclouddrive/search-results/<userId>/search-20260416-153012-a7b3c9.jsonl","count":100,"format":"jsonl","description":"完整搜索结果已写入此文件。每行一个 BrowseFileItem JSON，无 code/msg/type 包装。需要全量数据（过滤、排序、二次处理）时读此文件；stdout 的 list/result 行仅供预览。"},"action":"search","type":"artifact"}
```

**artifact data 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_path` | string | 落盘 jsonl 文件的绝对路径 |
| `count` | number | 文件实际写入的条数（= `result.data.total`） |
| `format` | string | 固定 `"jsonl"`，标识文件内容格式 |
| `description` | string | 固定文案：说明文件是全量搜索结果、每行一条 BrowseFileItem、如何消费 |

artifact 行是纯增量（可按调用方需求选择读或忽略）。

##### 落盘产物

| 维度 | 规则 |
|------|------|
| 目录 | `<skill_dir>/scripts/search-results/<userId>/`（`userId` 来自本地 config 登录账号，按用户隔离；未登录时为 `default`） |
| 文件名 | `search-<YYYYMMDD-HHMMSS>-<hex6>.jsonl`（秒级时间戳 + 6 字节随机后缀） |
| 内容 | 每行一个 `BrowseFileItem` JSON，**无 `code/msg/type` 包装** |
| 生命周期 | 每次 `search` 前自动清理目录下 mtime > 24h 的旧 `.jsonl` / `.jsonl.tmp` |
| 原子性 | tmp + rename 原子写，失败时残留 `.tmp` 由后续清理兜底 |

##### 降级行为

当目录创建或文件写入失败（如磁盘满、权限问题），CLI **不会**报错退出，而是：

- stdout **不输出** `type: "artifact"` 行
- `--verbose` 下 stderr 打印 `[WARN] 搜索结果落盘失败: <message>`
- 进程退出码仍为 0，原 list / result 行完全不受影响

调用方判定：`stdout` 中出现 `type: "artifact"` → 可读 `data.file_path`；未出现 → 搜索结果仅通过 NDJSON result 输出。

##### 消费示例

**bash + jq**：按 category 过滤文档类文件

```bash
file_path=$(node scripts/quark-drive.cjs search --keyword 报告 --size 100 --aggregate \
  | jq -r 'select(.type=="artifact") | .data.file_path')
jq -c 'select(.category==4)' "$file_path"
```

**Node.js**：逐行读取全量结果

```javascript
const readline = require('readline');
const fs = require('fs');

const rl = readline.createInterface({
  input: fs.createReadStream(filePath),
  crlfDelay: Infinity,
});
for await (const line of rl) {
  if (!line) continue;
  const item = JSON.parse(line); // 完整 BrowseFileItem
}
```

**何时读 artifact / 何时解析 stdout**：

- 仅展示搜索结果 → 从 NDJSON result 的 `data.file_list` 中解析并以表格展示给用户
- **对搜索结果执行后续操作（share、download 等）** → **必须**读 `artifact.data.file_path` 指向的 jsonl 获取全量 FID
- 大数据过滤排序二次处理 → 读 `artifact.data.file_path` 指向的 jsonl

#### 失败出参

| 错误码 | 默认错误信息 | 触发场景 |
|--------|-------------|---------|
| -1301 | 文件浏览器实例不存在 | SDK 文件浏览器初始化失败 |
| -1302 | --size 必须为 1-100 的正整数 | `--size` 参数不是 1-100 的正整数 |
| -1303 | 搜索操作失败 | SDK `searchFiles` 返回 `status !== 0`，`msg` 附带 SDK 返回的 `error_info` |
| -1304 | --category 必须为 0-8 的整数 | `--category` 参数不是 0-8 的整数 |

**失败示例**：

```jsonl
{"code":-1302,"msg":"--size 必须为 1-100 的正整数","data":{},"action":"search","type":"result"}
```

```jsonl
{"code":-1303,"msg":"search failed: errno=31001, message=invalid token","data":{},"action":"search","type":"result"}
```

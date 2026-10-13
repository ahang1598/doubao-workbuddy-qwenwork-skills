# 04 · share — 配置分享

> 把当前已绑定的巡店配置发给同事 / 接收他人分享的配置。**配置时操作**，与派发解耦。

---

## 速查表

| 想做什么 | 直接看 |
| :--- | :--- |
| 把当前 AI表格 配置发给同事 | [#分享配置发送方](#分享配置发送方) |
| 自己拿到了别人发的 BASE_ID | [#接收他人分享的配置](#接收他人分享的配置) |
| 生成标准格式分享语句 | [`share generate`](#share-generate) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py share --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### share generate

- **`--base-id` 不传时**默认读当前已绑定的 base_id；**未绑定且未传** → CLI 退出码 1，应先引导用户走 `init create` 或 `init url`
- **输出**：固定格式的分享语句到 stdout（含 `BASE_ID = BAS_xxx` + AI 表格链接 + 可选备注），便于用户**整段复制转发**

**Agent 决策提示**：
- 用户在对话中粘贴了「BASE_ID = BAS_xxx」字样 / 直接粘贴 `BAS_xxx` → 进入「[接收他人分享的配置](#接收他人分享的配置)」处方
- ⚠️ 工具**不支持**自动给对方加 AI 表格协作者，必须提示用户在 AI 表格右上角『分享』菜单**手动**添加为管理员 / 可编辑

---

## 分享配置（发送方）

**触发信号**：用户说"把这套巡店任务给同事用一下" / "把当前配置分享出去"。

### 步骤

1. **检查初始化**：先 `init validate`，未初始化则不能分享，引导用户先绑定 AI表格
2. **生成分享语句**：
   ```bash
   cd <SKILL_DIR> && uv run python scripts/cli.py share generate
   # 想加备注：
   cd <SKILL_DIR> && uv run python scripts/cli.py share generate --note "华东大区使用，9 月起切换"
   ```
3. **输出原文**给用户复制；**同时提醒**：在 AI 表格右上角『分享』菜单手动把对方加为「可编辑」或「管理员」，否则对方虽能绑定 BASE_ID 但无写权限

---

## 接收他人分享的配置

**触发信号**：用户在对话中粘贴含 `BASE_ID = BAS_xxx` 的分享语句，或直接粘贴 `BAS_xxx`。

### 步骤

1. **解析 BASE_ID**：从用户消息中提取 `BAS_` 开头的字符串
2. **检查当前是否已绑定**：先 `init validate`
   - **未绑定** → 直接进入步骤 3
   - **已绑定不同 BASE_ID** → 用 `ask_question` 工具问用户「当前已绑定 `BAS_yyy`，是否覆盖为 `BAS_xxx`？」
     - 是 → 先 `init unbind --confirm`，再走步骤 3
     - 否 → 中止本次接收，告知用户保留原配置
3. **绑定新 BASE_ID**：
   ```bash
   cd <SKILL_DIR> && uv run python scripts/cli.py init url <BAS_xxx> --auto-repair
   ```
4. **校验通过**后告知用户：
   - 已绑定 `BAS_xxx`
   - 如发现没有读 / 写权限，请联系分享方在 AI 表格『分享』菜单加为「可编辑」或「管理员」

> 接收方**不需要新 CLI 命令**——分享是单向的，对方提供 BASE_ID，本方走标准 `init url` 即可。

---

## 相关参考

- `init url / init unbind / init validate` 决策点：[01-init.md#命令参数先查--h再读决策点](./01-init.md#命令参数先查--h再读决策点)
- 高危确认规则（`init unbind --confirm`）：`../shared/hard-constraints.md#H5`

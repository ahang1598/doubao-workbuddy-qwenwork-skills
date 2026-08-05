# AI 主图优化

## 功能

对商品 1~5 张主图做 AI 背景/场景优化。逐张独立，单图失败不影响其他图。

- 四阶段：`prepare` → `customize` → `generate` → `apply`
- 比例：`1:1` 或 `3:4`
- 状态文件：`scripts/.image_state.json`（apply 后自动清理）

---

## 流程总览

```
prepare → customize → ⏸ 等商家确认 → generate → ⏸ 等商家确认 → apply
         （自动生成HTML）   （必须停下）              （必须停下）
```

---

## 回合详解

### 回合 ① prepare + customize（连续执行，不停顿）

**做什么：**
1. prepare：拉取主图 + 解析构图
2. 为每张图推荐**具象场景**（禁止空泛描述如"简约背景"），通过 `--customize` 的 `background` 字段注入
3. customize 执行后：
   - **必须自动生成** `scripts/prompt_editor_{offer_id}.html`
   - **必须自动在浏览器中打开**（不得询问、不得省略）
   - ⛔ **禁止在聊天框中直接询问**用户的「比例 / 文字卖点 / 场景」参数——HTML 编辑器是**唯一的参数收集入口**，不得以任何对话形式替代
   - HTML 中「场景」字段**预填 Agent 推荐的具象场景**作为默认值
4. 聊天框输出：
   - 醒目提示：「✨ 已为您打开提示词编辑器网页，可调整比例/文字卖点/场景」
   - 兜底提示：「网页未打开？手动打开 `scripts/prompt_editor_{offer_id}.html`」
   - 渲染 prompt 表（含 prompt 列 + 文字卖点列 + 场景列）
5. **立即进入回合 ②**

**可用 API：**
- [商品查询](../apis/cbu_offer_query_tool.md)
- [图片解析](../apis/cbu_image_analyse_tool.md)
- [Prompt 编辑器 HTML](../apis/prompt_editor_html.md)
- [customize 参数](../apis/cbu_image_generation_and_editing_tool.md#cli-阶段命令)

---

### 回合 ② 询问商家确认（⛔ 必须停下）

**输出两选项：**
1. 接受推荐，执行生成
2. 调整某些图的 比例 / 文字卖点 / 场景

**然后立即停下，等商家回复。**

- 商家选 1 → 进入回合 ③
- 商家选 2 → 用商家给的参数重跑 customize（⛔ 此时**不得再次生成 HTML 文件**，仅更新状态并渲染 prompt 表）→ 回到回合 ②

> ⛔ 无论任何情况（只有1张图、场景已合理），都必须停下等商家。严禁自行 generate。

---

### 回合 ③ generate（⛔ 必须停下）

执行 generate → 渲染原图/优化图对照（`![](url)` 格式）→ 输出三选项：
1. 全部应用
2. 部分应用
3. 不应用

**然后立即停下，等商家回复。严禁自行 apply。**

**可用 API：** [图片生成](../apis/cbu_image_generation_and_editing_tool.md)

---

### 回合 ④ apply（流程结束）

按商家选择执行 apply → 渲染最终主图表（`![](url)` 格式）→ 状态文件自动清理。

**可用 API：** [图片URL转换](../apis/image_bank_change_url_for_offer.md) · [修改商品主图](../apis/cbu_skill_change_main_image.md)

---

## 禁止事项

| 规则 | 说明 |
|------|------|
| 禁止跳过回合 ② | customize 后必须停下问商家，不得直接 generate |
| 禁止跳过回合 ③ | generate 后必须停下问商家，不得直接 apply |
| 禁止省略 HTML | customize 必须自动生成并打开编辑器 HTML |
| 禁止聊天框询参 | customize 后**绝不允许**在聊天中问「想用什么比例/卖点/场景」；商家改参数**只能通过 HTML 编辑器**，不得以对话、表单、逐项追问等方式替代 |
| 禁止纯文本 URL | 所有图片必须 `![alt](url)` 渲染 |
| 禁止非法字段 | customize JSON 只接受 `size` / `background` / `text_selling_points` 三个字段，其他字段（如 `prompt`、`selling_points`）CLI 直接报错 |
| 禁止 Agent 填卖点 | `text_selling_points` 默认空，只有商家能填，Agent 不得推断 |

---

## 异常处理

| 异常 | 处理 |
|------|------|
| 商品无主图 | prepare 失败，提示商家检查商品 ID |
| 单张解析失败 | 按「比例 + 背景」拼装 prompt，不影响其他图 |
| 单张生成失败 | 标注「已保留原图」，apply 用原图占位 |
| 图片链接转换失败 | 重试 3 次，均失败提示商家手动处理 |
| 主图修改失败 | 输出原因，不清理状态文件，可重试 |

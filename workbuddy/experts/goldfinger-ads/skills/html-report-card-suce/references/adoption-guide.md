# 接入指南（Adoption Guide）

给其他专家团参考：怎么把这套 HTML 卡片规范接进自己的专家包。

---

## 一、这套规范解决什么问题

多个专家/角色各自输出文档时，最常见的三个问题：

1. **视觉不统一** —— 每次生成的排版都不一样，看起来不像同一个产品出的
2. **组件乱用** —— 同样是"三条风险"，有时用三个色块、有时用一个大色块内嵌列表、有时用表格
3. **信息密度失控** —— 该给判断的地方在铺陈过程，该省略的地方在写废话

本包用**硬规则 + 固定组件配方 + 自检脚本**来解决：能自动检的交给脚本，需要判断的写成决策树。

---

## 二、最小接入（5 步）

1. **复制整个目录**到你的专家包 `skills/` 下，可改名（如 `skills/html-card-template/`）
2. **配置品牌**：
   - `assets/template.html` 里的 `{{BRAND_NAME}}` / `{{ROLE_NAME}}` 替换成你的品牌名与角色名
   - 不需要品牌行 → 整段删掉 `<p class="brand-tag">...</p>`
   - `assets/theme.css` 改 `--brand` / `--brand-deep` / `--brand-soft` 换主色
3. **在 agent 的 MD 里挂载并写清触发条件**（见下方模板）
4. **首次跑通后**把生成的产物用 `scripts/check_html.py` 检一遍
5. **把配置好的版本作为你的主副本**，后续多角色包从它同步

### agent MD 里怎么写

在专家的 frontmatter 挂上 skill：

```yaml
skills: [html-report-card-suce]
```

在「## 输出规范」章节加一段：

```markdown
### 呈现层：HTML 卡片渲染

以下产出信息量大、结构化明显，**默认渲染为 HTML 卡片**，走 `html-report-card-suce` 技能：

- {你的交付物1}（含 xxx + xxx）
- {你的交付物2}

**文件名格式**：`{角色}-{产出类型}-{YYYYMMDD-HHMM}.html`
**输出路径**：用户当前工作目录
**Banner brand-tag（强制）**：固定为 `{{BRAND_NAME}} · {{ROLE_NAME}}`，纯白小字，照抄不改字。

轻量对话答疑保持纯文本，不套 HTML。
```

---

## 三、按需裁剪

| 你的情况 | 怎么改 |
|---|---|
| **不需要品牌 banner** | 删 `template.html` 的 `.brand-tag` 整行；规则 14/16 的 brand-tag 约束自动失效，其余不变 |
| **只有一个角色，没有互相指路** | 删 `template.html` 第 ⑦ 节里的"可找 XXX"那条；其余保留 |
| **需要多角色各自 banner** | 为每个角色存一份 template.html，各自写死 brand-tag；⚠️ 见下方「多副本同步陷阱」 |
| **产出类型固定且少** | 建一张「产出类型 → 组件配方」映射表（本包原版有 `output-mapping.md`，已因行业耦合太重未随包发布，建议自建） |
| **要换字体/圆角/间距** | 只改 `theme.css`，不要在 HTML 里写 inline style（除 `<th style="width:...">` 列宽外） |
| **要加新组件** | 先问自己能不能用现有 9 个组件组合出来。真要加，必须同步写进 `design-rules.md` 并补自检规则，否则很快漂移 |

---

## 四、多副本同步陷阱（实战踩过）

如果你像原版一样**给每个角色包各存一份 skill 副本**，注意：

1. **`design-rules.md` / `component-guide.md` / `SKILL.md` 应逐字一致** —— 用 md5 定期核对：
   ```bash
   md5 -q */skills/html-report-card-suce/references/design-rules.md | sort -u | wc -l   # 应为 1
   ```
2. **`template.html` / `theme.css` 允许不一致**（brand-tag 按角色写死），**但绝不能用整文件覆盖同步** ——
   否则所有副本的角色名会被覆盖成同一个。要按「角色 → 角色名」对照表逐个重新写死。
3. **改规则时最容易漏的下游引用**：`SKILL.md` 里的规则摘要条、`component-guide.md` 的组件示例、
   `template.html` 与 `examples/*.html` 的实际写法。改了规则正文却漏了示例，等于规则没生效。
4. **真实案例**：原版有一个包因为单独改过规则 2/12 却没同步回其他包，形成"分叉版本"——
   它在两条规则上更先进，同时缺失了整套 brand-tag，导致它生成的 HTML 没有品牌 banner。
   **建议每次改完跑一次 md5 核对。**

---

## 五、最容易违反的 4 条规则

按实际返工频率排序：

1. **规则 2（`.lead`）** —— 两个方向都会错：要么每节硬塞导致出现「以下是 5 个候选方案」这种废话，
   要么加「结论：」固定前缀导致一份文档里"结论"重复七八次、反而没有重点。
   **正解**：有增量信息才写，不加前缀，按 section 性质决定写什么。
2. **规则 12（风险并列）** —— 习惯性套 `callout-warn`。**正解**：≥2 条一律裸 `plain-list`，
   孤立单条才用 callout-warn。整块黄底会稀释重点。
3. **规则 10（Markdown 残留）** —— 写 HTML 时手滑写成 `**加粗**`。**正解**：交付前跑自检脚本。
4. **规则 11/15（callout 滥用）** —— 把一组要点或决策枚举塞进 callout。
   **正解**：要点 ≥3 抽独立 section；决策枚举用 `plain-list` + `.tag-*` 字色。

---

## 六、验收

```bash
python3 scripts/check_html.py <你生成的.html>
```

必须 **0 error**。脚本能自动检出：Markdown 残留、`.lead` 固定前缀与废话占位、序号不连续、
`h3/h4` 降级、同 section 蓝黄混排、多条 warn 并列、callout 内嵌风险列表、icon 越界、
KV 表缺 thead、占位符未替换、CSS 未内联。

脚本检不了的（需人工过一眼）：
- 每节的 `.lead` 串起来能不能形成完整判断
- 组件选得对不对（表格 vs plain-list 的边界，见规则 13 决策树）
- 内容本身的准确性

> 建议把自检脚本接进你的交付流程，而不是靠记忆遵守规则 —— 16 条规则靠人记必然漂移。

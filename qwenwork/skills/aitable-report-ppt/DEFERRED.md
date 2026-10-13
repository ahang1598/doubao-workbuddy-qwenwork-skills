# 待执行项

发布 1.2.0 时有意跳过、需在后续版本补上的工作。**这些是记录在案的偏离，不是遗漏。**

## 1. iframe 归属：绑定 Playwright Frame 对象身份（Codex 第 2 组）

**现状**：按 `.avd-root` 内实际挂载 iframe 的 URL 前缀匹配来判定归属，且需规格声明 `expect_iframe`。

**缺口**：
- 若主题在下钻组件内放了**非记录用途的同域 iframe**，它的 401 会被误降级为人工项，而不是硬失败。这是三条残留风险中唯一有实际后果的一条。
- URL 前缀匹配（60 字符）在钉钉记录链接间可能碰撞。但碰撞双方都是记录 frame，归到同一类，后果良性。
- 规格声明了 `expect_iframe` 却从未真正执行 `open_row` 打开记录时，光凭声明即可解锁降级。

**应做**：响应事件保留 `request.frame()`，只有真实下钻流程产生的那个 Frame 的 401/403 才进人工项；`expect_iframe:true` 必须同时要求 `open_row`；补"已有预期 Frame + 混入额外同域 iframe，额外的必须硬失败"对照用例。

## 2. 第一组三条热力图真值反例未经验证

代码已实现（真值优先级：count 口径下 oracle 权威、cells 不得覆盖；非 count 口径以 `chart.cells` 为真值），并已有非 count 正样本（sum 口径，每格显示 10k、成员数 k）通过基线 163 项检查。

三条反例已跑过一轮，结果如下：

| 反例 | 结果 |
|---|---|
| `heatmap-wrong-ast-fields` | ✅ 被『heat-map grid matches its declared cells』拦下 |
| `noncount-wrong-display` | ⚠️ 注入脚本引号写坏导致 JS 语法错误，撞的是 runtime errors。**用例缺陷，非门禁缺陷**，已修 |
| `count-cells-contradict-oracle` | ⚠️ 存活，但**原因是测试够不到那条检查**，非门禁有洞 |

`count-cells-contradict-oracle` 的真相：`compareRenderedValues` 只在带 oracle 时执行，
而规格类故障当时一律不带 oracle（为避开指纹冲突），于是这条依赖真值的检查根本没跑。
**"存活"在这里等于"没测到"，不等于"没抓住"。**

已修：规格类故障改为**连 HTML 一并重建**，让指纹链自洽，真值检查才够得到。

**应做**：跑 `python3 tests/mutations/run_mutations.py` 确认这两条修复后被对应检查拦下。
在此之前，「count 口径下 oracle 权威、cells 不得覆盖」这条代码路径**属于已实现但未验证**。

## 3. 其他后置项（Codex 已同意不作为阻断）

- settle 中 ECharts `zr.animation.getClips()` 仍是采样一次，非轮询到 deadline
- categoryless pie/donut 未处理（当前 donut 均带 category）
- HSL 的非度数单位（`0.5turn`/`3.14rad`/`100grad`）会被当度数，属静默误解
- `chart.cells`、行字段、列字段尚未写入 schema 与 `validate_report_spec.py`

## 稀疏角色可以被内容重的页面冒领

**发现于**：2026-08-21，v5 第 9 页人工复核。

**现象**：第 9 页声明 `slide_role: statement`，因此豁免覆盖率检查；实际它挂着
5 条数据结论——是全篇内容最多的一页（其余每页 0–1 条），下半页整片空白。
稀疏页占比 2/10 = 20%，在 25% 上限内，所以门禁全绿放行。

**为什么这是洞**：`slide_role` 是自己声明的，声明 `cover/section/statement/closing`
就买到豁免。这与最初"页面大量留白"那个缺陷是同一个形状，只是换了条路径绕过——
不是把字缩小，而是给页面换个身份。

**怎么补**：稀疏角色必须**内容上也稀疏**。声明稀疏角色的页面若挂着 3 个以上内容
单元（findings + metrics + charts 之和），豁免不成立，照常按覆盖率考核。判据落在
规格层（`validate_report_spec.py`）比落在渲染层更早、更便宜。

补之前需配一组反例验证：真金句页（1 条内容）必须仍豁免，冒领页（5 条内容）必须被拦。

**为什么现在不补**：补上后 v5 第 9 页会当场失败，需重跑一轮生成。用户 2026-08-21
决定先发 v5，此项下轮处理。v5 硬失败为 0，此页在现行规则内合法。

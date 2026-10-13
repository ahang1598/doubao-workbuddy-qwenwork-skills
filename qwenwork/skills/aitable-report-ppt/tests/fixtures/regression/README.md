# 回归样本

## v5-known-good（必须通过）

2026-08-21 生成并经人工逐页确认的交付件。**它的正确状态是 `manual_required`
（退出码 1），不是 `passed`**——无头环境没有登录态，页面内嵌的钉钉原始记录必然
返回 401，这是设计内的第三态。

断言必须指名道姓：状态为 `manual_required`、硬失败恰好 0、唯一非通过项是
`embedded record sources need a signed-in check`。写成"退出码为 0"会让这份好
样本天天假失败；写成"退出码非 0"则与反例无异。

**已知瑕疵**：第 9 页声明 `slide_role: statement` 拿到稀疏豁免，实际挂着 5 条
数据结论、下半页留白。这在现行规则内合法，洞记在 `DEFERRED.md`。冻结它是因为
"当前规则下的合格线"就是这个样子——等那条规则补上后，本样本需重新生成。

### 为什么之前一直没有正样本

`positive-dense.*` 曾被冻结为正样本，但它与用户随后指出有缺陷的 v3 **逐字节相同**
（`9662cad1`）。当时它通过了全部 347 项检查，而人一眼就看出文字看不清、图表点不开。
把它当金标准，等于把"当时门禁看不见的缺陷"固化成了合格线。它已改名为
`v3-known-bad.*`，只作反例。

这段教训保留在这里：**正样本必须在门禁定稿后重新生成，并经人工逐页确认。**

## v3-known-bad（必须失败）

实测缺陷：84 处文字对比度不足（米色字写在米色卡片上仅 1.16:1）、
折线图数据点 `symbolSize:4`（实显 2.7px）而 tooltip 为 axis 触发——
悬浮有提示、点击无反应；页面内联的是合同 1.0 的 runtime。

期望：`validate_visual_report.js` 判定失败，且失败项应包含
`text meets contrast floors` 与 `page runtime meets the validator contract`。

## negative-underfilled（必须失败）

更早一轮的产物。平均内容覆盖率 20.8%、最大空白带占画布 63%、
主图写死 250px、图表轴字号落进 ECharts 默认 12px（实显 8px）。

期望失败项：字号下限、图表轴字号、单页覆盖率、平均覆盖率、空白带、主图高度。

## 怎么跑

```
node scripts/validate_visual_report.js tests/fixtures/regression/<名>.html \
  tests/fixtures/regression/<名>-spec.json
```

两份反例都应以退出码 1 结束。**若哪天它们开始通过，是门禁退化了，不是样本变好了。**

正样本 `v5-known-good` 也以退出码 1 结束，但原因完全不同（`manual_required`）。
**若它开始出现硬失败，是门禁收得过紧、误伤了合格产物。**

反例守下限、正样本守上限，缺哪一边都会往那个方向漂。

## 与故障注入的分工

这里的样本回答"这份具体产物有没有问题"；`tests/mutations/run_mutations.py`
回答的是另一件事——"尺子还量得准吗"。样本是封闭的，缺陷空间是开放的，
只靠样本无法发现门禁新长出来的盲区，两者不能互相替代。

# 竞品视觉证据合同

竞品分析的对象是**图片**，不是搜索摘要。没有实际看过图，不得写视觉结论。

**适用范围：discovery 模式读取全文；user-reference 模式只执行“内容/信息架构旁路”。**
有用户参考图时，风格只从用户图量测，但仍看至少 1 个同品类竞品的同类页面来确认模块与顺序；
不得把该竞品的色彩、字体、材质或构图写进风格 DNA。

## 0. 先认清宿主能力

宿主**没有网页截图能力**（`host_limits.CAPABILITY_WEB_SCREENSHOT = False`）：`web.fetch` 返回的是页面
文本与结构，不是界面位图。

因此"必须是自己截的界面截图"是一条**不可达硬门**。失败条件：拿不到截图时不会停下来，而是
下载了三张无关的服装模特照冒充竞品界面，并据此编造了八维分析写进文档——**门越硬，假证据越精致**。

所以合同改成：**图片可以来自搜索，但来源必须如实标注**。拿不到图的正确动作是**换站点继续搜**。

## 1. 取图流程（照做，直到拿到图）

```text
1  general_search 找具体实体与具体界面
     "<品牌/产品名> 官网首页"  "<品牌> UI 界面"  "<brand> homepage screenshot"
     禁止抽象题材词："洛丽塔 UI design" "高级感网站设计" —— 搜不到界面，只会返回素材图
2  能打开就 web.fetch 取页面结构与图片 URL
3  拿不到就**直接用搜索结果里返回的界面图**            ← 合法路径，不是降级
4  这个站点没有图 → 换站点、换关键词、换语言（中/英/日）继续搜
5  这个品牌实在没有 → 换一个同品类的真实品牌，回到第 1 步
   ——**循环直到拿到 `scopePlan.researchCount` 个不同产品的图**
6  下载：curl -L -sS --fail -o research/competitor-a.png "<url>"
     缺 -L 只会得到几十字节的重定向体（CDN 短链是 302）；文件 <8KB 一律视为下载失败
```

**竞品阶段不可跳过。** 零图 = research 阶段 FAIL，不存在"这次搜不到就算了"。

## 2. 来源分级（`imageSource` 必填）

| 值 | 含义 | 何时用 |
|---|---|---|
| `page-screenshot` | 本次实际打开页面截取的界面位图 | 宿主具备截图能力时 |
| `search-image` | 搜索结果返回的界面图/产品图 | **本宿主的默认路径** |
| `official-media` | 官方媒体库、发布稿、应用商店截图 | 找到官方素材时 |
| `user-supplied` | 用户直接提供的图片 | 仅兼容旧收据；新任务有用户参考图时应进入互斥的 user-reference 模式 |

`validate_research_evidence.py` 校验来源与图片事实是否自洽：

- 声明 `page-screenshot` 的**网页**界面图却是竖图 → INVALID（网页首屏必然横向）。
  它确实是移动端界面时，在 `screen` 里写明"移动端/App/小程序"。
- 任意研究图近重复、纯色、空白、无法解码 → INVALID
- 案例名或来源 URL 的唯一数量低于 `scopePlan.researchCount` → INVALID

**标错来源比没有图更糟**：它把"我没看到界面"伪装成"我看到了界面"，下游的所有判断都建立在假事实上。

## 3. 本任务最低证据

- 数量由 `ui-run.scopePlan.researchCount` 决定：单屏/组件/还原通常 1 个，常规任务通常 2 个，完整多场景通常 3 个；用户明确数量优先
- 必须来自**不同真实产品**；同一产品多张图不能冒充多个案例
- 每个竞品 ≥1 张本次实际看过的界面图，保存本地路径并记录来源 URL
- 每张图逐项写满 8 维：`layout` `color` `composition` `elements` `hierarchy` `type` `fontSize` `effects`
- 每维写「观察事实 → 起到的作用 → 本方案采用/拒绝什么」，禁止只写"简洁、高级、年轻"
- 分析只能基于**图里真的看得见的东西**。看不清的维度写"图中不可判"，不要靠品牌印象补全——
  这比编一句具体描述诚实得多，也更有用

## 4. 文档里怎么呈现

默认 `docLayout=single-canvas`：竞品图与分析在**白底画布**的 `data-canvas-section="competitors"` 区块里，
每张图 `<img data-role="competitor" data-source="https://…">`，图与分析紧邻。排法见
[doc-canvas.md](doc-canvas.md) §4。

`docLayout=native` 时才走原生 `<img caption="竞品 A · https://…">` + 对照表。

## 5. research-evidence.json

只写研究事实字段；`status / requestHash` 由 `complete research` 自动注入，收据也由它自动生成。
文件缺失时 complete 会把完整骨架打印出来，不必手抄：

```json
{
  "competitors": [{
    "name": "竞品代称",
    "screen": "页面或状态",
    "sourceUrl": "https://...",
    "imageSource": "search-image",
    "screenshotPath": "research/competitor-a.png",
    "visualAnalysis": {
      "layout": "...", "color": "...", "composition": "...", "elements": "...",
      "hierarchy": "...", "type": "...", "fontSize": "...", "effects": "..."
    },
    "adopt": ["..."], "reject": ["..."]
  }],
  "dnaCases": [{"jsonPath":"...dna.json", "thumbnailPath":"...webp", "why":"..."}],
  "brandTheme": {"subject":"...", "signals":["..."]}
}
```

证据的判据（这几条没有脚本替你查 —— 包里**没有**这个脚本，
所以它就是你自己要守的那条线）：截图必须可解码、不是纯色、彼此不近重复、
来源与分析自洽。**真的点进去看过**和"我知道那个站长什么样"是两回事。

包内已经有 4 个获奖站的**实测数值**可以直接当锚点：
`reference/fingerprints/index.json`。

## 6. 完全离线时

确实无法联网时：明确标记研究未完成，用 `reference/fingerprints/`
里的实测指纹与缩略图补位，并把交付状态标为草案。禁止伪造截图或 URL，禁止用 Pillow 生成占位图，也禁止用纯文字摘要冒充证据。

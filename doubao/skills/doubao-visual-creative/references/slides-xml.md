# Slides XML：宿主真值与可抄骨架

写第一页 XML 之前读完。这里的每一条都是在真实宿主上验过的——**照着写，不要凭直觉发明属性**。

> `hostcheck` 会打印这台机器上渲染层自带的语法文档路径。**那份文档是语法真值的第一来源**，
> 本文件是它的补充与工艺侧的经验；两边冲突时以 `hostcheck` 指出的那份为准。

---

## 一、提交形态

- 一次提交**一个 `<slide>` 元素**：不写 `<?xml ...?>` 声明，不包 `<presentation>`。
- **不要自己编 `id`**：留空，服务端分配；自造 ID 容易跨页撞车。
- 文本与属性值里的 `&`、`<`、`>` 必须转义成 `&amp;` `&lt;` `&gt;`。
- 画布默认 **960×540**，但**不要把它写死进算术**——从 `<presentation width height>` 或 `hostcheck` 读。
- 命名空间：`xmlns="https://www.larkoffice.com/sml/2.0"`（`http://` 亦可，服务端会规整）。
- 每页都要有 `<note>`：3–5 句可直接照读的讲稿。
- 页面顶部写一行注释记账，便于自己和后续检查对齐：
  `<!-- [p03] job=argument device=D11 ground=实色地 -->`

---

## 二、五条渲染事实（不知道就会踩）

**① `<content>` 必写 `autoFit="normal-auto-fit"`**
宿主默认 no-auto-fit：文字放不下时按原字号继续往下压，直接盖住下一块。写了 autoFit 宿主会缩字避让
（但只缩到 0.7×，再装不下还是会压）。**留框按 `fontSize × 1.5 × 行数` 算高度。**

**② `width`/`height` 是裁剪后的显示尺寸，裁剪关不掉**
图窗与源图比例不一致时，宿主把原图等比缩放到铺满窗口，再**从中心**裁掉多余。
- 想完整显示 → 让 `width:height` 对齐源图比例。
- 比例差 **≤10%** 才可用 `<crop anchor="top|bottom|left|right"/>` 选保哪侧；超过须换图/按新画幅重生，anchor/offset 均不豁免。
- 图窗更窄＝横向裁，只用 `left/right`；图窗更宽＝纵向裁，只用 `top/bottom`。anchor 不证明头脸完整，源图已截头只能换素材。
- 圆角 `<crop type="rect" presetHandlers="60"/>` 只改角形，不改变保留区比例，允许。
- ✗ **四个 offset 一个都不要写**：offset 与原图比例不一致时会把图拉伸变形。

宿主会把 `anchor=` 回读成四个 offset；比例与 anchor 必须在写入前检查，不用回读 offset 反推意图。

**③ slide 级 `<style><fill>` 是页背景的正路**
比铺一张满版 `rect` 好：不占元素、不参与遮挡判定、不会被当成大色块。

```xml
<slide xmlns="https://www.larkoffice.com/sml/2.0">
  <style><fill><fillColor color="rgba(242,240,233,1)"/></fill></style>
  <data>…</data>
</slide>
```
换成满版图：`<style><fill><fillImg src="<file_token>" alpha="1"/></fill></style>`
（`fillImg` 与 `fillColor` **二选一，不能并写**；它等比铺满并居中裁溢出，所以**只喂 16:9**。）

**④ `lineSpacing` 必须带单位前缀**
`lineSpacing="multiple:1.6"` 或 `lineSpacing="fixed:24"`，写在 `<content>` 上。
`lineHeight` / `line-height` / 不带前缀的 `1.6` 渲染层一律拒收。

**⑤ `letterSpacing` 写在 `<p>` 上**，不写在 `<span>` 上——宿主会把它上提到段落层，同段不同 span 不能有不同字距。
**只加宽不压缩**：负字距会让字面压叠，宿主原样执行。

---

## 三、原生语法（不用它就得拿 shape 拼，拼出来还不整齐）

**`textType`** 写在 `<content>` 上，宿主据此给默认排版：
`title` 主标题（≥24pt）｜`headline` 段标题/编号（18–24pt）｜`body` 正文｜`caption` 微字（≤11pt）。
字体属性写在 `<content>` 上就够，不必逐个 `<span>` 重复。

**`presetHandlers`** 圆角档位：`0`（直角）/`4`/`6`/`8`，写在 `<shape type="rect">` 上。

**`padding`**：`<content>` 的 `paddingTop/Bottom/Left/Right` 是文字与框边的间距。
卡片类块必须写（小字块 6–10，正文卡 12–24），**不写就贴边**。

**`<shape type="rect">` 可以直接承载文字**：一个块同时是底色和文字——这是卡片的正解，
不要用「色块 ＋ 另一个文字块」两块手算对齐。

**渐变**：`fillColor` 支持 `linear-gradient(<角度>deg, rgba(...) <位置>%, …)`，
必须用 `rgba()` ＋ 百分比停靠点。

**无效写法**（写了不生效，别当手段）：`opacity` / `fillOpacity` / `<content align=...>` / 独立 `<style>` 属性。
**透明度写进 `rgba(...)`，文字对齐写 `textAlign`。**

---

## 三·B、宿主字体表（`fontFamily` 只有写在表里的才真的生效）

**写一个宿主没有的字体名不会报错，会静默回落成默认字形**——写了等于没写，而且你在 XML 里看不出来。
`hostcheck` 会在这台机器上现探一遍并打印结果；探不到时以本表为准。

**中文有 8 种真字形。** 大量"楷体／文楷／点阵／今楷"类的名字**中文部分等于默认黑体**
（它们只换了拉丁），是假的可用——见下面的回落清单。

| 中文字形 | `fontFamily` 取值 | 气质 | 适合哪一档 |
| --- | --- | --- | --- |
| 黑体 | `思源黑体`（同 `Noto Sans SC`） | 正文默认，中性 | 全部（正文首选） |
| 宋体 | `思源宋体`（同 `Noto Serif SC`） | 衬线，端正 | 东方／时装／人文 |
| **细书宋** | **`寒蝉锦书宋`** | 纤细修长，书卷气 | 文化、香氛、时装、艺术画册 |
| **毛笔行楷** | **`有字库龙藏体`** | 笔锋凌厉，手写 | 国风、文旅、海报、题字 |
| 圆体 | `圆体`（同 `寒蝉团圆体 圆体`） | 圆润粗体 | 儿童、生活方式、娱乐 |
| **厚圆黄油体** | **`站酷庆科黄油体`** | 字面极满、厚、甜 | 潮玩、食物、快消、高饱和档 |
| 粗圆黑 | `抖音美好体` | 字面方满、粗、活泼 | 消费、活动、口号 |
| 粗圆手写感 | `站酷快乐体` | 字宽不一、跳脱 | 儿童、市集、手作 |

> **新加的这三款没有真粗体**：`bold="true"` 得到的是**合成加粗**（描边加厚、字形不变）——
> 细书宋一加粗就不再纤细。要它们的性格就别加粗，用字号和字距拉层级。

> **中文有 8 种字形可换，拉丁 display 还有 8 类**——加起来足够让两份稿一眼分得开。
> 一稿最多两款中文 ＋ 一款拉丁，角色分工由 Step 2 的字体角色表定，选定后全程不改。
> 下面每一款都只管**拉丁字形**，中文会用另一款字——所以它们只挂在拉丁串上，中文另配一款。

| 气质 | `fontFamily` 取值 |
| --- | --- |
| 窄体巨字 | `Bebas Neue` `Anton` `Antonio` `Oswald` `Teko` |
| 高对比衬线 display | `Playfair Display` `Abril Fatface` `DM Serif Display` |
| 老式／正文衬线 | `EB Garamond` `Libre Baskerville` `Crimson Text` `Lora` `Merriweather` `Vollkorn` `PT Serif` `Times New Roman` |
| 几何／人文无衬线 | `Montserrat` `Poppins` `Josefin Sans` `Work Sans` `Inter` `DM Sans` `Karla` `Rubik` `Archivo` `Lato` `Open Sans` `Roboto` |
| 圆润 | `Comfortaa` `Quicksand` `Righteous` |
| 手写／脚本 | `Lobster` `Pacifico` `Dancing Script` `Amatic SC` |
| 装饰 | `Monoton` |
| 等宽 | `Roboto Mono` `Source Code Pro` `Courier New` |

**这些名字会静默回落（写了等于没写）**：`楷体` `霞鹜文楷` `霞鹜975圆体` `精品点阵体` `仓耳今楷`
`阿里妈妈东方大楷` `得意黑` `优设标题黑` `江城斜黑体` `站酷高端黑` `方正清刻本悦宋` `汇文明朝体`
`锐字真言体` `三极行楷` `衡山毛笔行书` `字由芒果体` `OPPOSans` `HarmonyOS Sans` `MiSans`
`SimHei` `黑体` `宋体` `仿宋` `隶书` `幼圆` `等线`
`微软雅黑` `Microsoft YaHei` `苹方` `PingFang SC` `华文黑体` `方正黑体` `方正兰亭黑` `汉仪旗黑`
`阿里巴巴普惠体` `思源等宽` `Arial` `Arial Black` `Helvetica` `Verdana` `Tahoma` `Trebuchet MS`
`Georgia` `Futura` `Optima` `Gill Sans` `Avenir` `Century Gothic` `Impact` `Comic Sans MS`
`Segoe UI` `Menlo` `Monaco` `Consolas` `Space Grotesk` `Space Mono` `JetBrains Mono`
`Fira Code` `IBM Plex Mono` `Archivo Black` `Manrope` `Outfit` `Sora` `Orbitron` `Staatliches`。

`hostcheck` 会在本机现探一遍并打印结果——**以它的输出为准**，探不到时才按本表。

## 四、可抄骨架

### 4.1 满版影像页（承文①：字落图自身安静区，零形状）

```xml
<slide xmlns="https://www.larkoffice.com/sml/2.0">
  <style><fill><fillImg src="<file_token>" alpha="1"/></fill></style>
  <data>
    <shape type="text" topLeftX="60" topLeftY="46" width="420" height="18">
      <content textType="caption" fontSize="10" fontFamily="思源黑体"
               color="rgba(255,255,255,0.72)" autoFit="normal-auto-fit">
        <p letterSpacing="3">KYOTO · A WEEK OF ARCHITECTURE</p>
      </content>
    </shape>
    <shape type="text" topLeftX="60" topLeftY="360" width="600" height="86">
      <content textType="title" fontSize="56" fontFamily="思源黑体" bold="true"
               color="rgba(255,255,255,1)" lineSpacing="multiple:1.1" autoFit="normal-auto-fit">
        <p>静谧与秩序</p>
      </content>
    </shape>
    <shape type="text" topLeftX="60" topLeftY="452" width="520" height="24">
      <content fontSize="14" fontFamily="思源黑体" color="rgba(255,255,255,0.86)"
               autoFit="normal-auto-fit"><p>我在京都的一周建筑摄影之旅</p></content>
    </shape>
  </data>
  <note><content textType="body"><p>开场：这一周我在看什么。</p><p>三条线索：光、材料、秩序。</p><p>接下来先讲出发前的问题。</p></content></note>
</slide>
```

### 4.2 半版竖图贴边（承文②a：图贴三边，另一半是页面地色，图上零形状）

```xml
<slide xmlns="https://www.larkoffice.com/sml/2.0">
  <style><fill><fillColor color="rgba(244,240,233,1)"/></fill></style>
  <data>
    <img src="<file_token>" topLeftX="0" topLeftY="0" width="400" height="540">
      <crop anchor="top"/>
    </img>
    <shape type="text" topLeftX="452" topLeftY="46" width="300" height="16">
      <content textType="caption" fontSize="10" color="rgba(140,124,100,1)" autoFit="normal-auto-fit">
        <p letterSpacing="2">02 · KARE — QUIETUDE</p>
      </content>
    </shape>
    <shape type="text" topLeftX="452" topLeftY="112" width="440" height="52">
      <content textType="title" fontSize="34" fontFamily="思源黑体" bold="true"
               color="rgba(38,40,42,1)" autoFit="normal-auto-fit"><p>银阁寺：不涂金的银</p></content>
    </shape>
    <shape type="rect" topLeftX="452" topLeftY="196" width="88" height="2" presetHandlers="0">
      <fill><fillColor color="rgba(178,58,46,1)"/></fill>
    </shape>
    <shape type="text" topLeftX="452" topLeftY="230" width="440" height="96">
      <content fontSize="14" fontFamily="思源黑体" color="rgba(60,58,54,1)"
               lineSpacing="multiple:1.8" autoFit="normal-auto-fit">
        <p>足利义政的山庄，与金阁寺隔了一个世纪，却始终没有贴过银箔。</p>
      </content>
    </shape>
  </data>
  <note><content textType="body"><p>…</p></content></note>
</slide>
```

### 4.3 数据卡组（一个 rect 同时是底色和文字）

```xml
<shape type="rect" topLeftX="60" topLeftY="180" width="200" height="130" presetHandlers="6">
  <fill><fillColor color="rgba(24,24,26,1)"/></fill>
  <content paddingTop="18" paddingLeft="18" paddingRight="18" autoFit="normal-auto-fit">
    <p><span fontSize="44" fontFamily="思源黑体" bold="true" color="rgba(255,255,255,1)">24.9</span><span
        fontSize="16" fontFamily="思源黑体" color="rgba(255,255,255,0.8)">M</span></p>
    <p><span fontSize="12" fontFamily="思源黑体" color="rgba(255,255,255,0.86)">品牌总曝光人次</span></p>
    <p letterSpacing="2"><span fontSize="9" fontFamily="思源黑体" color="rgba(255,255,255,0.5)">TOTAL IMPRESSIONS</span></p>
  </content>
</shape>
```

### 4.4 幽灵巨字（压在底层，实内容压其上）

```xml
<shape type="text" topLeftX="40" topLeftY="120" width="420" height="220">
  <content fontSize="200" fontFamily="思源黑体" bold="true"
           color="rgba(255,255,255,0.10)" autoFit="normal-auto-fit"><p>01</p></content>
</shape>
```

### 4.5 竖排文字带（每行一个汉字，不依赖宿主竖排）

```xml
<shape type="text" topLeftX="892" topLeftY="60" width="28" height="220">
  <content fontSize="18" fontFamily="思源宋体" color="rgba(140,124,100,1)"
           lineSpacing="multiple:1.35" autoFit="normal-auto-fit">
    <p>归</p><p>园</p><p>·</p><p>空</p><p>间</p>
  </content>
</shape>
```

### 4.6 原生结构件（图表 / 表格）

**语法见 §五。** ✗ 不要用矩形拼柱子、不要用矩形拼表格——拼出来对不齐，而且改一个数要挪十个块。

---

## 五、原生结构件：图表与表格

**下面三段都在真宿主上渲染验证过，可以直接抄。**
`<chart>` 与 `<table>` 是 `<data>` 的直接子元素，和 `<shape>`／`<img>` 平级，自带几何四属性。

### 5.1 `<chart>`（`type` 实测可用：`column` 柱 / `bar` 横条 / `line` 折线 / `pie` 饼）

```xml
<chart width="420" height="220" topLeftX="40" topLeftY="120" id="c1">
  <chartPlotArea>
    <chartPlot type="column"><chartExtra/></chartPlot>
    <chartAxes>
      <chartAxis type="x"><chartLabel fontSize="9" color="rgba(190,184,174,0.7)"/></chartAxis>
      <chartAxis type="y" position="left">
        <chartGridLine color="rgb(52, 47, 42)"/>
        <chartLabel fontSize="9" color="rgba(190,184,174,0.7)"/>
      </chartAxis>
    </chartAxes>
  </chartPlotArea>
  <chartData isStaticData="true">
    <dim1>
      <chartField name="年份">2023,2024,2025<chartParsedValues>2023</chartParsedValues><chartParsedValues>2024</chartParsedValues><chartParsedValues>2025</chartParsedValues></chartField>
    </dim1>
    <dim2>
      <chartField name="到店">18,26,31</chartField>
      <chartField name="线上">12,19,28</chartField>
    </dim2>
  </chartData>
  <chartStyle>
    <chartBackground color="rgba(0,0,0,0)"/>
    <chartBorder color="rgba(0,0,0,0)" width="0"/>
    <chartColorTheme><color value="rgb(40,60,120)"/><color value="rgb(201,85,46)"/></chartColorTheme>
  </chartStyle>
</chart>
```

- `<dim1>` **类目轴**：`name` 是维度名，正文是逗号串，**再逐个重复成 `<chartParsedValues>`**（两处都要写）。
- `<dim2>` **数值系列**：一个 `<chartField>` 一条系列，正文是逗号串，**不写 `chartParsedValues`**。
- `pie` 只用一条系列，且**不写 `<chartAxes>`**。
- `<chartBackground>` 与 `<chartBorder>` 设成全透明，图表才融得进页面的地。
- **网格线默认是开的、而且是浅色**——深底上会变成一排刺眼的白线。
  **要压掉就显式给它一个贴近地色的实色**：`<chartGridLine color="rgb(52, 47, 42)"/>`（写在 y 轴里）。
  ⚠ **`rgba(...)` 带 alpha 的写法这里不生效**，只有 `rgb(r, g, b)` 有效（实测）。
- 轴标签颜色用 `<chartLabel color="rgba(...)"/>`（这里 `rgba` 有效）；深底上不给颜色会是暗灰，读不清。
- **样式纪律**：网格线压到几乎看不见、无图例框、只用墨色＋中性灰＋强调色，不引第二色族；
  要给 y 轴限幅写 `<chartAxis type="y" position="left" max="10" min="7">`。

### 5.2 `<table>`（参数、规格、对照——比矩形拼稳，且能改列宽与底色）

```xml
<table width="700" height="120" topLeftX="40" topLeftY="300" id="t1">
  <colgroup><col span="1" width="260"/><col span="1" width="220"/><col span="1" width="220"/></colgroup>
  <tr height="34">
    <td><fill><fillColor color="rgba(40,60,120,1)"/></fill>
      <content fontSize="12" fontFamily="思源黑体" color="rgba(255,255,255,1)" bold="true" textAlign="left"><p>参数</p></content></td>
    <td><fill><fillColor color="rgba(40,60,120,1)"/></fill>
      <content fontSize="12" fontFamily="思源黑体" color="rgba(255,255,255,1)" bold="true" textAlign="left"><p>方案 A</p></content></td>
  </tr>
  <tr height="30">
    <td><content fontSize="12" fontFamily="思源黑体" color="rgba(45,45,45,1)" textAlign="left"><p>层数</p></content></td>
    <td><content fontSize="12" fontFamily="思源黑体" color="rgba(45,45,45,1)" textAlign="left"><p>6</p></content></td>
  </tr>
</table>
```

- `<colgroup><col width>` 定列宽，**加起来等于 `<table>` 的 width**；`<tr height>` 定行高。
- 单元格底色写 `<td><fill><fillColor .../></fill>…</td>`——**`<fill>` 是 `<td>` 的直接子元素**，
  ✗ 外面套 `<style>` 会**静默不渲染**（表头白字就此消失在白底上）。
- 表头行给深色底＋反白字，正文行留空或隔行给一层极浅底；**不画竖线**，靠列宽与底色分栏。

### 5.3 `<embed>` ＋ 内联 `<svg>`（**先渲染确认再用**）

宿主的 XML 里有 `<embed>` 可以内嵌 SVG，但**在预览通路上实测渲染成占位图**
（单 `path`、多元素、多 `path` 三种写法一致）。**要用它就先渲染一页确认**，
看到占位图就退回下面这条对照写法——它实测通过：

```xml
<shape type="rect" topLeftX="40" topLeftY="300" width="130" height="54" presetHandlers="0">
  <fill><fillColor color="rgba(255,255,255,1)"/></fill><border color="rgba(40,60,122,1)" width="2"/>
  <content fontSize="14" fontFamily="思源黑体" color="rgba(40,64,122,1)"><p>编码层</p></content>
</shape>
<line startX="176" startY="327" endX="212" endY="327" id="l1"><border color="rgba(40,64,122,1)" width="2"/></line>
```

**流程图、架构图、时序图用 `rect`＋`line` 拼是正当做法**（参照稿里最密的一份线框图解 61 条 `<line>`、0 张图）——
§二 §三 的"不要拿 shape 拼"说的是**表格与图表**，不是示意图。

### 4.7 原生表格

参数、规格、对照一律用原生表格，不要用矩形拼。列宽写在 `colgroup` 的 `col width` 上。

### 4.8 细线与分隔（**`<line>` 用起止点，不用 topLeft/width/height**）

```xml
<!-- 横线 -->
<line startX="60" startY="96" endX="900" endY="96">
  <stroke><strokeColor color="rgba(0,0,0,0.12)"/></stroke>
</line>
<!-- 竖线：同一套写法，改成起止点的 x 相同 -->
<line startX="480" startY="80" endX="480" endY="460">
  <stroke><strokeColor color="rgba(140,124,100,0.25)"/></stroke>
</line>
```

⚠ **写成 `<line topLeftX=… width=… height=…>` 会被服务端拒收**，那一整页写入失败
（尤其竖线写成 `width="0"`）。真稿里的线一律是 `startX/startY/endX/endY`。
要一条有厚度的色带就别用 `<line>`，用 `<shape type="rect">` 给它宽高。

---

## 六、图片写法要点

- `<img src>` 只接受宿主的图片 **`file_token`**（先上传拿到）。**外链 http(s) 不渲染。**
- 同题材可换尺度与位置复现；换比例须重生/重检索，≤10% 才可裁。主体画面只用一页；纹理／氛围底板另计，用户明确要求复用时各页写同一 `reuse=user:<用户要求>`
- 图片不贴页边、面积又小、又没有底色托底 → 渲染出来是一块悬空矩形。要么出血，要么给它托底/边框。
- 附件里的图纸、照片**不许裁切**：调整图窗比例去适配它，而不是让它适配版面。

---

## 七、写入与排障

**图片刚上传完不要马上渲染**：拿到 `file_token` 之后有几十秒索引延迟，这期间渲染出来的是
**占位图**（灰方块＋感叹号），而命令本身**退出 0**。看到占位图先隔一会儿重截，不要以为是 `src` 写错了。

- 写入命令、截图命令、回读命令**一律以 `hostcheck` 打印的为准**，不要凭记忆写。
- **上传命令会先打印一行进度再打印 JSON**：直接 `json.load` 会炸。取 token 时先把 JSON 之前的行剥掉
  （例：`… | sed -n '/^{/,$p'`），再取 `data.file_token`。
- 写入返回成功 ≠ 页面有内容：**必须回读确认**。
- 中途失败不要假设原操作原子成功：先回读看现在有几页，再补写或重写。
- 插页要指定「插在哪一页之前」时，注意这类参数通常**只能放进请求体**，放进 query 会被静默忽略（接口照样返回成功，新页却跑到末尾）。

# 纸张、印花与贴布细节原子

按质感机制检索，所有作用对象共用下列生成器，不复制“背景版／卡片版”。状态：程序化 SVG 近似实现；每项的局限见正文。不能将近似渲染当作原图材质复刻通过。

实现源：[make-craft-texture.py](../../../../scripts/runtime/make-craft-texture.py)。脚本使用标准库，固定 seed 可复现；拒绝覆盖已有输出。输出为完整独立 SVG，无网络依赖。SVG/filter 不能运行时，须在受支持浏览器中预渲染资产并检查；不得悄悄退回纯色后仍称效果完成。

参考：TT 提供的纸片／蜡封素材板（958cf1b8）与 GORGEOUS 贴布字板（dda013c9），2026-09-12；只分析机制，不打包或分发原参考图。字典文字是内容，星星／蝴蝶是造型，天空是图像，均不登记为纹理。

## 共用参数与绑定

`--width/--height` 64–4096px；`--seed` 默认17；`--color/--base` 为 #RRGGBB；`--step` 4–256px（仅印纹）；`--strength` 0–1（颗粒／浮雕）；`--font/--weight/--text` 仅文字或印记。默认配色只是样例，生成时必须绑定当前设计的颜色。

- 背景：SVG作为独立表面层，设定范围与缩放；纹理透明度只作用于纹理层，不能模糊／淡化正文。
- 卡片：生成尺寸匹配载体比例，不把撕边与卷角强拉伸；内容层独立，按实际形状预留安全区。
- 字体：印花／金箔通过现有 [text.paint](../layouts/layout-and-type.md#text.paint) 裁切到字形。贴布字直接生成SVG text；默认Arial 700；实际任务须用已验证字体与真实字重，例如 Arial 700 或 Source Han Sans 900，确认加载后再导出。避免细小正文、细字重与复杂字腔。
- 图2格纹布上叠贴布字：先生成gingham作底，再将applique透明SVG置于上层；两层分别控制配色与尺度。波点复用 [surface.dot-pattern](paper-and-print.md#surface.dot-pattern)，不用新建第二个波点原子。
- 内嵌多个SVG时应对内部ID做实例前缀处理；作为各自的img文件使用则无ID冲突。生产交付仍遵循现有SVG内嵌、字体和渲染协议。

<a id="surface.crumpled-paper"></a>
## 揉皱纸折面

风格标签：通用。机制：纸张印刷；适用对象：card / background。

分片明暗＋折线＋细粒。强折痕为三角折面近似，不是照片级揉纸；强度建议 .25–.65。

```bash
python3 scripts/runtime/make-craft-texture.py crumpled-paper /任务目录/crumpled-paper.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="crumpled-paper.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="shape.fiber-edge"></a>
## 撕边外露纤维

风格标签：通用。机制：纸张印刷；适用对象：card。

不规则轮廓与短纤维线；透明外缘保留20px，文字安全区至少32px。不是旧撕边轮廓的重复登记，增加了外露纤维。

```bash
python3 scripts/runtime/make-craft-texture.py fiber-edge /任务目录/fiber-edge.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="fiber-edge.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="shape.paper-curl"></a>
## 纸张卷角

风格标签：通用。机制：纸张印刷；适用对象：card。

右下角向内翻起的纸背、原角留空和独立接触阴影；卷角边长为短边27%，内容避开该区。只支持单角二维近似。

```bash
python3 scripts/runtime/make-craft-texture.py paper-curl /任务目录/paper-curl.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="paper-curl.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.crumpled-foil"></a>
## 粗糙金箔浮雕

风格标签：通用。机制：金属浮雕；适用对象：text / card / background。

多尺度噪声高度场＋定向光照；颜色建议 #b99a48，强度默认 .45，建议 .2–.5；起伏已降低，高光收敛。属于浮雕金箔近似，不是实拍金属反射。

```bash
python3 scripts/runtime/make-craft-texture.py crumpled-foil /任务目录/crumpled-foil.svg --width 600 --height 360 --color '#b99a48' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="crumpled-foil.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="shape.wax-seal"></a>
## 蜡封凸缘与压印

风格标签：通用。机制：金属浮雕；适用对象：card。

不规则圆缘、凹环与双层错位压印。示例用两字母印记；复杂玫瑰徽章需提供真实路径，不声称已复刻玫瑰。蜡封为局部装饰，不铺整页。

```bash
python3 scripts/runtime/make-craft-texture.py wax-seal /任务目录/wax-seal.svg --width 600 --height 360 --color '#b99a48' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="wax-seal.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.graph-paper"></a>
## 方格纸印纹

风格标签：通用。机制：纸张印刷；适用对象：text / card / background。

两向等距细线，可调格距与颜色；step为最终SVG像素格距，缩放后检查线条。

```bash
python3 scripts/runtime/make-craft-texture.py graph-paper /任务目录/graph-paper.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="graph-paper.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.ruled-paper"></a>
## 横线纸印纹

风格标签：通用。机制：纸张印刷；适用对象：text / card / background。

水平等距细线；文字行高与横线间距分别控制，不能自动认定基线已对齐。

```bash
python3 scripts/runtime/make-craft-texture.py ruled-paper /任务目录/ruled-paper.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="ruled-paper.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.gingham"></a>
## 格纹布与经纬细纹

风格标签：通用。机制：织物编织；适用对象：text / card / background。

横竖半透明宽色带交叠成深格，叠加细经纬；格距建议24–64px，区别于仅有细线的woven-grid。真实布面皱褶仍需另加折面或素材。

```bash
python3 scripts/runtime/make-craft-texture.py gingham /任务目录/gingham.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="gingham.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.chevron"></a>
## 锯齿印花

风格标签：通用。机制：纸张印刷；适用对象：text / card / background。

周期折线印花，线宽为周期25%；只生成印花，不自动添加布料厚度。

```bash
python3 scripts/runtime/make-craft-texture.py chevron /任务目录/chevron.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="chevron.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察纹理尺度、边缘裁切、文字安全区与缩图摩尔纹。不存在引用图片即自动完成材质的判定。

<a id="surface.applique"></a>
## 贴布缝线字

风格标签：通用。机制：织物编织；适用对象：text。

真实SVG文字轮廓描边＋虚线针脚＋粗糙外缘＋字形内侧微阴影（偏移0.8px、模糊0.55px、透明度0.22；600px画布）＋松线，非矩形缝线框。字符保持可编辑；粗绒、逐根毛线和精密刺绣为近似。

```bash
python3 scripts/runtime/make-craft-texture.py applique /任务目录/applique.svg --width 600 --height 360 --color '#87b2d0' --base '#f8f1df' --weight 700
```

HTML 绑定（文件在任务中复制／内嵌，路径按任务调整）：

```html
<img src="applique.svg" alt="" aria-hidden="true" style="display:block;width:100%;height:auto;pointer-events:none">
```

检查：在最终输出尺寸观察字腔是否堵塞、针脚是否沿字形、字体是否实际加载。不存在引用图片即自动完成材质的判定。


## 布艺拼贴字体组合

以下为参考图启发的可用搭配，非原字形鉴定。拉丁字选 **Arial 700**（预览实际使用；轮廓较规整），中文选 **Source Han Sans 900**，任务中先验证字体文件加载。需要参考中摇摆、膨胀的字形时须单独调整字形，不能声称换色后已复刻。描边8px、针脚2px／3px虚线在600px示例画布上定义，随SVG等比缩放；标题建议最终不小于36px。投影仅保留字形内部窄边，不向下外扩；针脚层位于内阴影上方。四组共用applique与gingham，不复制纹理实现。

<a id="combination.craft-denim-cocoa"></a>
### 丹宁蓝 × 可可格纹

- 配色：字面 `#98c9e0`；外描边 `#567b99`；针脚 `#e5eff0`；底布格纹 `#644b39`／`#ddcdb7`。
- 字体：Arial 700 / Source Han Sans 900；粗标题，单行或人工断行。
- 质感：细经纬布面、淡色短针脚；布底step=40，字面细纹4px。正文不套用贴布字。
- 关系：底布为独立背层，标题透明SVG叠于其上，四边至少24px安全区；装饰松线留在标题图层，不跨正文。

```bash
python3 scripts/runtime/make-craft-texture.py gingham /任务目录/denim-cocoa-cloth.svg --color '#644b39' --base '#ddcdb7' --step 40
python3 scripts/runtime/make-craft-texture.py applique /任务目录/denim-cocoa-title.svg --color '#98c9e0' --outline '#567b99' --base '#e5eff0' --font Arial --weight 700 --text GORGEOUS
```

<a id="combination.craft-butter-rose"></a>
### 奶油黄 × 玫瑰粉

- 配色：字面 `#ede79a`；外描边 `#6c965f`；针脚 `#fff6d2`；底布格纹 `#d9829b`／`#fbe7ea`。
- 字体：Arial 700 / Source Han Sans 900；粗标题，单行或人工断行。
- 质感：浅黄布面、绿轮廓、奶油色针脚；布底step=40，字面细纹4px。正文不套用贴布字。
- 关系：底布为独立背层，标题透明SVG叠于其上，四边至少24px安全区；装饰松线留在标题图层，不跨正文。

```bash
python3 scripts/runtime/make-craft-texture.py gingham /任务目录/butter-rose-cloth.svg --color '#d9829b' --base '#fbe7ea' --step 40
python3 scripts/runtime/make-craft-texture.py applique /任务目录/butter-rose-title.svg --color '#ede79a' --outline '#6c965f' --base '#fff6d2' --font Arial --weight 700 --text GORGEOUS
```

<a id="combination.craft-pink-cocoa"></a>
### 樱花粉 × 深巧克力

- 配色：字面 `#edb3ca`；外描边 `#794b59`；针脚 `#fff1e4`；底布格纹 `#543729`／`#f4d8bf`。
- 字体：Arial 700 / Source Han Sans 900；粗标题，单行或人工断行。
- 质感：柔粉织纹、深玫瑰外缘、浅米针脚；布底step=40，字面细纹4px。正文不套用贴布字。
- 关系：底布为独立背层，标题透明SVG叠于其上，四边至少24px安全区；装饰松线留在标题图层，不跨正文。

```bash
python3 scripts/runtime/make-craft-texture.py gingham /任务目录/pink-cocoa-cloth.svg --color '#543729' --base '#f4d8bf' --step 40
python3 scripts/runtime/make-craft-texture.py applique /任务目录/pink-cocoa-title.svg --color '#edb3ca' --outline '#794b59' --base '#fff1e4' --font Arial --weight 700 --text GORGEOUS
```

<a id="combination.craft-ivory-red"></a>
### 象牙白 × 草莓红

- 配色：字面 `#f5ecd8`；外描边 `#a18f75`；针脚 `#fffdf4`；底布格纹 `#cf344c`／`#ffece5`。
- 字体：Arial 700 / Source Han Sans 900；粗标题，单行或人工断行。
- 质感：米白经纬、灰褐窄外缘、白针脚；布底step=40，字面细纹4px。正文不套用贴布字。
- 关系：底布为独立背层，标题透明SVG叠于其上，四边至少24px安全区；装饰松线留在标题图层，不跨正文。

```bash
python3 scripts/runtime/make-craft-texture.py gingham /任务目录/ivory-red-cloth.svg --color '#cf344c' --base '#ffece5' --step 40
python3 scripts/runtime/make-craft-texture.py applique /任务目录/ivory-red-title.svg --color '#f5ecd8' --outline '#a18f75' --base '#fffdf4' --font Arial --weight 700 --text GORGEOUS
```

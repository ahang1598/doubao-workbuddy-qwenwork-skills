# 点缀-HTML合集

按条目检索读取，不整篇加载。

## 卡片-折痕纸张

逻辑路径：assets/模板库/点缀/卡片-折痕纸张.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0236
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>卡片-折痕纸张</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}body{display:grid;place-items:center;background:#cecece}.paper{--width:628px;--edge-width:.65;--edge-color:#c4c4c4;--corner-radius:1px;--fine-noise-opacity:.1;--coarse-noise-opacity:.08;--fiber-opacity:.065;--fold-dark-opacity:.1;--fold-light-opacity:.16;--fold-blur:1.25px;--shadow-opacity:.16;position:relative;width:min(var(--width),90vw,calc(90vh * 1.57));aspect-ratio:1.57;container-type:inline-size;border-radius:var(--corner-radius);filter:drop-shadow(0 3px 3px rgb(0 0 0 / var(--shadow-opacity)));color:#373737}.layer{position:absolute;display:block;pointer-events:none}.base,.texture{inset:0;width:100%;height:100%}.base{z-index:0}.texture{z-index:1}.fold{z-index:2;left:0;top:29%;width:100%;height:8%;overflow:hidden}.copy{position:absolute;z-index:3;left:5.5%;top:10%;width:89%;height:80%}.heading{display:flex;justify-content:space-between;align-items:baseline;gap:1em;font:400 4.7cqw/1.15 Georgia,'Songti SC',serif;letter-spacing:0}.heading time{font-variant-numeric:lining-nums}.story{position:absolute;left:0;right:0;top:40%;margin:0;font:600 4.3cqw/1.4 Arial,'Microsoft YaHei',sans-serif;letter-spacing:0}.story p{margin:0}.story p+p{margin-top:.65em}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><article class="paper" data-component-class="card" aria-label="卡片-折痕纸张"><svg class="layer base" viewbox="0 0 628 400" preserveaspectratio="none" aria-hidden="true"><defs><lineargradient id="paper-tone" x1="0" y1="0" x2=".35" y2="1"><stop stop-color="#ededed"></stop><stop offset=".48" stop-color="#e8e8e8"></stop><stop offset="1" stop-color="#e3e3e3"></stop></lineargradient></defs><path d="M1.4 1.2L152 .7 298 1.5 449 .8 626.4 1.6 627.2 94 626.6 182 627.3 293 626.1 398.6 465 399.1 307 398.3 151 399.2 1.1 398.3 .7 284 1.4 199 .6 103Z" fill="url(#paper-tone)" stroke="var(--edge-color)" stroke-width="var(--edge-width)"></path><path d="M3 2.5L152 2 298 2.8 449 2.1 625 2.9" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width=".8"></path></svg><svg class="layer texture" viewbox="0 0 628 400" preserveaspectratio="none" aria-hidden="true"><defs><clippath id="paper-clip"><path d="M1.4 1.2L152 .7 298 1.5 449 .8 626.4 1.6 627.2 94 626.6 182 627.3 293 626.1 398.6 465 399.1 307 398.3 151 399.2 1.1 398.3 .7 284 1.4 199 .6 103Z"></path></clippath><filter id="fine-grain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feturbulence type="fractalNoise" basefrequency=".83" numoctaves="3" seed="12" stitchtiles="stitch"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter><filter id="coarse-grain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feturbulence type="fractalNoise" basefrequency=".035 .055" numoctaves="3" seed="8" stitchtiles="stitch"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter><filter id="fiber-grain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feturbulence type="fractalNoise" basefrequency=".12 .7" numoctaves="2" seed="21" stitchtiles="stitch"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter><pattern id="loose-fibers" width="97" height="73" patternunits="userSpaceOnUse"><g fill="none" stroke="#666" stroke-width=".45"><path d="M7 12l4 -1m23 15l2 3m35 -19l6 1M14 55l5 -2m43 8l3 -1m21 -20l2 3M45 45l5 -1"></path></g><g fill="none" stroke="#fff" stroke-width=".65"><path d="M20 31l6 1m29 -16l3 -1m18 42l6 1M3 67l4 -1m39 -5l3 2"></path></g></pattern></defs><g clip-path="url(#paper-clip)"><rect width="628" height="400" filter="url(#fine-grain)" opacity="var(--fine-noise-opacity)"></rect><rect width="628" height="400" filter="url(#coarse-grain)" opacity="var(--coarse-noise-opacity)"></rect><rect width="628" height="400" filter="url(#fiber-grain)" opacity="var(--fiber-opacity)"></rect><rect width="628" height="400" fill="url(#loose-fibers)" opacity=".18"></rect></g></svg><svg class="layer fold" viewbox="0 0 628 32" preserveaspectratio="none" aria-hidden="true"><defs><lineargradient id="fold-fade"><stop stop-color="#000"></stop><stop offset=".13" stop-color="#fff"></stop><stop offset=".84" stop-color="#fff"></stop><stop offset="1" stop-color="#000"></stop></lineargradient><mask id="fold-mask"><rect width="628" height="32" fill="url(#fold-fade)"></rect></mask><lineargradient id="crease" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#555" stop-opacity="0"></stop><stop offset=".38" stop-color="#555" stop-opacity="var(--fold-dark-opacity)"></stop><stop offset=".49" stop-color="#444" stop-opacity="var(--fold-dark-opacity)"></stop><stop offset=".57" stop-color="#fff" stop-opacity="var(--fold-light-opacity)"></stop><stop offset=".73" stop-color="#fff" stop-opacity="var(--fold-light-opacity)"></stop><stop offset="1" stop-color="#fff" stop-opacity="0"></stop></lineargradient></defs><g mask="url(#fold-mask)"><path d="M0 3Q160 5 315 7T628 10L628 24Q472 21 315 21T0 17Z" fill="url(#crease)" style="filter:blur(var(--fold-blur))"></path><path d="M0 10Q158 12 315 14T628 17" fill="none" stroke="#666" stroke-opacity=".055" stroke-width=".7"></path><path d="M0 11.2Q158 13.2 315 15.2T628 18.2" fill="none" stroke="#fff" stroke-opacity=".16" stroke-width=".8"></path></g></svg><div class="copy"><header class="heading" data-role="内容层"><span>说明文字</span><time datetime="2026">00.00</time></header><div class="story" data-role="内容层"><p>说明文字</p><p>说明文字<br>说明文字</p></div></div></article></body></html>
````

## 点缀-三笔动感线

逻辑路径：assets/模板库/点缀/点缀-三笔动感线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0134
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-三笔动感线</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e5e5e5}.motion{--size:min(65vw,54vh,260px);--stroke-width:19;--ink:#414141;--rotation:0deg;--mirror:1;--cap:round;width:var(--size);aspect-ratio:.78;transform:rotate(var(--rotation)) scaleX(var(--mirror));transform-origin:100% 50%}.motion svg{display:block;width:100%;height:100%;overflow:visible}.motion path{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:var(--cap);stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="motion" data-component-class="decoration" data-role="内容层" role="img" aria-label="点缀-三笔动感线"><svg viewbox="0 0 100 100" preserveaspectratio="none" aria-hidden="true"><g><path d="M 54 12 Q 72 19 86 28"></path><path d="M 20 47 Q 35 44 45 54"></path><path d="M 14 84 Q 34 83 50 84"></path></g></svg></div></body></html>
````

## 点缀-三角小旗

逻辑路径：assets/模板库/点缀/点缀-三角小旗.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0092
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-三角小旗</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e6e6e6}.flag{--size:min(52vw,42vh,210px);--pole-width:2.03;--pole-tone:#535353;--cloth-tone:#777;--grain-opacity:.12;--rotation:0deg;width:var(--size);aspect-ratio:.58;transform:rotate(var(--rotation))}.flag svg{display:block;width:100%;height:100%;overflow:visible}.pole{stroke:var(--pole-tone);stroke-width:var(--pole-width);stroke-linecap:butt}.cloth{fill:var(--cloth-tone)}.grain{opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="flag" data-component-class="decoration" role="img" aria-label="点缀-三角小旗"><svg viewbox="0 0 58 100" aria-hidden="true"><defs><clippath id="clothClip"><path d="M 9.28 5 L 55.68 34 L 9.28 66 Z"></path></clippath><pattern id="brush" width="13" height="11" patternunits="userSpaceOnUse"><g fill="none" stroke-linecap="round"><path d="M-3 8L15 2 M0 10L9 7 M5 4L14 1" stroke="#fff" stroke-width=".65"></path><path d="M2-2L6 12 M10-2L12 10" stroke="#252525" stroke-width=".45"></path><path d="M-2 5L5 3" stroke="#fff" stroke-width="1.2"></path></g></pattern></defs><path class="pole" d="M 9.28 0 L 9.28 100" fill="none"></path><path class="cloth" d="M 9.28 5 L 55.68 34 L 9.28 66 Z"></path><g class="grain" clip-path="url(#clothClip)"><path d="M 9.28 5 L 55.68 34 L 9.28 66 Z" fill="url(#brush)"></path><path d="M 11 18 L 46 32 M 11 46 L 37 36 M 12 57 L 28 44" fill="none" stroke="#fff" stroke-width=".7"></path></g></svg></div></body></html>
````

## 点缀-三重上箭头

逻辑路径：assets/模板库/点缀/点缀-三重上箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0171
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-三重上箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e5e5e5}.arrows{--size:min(54vw,42vh,220px);--stroke-width:10.98;--ink:#515151;--rotation:0deg;--linecap:butt;--linejoin:miter;width:var(--size);aspect-ratio:.61;transform:rotate(var(--rotation));transform-origin:50% 50%}.arrows svg{display:block;width:100%;height:100%;overflow:visible}.arrows polyline{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:var(--linecap);stroke-linejoin:var(--linejoin);stroke-miterlimit:4}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="arrows" data-component-class="decoration" role="img" aria-label="点缀-三重上箭头"><svg viewbox="0 0 61 100" aria-hidden="true"><polyline points="6.1,29 30.5,6 54.9,29"></polyline><polyline points="6.1,59 30.5,36 54.9,59"></polyline><polyline points="6.1,89 30.5,66 54.9,89"></polyline></svg></div></body></html>
````

## 点缀-三预设放射贴纸

逻辑路径：assets/模板库/点缀/点缀-三预设放射贴纸.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-三预设放射贴纸</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.cv-radial,.cv-radial *{box-sizing:border-box}.cv-radial{--cv-sticker-size:128px;--cv-sticker-color:#bd573a;--cv-sticker-rotate:0deg;--cv-arm-width:14px;display:block;width:var(--cv-sticker-size);max-width:100%;aspect-ratio:1;color:var(--cv-sticker-color);transform:rotate(var(--cv-sticker-rotate));overflow:visible}.cv-radial .cv-radial-asterisk,.cv-radial .cv-radial-petal,.cv-radial .cv-radial-spike{display:none}.cv-radial[data-preset=asterisk] .cv-radial-asterisk{display:block;fill:none;stroke:currentColor;stroke-width:var(--cv-arm-width);stroke-linecap:butt}.cv-radial[data-preset=petal] .cv-radial-petal{display:block;fill:currentColor}.cv-radial[data-preset=spike] .cv-radial-spike{display:block;fill:currentColor}.cv-radial-demo,.cv-radial-demo *{box-sizing:border-box}.cv-radial-demo{width:min(100%,680px);padding:28px;background:#f7f2e7;color:#343b30;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-radial-demo h2{margin:0 0 10px;font-size:22px}.cv-radial-demo p{margin:0 0 22px}.cv-radial-demo .cv-radial-list{display:flex;flex-wrap:wrap;gap:28px;padding:16px}.cv-radial-demo figure{margin:0}.cv-radial-demo figcaption{text-align:center;margin-top:14px}
</style></head><body><section class="cv-radial-demo"><h2>放射造型</h2><p>Alex Chen · Visual Designer<br>Editorial experiments, 2021–2025</p><div class="cv-radial-list"><figure><svg class="cv-radial" data-preset="asterisk" viewBox="0 0 100 100" role="img" aria-label="八臂星号"><g class="cv-radial-asterisk"><path d="M50 6V94M6 50H94M19 19L81 81M19 81L81 19"/></g><g class="cv-radial-petal"><circle cx="50" cy="50" r="29"/><circle cx="50" cy="20" r="17"/><circle cx="71.2" cy="28.8" r="17"/><circle cx="80" cy="50" r="17"/><circle cx="71.2" cy="71.2" r="17"/><circle cx="50" cy="80" r="17"/><circle cx="28.8" cy="71.2" r="17"/><circle cx="20" cy="50" r="17"/><circle cx="28.8" cy="28.8" r="17"/></g><polygon class="cv-radial-spike" points="50,3 57.8,21 73.5,9.3 71.2,28.8 90.7,26.5 79,42.2 97,50 79,57.8 90.7,73.5 71.2,71.2 73.5,90.7 57.8,79 50,97 42.2,79 26.5,90.7 28.8,71.2 9.3,73.5 21,57.8 3,50 21,42.2 9.3,26.5 28.8,28.8 26.5,9.3 42.2,21"/></svg><figcaption>八臂星号</figcaption></figure><figure><svg class="cv-radial" data-preset="petal" viewBox="0 0 100 100" role="img" aria-label="八圆瓣"><g class="cv-radial-petal"><circle cx="50" cy="50" r="29"/><circle cx="50" cy="20" r="17"/><circle cx="71.2" cy="28.8" r="17"/><circle cx="80" cy="50" r="17"/><circle cx="71.2" cy="71.2" r="17"/><circle cx="50" cy="80" r="17"/><circle cx="28.8" cy="71.2" r="17"/><circle cx="20" cy="50" r="17"/><circle cx="28.8" cy="28.8" r="17"/></g></svg><figcaption>圆瓣</figcaption></figure><figure><svg class="cv-radial" data-preset="spike" viewBox="0 0 100 100" role="img" aria-label="十二尖角"><polygon class="cv-radial-spike" points="50,3 57.8,21 73.5,9.3 71.2,28.8 90.7,26.5 79,42.2 97,50 79,57.8 90.7,73.5 71.2,71.2 73.5,90.7 57.8,79 50,97 42.2,79 26.5,90.7 28.8,71.2 9.3,73.5 21,57.8 3,50 21,42.2 9.3,26.5 28.8,28.8 26.5,9.3 42.2,21"/></svg><figcaption>尖角</figcaption></figure></div></section>
</body></html>
````

## 点缀-乳白月盘

逻辑路径：assets/模板库/点缀/点缀-乳白月盘.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0224
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-乳白月盘</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#d7d7d7}.moon{--size:min(80vw,80vh,440px);--cloud-opacity:.08;--grain-opacity:.05;--disc-opacity:1;--rotation:0deg;--edge-softness:3.6px;width:var(--size);aspect-ratio:1;transform:rotate(var(--rotation))}.moon svg{display:block;width:100%;height:100%}.fill{opacity:var(--disc-opacity)}.cloud{opacity:var(--cloud-opacity)}.grain{opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="moon" data-component-class="decoration" role="img" aria-label="点缀-乳白月盘"><svg viewbox="0 0 400 400" aria-hidden="true"><defs><path id="outline" d="M 199 5 C 231 3 260 13 287 25 C 319 40 343 62 363 89 C 383 119 393 148 395 183 C 397 211 393 245 380 275 C 367 308 343 336 315 357 C 286 380 252 390 219 394 C 184 398 154 392 123 380 C 92 370 67 351 46 324 C 24 297 12 265 7 234 C 2 203 4 170 15 139 C 24 110 41 84 63 62 C 86 40 114 24 143 14 C 164 7 182 6 199 5 Z"></path><radialgradient id="milk" cx="49%" cy="48%" r="51%"><stop offset="0" stop-color="#fff" stop-opacity=".04"></stop><stop offset=".5" stop-color="#fff" stop-opacity=".14"></stop><stop offset=".82" stop-color="#fff" stop-opacity=".58"></stop><stop offset=".96" stop-color="#fff" stop-opacity=".64"></stop><stop offset="1" stop-color="#fff" stop-opacity=".12"></stop></radialgradient><filter id="edge" x="-5%" y="-5%" width="110%" height="110%"><fegaussianblur stddeviation="1.8"></fegaussianblur></filter><mask id="softMask" maskunits="userSpaceOnUse" x="0" y="0" width="400" height="400"><use href="#outline" fill="#fff" filter="url(#edge)"></use></mask><filter id="cloudNoise" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency=".014" numoctaves="2" seed="12" result="noise"></feturbulence><fecolormatrix in="noise" type="saturate" values="0"></fecolormatrix><fecomponenttransfer><fefuncr type="linear" slope="0" intercept="1"></fefuncr><fefuncg type="linear" slope="0" intercept="1"></fefuncg><fefuncb type="linear" slope="0" intercept="1"></fefuncb><fefunca type="gamma" amplitude="1" exponent="1.6" offset="0"></fefunca></fecomponenttransfer></filter><filter id="fineNoise" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency="1.65" numoctaves="1" seed="41"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter><radialgradient id="cloudPatch" cx="34%" cy="39%" r="65%"><stop stop-color="#fff" stop-opacity=".75"></stop><stop offset=".42" stop-color="#fff" stop-opacity=".05"></stop><stop offset=".72" stop-color="#fff" stop-opacity=".6"></stop><stop offset="1" stop-color="#fff" stop-opacity="0"></stop></radialgradient></defs><g mask="url(#softMask)"><g class="fill"><use href="#outline" fill="url(#milk)" filter="url(#edge)"></use></g><g class="cloud"><rect width="400" height="400" fill="#fff" filter="url(#cloudNoise)"></rect><path d="M 34 131 C 108 62 170 155 244 96 C 295 62 361 109 384 171 L 371 296 C 293 330 258 214 180 289 C 112 341 41 268 18 219 Z" fill="url(#cloudPatch)" filter="url(#edge)"></path></g><rect class="grain" width="400" height="400" filter="url(#fineNoise)"></rect></g></svg></div></body></html>
````

## 点缀-低丘剪影

逻辑路径：assets/模板库/点缀/点缀-低丘剪影.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0122
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-低丘剪影</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#ededed}.hill{--size:660px;--fill:#484848;--stroke-width:0;--rotation:0deg;width:min(var(--size),86vw,210vh);aspect-ratio:3;transform:rotate(var(--rotation))}.hill svg{display:block;width:100%;height:100%;overflow:visible}.silhouette{fill:var(--fill);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="hill" data-component-class="decoration" role="img" aria-label="点缀-低丘剪影"><svg viewbox="0 0 300 100" xmlns="http://www.w3.org/2000/svg"><path class="silhouette" transform="scale(300 100)" d="M0 1 C.02 .64 .09 .75 .14 .40 C.26 -.10 .36 .03 .48 .31 C.62 .63 .66 .35 .80 .52 C.90 .64 .95 .81 1 1 Z"></path></svg></div></body></html>
````

## 点缀-倾斜奖杯

逻辑路径：assets/模板库/点缀/点缀-倾斜奖杯.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0173
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-倾斜奖杯</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#eeeeee}.trophy{--size:430px;--body:#a9a9a9;--rim:#747474;--base:#858585;--highlight:#e3e3e3;--mark:#424242;--handle-stroke:5;--rotation:-24deg;width:min(var(--size),82vw,80vh);aspect-ratio:1}.trophy svg{display:block;width:100%;height:100%}.assembly{transform:rotate(var(--rotation));transform-origin:50px 50px}.handles{fill:none;stroke:var(--rim);stroke-width:var(--handle-stroke)}.bowl{fill:var(--body)}.highlight{fill:var(--highlight)}.rim{fill:var(--rim)}.base{fill:var(--base)}.mark{fill:var(--mark)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="trophy" data-component-class="decoration" role="img" aria-label="点缀-倾斜奖杯"><svg viewbox="-17 -17 134 134" xmlns="http://www.w3.org/2000/svg"><g class="assembly"><g class="handles"><ellipse cx="15" cy="29.5" rx="10.5" ry="19"></ellipse><ellipse cx="85" cy="29.5" rx="10.5" ry="19"></ellipse></g><g><path class="base" d="M45 54 H55 V76 H45 Z"></path><path class="base" d="M36 75 H64 L70 100 H30 Z"></path></g><g><path class="bowl" d="M19 4 H81 L77 31 C74 49 64 59 50 59 C36 59 26 49 23 31 Z"></path><path class="highlight" d="M25 12 H31 L34 33 C36 42 40 48 45 52 C33 48 29 39 27 29 Z"></path></g><g><path fill="#555555" d="M19 8 H81 L80 14 H20 Z"></path><path class="rim" d="M17 4 H83 V10 H17 Z"></path></g><path class="mark" data-slot="content-1" d="M50 80 C51.4 85.5 52.6 86.7 58 88 C52.6 89.3 51.4 90.5 50 96 C48.6 90.5 47.4 89.3 42 88 C47.4 86.7 48.6 85.5 50 80 Z" data-role="内容槽"></path></g></svg></div></body></html>
````

## 点缀-像素斜指针

逻辑路径：assets/模板库/点缀/点缀-像素斜指针.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0220
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-像素斜指针</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#bcbcbc}.pointer{--size:290px;--fill:#f1f1f1;--outline:#383838;--stroke-width:.84;--corner-radius:0px;width:min(var(--size),74vw,74vh);aspect-ratio:1}.pointer svg{display:block;width:100%;height:100%;shape-rendering:crispEdges}.outline{fill:var(--outline);stroke:var(--outline);stroke-width:var(--stroke-width);stroke-linejoin:miter}.fill{fill:var(--fill)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="pointer" data-component-class="decoration" role="img" aria-label="点缀-像素斜指针"><svg viewbox="0 0 12 12" xmlns="http://www.w3.org/2000/svg"><defs><path id="cursor" d="M1 1 H2 V2 H3 V3 H4 V4 H5 V5 H7 V6 H9 V7 H11 V8 H7 V9 H8 V10 H9 V11 H7 V10 H6 V9 H5 V8 H4 V9 H3 V10 H2 V11 H1 Z"></path></defs><use href="#cursor" class="outline"></use><use href="#cursor" class="fill"></use></svg></div></body></html>
````

## 点缀-内收四角星芒

逻辑路径：assets/模板库/点缀/点缀-内收四角星芒.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-内收四角星芒</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-sparkle { display:inline-block; flex:none; width:var(--vl-star-size,24px); aspect-ratio:1; background:var(--vl-paint,var(--vl-accent,#edff79)); clip-path:polygon(50% 0,var(--vl-star-inset,42%) var(--vl-star-inset,42%),0 50%,var(--vl-star-inset,42%) calc(100% - var(--vl-star-inset,42%)),50% 100%,calc(100% - var(--vl-star-inset,42%)) calc(100% - var(--vl-star-inset,42%)),100% 50%,calc(100% - var(--vl-star-inset,42%)) var(--vl-star-inset,42%)); transform:rotate(var(--vl-rotate,0deg)); }
</style></head><body><span class="vl-sparkle" aria-hidden="true" style="--vl-star-size:20px;--vl-star-inset:45%;--vl-accent:#b7eeff"></span>
</body></html>
````

## 点缀-半透明圆点

逻辑路径：assets/模板库/点缀/点缀-半透明圆点.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0117
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-半透明圆点</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#eeeeee}.marker{--target-height:min(78vmin,800px);--diameter-ratio:.18;--disc-opacity:.52;--disc-fill:#777;--stroke-width:0;--radius:50%;width:calc(var(--target-height) * var(--diameter-ratio));aspect-ratio:1;border-radius:var(--radius);isolation:isolate}.marker svg{display:block;width:100%;height:100%}.marker circle{fill:var(--disc-fill);opacity:var(--disc-opacity);stroke:none;stroke-width:var(--stroke-width);mix-blend-mode:normal}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="marker" data-component-class="decoration" role="img" aria-label="点缀-半透明圆点"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 100" aria-hidden="true"><circle id="marker-disc" cx="50" cy="50" r="50"></circle></svg></div></body></html>
````

## 点缀-双列圆点

逻辑路径：assets/模板库/点缀/点缀-双列圆点.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0163
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-双列圆点</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#858585}.dot-grid{--group-height:min(78vh,520px);--dot-fill:#ececec;--dot-opacity:1;--stroke-width:0;--dot-radius:9.5px;height:var(--group-height);max-width:80vw;aspect-ratio:100/511.1}.dot-grid svg{display:block;width:100%;height:100%}.dot-grid circle{r:var(--dot-radius);fill:var(--dot-fill);opacity:var(--dot-opacity);stroke:none;stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="dot-grid" data-component-class="decoration" role="img" aria-label="点缀-双列圆点"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 511.1" preserveaspectratio="xMidYMid meet" aria-hidden="true"><g id="dot-grid"><circle cx="12" cy="9.5" r="9.5"></circle><circle cx="88" cy="9.5" r="9.5"></circle><circle cx="12" cy="79.8" r="9.5"></circle><circle cx="88" cy="79.8" r="9.5"></circle><circle cx="12" cy="150.1" r="9.5"></circle><circle cx="88" cy="150.1" r="9.5"></circle><circle cx="12" cy="220.4" r="9.5"></circle><circle cx="88" cy="220.4" r="9.5"></circle><circle cx="12" cy="290.7" r="9.5"></circle><circle cx="88" cy="290.7" r="9.5"></circle><circle cx="12" cy="361" r="9.5"></circle><circle cx="88" cy="361" r="9.5"></circle><circle cx="12" cy="431.3" r="9.5"></circle><circle cx="88" cy="431.3" r="9.5"></circle><circle cx="12" cy="501.6" r="9.5"></circle><circle cx="88" cy="501.6" r="9.5"></circle></g></svg></div></body></html>
````

## 点缀-双波浪线

逻辑路径：assets/模板库/点缀/点缀-双波浪线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0154
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-双波浪线</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#f4f4f4}.component{--size:420px;--line-color:#525252;--stroke-width:8;--line-cap:round;--opacity:1;width:min(var(--size),88vw,176vh);aspect-ratio:2;opacity:var(--opacity)}svg{display:block;width:100%;height:100%;overflow:visible}.wave{fill:none;stroke:var(--line-color);stroke-width:var(--stroke-width);stroke-linecap:var(--line-cap)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 50" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-双波浪线"><g data-role="内容层"><path id="wave-01" class="wave" d="M5 13 C20 32 30 -2 49 13 S75 26 95 13"></path><path id="wave-02" class="wave" transform="translate(0 22)" d="M5 13 C20 32 30 -2 49 13 S75 26 95 13"></path></g></svg></div></body></html>
````

## 点缀-双线六边徽章

逻辑路径：assets/模板库/点缀/点缀-双线六边徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0016
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-双线六边徽章</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f4f4f4}.component{--size:340px;--outline:#555;--icon-color:#666;--counter-fill:#555;--number-color:#fff;--stroke-width:1.35;--icon-stroke:2.2;--icon-radius:2px;--opacity:1;width:min(var(--size),86vw,86vh);aspect-ratio:1;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.hex{fill:none;stroke:var(--outline);stroke-width:var(--stroke-width);stroke-linejoin:miter}.icon{fill:none;stroke:var(--icon-color);stroke-width:var(--icon-stroke);stroke-linecap:round;stroke-linejoin:round}.paper{rx:var(--icon-radius)}.number{font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:400;fill:var(--number-color);text-anchor:middle;dominant-baseline:central}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 100" role="img" aria-label="点缀-双线六边徽章"><path id="hex-outer" class="hex" d="M47 2 L89 25 L89 71 L47 94 L5 71 L5 25 Z"></path><path id="hex-inner" class="hex" d="M47 7 L84 27.7 L84 68.3 L47 89 L10 68.3 L10 27.7 Z"></path><svg id="hex-icon" x="24" y="23" width="44" height="46" viewbox="0 0 44 46" data-role="内容层"><g class="icon"><rect class="paper" x="5" y="2" width="34" height="42"></rect><path d="M12 12 L14.5 14.5 L19 9 M24 12 H32 M12 24 L14.5 26.5 L19 21 M24 24 H32 M12 36 L14.5 38.5 L19 33 M24 36 H32"></path></g></svg><circle id="hex-counter" cx="86" cy="75" r="13" fill="var(--counter-fill)"></circle><text id="hex-number" class="number" x="86" y="75" data-role="内容层">1</text></svg></div></body></html>
````

## 点缀-双菱结线饰

逻辑路径：assets/模板库/点缀/点缀-双菱结线饰.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0056
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-双菱结线饰</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f2f1ef}.component{--size:360px;--stroke:3.5;--ink:#686868;--corner:round;width:min(var(--size),86vw,150vh);aspect-ratio:1.8}.component svg{display:block;width:100%;height:100%;fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:var(--corner);stroke-linejoin:var(--corner)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 180 100" role="img" aria-label="点缀-双菱结线饰"><path d="M57 10 Q63 4 69 10 L103 44 Q109 50 103 56 L69 90 Q63 96 57 90 L23 56 Q17 50 23 44 Z"></path><path d="M59 22 Q63 18 67 22 L91 46 Q95 50 91 54 L67 78 Q63 82 59 78 L35 54 Q31 50 35 46 Z"></path><path d="M111 10 Q117 4 123 10 L157 44 Q163 50 157 56 L123 90 Q117 96 111 90 L77 56 Q71 50 77 44 Z"></path><path d="M113 22 Q117 18 121 22 L145 46 Q149 50 145 54 L121 78 Q117 82 113 78 L89 54 Q85 50 89 46 Z"></path></svg></div></body></html>
````

## 点缀-双鸟衔心

逻辑路径：assets/模板库/点缀/点缀-双鸟衔心.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0040
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-双鸟衔心</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f0efed}.component{--size:430px;--stroke:1.8;--detail-stroke:1;--ink:#626262;--paper:#faf9f7;--heart:#b1b1b1;width:min(var(--size),88vw,151vh);aspect-ratio:1.8}.component svg{display:block;width:100%;height:100%;overflow:visible}.outline{stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}.detail{fill:none;stroke:var(--ink);stroke-width:var(--detail-stroke);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 200 111.111" role="img" aria-label="点缀-双鸟衔心"><defs><g id="bird"><path class="outline" fill="var(--paper)" d="M68 46 C60 37 42 22 9 21 C11 28 17 33 24 36 C14 32 7 31 2 32 C7 43 18 49 29 51 C17 48 10 47 6 49 C11 60 25 66 38 66 L20 78 L3 85 L18 87 L10 99 L28 93 L30 103 L47 83 C60 84 72 76 79 63 C82 58 87 57 88 49 C90 40 85 35 79 35 C74 35 70 39 68 46 Z"></path><path class="outline" fill="#bcbcbc" d="M88 42 L92 40 L89 49 Z"></path><path class="detail" d="M66 48 C50 44 40 37 27 29 M61 53 C46 52 33 43 22 40 M57 59 C43 60 32 55 22 53 M68 46 C70 58 62 68 49 72 C42 75 35 74 30 75 M43 80 L28 91 M31 82 L19 90 M55 82 L53 92 L48 96 M53 92 L58 95"></path><path class="detail" d="M77 56 Q80 59 83 56 M36 63 L39 64 M41 65 L44 66 M47 65 L49 65 M52 63 L54 62"></path><circle cx="81" cy="43" r="1.55" fill="var(--ink)"></circle><g fill="var(--ink)" opacity=".65"><circle cx="63" cy="70" r=".9"></circle><circle cx="59" cy="73" r=".8"></circle><circle cx="56" cy="68" r=".85"></circle><circle cx="53" cy="74" r=".65"></circle><circle cx="60" cy="64" r=".65"></circle></g></g></defs><g><use href="#bird"></use><use href="#bird" transform="translate(200 0) scale(-1 1)"></use><path class="detail" d="M92 41 Q94 29 100 30 Q106 29 108 41"></path></g><path class="outline" fill="var(--heart)" d="M100 35 C96 30 84 22 84 12 C84 3 94 1 100 9 C106 1 118 3 118 12 C118 21 105 31 100 35 Z"></path><path d="M89 13 Q89 7 95 9" stroke="#f5f5f5" stroke-width="1.4" fill="none" stroke-linecap="round"></path></svg></div></body></html>
````

## 点缀-发光满月

逻辑路径：assets/模板库/点缀/点缀-发光满月.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0222
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-发光满月</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#252525}.component{--size:510px;--halo-opacity:.3;--halo-scale:1;--texture-opacity:.28;--rim-width:.65;width:min(var(--size),94vw,94vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%}.halo{opacity:var(--halo-opacity);mix-blend-mode:screen;transform:scale(var(--halo-scale));transform-origin:200px 200px}.grain{opacity:var(--texture-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 400 400" role="img" aria-label="点缀-发光满月"><defs><radialgradient id="halo"><stop offset="0" stop-color="#fff" stop-opacity=".2"></stop><stop offset=".65" stop-color="#fff" stop-opacity=".3"></stop><stop offset="1" stop-color="#fff" stop-opacity="0"></stop></radialgradient><radialgradient id="surface" cx="40%" cy="36%" r="68%"><stop stop-color="#eee"></stop><stop offset=".56" stop-color="#d3d3d3"></stop><stop offset=".88" stop-color="#b2b2b2"></stop><stop offset="1" stop-color="#7f7f7f"></stop></radialgradient><radialgradient id="basin"><stop stop-color="#777" stop-opacity=".66"></stop><stop offset=".72" stop-color="#858585" stop-opacity=".4"></stop><stop offset="1" stop-color="#999" stop-opacity="0"></stop></radialgradient><radialgradient id="crater"><stop offset="0" stop-color="#acacac"></stop><stop offset=".55" stop-color="#b8b8b8"></stop><stop offset=".75" stop-color="#8c8c8c"></stop><stop offset=".87" stop-color="#e8e8e8"></stop><stop offset="1" stop-color="#d4d4d4" stop-opacity="0"></stop></radialgradient><clippath id="disc"><circle cx="200" cy="200" r="140"></circle></clippath><filter id="rough" x="-15%" y="-15%" width="130%" height="130%"><feturbulence type="fractalNoise" basefrequency=".035" numoctaves="4" seed="17" result="noise"></feturbulence><fedisplacementmap in="SourceGraphic" in2="noise" scale="15" xchannelselector="R" ychannelselector="G"></fedisplacementmap><fegaussianblur stddeviation="1.2"></fegaussianblur></filter><filter id="grain" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency=".3" numoctaves="4" seed="29"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix><feblend in2="SourceGraphic" mode="multiply"></feblend></filter><filter id="terrain" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency=".065" numoctaves="5" seed="9"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix><feblend in2="SourceGraphic" mode="soft-light"></feblend></filter></defs><circle class="halo" cx="200" cy="200" r="189" fill="url(#halo)"></circle><g clip-path="url(#disc)"><circle cx="200" cy="200" r="140" fill="url(#surface)"></circle><g filter="url(#rough)"><path fill="#858585" opacity=".45" d="M93 115 Q119 98 136 115 Q153 98 180 120 L190 144 Q178 161 161 155 Q167 174 145 186 Q154 210 139 221 Q115 224 111 196 Q91 183 90 163 Q74 141 93 115 Z"></path><path fill="#858585" opacity=".46" d="M197 110 Q218 95 243 113 Q255 125 249 146 Q272 141 284 158 Q300 186 272 202 Q249 215 232 198 Q205 202 197 178 Q176 166 189 148 Q179 125 197 110 Z"></path><path fill="#8b8b8b" opacity=".37" d="M218 210 Q234 194 249 210 Q273 205 283 226 Q283 248 261 252 Q243 268 225 249 Q204 249 206 227 Z"></path><ellipse cx="172" cy="222" rx="30" ry="21" fill="url(#basin)"></ellipse><ellipse cx="103" cy="241" rx="26" ry="34" fill="url(#basin)"></ellipse><ellipse cx="256" cy="99" rx="30" ry="15" fill="url(#basin)"></ellipse></g><circle cx="200" cy="200" r="140" fill="#cecece" filter="url(#terrain)" opacity=".26"></circle><g fill="url(#crater)"><circle cx="158" cy="193" r="17"></circle><circle cx="189" cy="271" r="21"></circle><circle cx="142" cy="257" r="11"></circle><circle cx="274" cy="274" r="18"></circle><circle cx="222" cy="305" r="12"></circle><circle cx="201" cy="92" r="9"></circle><circle cx="292" cy="133" r="8"></circle><circle cx="303" cy="225" r="10"></circle><circle cx="128" cy="288" r="8"></circle><circle cx="165" cy="304" r="12"></circle><circle cx="111" cy="209" r="7"></circle><circle cx="229" cy="166" r="7"></circle><circle cx="254" cy="237" r="5"></circle><circle cx="175" cy="113" r="6"></circle><circle cx="282" cy="189" r="6"></circle><circle cx="233" cy="279" r="6"></circle><circle cx="209" cy="235" r="8"></circle></g><g stroke="#f0f0f0" fill="none" opacity=".28" stroke-linecap="round"><path d="M189 271 L152 222 M189 271 L192 221 M189 271 L221 240 M189 271 L250 261 M189 271 L226 295 M189 271 L199 332 M189 271 L151 319 M189 271 L128 279" stroke-width="1.2"></path><path d="M158 193 L135 174 M158 193 L173 166 M158 193 L180 204 M158 193 L151 222" stroke-width=".8"></path></g><circle class="grain" cx="200" cy="200" r="140" fill="#d8d8d8" filter="url(#grain)"></circle><circle cx="200" cy="200" r="139.65" fill="none" stroke="#f2f2f2" stroke-opacity=".35" style="stroke-width:var(--rim-width)"></circle></g></svg></div></body></html>
````

## 点缀-叠层下箭头

逻辑路径：assets/模板库/点缀/点缀-叠层下箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0218
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-叠层下箭头</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#efefed}.component{--size:210px;--stroke:11;--ink:#666;--effect-opacity:1;width:min(var(--size),76vw,76vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%;fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:butt;stroke-linejoin:miter;opacity:var(--effect-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-叠层下箭头"><path d="M10 5 L50 40 L90 5"></path><path d="M10 29 L50 64 L90 29"></path><path d="M10 53 L50 88 L90 53"></path></svg></div></body></html>
````

## 点缀-叠放半圆

逻辑路径：assets/模板库/点缀/点缀-叠放半圆.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0159
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-叠放半圆</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f0efed}.component{--size:240px;--fill-light:#c7c7c7;--fill-dark:#858585;--stroke-width:0;--stroke:#777;--effect-opacity:1;width:min(var(--size),80vw,76vh);aspect-ratio:.9091}.component svg{display:block;width:100%;height:100%;opacity:var(--effect-opacity)}.bowl{fill:url("#fill");stroke:var(--stroke);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 200 220" role="img" aria-label="点缀-叠放半圆"><defs><linearGradient id="fill" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="var(--fill-light)"></stop><stop offset="100%" stop-color="var(--fill-dark)"></stop></linearGradient></defs><path class="bowl" d="M0 0 H200 A100 100 0 0 1 0 0 Z"></path><path class="bowl" d="M0 120 H200 A100 100 0 0 1 0 120 Z"></path></svg></div></body></html>
````

## 点缀-古典热气球

逻辑路径：assets/模板库/点缀/点缀-古典热气球.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0204
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-古典热气球</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#eeedea}.component{--size:340px;--stroke:1.4;--detail-stroke:.7;--ink:#555;--paper:#deddd9;--stripe-dark:#898989;--stripe-light:#e5e4e1;--engraving-opacity:.5;width:min(var(--size),84vw,59vh);aspect-ratio:300/450}.component[data-variant="engraving"]{--stripe-dark:#bbb;--stripe-light:#e5e4e1;--engraving-opacity:.8}.component svg{display:block;width:100%;height:100%}.line{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linejoin:round;stroke-linecap:round}.fine{fill:none;stroke:var(--ink);stroke-width:var(--detail-stroke);stroke-linecap:round}.engraving{opacity:var(--engraving-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" data-variant="striped"><svg viewbox="0 0 300 450" role="img" aria-label="点缀-古典热气球"><defs><path id="envelope" d="M150 12 C82 12 32 48 29 116 C25 183 66 234 103 280 Q119 300 128 320 L172 320 Q181 300 197 280 C234 234 275 183 271 116 C268 48 218 12 150 12 Z"></path><clippath id="balloon-clip"><use href="#envelope"></use></clippath><lineargradient id="volume" x1="0" y1="0" x2="1" y2=".15"><stop stop-color="#333" stop-opacity=".27"></stop><stop offset=".32" stop-color="#fff" stop-opacity=".24"></stop><stop offset=".55" stop-color="#fff" stop-opacity="0"></stop><stop offset="1" stop-color="#222" stop-opacity=".3"></stop></lineargradient><lineargradient id="basket" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#777"></stop><stop offset=".4" stop-color="#c4c2bd"></stop><stop offset="1" stop-color="#868686"></stop></lineargradient><pattern id="hatch" width="6" height="6" patternunits="userSpaceOnUse"><path d="M-1 6 L6 -1 M5 7 L7 5" stroke="#444" stroke-width=".45" fill="none"></path></pattern><pattern id="weave" width="8" height="6" patternunits="userSpaceOnUse"><path d="M0 1 H8 M0 4 H8 M2 1 V4 M6 4 V7 M6 -2 V1" stroke="#515151" stroke-width=".65" fill="none"></path><path d="M0 2 H8" stroke="#e4e2df" stroke-opacity=".4" stroke-width=".6"></path></pattern></defs><g class="line"><path d="M107 280 L126 387 M193 280 L174 387 M127 319 L135 387 M173 319 L165 387"></path><path d="M115 302 Q120 346 132 372 M185 302 Q180 346 168 372" stroke-width=".8"></path></g><use href="#envelope" fill="var(--paper)"></use><g clip-path="url(#balloon-clip)"><path d="M150 12 C96 25 66 66 65 126 C63 202 99 258 136 320 L128 320 C109 279 53 232 34 174 C13 108 46 23 150 12 Z" fill="var(--stripe-dark)"></path><path d="M150 12 C122 37 106 77 106 129 C106 206 125 268 143 320 L136 320 C99 258 63 202 65 126 C66 66 96 25 150 12 Z" fill="var(--stripe-light)"></path><path d="M150 12 C139 44 133 84 133 131 C133 208 140 274 147 320 L143 320 C125 268 106 206 106 129 C106 77 122 37 150 12 Z" fill="var(--stripe-dark)"></path><path d="M150 12 C161 44 167 84 167 131 C167 208 160 274 153 320 L147 320 C140 274 133 208 133 131 C133 84 139 44 150 12 Z" fill="var(--stripe-light)"></path><path d="M150 12 C178 37 194 77 194 129 C194 206 175 268 157 320 L153 320 C160 274 167 208 167 131 C167 84 161 44 150 12 Z" fill="var(--stripe-dark)"></path><path d="M150 12 C204 25 234 66 235 126 C237 202 201 258 164 320 L157 320 C175 268 194 206 194 129 C194 77 178 37 150 12 Z" fill="var(--stripe-light)"></path><path d="M150 12 C254 23 287 108 266 174 C247 232 191 279 172 320 L164 320 C201 258 237 202 235 126 C234 66 204 25 150 12 Z" fill="var(--stripe-dark)"></path><use href="#envelope" fill="url(#volume)"></use><g class="fine"><path d="M150 12 C96 25 66 66 65 126 C63 202 99 258 136 320 M150 12 C122 37 106 77 106 129 C106 206 125 268 143 320 M150 12 C139 44 133 84 133 131 C133 208 140 274 147 320 M150 12 C161 44 167 84 167 131 C167 208 160 274 153 320 M150 12 C178 37 194 77 194 129 C194 206 175 268 157 320 M150 12 C204 25 234 66 235 126 C237 202 201 258 164 320"></path><path d="M40 80 Q150 43 260 80 M32 100 Q150 65 268 100" opacity=".6"></path></g><path d="M29 153 Q150 177 271 153 L268 170 Q150 195 32 170 Z" fill="#bcbab5" stroke="var(--ink)" stroke-width="1"></path><path class="fine" d="M30 158 Q150 182 270 158 M32 166 Q150 190 268 166"></path><g class="line" stroke-width="1"><path d="M36 171 Q48 203 70 178 Q86 220 111 183 Q132 228 150 185 Q169 228 189 183 Q215 220 230 178 Q252 203 264 171"></path><path d="M36 176 Q48 210 70 184 Q86 227 111 189 Q132 235 150 191 Q169 235 189 189 Q215 227 230 184 Q252 210 264 176" stroke-width=".65"></path></g><g fill="#666" stroke="#e1dfdb" stroke-width=".6"><path d="M70 173 l4 6 -4 8 -4 -8 Z M111 178 l4 6 -4 8 -4 -8 Z M150 180 l4 6 -4 8 -4 -8 Z M189 178 l4 6 -4 8 -4 -8 Z M230 173 l4 6 -4 8 -4 -8 Z"></path></g><path class="engraving" fill="url(#hatch)" d="M30 45 H64 V231 H30 Z M234 40 H277 V245 H234 Z M100 265 Q150 285 200 265 L175 325 H125 Z"></path><g class="fine engraving"><path d="M47 109 Q42 130 47 150 M51 102 Q46 130 51 151 M55 99 Q51 131 55 151 M249 102 Q255 128 250 151 M244 98 Q250 126 246 152 M77 218 L104 258 M84 223 L113 266 M213 225 L190 260 M219 221 L194 263 M139 40 L136 68 M160 40 L164 69"></path></g><path d="M120 305 Q150 313 180 305 L172 321 Q150 326 128 321 Z" fill="#727272"></path><path class="fine" stroke="#ccc" d="M125 311 Q150 317 175 311 M128 316 Q150 322 172 316"></path></g><use href="#envelope" class="line"></use><ellipse cx="150" cy="13" rx="10" ry="2.5" fill="#888" stroke="var(--ink)" stroke-width=".8"></ellipse><g class="line"><path d="M128 323 L135 354 Q150 361 165 354 L172 323"></path><path d="M134 351 Q150 356 166 351"></path></g><g fill="#777" stroke="var(--ink)" stroke-width="1"><path d="M141 348 L141 357 L159 357 L159 348"></path><path d="M144 357 L145 365 H155 L156 357 Z"></path></g><path d="M121 387 Q150 382 179 387 L174 422 Q150 432 126 422 Z" fill="url(#basket)" stroke="var(--ink)" stroke-width="1.5"></path><path d="M123 392 Q150 397 177 392 L173 422 Q150 429 127 421 Z" fill="url(#weave)"></path><path d="M120 386 Q150 391 180 386 L180 393 Q150 399 120 393 Z" fill="#a5a39f" stroke="var(--ink)" stroke-width="1.2"></path><path class="fine" d="M122 389 Q150 394 178 389 M127 420 Q150 428 173 420 M131 398 L134 423 M169 398 L166 423"></path><g fill="#b9b7b2" stroke="var(--ink)" stroke-width=".9"><path d="M127 401 C122 402 120 410 123 415 Q126 419 130 415 C133 412 131 404 129 401 L129 397 L126 397 Z"></path><path d="M174 401 C170 403 168 412 172 416 Q176 419 179 414 C181 410 178 403 176 401 L177 397 L173 397 Z"></path></g><path class="fine" d="M126 405 L125 412 M175 405 L174 413"></path></svg></div></body></html>
````

## 点缀-四瓣珠光徽章

逻辑路径：assets/模板库/点缀/点缀-四瓣珠光徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0008
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-四瓣珠光徽章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.badge{--size:min(360px,82vmin);--outer-stroke:1.2;--inner-stroke:.8;--highlight-alpha:.65;--glint-alpha:.7;--shadow-alpha:.14;width:var(--size);aspect-ratio:1;filter:drop-shadow(0 6px 8px rgb(0 0 0 / var(--shadow-alpha)))}svg{display:block;width:100%;height:100%;overflow:visible}.outer{stroke-width:var(--outer-stroke)}.inner{stroke-width:var(--inner-stroke)}.label{font-family:'Songti SC','SimSun',serif;font-weight:400;fill:#414141}.note{font-family:'PingFang SC','Microsoft YaHei',sans-serif;font-weight:400;fill:#585858}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-四瓣珠光徽章"><defs><path id="body" d="M50 3 C64 3 67 21 82 28 C101 38 103 56 88 68 C72 77 68 98 50 98 C32 98 28 78 12 69 C-3 57 -1 39 17 29 C33 20 36 3 50 3 Z"></path><clippath id="clip"><use href="#body"></use></clippath><lineargradient id="pearl" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fafafa"></stop><stop offset=".28" stop-color="#e6e6e6"></stop><stop offset=".49" stop-color="#fcfcfc"></stop><stop offset=".7" stop-color="#c8c8c8"></stop><stop offset=".85" stop-color="#e5e5e5"></stop><stop offset="1" stop-color="#aaa"></stop></lineargradient><radialgradient id="shine"><stop stop-color="#fff"></stop><stop offset="1" stop-color="#fff" stop-opacity="0"></stop></radialgradient><lineargradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#aaa"></stop><stop offset=".35" stop-color="#fff"></stop><stop offset=".65" stop-color="#8f8f8f"></stop><stop offset="1" stop-color="#eee"></stop></lineargradient><lineargradient id="glint" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#fff" stop-opacity="0"></stop><stop offset=".38" stop-color="#fff"></stop><stop offset=".7" stop-color="#fff"></stop><stop offset="1" stop-color="#fff" stop-opacity="0"></stop></lineargradient><lineargradient id="band" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#777" stop-opacity="0"></stop><stop offset=".6" stop-color="#777" stop-opacity=".16"></stop><stop offset="1" stop-color="#fff" stop-opacity=".12"></stop></lineargradient></defs><g><use href="#body" fill="url(#pearl)"></use><g clip-path="url(#clip)"><ellipse cx="31" cy="25" rx="46" ry="27" transform="rotate(-35 31 25)" fill="url(#shine)" opacity="var(--highlight-alpha)"></ellipse><path d="M-5 55 Q40 103 99 56 L108 100 L0 107Z" fill="url(#band)"></path></g></g><g fill="none"><use href="#body" stroke="#fff" stroke-opacity=".42" stroke-width="3.5" clip-path="url(#clip)"></use><use href="#body" class="outer" stroke="url(#rim)"></use><use href="#body" class="inner" transform="translate(4 4) scale(.92)" stroke="#fafafa" stroke-opacity=".9"></use></g><path d="M7 52 C5 42 12 35 20 31 C35 23 38 7 50 7 C56 7 60 11 64 17" fill="none" stroke="url(#glint)" stroke-width="1.7" stroke-linecap="round" opacity="var(--glint-alpha)"></path><g text-anchor="middle" dominant-baseline="central"><text class="label" x="50" y="29" font-size="13" data-slot="copy-1" data-role="说明槽">说明文字</text><text class="label" x="50" y="53" font-size="17" data-slot="title-1" data-role="标题槽">标题文字</text><text class="note" x="50" y="76" font-size="9.5" data-slot="note-1" data-role="说明槽">说明文字</text></g></svg></div></body></html>
````

## 点缀-四芒闪星

逻辑路径：assets/模板库/点缀/点缀-四芒闪星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0168
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-四芒闪星</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.sparkle{--size:min(280px,74vmin);--fill:#555;--stroke-width:0;width:var(--size);aspect-ratio:1}svg{display:block;width:100%;height:100%}path{fill:var(--fill);stroke:var(--fill);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="sparkle" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-四芒闪星"><path data-role="内容层" d="M50 0 C50 34 66 50 100 50 C66 50 50 66 50 100 C50 66 34 50 0 50 C34 50 50 34 50 0 Z"></path></svg></div></body></html>
````

## 点缀-四角星芒

逻辑路径：assets/模板库/点缀/点缀-四角星芒.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0170
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-四角星芒</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.spark{--height:min(290px,76vmin);--fill:#686868;--stroke-width:0;height:var(--height);aspect-ratio:.85}svg{display:block;width:100%;height:100%}path{fill:var(--fill);stroke:var(--fill);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="spark" data-component-class="decoration"><svg viewbox="0 0 1 1" preserveaspectratio="none" role="img" aria-label="点缀-四角星芒"><path d="M .5 0 Q .59 .41 1 .5 Q .59 .59 .5 1 Q .41 .59 0 .5 Q .41 .41 .5 0 Z"></path></svg></div></body></html>
````

## 点缀-四角闪星

逻辑路径：assets/模板库/点缀/点缀-四角闪星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0155
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-四角闪星</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.flash{--size:min(270px,74vmin);--fill:#424242;--stroke-width:0;width:var(--size);aspect-ratio:1}svg{display:block;width:100%;height:100%}path{fill:var(--fill);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="flash" data-component-class="decoration"><svg viewbox="0 0 100 100" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-四角闪星"><path data-role="内容层" d="M50 0 Q58 42 100 50 Q58 58 50 100 Q42 58 0 50 Q42 42 50 0 Z"></path></svg></div></body></html>
````

## 点缀-回环曲线

逻辑路径：assets/模板库/点缀/点缀-回环曲线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0150
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-回环曲线</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.loop{--size:min(360px,76vmin);--line-color:#656565;--stroke-width:1.2;--linecap:round;width:var(--size);aspect-ratio:1}svg{display:block;width:100%;height:100%;overflow:visible}path{fill:none;stroke:var(--line-color);stroke-width:var(--stroke-width);stroke-linecap:var(--linecap);stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="loop" data-component-class="decoration"><svg viewbox="0 0 100 100" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-回环曲线"><path data-role="内容层" d="M0 0 C0 30 38 60 52 42 C65 23 27 23 43 57 C54 81 78 89 100 100"></path></svg></div></body></html>
````

## 点缀-回环箭头

逻辑路径：assets/模板库/点缀/点缀-回环箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0093
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-回环箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#ededed}.arrow{--width:min(230px,38vw,38vh);--stroke-width:5.5;--stroke-variation:.25;--ink:#575757;--grain-opacity:.15;--linecap:round;width:var(--width);aspect-ratio:100/220}svg{display:block;width:100%;height:100%;overflow:visible}.ink{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:var(--linecap);stroke-linejoin:round}.variation{stroke-width:calc(var(--stroke-width) * var(--stroke-variation));opacity:.7}.grain{fill:none;stroke:#ededed;stroke-width:.7;stroke-linecap:round;opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="arrow" data-component-class="decoration"><svg viewbox="0 0 100 220" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-回环箭头"><g><path class="ink" d="M28 5 C-3 55 2 115 38 121 C65 119 65 74 47 93 C24 124 59 178 87 205"></path><path class="ink variation" d="M11 48 C5 69 5 89 15 106" transform="translate(-2 0)"></path><path class="ink variation" d="M44 144 Q59 181 87 205" transform="translate(1.6 0)"></path></g><g><path class="ink" d="M48 186 Q72 204 89 205 M89 205 L82 177"></path><path class="ink variation" d="M58 194 Q75 204 88 205" transform="translate(0 1.8)"></path></g><g class="grain"><path d="M19 22 l-1 3 M9 59 l-.4 4 M10 88 l1 3 M26 117 l3 1 M49 115 l2-2 M54 97 l-1-2 M43 105 l-1 3 M47 147 l1 3 M63 178 l2 3 M78 195 l2 2 M60 193 l3 1.5 M85 190 l.4 3"></path><path d="M8 74 l1.5 .3 M39 120 l2-.8 M49 94 l1.5 1 M53 160 l1.2-.5 M84 202 l2 .6" stroke-width="1.1"></path></g></svg></div></body></html>
````

## 点缀-圆头曲线

逻辑路径：assets/模板库/点缀/点缀-圆头曲线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0151
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆头曲线</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#ededed}.curve{--size:min(72vw,160vh,640px);--stroke-width:9;--stroke:#626262;--opacity:1;width:var(--size);aspect-ratio:100/30}.curve svg{display:block;width:100%;height:100%;overflow:visible}.curve path{fill:none;stroke:var(--stroke);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round;opacity:var(--opacity)}.curve[data-variant=wave] .arc,.curve[data-variant=arc] .wave{display:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="curve" data-component-class="decoration" data-variant="wave"><svg viewbox="0 0 100 30" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-圆头曲线"><path class="wave" data-role="内容层" d="M-5 25 C18 4 40 1 60 13 S87 26 97 12"></path><path class="arc" data-role="内容层" d="M7 24 Q50 -1 93 22"></path></svg></div></body></html>
````

## 点缀-圆底联络符号

逻辑路径：assets/模板库/点缀/点缀-圆底联络符号.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0153
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆底联络符号</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#ededed}.contact{--size:min(60vw,60vh,240px);--disc:#5e5e5e;--symbol:#fafafa;--stroke-width:4.5;--corner-radius:4;width:var(--size);aspect-ratio:1}.contact svg{display:block;width:100%;height:100%}.disc{fill:var(--disc)}.symbol{display:none;fill:none;stroke:var(--symbol);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}.envelope rect{rx:var(--corner-radius)}[data-variant=envelope] .envelope,[data-variant=phone] .phone,[data-variant=pin] .pin{display:block}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="contact" data-component-class="decoration" data-variant="envelope"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆底联络符号"><circle class="disc" cx="50" cy="50" r="50"></circle><g class="symbol envelope" data-role="内容层"><rect x="25.25" y="25.25" width="49.5" height="49.5" rx="4"></rect><path d="M26 30 L50 51 L74 30 M26 70 L41 56 M74 70 L59 56"></path></g><g class="symbol phone" data-role="内容层"><path d="M29 25.5 Q25.25 25.5 25.25 31 Q24.5 49 39 63 Q52 75 68 74.75 Q73 74.75 74.75 70 L74.75 61 L61 54 L55 62 Q44 58 38 46 L45 39 L38 25.25 Z"></path></g><g class="symbol pin" data-role="内容层"><path d="M50 74.75 C44 66 30 53 30 43.5 A20 18.25 0 0 1 70 43.5 C70 53 56 66 50 74.75 Z"></path><circle cx="50" cy="43" r="7"></circle></g></svg></div></body></html>
````

## 点缀-圆形播放键

逻辑路径：assets/模板库/点缀/点缀-圆形播放键.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0219
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆形播放键</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#c8c8c8}.play{--size:min(60vw,60vh,260px);--disc-fill:#fafafa;--disc-stroke:#686868;--disc-opacity:.76;--stroke-width:1.4;--triangle-fill:#545454;width:var(--size);aspect-ratio:1}.play svg{display:block;width:100%;height:100%}.disc{fill:var(--disc-fill);stroke:var(--disc-stroke);stroke-width:var(--stroke-width);opacity:var(--disc-opacity);r:calc(50px - var(--stroke-width)*.5px)}.triangle{fill:var(--triangle-fill)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="play" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆形播放键"><circle class="disc" cx="50" cy="50" r="49.3"></circle><path class="triangle" d="M36 25 L36 75 L73 50 Z"></path></svg></div></body></html>
````

## 点缀-圆点阵列

逻辑路径：assets/模板库/点缀/点缀-圆点阵列.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0157
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆点阵列</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#ededed}.dots{--size:min(70vw,80vh,420px);--dot-fill:#666;--dot-radius:6.5px;--opacity:1;width:var(--size);aspect-ratio:113/88}.dots svg{display:block;width:100%;height:100%;overflow:visible}.dots circle{fill:var(--dot-fill);r:var(--dot-radius);opacity:var(--opacity)}.dots .narrow{display:none}.dots[data-variant='4x2']{width:calc(var(--size)*38/113);aspect-ratio:38/88}.dots[data-variant='4x2'] .wide{display:none}.dots[data-variant='4x2'] .narrow{display:block}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="dots" data-component-class="decoration" data-variant="4x5"><svg class="wide" viewbox="0 0 113 88" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-圆点阵列"><g data-role="内容层"><circle cx="6.5" cy="6.5" r="6.5"></circle><circle cx="31.5" cy="6.5" r="6.5"></circle><circle cx="56.5" cy="6.5" r="6.5"></circle><circle cx="81.5" cy="6.5" r="6.5"></circle><circle cx="106.5" cy="6.5" r="6.5"></circle><circle cx="6.5" cy="31.5" r="6.5"></circle><circle cx="31.5" cy="31.5" r="6.5"></circle><circle cx="56.5" cy="31.5" r="6.5"></circle><circle cx="81.5" cy="31.5" r="6.5"></circle><circle cx="106.5" cy="31.5" r="6.5"></circle><circle cx="6.5" cy="56.5" r="6.5"></circle><circle cx="31.5" cy="56.5" r="6.5"></circle><circle cx="56.5" cy="56.5" r="6.5"></circle><circle cx="81.5" cy="56.5" r="6.5"></circle><circle cx="106.5" cy="56.5" r="6.5"></circle><circle cx="6.5" cy="81.5" r="6.5"></circle><circle cx="31.5" cy="81.5" r="6.5"></circle><circle cx="56.5" cy="81.5" r="6.5"></circle><circle cx="81.5" cy="81.5" r="6.5"></circle><circle cx="106.5" cy="81.5" r="6.5"></circle></g></svg><svg class="narrow" viewbox="0 0 38 88" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-圆点阵列"><g data-role="内容层"><circle cx="6.5" cy="6.5" r="6.5"></circle><circle cx="31.5" cy="6.5" r="6.5"></circle><circle cx="6.5" cy="31.5" r="6.5"></circle><circle cx="31.5" cy="31.5" r="6.5"></circle><circle cx="6.5" cy="56.5" r="6.5"></circle><circle cx="31.5" cy="56.5" r="6.5"></circle><circle cx="6.5" cy="81.5" r="6.5"></circle><circle cx="31.5" cy="81.5" r="6.5"></circle></g></svg></div></body></html>
````

## 点缀-圆片表情

逻辑路径：assets/模板库/点缀/点缀-圆片表情.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0082
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆片表情</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#ededed}.face{--size:min(62vw,62vh,320px);--disc-fill:#8b8b8b;--eye-white:#f9f9f9;--ink:#292929;--stroke-width:1.7;--accessory-radius:3;--shadow-x:.2px;--shadow-y:1.3px;--shadow-blur:.8px;--shadow-opacity:.28;width:var(--size);aspect-ratio:1}.face svg{display:block;width:100%;height:100%;overflow:visible}.shadow{fill:#000;opacity:var(--shadow-opacity);transform:translate(var(--shadow-x),var(--shadow-y));filter:blur(var(--shadow-blur));mix-blend-mode:multiply}.disc{fill:var(--disc-fill)}.eyes{fill:var(--eye-white)}.pupils{fill:var(--ink)}.mouth,.accessory{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}.accessory rect{rx:var(--accessory-radius)}[data-accessory=none] .accessory{display:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="face" data-component-class="decoration" data-expression="side-glance" data-accessory="none"><svg viewbox="0 0 100 100" preserveaspectratio="xMidYMid meet" role="img" aria-label="点缀-圆片表情"><circle class="shadow" cx="50" cy="50" r="50"></circle><circle class="disc" data-role="内容层" cx="50" cy="50" r="50"></circle><g class="eyes" data-role="内容层"><ellipse cx="38" cy="42" rx="7.5" ry="9"></ellipse><ellipse cx="58" cy="40" rx="7.5" ry="9"></ellipse></g><g class="pupils"><ellipse cx="40.8" cy="42.7" rx="3.25" ry="4.75"></ellipse><ellipse cx="60.8" cy="40.7" rx="3.25" ry="4.75"></ellipse></g><path class="mouth" d="M39 59 C42 72.5 58 72.5 62 59"></path><g class="accessory" data-role="内容层"><rect x="28" y="30" width="19" height="24" rx="3"></rect><rect x="49" y="28" width="19" height="24" rx="3"></rect><path d="M47 38 L49 37 M28 36 L22 33 M68 34 L75 30"></path></g></svg></div></body></html>
````

## 点缀-圆环书法徽记

逻辑路径：assets/模板库/点缀/点缀-圆环书法徽记.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0177
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆环书法徽记</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#f4f4f4}.badge{--size:340px;--ring-stroke:3;--ring-tone:#858585;--ink:#626262;--opacity:1;width:min(var(--size),86vw,86vh);aspect-ratio:1.0842;opacity:var(--opacity)}svg{display:block;width:100%;height:100%;overflow:visible}.ring{fill:none;stroke:var(--ring-tone);stroke-width:var(--ring-stroke)}.glyph{fill:var(--ink)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg viewbox="0 0 108.42 100" role="img" aria-label="点缀-圆环书法徽记"><circle class="ring" cx="58.5468" cy="50" r="48"></circle><g class="glyph" data-slot="title-1" aria-label="通用内容槽" data-role="标题槽"><title>点缀-圆环书法徽记</title><path d="M3 24 C22 21 42 17 65 15 L87 11 L94 14 L88 19 C62 22 29 28 9 30 L0 28 Z"></path><path d="M30 3 L39 0 L42 4 C39 15 35 28 30 39 L25 43 L25 35 L29 14 Z"></path><path d="M65 3 L74 1 L79 5 C75 17 69 29 61 38 L55 40 C60 30 63 19 65 10 Z"></path><path d="M21 47 C35 44 55 39 70 38 C76 37 82 39 83 43 C76 51 67 56 58 63 C43 73 31 84 35 88 C40 93 66 89 76 84 C81 81 85 75 88 67 L90 69 C90 80 86 88 80 92 C65 98 38 99 28 92 C18 86 26 77 34 70 L63 47 C47 50 33 54 25 55 L17 52 Z"></path></g></svg></div></body></html>
````

## 点缀-圆瓣交叉

逻辑路径：assets/模板库/点缀/点缀-圆瓣交叉.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0160
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆瓣交叉</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f4f4f4}.cross{--size:280px;--petal-fill:#777;--petal-opacity:1;--petal-length:50px;--petal-radius:13.5px;width:min(var(--size),86vw,86vh);aspect-ratio:1}svg{display:block;width:100%;height:100%}ellipse{fill:var(--petal-fill);opacity:var(--petal-opacity);rx:var(--petal-length);ry:var(--petal-radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="cross" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆瓣交叉"><g data-slot="content-1" data-role="内容槽"><ellipse cx="50" cy="50" rx="50" ry="13.5" transform="rotate(45 50 50)"></ellipse><ellipse cx="50" cy="50" rx="50" ry="13.5" transform="rotate(-45 50 50)"></ellipse></g></svg></div></body></html>
````

## 点缀-圆角手绘星

逻辑路径：assets/模板库/点缀/点缀-圆角手绘星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0133
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆角手绘星</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f4f4f4}.star{--size:265px;--fill:#a0a0a0;--outline:#414141;--stroke:7;--rotation:-12deg;--join:round;--opacity:1;width:min(var(--size),78vw,78vh);aspect-ratio:1;opacity:var(--opacity)}svg{display:block;width:100%;height:100%;overflow:visible;transform:rotate(var(--rotation));transform-origin:50% 50%}path{fill:var(--fill);stroke:var(--outline);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:var(--join)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="star" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆角手绘星"><path d="M45.5 13 C48.5 6 51.8 5.2 54.1 12.4 L60.1 29.8 Q61.1 33.4 65.4 33.9 L85.9 36.2 Q95 37.1 88.2 43.5 L73.8 57 Q71.2 59.1 72.3 63 L77.1 84.2 Q79.1 92.3 71.7 87.9 L53.9 76.8 Q51.4 75.1 48.2 76.8 L27.6 87.4 Q20.5 91.6 22.5 83.5 L27.6 63 Q28.7 59.3 25.6 56.8 L11.3 45.3 Q4.3 39.7 13.5 38.1 L33.2 34.3 Q36.6 33.7 38 30.2 Z"></path></svg></div></body></html>
````

## 点缀-圆角星形

逻辑路径：assets/模板库/点缀/点缀-圆角星形.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0148
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆角星形</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f4f4f4}.star{--size:245px;--accent:#bcbcbc;--contour:#303030;--stroke:9;--join:round;--opacity:1;width:min(var(--size),84vw,84vh);aspect-ratio:1;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.shape{fill:var(--accent);stroke:var(--contour);stroke-width:var(--stroke);stroke-linejoin:var(--join);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="star" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆角星形"><path class="shape" data-fill-role="强调色" data-stroke-role="轮廓色" d="M47.8 11.3 Q50 7 52.2 11.3 L62.55 31 Q63.45 32.49 65.6 32.9 L87.4 35.85 Q91.85 36.9 88.55 40.1 L73.75 55.7 Q71.76 58.07 72.18 60.7 L75.2 81.4 Q75.86 86.1 71.6 84 L52.5 74.57 Q50 73.38 47.5 74.57 L28.4 84 Q24.14 86.1 24.8 81.4 L27.82 60.7 Q28.24 58.07 26.25 55.7 L11.45 40.1 Q8.15 36.9 12.6 35.85 L34.4 32.9 Q36.55 32.49 37.45 31 Z"></path></svg></div></body></html>
````

## 点缀-圆角星星

逻辑路径：assets/模板库/点缀/点缀-圆角星星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0130
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-圆角星星</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f4f4f4}.star{--size:270px;--fill:#e0e0e0;--outline:#383838;--stroke:10;--join:round;--opacity:1;width:min(var(--size),84vw,84vh);aspect-ratio:1;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.fill{fill:var(--fill)}.outline{fill:none;stroke:var(--outline);stroke-width:var(--stroke);stroke-linejoin:var(--join);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="star" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-圆角星星"><defs><path id="star-contour" d="M48.4 12.6 Q52 7 54.4 13 L61.6 30.5 Q62.7 33.9 66.5 34.5 L85 37.8 Q91 39 86.6 43.2 L73.2 56.3 Q70.8 58.5 71.4 62 L74.2 81.1 Q75 87 69.7 84.5 L52.1 76 Q49 74.5 46.1 76.2 L28.1 86.9 Q23 90 24.1 84 L27.9 62.1 Q28.5 58.7 25.9 56.6 L12.4 45.2 Q8 41 14 39.8 L32.8 36 Q36 35.4 37.6 32.3 Z"></path></defs><use href="#star-contour" class="fill"></use><use href="#star-contour" class="outline"></use></svg></div></body></html>
````

## 点缀-地图定位针

逻辑路径：assets/模板库/点缀/点缀-地图定位针.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0089
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-地图定位针</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#f4f4f4}.component{--size:210px;--ink:#484848;--stroke:0px;--base-radius:3px;width:min(var(--size),80vw,56vh);aspect-ratio:0.7}.component svg{display:block;width:100%;height:100%}.pin{fill:var(--ink);stroke:var(--ink);stroke-width:var(--stroke)}.base{fill:var(--ink);rx:var(--base-radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 70 100" role="img" aria-label="点缀-地图定位针"><path class="pin" fill-rule="evenodd" d="M35 0C18 0 7 13 7 29C7 47 24 69 35 85C46 69 63 47 63 29C63 13 52 0 35 0ZM44.45 30A9.45 9.45 0 1 1 25.55 30A9.45 9.45 0 1 1 44.45 30Z"></path><rect class="base" x="12.6" y="91" width="44.8" height="6" rx="3"></rect></svg></div></body></html>
````

## 点缀-垂穗华盖

逻辑路径：assets/模板库/点缀/点缀-垂穗华盖.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0175
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-垂穗华盖</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;min-height:100vh;background:#f5f5f5}.component{--size:340px;--outline:#505050;--stroke:1.5;--chain-stroke:1.25;--thread-opacity:.72;width:min(var(--size),86vw,61.92vh);aspect-ratio:.72}.component svg{display:block;width:100%;height:100%}.edge{stroke:var(--outline);stroke-width:var(--stroke);stroke-linejoin:round;stroke-linecap:round}.chain{fill:none;stroke:#666;stroke-width:var(--chain-stroke)}.threads{fill:none;stroke:#505050;stroke-width:.8;opacity:var(--thread-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 288 400" role="img" aria-label="点缀-垂穗华盖"><defs><lineargradient id="roof" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#dedede"></stop><stop offset=".55" stop-color="#a0a0a0"></stop><stop offset="1" stop-color="#d0d0d0"></stop></lineargradient><lineargradient id="silk"><stop stop-color="#696969"></stop><stop offset=".32" stop-color="#d0d0d0"></stop><stop offset=".56" stop-color="#a4a4a4"></stop><stop offset="1" stop-color="#595959"></stop></lineargradient><g id="link"><ellipse class="chain" cy="5" rx="2.35" ry="4.7"></ellipse><ellipse class="chain" cy="13" rx="1.6" ry="4.6"></ellipse></g><g id="chain32"><use href="#link"></use><use href="#link" y="16"></use></g><g id="chain64"><use href="#chain32"></use><use href="#chain32" y="32"></use></g><g id="tassel"><path class="edge" fill="#c4c4c4" d="M0 0C-6 3-6 9 0 13C6 9 6 3 0 0Z"></path><path class="edge" fill="#737373" d="M-6 13Q0 9 6 13L7 20H-7Z"></path><path class="edge" fill="url(#silk)" d="M-6 20C-7 36-9 55-12 72Q0 78 12 72C9 55 7 36 6 20Z"></path><path class="threads" d="M-4 23L-8 71M-2 23L-4 74M0 23V75M2 23L4 74M4 23L8 71"></path><path fill="none" stroke="#e1e1e1" stroke-width="2" d="M-6 17H6"></path></g><g id="sidehang"><g transform="translate(20 158)"><use href="#chain64"></use><use href="#chain32" y="64"></use><use href="#tassel" y="96"></use></g><g transform="translate(53 169)"><use href="#chain64"></use><use href="#tassel" y="65"></use></g><g transform="translate(84 174)"><use href="#chain64"></use><use href="#chain64" y="64"></use><use href="#tassel" y="128"></use></g><g transform="translate(115 176)"><use href="#chain64"></use><use href="#chain32" y="64"></use><use href="#tassel" y="96"></use></g><path class="chain" d="M20 164Q35 207 53 172Q69 219 84 176Q100 220 115 178Q129 215 144 178"></path><g fill="#8a8a8a" stroke="#505050" stroke-width="1"><circle cx="35" cy="186" r="2.5"></circle><circle cx="69" cy="195" r="2.5"></circle><circle cx="100" cy="198" r="2.5"></circle><circle cx="129" cy="195" r="2.5"></circle></g></g></defs><path class="edge" fill="url(#roof)" d="M144 17C133 47 106 78 70 103C48 120 23 132 3 145Q9 158 21 163Q144 185 267 163Q279 158 285 145C263 132 240 120 218 103C182 78 155 47 144 17Z"></path><path class="edge" fill="#737373" d="M144 20C139 67 107 112 62 150L20 154C84 115 125 68 144 20ZM144 20C149 67 181 112 226 150L268 154C204 115 163 68 144 20Z"></path><path class="edge" fill="#c5c5c5" d="M144 23C130 89 121 115 103 157H185C167 115 158 89 144 23Z"></path><path fill="none" stroke="#ededed" stroke-width="2" d="M144 39V150M133 59Q119 116 91 150M155 59Q169 116 197 150M116 73Q84 126 47 145M172 73Q204 126 241 145"></path><g class="edge" fill="#e0e0e0"><path d="M144 4L149 12L144 22L139 12Z"></path><path d="M136 24Q144 20 152 24L155 30H133Z"></path></g><path class="edge" fill="#666" d="M3 145Q144 166 285 145L278 158Q144 183 10 158Z"></path><path fill="none" stroke="#e4e4e4" stroke-width="2" d="M9 150Q144 174 279 150"></path><path class="edge" fill="#bdbdbd" d="M11 158Q21 179 35 164Q49 187 64 170Q79 192 94 174Q110 193 125 177Q144 199 163 177Q178 193 194 174Q209 192 224 170Q239 187 253 164Q267 179 277 158Q144 182 11 158Z"></path><g fill="#555"><circle cx="21" cy="165" r="2"></circle><circle cx="53" cy="172" r="2"></circle><circle cx="84" cy="176" r="2"></circle><circle cx="115" cy="179" r="2"></circle><circle cx="144" cy="184" r="2"></circle><circle cx="173" cy="179" r="2"></circle><circle cx="204" cy="176" r="2"></circle><circle cx="235" cy="172" r="2"></circle><circle cx="267" cy="165" r="2"></circle></g><use href="#sidehang"></use><use href="#sidehang" transform="translate(288 0) scale(-1 1)"></use><g transform="translate(144 185)"><use href="#chain64"></use><use href="#chain64" y="64"></use><use href="#link" y="128"></use><use href="#tassel" y="140"></use></g></svg></div></body></html>
````

## 点缀-多弧礼仪压边

逻辑路径：assets/模板库/点缀/点缀-多弧礼仪压边.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-多弧礼仪压边</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-ceremony-edge { position:relative; width:100%; height:var(--vl-cap-height,200px); }
.vl-ceremony-edge__rim,.vl-ceremony-edge__face { position:absolute; inset:0; mask:url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAwIDI2MCIgcHJlc2VydmVBc3BlY3RSYXRpbz0ibm9uZSI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0wIDBIMTAwMFYzNSBROTY1IDc3IDkxMCA3OSBRODMzIDE5MyA2NjkgMTg1IFE2MDAgMjUwIDUwMCAyNTMgUTQwMCAyNTAgMzMxIDE4NSBRMTY3IDE5MyA5MCA3OSBRMzUgNzcgMCAzNVoiLz48L3N2Zz4=") 0 0/100% 100% no-repeat; }
.vl-ceremony-edge__rim { background:var(--vl-cap-rim,#e6c77d); transform:translateY(var(--vl-cap-edge,5px)); }
.vl-ceremony-edge__face { background:var(--vl-cap-color,#a30e15); }
</style></head><body><div class="vl-ceremony-edge" aria-hidden="true"><span class="vl-ceremony-edge__rim"></span><span class="vl-ceremony-edge__face"></span></div>
</body></html>
````

## 点缀-对话标签

逻辑路径：assets/模板库/点缀/点缀-对话标签.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0058
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-对话标签</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#a6a6a6}.component{--size:378px;--fill:#484848;--outline:#ededed;--outline-width:9;--corner:15px;--label:#fafafa;width:min(var(--size),88vw,176.4vh);aspect-ratio:2.1}.component svg{display:block;width:100%;height:100%;overflow:visible}.outline{fill:none;stroke:var(--outline);stroke-width:var(--outline-width);stroke-linejoin:round}.fill{fill:var(--fill)}text{font-family:Arial,'Microsoft YaHei',sans-serif;font-size:54.6px;font-weight:800;fill:var(--label)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 210 100" role="img" aria-label="点缀-对话标签"><defs><path id="tag" d="M20 5H190Q205 5 205 20V62Q205 77 190 77H175.35L161.7 95L148.05 77H20Q5 77 5 62V20Q5 5 20 5Z"></path></defs><use class="outline" href="#tag"></use><use class="fill" href="#tag"></use><text x="105" y="44" text-anchor="middle" dominant-baseline="central">标签</text></svg></div></body></html>
````

## 点缀-尖角爆炸星

逻辑路径：assets/模板库/点缀/点缀-尖角爆炸星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0156
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-尖角爆炸星</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{min-height:100vh;display:grid;place-items:center;background:#f5f5f5}.component{--size:330px;--fill:#777;--stroke-width:0;--stroke:#777;--opacity:1;width:min(var(--size),86vw,86vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%}.burst{fill:var(--fill);stroke:var(--stroke);stroke-width:var(--stroke-width);opacity:var(--opacity);stroke-linejoin:miter}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 200 200" role="img" aria-label="点缀-尖角爆炸星"><polygon class="burst" points="93.3,4.2 117.8,51.1 165.6,24.5 149.4,73.7 193.9,80 150.2,108.9 184,152.5 136.5,145.1 137.9,189.3 100,151 65.8,194 64.1,144.3 16.9,151.9 49.9,109.7 4.5,83.2 51.1,70.6 37.7,23.1 82.2,51.1"></polygon></svg></div></body></html>
````

## 点缀-层叠祥云

逻辑路径：assets/模板库/点缀/点缀-层叠祥云.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0086
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-层叠祥云</title><style>:root{--size:700px;--fill-opacity:.72;--stroke-width:2.56;--edge-softness:.9px;--base:#999;--lobe:#e5e5e5;--line:#858585}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#d0d0d0}.cloud{width:min(var(--size),88vw,170vh);aspect-ratio:2.3}.cloud svg{display:block;width:100%;height:100%;overflow:visible}.base{fill:var(--base);opacity:var(--fill-opacity);filter:blur(var(--edge-softness))}.lobes{fill:var(--lobe);opacity:var(--fill-opacity)}.lines{fill:none;stroke:var(--line);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round;opacity:.64}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="cloud" data-component-class="decoration"><svg viewbox="0 0 660 287" role="img" aria-label="点缀-层叠祥云"><defs><lineargradient id="wash" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".7"></stop><stop offset="1" stop-color="#eee" stop-opacity="0"></stop></lineargradient></defs><path class="base" d="M20 211C-2 186 15 162 48 163C37 140 57 114 87 118C76 83 112 57 145 72C151 38 191 20 221 42C244 5 301 7 323 45C356 28 391 46 396 76C426 62 462 80 467 107C488 94 513 104 521 124C546 105 579 124 574 149C616 134 649 157 642 183C668 206 644 235 611 234C593 261 546 269 510 251C473 283 418 270 395 250C359 279 309 270 286 249C261 267 211 266 190 242C155 262 118 251 107 235C72 254 40 242 40 224C29 226 21 220 20 211Z"></path><g class="lobes"><path d="M29 201C10 183 32 165 61 175C49 151 66 131 94 138C75 100 119 72 148 96C139 65 179 43 202 63C225 85 204 109 180 97C207 132 251 110 244 79C237 48 267 31 291 42C312 50 318 71 306 86C339 63 370 79 369 104C406 86 449 108 441 137C416 118 391 130 394 151C360 135 333 146 321 168C295 152 270 155 260 173C242 150 205 149 185 167C163 147 131 151 121 174C99 157 70 178 79 194C56 183 39 190 42 209Z"></path><path d="M110 225C99 204 122 187 143 198C141 174 170 160 190 177C201 186 199 200 190 206C219 187 246 201 248 220C270 201 294 208 305 222C326 191 366 195 379 217C402 197 432 204 439 224C463 201 493 203 502 225C527 205 551 215 560 232C586 217 610 215 624 198C623 223 598 244 569 239C548 258 518 246 508 239C475 263 440 249 427 236C400 253 370 248 354 235C330 253 303 241 288 235C254 252 219 242 210 229C173 247 146 235 140 222C132 230 119 231 110 225Z"></path><path d="M450 167C438 151 451 136 468 143C461 122 483 112 496 123C504 130 502 140 496 146C516 134 536 143 537 158C560 142 582 155 575 173C604 155 626 171 617 190C598 183 583 189 579 200C553 185 538 193 527 205C510 185 488 187 479 195C478 180 465 171 450 167Z"></path></g><path fill="url(#wash)" d="M90 124C68 100 110 70 141 89C149 50 183 43 208 63C236 20 292 24 308 61C276 45 253 56 252 81C244 126 194 140 160 109C137 129 113 114 90 124Z"></path><g class="lines"><path d="M78 188C58 158 95 140 119 162C128 143 151 137 168 147"></path><path d="M145 103C153 126 189 139 214 122C240 104 231 70 210 66"></path><path d="M260 80C257 60 285 49 298 67C307 80 292 95 281 84"></path><path d="M321 169C330 140 368 128 394 151C406 164 395 179 382 175C370 172 370 159 378 156"></path><path d="M440 180C455 167 475 169 482 183"></path><path d="M494 145C505 160 529 168 541 157"></path><path d="M152 215C153 195 183 190 191 206C197 220 179 226 173 217"></path><path d="M309 229C323 213 347 213 359 227"></path><path d="M521 232C539 215 563 220 568 235"></path></g></svg></div></body></html>
````

## 点缀-展翅飞鸟

逻辑路径：assets/模板库/点缀/点缀-展翅飞鸟.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0095
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-展翅飞鸟</title><style>:root{--size:360px;--silhouette:#f1f1f1;--rotation:-12deg}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#888}.bird{width:min(var(--size),65vw,65vh);aspect-ratio:1.5;transform:rotate(var(--rotation));transform-origin:50% 50%}.bird svg{display:block;width:100%;height:100%;fill:var(--silhouette)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="bird" data-component-class="decoration" data-pose="平展" data-fill-role="高明度点缀"><svg viewbox="0 0 300 200" role="img" aria-label="点缀-展翅飞鸟"><path d="M0 18C37 23 74 42 104 70C119 82 127 88 139 91C139 81 143 75 150 74C157 73 163 77 166 82L179 88L164 93C177 94 191 84 206 69C236 42 269 24 300 18C282 40 266 57 244 73C255 69 263 67 271 66C254 86 234 98 215 104L234 102C214 117 194 123 176 124C166 137 164 153 170 175L183 198L151 181L127 198L135 175C140 154 139 138 127 125C106 122 86 116 66 102L86 104C65 96 46 85 29 66L56 73C33 56 16 39 0 18Z"></path></svg></div></body></html>
````

## 点缀-平底山丘

逻辑路径：assets/模板库/点缀/点缀-平底山丘.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0120
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-平底山丘</title><style>:root{--size:760px;--hill-fill:#727272;--rotation:0deg}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eee}.hill{width:min(var(--size),88vw,380vh);aspect-ratio:4.8333;transform:rotate(var(--rotation));transform-origin:50% 100%}.hill svg{display:block;width:100%;height:100%;fill:var(--hill-fill)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="hill" data-component-class="decoration"><svg viewbox="0 0 290 60" role="img" aria-label="点缀-平底山丘"><path d="M0 60 C4 32 13 38 31 25 C55 1 71 -3 94 4 C119 10 139 26 171 25 C208 21 238 25 257 35 C270 43 281 51 290 60 Z"></path></svg></div></body></html>
````

## 点缀-平底山丘剪影

逻辑路径：assets/模板库/点缀/点缀-平底山丘剪影.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0116
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-平底山丘剪影</title><style>:root{--size:760px;--silhouette:#303030;--rotation:0deg}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eee}.hill{width:min(var(--size),88vw,380vh);aspect-ratio:4.8519;transform:rotate(var(--rotation));transform-origin:50% 100%}.hill svg{display:block;width:100%;height:100%;fill:var(--silhouette)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="hill" data-component-class="decoration" data-fill-role="深色前景"><svg viewbox="0 0 1000 210" preserveaspectratio="none" role="img" aria-label="点缀-平底山丘剪影"><path d="M0 210 C85 120 130 90 275 86 C355 80 400 110 480 76 C585 35 645 -10 730 9 C790 17 815 50 855 84 C910 131 975 91 1000 210 Z"></path></svg></div></body></html>
````

## 点缀-弧形飘带

逻辑路径：assets/模板库/点缀/点缀-弧形飘带.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0020
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-弧形飘带</title><style>:root{--size:860px;--band-thickness:88px;--band-fill:#bcbcbc;--text-fill:#292929;--text-size:61.92px;--shadow-offset:13.76px;--shadow-blur:10.32px;--shadow-alpha:.22}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eee}.ribbon{width:min(var(--size),88vw,245vh)}svg{display:block;width:100%;height:auto;overflow:visible}.band{fill:none;stroke:var(--band-fill);stroke-width:var(--band-thickness);stroke-linecap:butt}.shadow{fill:none;stroke:#000;stroke-width:var(--band-thickness);opacity:var(--shadow-alpha);transform:translateY(var(--shadow-offset));filter:blur(var(--shadow-blur))}.copy{fill:var(--text-fill);font-family:Arial,'Microsoft YaHei',sans-serif;font-size:var(--text-size);font-weight:800;letter-spacing:1px}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="ribbon" data-component-class="decoration"><svg viewbox="-32 -52 924 284" role="img" aria-label="点缀-弧形飘带"><defs><path id="ribbon-arc" d="M25.8 64 Q455.8 184 825.6 24"></path></defs><use class="shadow" href="#ribbon-arc"></use><use class="band" href="#ribbon-arc"></use><text class="copy" dy=".34em" data-role="内容层"><textpath href="#ribbon-arc" startoffset="50%" text-anchor="middle">说明文字</textpath></text></svg></div></body></html>
````

## 点缀-弧线动势符

逻辑路径：assets/模板库/点缀/点缀-弧线动势符.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0141
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-弧线动势符</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f5f5f5}.motion{--size:220px;--ink:#555;--stroke:11;--rotation:0deg;--mirror:1;width:min(var(--size),76vw,60vh);aspect-ratio:.8;transform:rotate(var(--rotation)) scaleX(var(--mirror))}.motion svg{display:block;width:100%;height:100%;overflow:visible}.arcs{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="motion" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 100" preserveaspectratio="none" role="img" aria-label="点缀-弧线动势符"><g class="arcs"><path d="M12 12 Q45 62 32 92"></path><path d="M65 7 Q97 47 82 75"></path></g></svg></div></body></html>
````

## 点缀-弧线星轨

逻辑路径：assets/模板库/点缀/点缀-弧线星轨.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0033
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-弧线星轨</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f5f5f5}.orbit{--size:540px;--ink:#626262;--star:#666;--stroke:3.6;--line-opacity:.85;--rotation:0deg;width:min(var(--size),86vw,150vh);aspect-ratio:2;transform:rotate(var(--rotation))}.orbit svg{width:100%;height:100%;display:block}.track{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;opacity:var(--line-opacity)}.dust{fill:var(--ink)}.stars{fill:var(--star)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="orbit" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 400 200" role="img" aria-label="点缀-弧线星轨"><g class="track"><path d="M20 150 C20 103 86 24 195 24"></path><path d="M254 35 C317 47 380 101 380 140 C380 180 268 180 211 175 C179 172 155 165 141 156"></path></g><g class="dust"><circle cx="32" cy="126" r="3.2"></circle><circle cx="63" cy="74" r="2.3"></circle><circle cx="167" cy="30" r="2.6"></circle><circle cx="247" cy="27" r="2.1"></circle><circle cx="350" cy="94" r="3.3"></circle><circle cx="339" cy="172" r="2.4"></circle><circle cx="116" cy="145" r="3.4"></circle></g><g class="stars"><path transform="translate(224 56) rotate(-12)" d="M0-26 L7.1-8.5 L24.7-8 L11.5 3.7 L15.3 21 L0 11.8 L-15.3 21 L-11.5 3.7 L-24.7-8 L-7.1-8.5 Z"></path><path transform="translate(312 114) rotate(15)" d="M0-15 L4.1-5 L14.3-4.6 L6.7 2.2 L8.8 12.1 L0 6.8 L-8.8 12.1 L-6.7 2.2 L-14.3-4.6 L-4.1-5 Z"></path></g></svg></div></body></html>
````

## 点缀-心形布贴

逻辑路径：assets/模板库/点缀/点缀-心形布贴.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0077
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-心形布贴</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f4f4f4}.patch{--size:330px;--rotation:-9deg;--edge:#e6e6e6;--fabric:#a7a7a7;--thread:#f4f4f4;--ink:#545454;--edge-width:16.8;--stitch-width:1.89;--stitch-dash:4.62 3.78;--grain-opacity:.12;width:min(var(--size),72vw,72vh);aspect-ratio:1.05;transform:rotate(var(--rotation))}.patch svg{width:100%;height:100%;display:block;overflow:visible}.edge{fill:var(--edge);stroke:var(--edge);stroke-width:var(--edge-width);stroke-linejoin:round}.serration{fill:none;stroke:var(--edge);stroke-width:18;stroke-dasharray:1 5.7;stroke-linecap:round}.fabric{fill:var(--fabric)}.grain{opacity:var(--grain-opacity)}.stitches{fill:none;stroke:var(--thread);stroke-width:var(--stitch-width);stroke-dasharray:var(--stitch-dash);stroke-linecap:round}.emblem{fill:none;stroke:var(--ink);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="patch" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 210 200" role="img" aria-label="点缀-心形布贴"><defs><path id="heart" d="M105 178 C91 165 24 124 20 82 C14 49 30 24 57 24 C78 24 95 36 105 51 C118 28 136 20 157 24 C186 29 196 54 188 84 C179 120 124 164 105 178 Z"></path><clippath id="heart-clip"><use href="#heart"></use></clippath><pattern id="weave" width="3" height="3" patternunits="userSpaceOnUse"><path d="M0 .5H3 M.5 0V3" stroke="#fff" stroke-width=".35" opacity=".32"></path><path d="M0 2H3 M2 0V3" stroke="#333" stroke-width=".3" opacity=".17"></path></pattern><filter id="grain" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency=".8" numoctaves="3" stitchtiles="stitch"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter></defs><g><use href="#heart" class="edge"></use><use href="#heart" class="serration"></use></g><use href="#heart" class="fabric"></use><g clip-path="url(#heart-clip)"><rect width="210" height="200" fill="url(#weave)"></rect><rect width="210" height="200" filter="url(#grain)" class="grain"></rect></g><use href="#heart" class="stitches" transform="translate(105 100) scale(.88) translate(-105 -100)"></use><g class="emblem" data-slot="image-1" role="img" aria-label="通用内容槽" data-role="图片槽"><path d="M105 136 C104 119 106 102 112 84"></path><path d="M108 113 C89 115 78 102 79 88 C95 88 107 96 108 113 Z"></path><path d="M110 100 C109 85 121 74 139 75 C136 91 125 101 110 100 Z"></path><path d="M88 97 Q99 103 108 113 M111 99 Q124 86 132 81"></path><path d="M88 139 Q106 144 123 137"></path><path d="M80 66 L81.8 71.2 L87 73 L81.8 74.8 L80 80 L78.2 74.8 L73 73 L78.2 71.2 Z"></path></g></svg></div></body></html>
````

## 点缀-扁平山丘

逻辑路径：assets/模板库/点缀/点缀-扁平山丘.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0113
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-扁平山丘</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f5f5f5}.hill{--size:560px;--fill:#bcbcbc;--rotation:0deg;width:min(var(--size),86vw,330vh);aspect-ratio:4.3;transform:rotate(var(--rotation));transform-origin:50% 100%}.hill svg{width:100%;height:100%;display:block;fill:var(--fill);stroke:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="hill" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 430 100" role="img" aria-label="点缀-扁平山丘"><g transform="scale(430 100)"><path d="M0 1 Q.12 .48 .28 .48 Q.39 .51 .48 .47 Q.58 .4 .65 .15 Q.75 -.08 .82 .31 Q.88 .65 .95 .67 L1 1 Z"></path></g></svg></div></body></html>
````

## 点缀-扇形叶冠

逻辑路径：assets/模板库/点缀/点缀-扇形叶冠.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0099
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-扇形叶冠</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f5f5f5}.crown{--size:300px;--fill:#777;--rotation:0deg;width:min(var(--size),76vw,78vh);aspect-ratio:1.12;transform:rotate(var(--rotation));transform-origin:50% 85%}.crown svg{display:block;width:100%;height:100%;fill:var(--fill);stroke:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="crown" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 112 100" role="img" aria-label="点缀-扇形叶冠"><path d="M9 80 C15 62 15 47 10 30 C9 26 11 25 14 28 C25 36 32 44 35 54 C31 36 29 19 35 5 C36 2 38 2 39 6 C42 19 49 34 52 42 C53 23 63 13 70 8 C74 5 75 7 73 11 C68 29 69 39 66 50 C80 35 93 29 104 31 C108 31 109 33 105 35 C91 44 85 55 80 62 C95 57 104 58 109 63 C112 65 111 67 107 67 C95 70 87 80 80 81 C91 82 98 86 99 91 C100 94 97 94 94 93 C81 89 71 95 60 96 C51 95 48 89 44 85 C33 76 22 75 9 80 Z"></path></svg></div></body></html>
````

## 点缀-手绘云朵

逻辑路径：assets/模板库/点缀/点缀-手绘云朵.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0129
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘云朵</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e6e6e6}.cloud{--size:540px;--stroke:6.5px;--fill:#fff;--ink:#252525;--rotation:0deg;width:min(var(--size),88vw,176vh);aspect-ratio:2.2;transform:rotate(var(--rotation))}.cloud svg{display:block;width:100%;height:100%;overflow:visible}.outline{fill:var(--fill);stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="cloud" data-component-class="decoration"><svg viewbox="0 0 500 227" role="img" aria-label="点缀-手绘云朵"><path class="outline" d="M77 197 C45 207 15 190 15 165 C13 143 29 128 53 123 C41 103 55 76 81 72 C93 69 108 72 117 79 C119 46 146 25 176 29 C195 30 213 42 219 57 C235 25 265 15 291 24 C313 30 326 47 330 68 C355 48 385 56 400 77 C407 87 409 99 406 110 C439 98 474 113 482 138 C492 166 473 188 444 189 C428 208 397 210 371 198 C350 214 318 215 294 204 C273 218 242 217 220 205 C190 218 159 214 140 200 C117 211 94 210 77 197 Z"></path></svg></div></body></html>
````

## 点缀-手绘五角星

逻辑路径：assets/模板库/点缀/点缀-手绘五角星.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0071
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘五角星</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e9e9e9}.star{--size:330px;--fill:#d2d2d2;--ink:#414141;--outline-width:10.5px;--edge-offset:1px;--grain-opacity:.1;--rotation:-5deg;width:min(var(--size),78vw,78vh);aspect-ratio:1;transform:rotate(var(--rotation))}.star[data-variant="dark"]{--fill:#777;--outline-width:0px;--grain-opacity:.07}.star svg{display:block;width:100%;height:100%;overflow:visible}.fill{fill:var(--fill)}.edge{fill:none;stroke:var(--ink);stroke-width:var(--outline-width);stroke-linejoin:round;transform:translate(var(--edge-offset),0)}.grain{opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="star" data-component-class="decoration" data-variant="light"><svg viewbox="0 0 300 300" role="img" aria-label="点缀-手绘五角星"><defs><path id="star-shape" d="M153 17 L185 102 L280 111 L207 174 L226 271 L148 221 L69 266 L86 174 L19 112 L117 99 Z"></path><clippath id="star-clip"><use href="#star-shape"></use></clippath><pattern id="star-grain" width="23" height="27" patternunits="userSpaceOnUse"><circle cx="3" cy="7" r=".9" fill="#171717"></circle><circle cx="17" cy="20" r="1.2" fill="#171717"></circle><path d="M11 2l2 1M7 22l1-2M21 10l-2 1" stroke="#fff" stroke-width="1.4"></path><circle cx="10" cy="13" r=".6" fill="#111"></circle></pattern></defs><use class="fill" href="#star-shape"></use><use class="edge" href="#star-shape"></use><g class="grain" clip-path="url(#star-clip)"><path d="M0 0H300V300H0Z" fill="url(#star-grain)"></path></g></svg></div></body></html>
````

## 点缀-手绘办公物件

逻辑路径：assets/模板库/点缀/点缀-手绘办公物件.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0213
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘办公物件</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e5e5e5}.office{--size:720px;--stroke:3.6px;--ink:#363636;--rotation:0deg;width:min(var(--size),90vw,140vh);aspect-ratio:5/3;transform:rotate(var(--rotation))}.office svg{display:block;width:100%;height:100%}.line{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="office" data-component-class="decoration"><svg viewbox="0 0 600 360" role="img" aria-label="点缀-手绘办公物件"><g class="line"><g id="hanging-lamp"><path d="M443 15L444 47M444 55L442 79 C430 84 424 96 423 107 L404 137 Q442 144 483 137 L463 106 C461 92 453 81 442 79"></path><path d="M424 108Q442 113 463 106M407 138Q440 153 480 139M432 146Q442 163 453 146"></path><path d="M407 164l-6 11M442 172v15M479 163l7 12"></path></g><g id="desk-computer-vase"><path d="M137 238L26 239 L21 250 Q219 253 389 249M407 248L451 248M32 239L28 228 L411 225 L446 235"></path><path d="M41 253L35 336M62 253L57 335M35 338L57 337M309 251L314 331M325 251L331 333M315 337L331 337"></path><path d="M83 255L82 298L282 297L282 253M84 275L282 274M165 263L197 263M167 286L198 285"></path><path d="M164 122Q164 118 170 119 L302 117 Q309 118 308 124 L310 206 Q309 210 303 210 L169 211 Q163 212 163 204Z"></path><path d="M174 130L297 128 L298 194L175 196 L174 137M166 200L308 199M231 211L228 221 L247 221L242 210M211 226Q237 218 264 225"></path><path d="M237 205l1 0M177 236L288 234L280 228L185 229ZM298 233Q301 224 310 226Q316 227 318 233Q308 237 298 233M308 227v3"></path><path d="M73 173Q71 166 78 166 L111 166 Q118 167 113 175 C109 186 119 203 117 215 Q116 227 95 227 Q72 228 70 215 C67 202 79 184 73 173Z"></path><path d="M75 173Q92 179 113 173M80 210Q81 218 88 219"></path><path d="M93 168Q90 132 75 111M100 168Q100 139 119 120M94 149Q77 143 69 129M98 140Q104 118 98 98"></path><path d="M76 115Q58 118 54 102Q71 99 76 115ZM84 134Q85 117 95 118Q101 131 84 134ZM115 128Q111 108 127 107Q133 119 115 128ZM99 112Q88 108 86 94Q99 90 99 104M72 132Q56 137 51 121Q67 119 72 132Z"></path></g><g id="chair"><path d="M400 267Q390 233 394 213 Q398 199 421 199 L494 201 Q512 202 513 218 L506 269M405 262L402 220Q401 211 415 212 L491 214Q502 214 501 226L496 263"></path><path d="M389 275Q446 263 514 274 L516 287Q453 295 389 285Z"></path><path d="M405 291L398 337M418 292L414 337M491 292L501 337M504 290L516 336M398 340L414 340M502 341L516 340"></path><path d="M432 222L433 251M468 223L467 252"></path></g></g></svg></div></body></html>
````

## 点缀-手绘动物头像

逻辑路径：assets/模板库/点缀/点缀-手绘动物头像.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0138
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘动物头像</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#dedede}.animal{--size:540px;--fill:#fafafa;--ink:#262626;--stroke:13.5px;--rotation:0deg;width:min(var(--size),86vw,172vh);aspect-ratio:2.25;transform:rotate(var(--rotation))}.animal svg{display:block;width:100%;height:100%;overflow:visible}.silhouette{fill:var(--fill);stroke:var(--ink);stroke-width:var(--stroke);stroke-linejoin:round;stroke-linecap:round}.feature{fill:var(--ink)}.line{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="animal" data-component-class="decoration" data-palette-role="填充与轮廓颜色"><svg viewbox="0 0 450 200" role="img" aria-label="点缀-手绘动物头像"><g data-role="内容层"><path class="silhouette" d="M129 56 C113 24 81 19 61 40 C38 63 46 101 76 114 C82 118 91 118 98 117 C96 145 119 165 155 172 C207 183 285 180 333 164 C355 157 367 139 362 117 C388 125 417 107 424 82 C432 57 415 28 391 26 C367 23 351 37 343 58 C310 37 277 32 238 34 C195 33 157 41 129 56 Z"></path><g id="head-features"><path class="line" d="M94 60 C77 53 69 66 73 82M382 60 C396 53 405 67 398 82"></path><ellipse class="feature" cx="174" cy="102" rx="8" ry="10"></ellipse><ellipse class="feature" cx="302" cy="102" rx="8" ry="10"></ellipse><path class="feature" d="M238 69 C218 68 211 87 213 109 L217 136 Q238 151 258 136 L262 108 C264 84 255 69 238 69Z"></path><path class="line" d="M238 144L238 155" style="stroke-width:7px"></path></g></g><g id="head-accent" class="line"><path d="M43 28L27 14M28 52L10 47M67 18L62 8"></path></g></svg></div></body></html>
````

## 点缀-手绘叶片

逻辑路径：assets/模板库/点缀/点缀-手绘叶片.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0128
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘叶片</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e8e8e8}.leaf{--size:300px;--fill:#a6a6a6;--ink:#292929;--stroke:16.5px;--rotation:0deg;width:min(var(--size),78vw,78vh);aspect-ratio:1;transform:rotate(var(--rotation))}.leaf svg{display:block;width:100%;height:100%}.blade{fill:var(--fill);stroke:var(--ink);stroke-width:var(--stroke);stroke-linejoin:round;stroke-linecap:round}.vein{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="leaf" data-component-class="decoration"><svg viewbox="0 0 300 300" role="img" aria-label="点缀-手绘叶片"><path class="blade" d="M65 230 C44 196 52 141 91 103 C133 61 205 68 262 30 C253 88 248 151 210 192 C174 233 119 246 81 227 L47 266 Q39 272 34 264 Q31 260 38 251Z"></path><g class="vein"><path d="M64 238 C99 207 117 177 151 149 C179 124 209 98 231 69"></path><path d="M120 180 Q105 156 108 132M151 151 Q180 158 203 144"></path></g></svg></div></body></html>
````

## 点缀-手绘四瓣花

逻辑路径：assets/模板库/点缀/点缀-手绘四瓣花.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0232
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘四瓣花</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e6e6e6}.flower{--size:400px;--petal:#aaa;--center:#383838;--texture-opacity:.19;--stroke:0px;--rotation:-9deg;width:min(var(--size),72vw,72vh);aspect-ratio:1;transform:rotate(var(--rotation))}.flower svg{display:block;width:100%;height:100%;overflow:visible}.petals{fill:var(--petal);stroke:#888;stroke-width:var(--stroke);stroke-linejoin:round}.texture{opacity:var(--texture-opacity)}.heart{fill:var(--center)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="flower" data-component-class="decoration" data-role="内容层"><svg viewbox="0 0 300 300" role="img" aria-label="点缀-手绘四瓣花"><defs><path id="petal-shape" d="M147 109 C143 78 124 33 93 15 C67 0 35 10 17 34 C0 58 4 89 22 111 C41 134 75 143 109 147 C77 152 36 161 17 187 C-1 212 8 247 31 268 C51 289 82 292 105 273 C129 254 140 220 148 190 C153 227 166 264 194 286 C218 303 250 294 272 272 C295 250 296 218 279 195 C260 169 220 154 190 147 C220 142 261 126 282 101 C302 78 296 46 274 24 C253 3 222 0 199 17 C172 37 155 77 147 109 Z"></path><clippath id="petal-mask"><use href="#petal-shape"></use></clippath><pattern id="paper-fibers" width="31" height="37" patternunits="userSpaceOnUse"><path d="M2 5l4-1M17 8l1 4M8 26l5-2M25 32l3 1M24 18l-3 2" stroke="#fff" stroke-width="1.1" opacity=".8"></path><path d="M11 15l2 1M3 34l2-3M27 7l2 2M19 29l-2 1" stroke="#333" stroke-width=".8" opacity=".7"></path><circle cx="6" cy="16" r=".8" fill="#fff"></circle><circle cx="21" cy="3" r=".65" fill="#333"></circle></pattern></defs><use class="petals" href="#petal-shape"></use><g class="texture" clip-path="url(#petal-mask)"><g fill="none" stroke-linecap="round"><path d="M130 126Q88 71 49 43M124 139Q74 120 28 78M164 125Q192 64 233 32M177 136Q239 105 270 56M125 164Q67 189 38 230M140 179Q108 242 65 265M173 174Q211 231 260 254M183 162Q248 189 278 227" stroke="#f9f9f9" stroke-width="9"></path><path d="M111 118Q71 84 50 59M181 117Q222 74 247 49M113 182Q74 216 54 242M183 189Q214 239 241 266" stroke="#f4f4f4" stroke-width="3"></path><path d="M95 31Q110 66 127 93M254 32Q217 78 202 113M24 199Q64 176 95 170M171 221Q184 253 213 278" stroke="#4c4c4c" stroke-width="5"></path></g><path d="M0 0H300V300H0Z" fill="url(#paper-fibers)"></path></g><path class="heart" d="M153 117 C173 115 188 131 189 152 C191 174 176 192 154 192 C133 193 118 178 117 157 C115 137 129 119 153 117Z"></path></svg></div></body></html>
````

## 点缀-手绘小花

逻辑路径：assets/模板库/点缀/点缀-手绘小花.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0041
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘小花</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#dededb}.component{--size:260px;--stroke:2.5;--paper:#f7f7f3;--ink:#414141;--center:#aaa9a5;--rotation:-6deg;--linejoin:round;width:min(var(--size),82vw,82vh);aspect-ratio:1;transform:rotate(var(--rotation))}svg{display:block;width:100%;height:100%;overflow:visible}.petals{fill:var(--paper);stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:var(--linejoin)}.center{fill:var(--center);stroke:var(--ink);stroke-width:calc(var(--stroke)*.8)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><main class="component" data-component-class="decoration" aria-label="点缀-手绘小花"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-手绘小花"><path class="petals" d="M43 33 C35 24 35 8 46 6 C61 2 69 18 59 33 C71 21 86 22 92 33 C99 46 84 54 68 53 C82 57 92 70 83 81 C73 93 60 83 55 67 C57 82 50 98 37 92 C23 86 28 71 39 62 C26 74 10 75 6 62 C1 48 16 42 33 45 C17 45 5 33 12 21 C19 8 35 18 43 33 Z"></path><circle class="center" cx="50" cy="50" r="7.5"></circle></svg></main></body></html>
````

## 点缀-手绘弯箭头

逻辑路径：assets/模板库/点缀/点缀-手绘弯箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0187
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘弯箭头</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e4e4e1}.component{--size:300px;--stroke:3.5;--ink:#393939;--rotation:0deg;--linecap:round;--linejoin:round;width:min(var(--size),80vw,80vh);aspect-ratio:1;transform:rotate(var(--rotation))}.component[data-tone="light"]{--ink:#fafaf7}svg{display:block;width:100%;height:100%}path{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:var(--linecap);stroke-linejoin:var(--linejoin)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><main class="component" data-component-class="decoration" data-tone="dark" aria-label="点缀-手绘弯箭头"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-手绘弯箭头"><path d="M15 5 C12 25 53 19 56 39 C59 55 38 60 49 74 C56 83 73 88 85 90"></path><path d="M68.8 97.8 L85 90 L72.8 76.8"></path></svg></main></body></html>
````

## 点缀-手绘星芒

逻辑路径：assets/模板库/点缀/点缀-手绘星芒.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0192
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘星芒</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e4e4e1}.component{--size:240px;--stroke:3.7;--ink:#4a4a48;--rotation:-4deg;--linecap:round;--linejoin:round;width:min(var(--size),80vw,80vh);aspect-ratio:1;transform:rotate(var(--rotation))}svg{display:block;width:100%;height:100%}.rays{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:var(--linecap);stroke-linejoin:var(--linejoin)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><main class="component" data-component-class="decoration" aria-label="点缀-手绘星芒"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-手绘星芒"><g class="rays"><path d="M49.6 39 Q48 23 51 6"></path><path d="M59 39 Q65 32 72 25"></path><path d="M63 49 Q79 46 94 48"></path><path d="M59 60 Q69 68 77 78"></path><path d="M49 63 Q47 81 50 94"></path><path d="M39 60 Q32 68 26 72"></path><path d="M37 50 Q20 53 6 49"></path><path d="M39 39 Q31 29 19 20"></path></g></svg></main></body></html>
````

## 点缀-手绘气球

逻辑路径：assets/模板库/点缀/点缀-手绘气球.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0102
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘气球</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e4e4e1}.component{--height:420px;--stroke:3.5;--ink:#424242;--balloon-fill:#a9a9a6;--highlight:#fafaf8;--highlight-opacity:.95;--rotation:0deg;--linejoin:round;height:min(var(--height),84vh,145vw);aspect-ratio:108/195;transform:rotate(var(--rotation))}svg{display:block;width:100%;height:100%}.string{fill:none;stroke:var(--ink);stroke-width:calc(var(--stroke)*.62);stroke-linecap:round}.body,.knot{fill:var(--balloon-fill);stroke:var(--ink);stroke-width:var(--stroke);stroke-linejoin:var(--linejoin);stroke-linecap:round}.highlight{fill:none;stroke:var(--highlight);stroke-width:calc(var(--stroke)*1.35);stroke-linecap:round;opacity:var(--highlight-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><main class="component" data-component-class="decoration" aria-label="点缀-手绘气球"><svg viewbox="-4 -5 108 195" role="img" aria-label="点缀-手绘气球"><path class="string" data-slot="content-1" data-anchor-end="0.84,1.0" d="M52 112.85 C48 129 66 133 59 147 C51 162 75 169 84 185" data-role="内容槽"></path><g data-slot="content-2" data-role="内容槽"><path class="knot" d="M49 101.75 Q54 102 56 107 L62 116 Q51 112 42 116.55 L49 101.75Z"></path><path class="body" d="M50 0 C22 0 6 20 6 47 C6 75 24 101 50 109.15 C74 103 94 76 94 46 C94 18 77 0 50 0 Z"></path></g><path class="highlight" d="M23 27.75 C19.5 33 17.5 42 19 49.95"></path></svg></main></body></html>
````

## 点缀-手绘波线

逻辑路径：assets/模板库/点缀/点缀-手绘波线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0137
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘波线</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e4e4e1}.component{--length:440px;--ink:#51514e;--floating-stroke:2.7;--divider-stroke:.6;--rotation:0deg;--linecap:round;--linejoin:round;width:min(var(--length),84vw,240vh);transform:rotate(var(--rotation))}svg{display:block;width:100%;height:auto;overflow:visible}path{fill:none;stroke:var(--ink);stroke-linecap:var(--linecap);stroke-linejoin:var(--linejoin)}.floating path{stroke-width:var(--floating-stroke)}.divider{display:none}.divider path{stroke-width:var(--divider-stroke)}.component[data-variant="divider"] .floating{display:none}.component[data-variant="divider"] .divider{display:block}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><main class="component" data-component-class="decoration" data-variant="floating" data-slot="content-1" aria-label="通用内容槽" data-role="内容槽"><svg class="floating" viewbox="-3 -3 106 36" role="img" aria-label="点缀-手绘波线"><path d="M0 16 C8 7 13 5 20 10 C27 15 31 24 39 20 C47 16 50 6 59 9 C67 12 69 21 78 20 C87 19 91 9 100 14"></path></svg><svg class="divider" viewbox="-1 -2 102 6" role="img" aria-label="点缀-手绘波线"><path d="M0 1 C7 .3 13 .4 19 .8 C26 1.4 31 1.7 38 1.2 C44 .7 49 .2 57 .6 C66 1 69 1.8 77 1.4 C85 1 92 .3 100 .9"></path></svg></main></body></html>
````

## 点缀-手绘爱心

逻辑路径：assets/模板库/点缀/点缀-手绘爱心.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0104
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘爱心</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeee}.heart{--size:min(62vmin,280px);--fill:#a5a5a5;--outline:#303030;--stroke:8;--rotation:8deg;--join:round;width:var(--size);aspect-ratio:1;transform:rotate(var(--rotation))}.heart svg{display:block;width:100%;height:100%;overflow:visible}.heart path{fill:var(--fill);stroke:var(--outline);stroke-width:var(--stroke);stroke-linejoin:var(--join);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="heart" data-component-class="decoration"><svg viewbox="-5 -5 110 110" role="img" aria-label="点缀-手绘爱心"><path data-layer="heart-body" data-role="内容层" d="M49 91 C40 83 8 61 5 39 C2 22 10 10 23 10 C35 8 44 17 49 27 C57 10 69 6 81 11 C95 16 98 29 94 42 C89 61 64 82 49 91 Z"></path></svg></div></body></html>
````

## 点缀-手绘番茄

逻辑路径：assets/模板库/点缀/点缀-手绘番茄.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0197
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘番茄</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeee}.tomato{--size:min(66vmin,310px);--fruit:#969696;--leaf:#555555;--outline:#333333;--highlight:#dedede;--stroke:2.2;--detail-stroke:1.5;--rotation:0deg;--join:round;width:var(--size);aspect-ratio:1;transform:rotate(var(--rotation));transform-origin:50% 50%}.tomato svg{width:100%;height:100%;display:block}.outlined{stroke:var(--outline);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:var(--join)}.detail{fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-width:var(--detail-stroke)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="tomato" data-component-class="decoration"><svg viewbox="-3 -3 106 106" role="img" aria-label="点缀-手绘番茄"><path data-layer="tomato-body" class="outlined" fill="var(--fruit)" d="M47 19 C32 12 17 21 10 37 C4 48 5 65 11 77 C18 91 31 96 46 98 C63 99 80 92 88 78 C96 65 96 49 89 35 C82 20 64 13 54 19 Q50 21 47 19 Z"></path><g data-layer="tomato-calyx" class="outlined" fill="var(--leaf)"><path d="M49 22 C48 14 47 7 51 1 L56 2 C53 9 54 15 56 21 L70 13 L66 25 L80 29 L65 32 L69 43 L55 34 L45 44 L45 32 L29 34 L40 25 L30 17 L46 21 Z"></path></g><g data-layer="tomato-detail" class="detail"><path stroke="#363636" opacity=".7" d="M53 23 L55 31 M55 28 L65 25 M48 27 L39 29 M48 37 L51 30"></path><path stroke="var(--highlight)" stroke-width="3" d="M20 43 Q17 49 17 55 M17 62 L18 66 M26 33 L30 30"></path><path stroke="#525252" opacity=".55" d="M80 66 Q78 78 68 84 M38 89 Q44 91 49 90"></path></g></svg></div></body></html>
````

## 点缀-手绘纸夹

逻辑路径：assets/模板库/点缀/点缀-手绘纸夹.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0186
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘纸夹</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e7e7e7}.clip{--height:min(72vmin,360px);--paper:#fafafa;--outline:#383838;--stroke:3;--detail-stroke:2.1;--join:round;--rotation:0deg;height:var(--height);aspect-ratio:1/2;transform:rotate(var(--rotation));transform-origin:50% 50%;isolation:isolate}.clip svg{display:block;width:100%;height:100%;overflow:visible}.body{fill:var(--paper);stroke:var(--outline);stroke-width:var(--stroke);stroke-linejoin:var(--join);stroke-linecap:round}.details{stroke:var(--outline);stroke-width:var(--detail-stroke);stroke-linecap:round;stroke-linejoin:round;fill:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="clip" data-component-class="decoration" data-attachment-anchor="0.5,0.5" data-overlap-card-top-ratio="0.45"><svg viewbox="-3 -6 56 112" role="img" aria-label="点缀-手绘纸夹"><path data-layer="body" class="body" d="M5 2 Q25 -1 45 3 Q49 4 48 10 L39 88 Q38 96 32 98 Q25 100 18 97 Q12 95 11 87 L2 11 Q0 3 5 2 Z"></path><g data-layer="details" class="details"><path d="M10 10 Q25 8 40 11"></path><path fill="#d4d4d4" d="M29 20 C29 23 27 25 24 24 C21 24 20 22 21 19 C22 16 28 16 29 20 Z"></path><path d="M18 82 Q18 89 23 90 L29 90" opacity=".72"></path></g></svg></div></body></html>
````

## 点缀-手绘草莓

逻辑路径：assets/模板库/点缀/点缀-手绘草莓.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0231
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘草莓</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}body{display:grid;place-items:center;background:#f3f2f0}.strawberry{--size:360px;--rotation:0deg;--body-color:#a2a09d;--body-edge:#8b8986;--seed-color:#53514e;--leaf-color:#676963;--leaf-line:#96988f;--stroke-width:.38px;--grain-opacity:.09;--seed-rx:1.4px;--seed-ry:2.35px;width:min(var(--size),80vw,80vh);aspect-ratio:1;transform:rotate(var(--rotation))}.strawberry svg{display:block;width:100%;height:100%;overflow:visible}.fruit{fill:var(--body-color);stroke:var(--body-edge);stroke-width:var(--stroke-width);stroke-linejoin:round}.grain{opacity:var(--grain-opacity)}.seeds{fill:var(--seed-color)}.seeds ellipse{rx:var(--seed-rx);ry:var(--seed-ry)}.leaves{fill:var(--leaf-color);stroke:var(--leaf-color);stroke-width:var(--stroke-width);stroke-linejoin:round}.veins{fill:none;stroke:var(--leaf-line);stroke-width:.45;stroke-linecap:round;opacity:.55}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="strawberry" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 100 100" role="img" aria-label="点缀-手绘草莓"><defs><path id="fruit-shape" d="M49 17 C39 13 29 13 21 18 C11 24 6 33 6 43 C6 55 13 68 21 78 C29 88 40 98 49 98 C57 98 68 87 76 77 C86 64 94 51 94 39 C94 28 88 20 78 16 C69 13 58 13 49 17Z"></path><clippath id="fruit-clip"><use href="#fruit-shape"></use></clippath><filter id="paper-grain" x="0" y="0" width="100%" height="100%"><feturbulence type="fractalNoise" basefrequency="1.35" numoctaves="3" seed="19" stitchtiles="stitch"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter><filter id="hand-edge" x="-3%" y="-3%" width="106%" height="106%"><feturbulence type="fractalNoise" basefrequency=".36" numoctaves="2" seed="7" result="edge"></feturbulence><fedisplacementmap in="SourceGraphic" in2="edge" scale=".25" xchannelselector="R" ychannelselector="G"></fedisplacementmap></filter></defs><g id="berry-body"><use href="#fruit-shape" class="fruit" filter="url(#hand-edge)"></use></g><g id="berry-grain" clip-path="url(#fruit-clip)"><rect x="5" y="12" width="90" height="87" class="grain" filter="url(#paper-grain)"></rect><g fill="#e7e5e1" opacity=".08"><path d="M15 38C17 24 29 20 36 22C24 29 22 42 20 54C17 50 14 44 15 38Z"></path><path d="M33 59C40 53 51 53 57 59C61 65 54 71 46 73C36 73 29 67 33 59Z"></path><ellipse cx="72" cy="41" rx="9" ry="6"></ellipse></g><g fill="#54524e" opacity=".055"><ellipse cx="28" cy="48" rx="6" ry="4"></ellipse><ellipse cx="63" cy="74" rx="7" ry="5"></ellipse><ellipse cx="53" cy="34" rx="8" ry="4"></ellipse><path d="M83 53C76 71 62 86 48 95C55 94 67 83 75 74C83 62 87 56 89 49Z"></path></g></g><g id="berry-seeds" class="seeds"><ellipse cx="25" cy="29" transform="rotate(-20 25 29)"></ellipse><ellipse cx="40" cy="32" transform="rotate(-8 40 32)"></ellipse><ellipse cx="57" cy="32" transform="rotate(9 57 32)"></ellipse><ellipse cx="75" cy="29" transform="rotate(21 75 29)"></ellipse><ellipse cx="16" cy="43" style="--seed-rx:1.15px;--seed-ry:2.05px" transform="rotate(-22 16 43)"></ellipse><ellipse cx="31" cy="45" transform="rotate(-13 31 45)"></ellipse><ellipse cx="49" cy="45" transform="rotate(3 49 45)"></ellipse><ellipse cx="67" cy="45" transform="rotate(12 67 45)"></ellipse><ellipse cx="84" cy="42" style="--seed-rx:1.2px;--seed-ry:2.15px" transform="rotate(20 84 42)"></ellipse><ellipse cx="23" cy="59" transform="rotate(-18 23 59)"></ellipse><ellipse cx="40" cy="59" style="--seed-rx:1.65px" transform="rotate(-7 40 59)"></ellipse><ellipse cx="58" cy="59" transform="rotate(7 58 59)"></ellipse><ellipse cx="76" cy="57" transform="rotate(18 76 57)"></ellipse><ellipse cx="32" cy="73" style="--seed-rx:1.25px;--seed-ry:2.1px" transform="rotate(-15 32 73)"></ellipse><ellipse cx="49" cy="73" transform="rotate(-2 49 73)"></ellipse><ellipse cx="65" cy="72" style="--seed-rx:1.3px;--seed-ry:2.2px" transform="rotate(17 65 72)"></ellipse><ellipse cx="42" cy="85" style="--seed-rx:1.1px;--seed-ry:1.85px" transform="rotate(-8 42 85)"></ellipse><ellipse cx="56" cy="85" style="--seed-rx:1.15px;--seed-ry:1.9px" transform="rotate(12 56 85)"></ellipse></g><g id="berry-leaves"><g class="leaves" filter="url(#hand-edge)"><path d="M50 16C47 11 48 5 51 0L55 1C52 6 51 10 54 15Z"></path><path d="M51 17C43 15 38 10 35 5C42 5 50 9 53 14C57 8 62 5 69 5C66 11 61 15 56 17C66 13 75 14 82 18C74 23 66 23 58 20C62 23 64 26 64 29C57 28 53 25 51 21C47 26 42 29 37 29C37 25 41 21 46 18C37 22 31 22 25 19C31 14 40 13 48 16Z"></path></g><g class="veins"><path d="M51 18L39 9M53 17L64 8M55 18L76 18M53 19L61 26M49 19L40 26M47 17L30 19"></path><path d="M51 13Q50 7 53 3"></path></g></g></svg></div></body></html>
````

## 点缀-手绘虚线箭头

逻辑路径：assets/模板库/点缀/点缀-手绘虚线箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0064
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘虚线箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeee}.arrow{--size:min(78vmin,430px);--ink:#424242;--stroke:3px;--dash:10 9;--opacity:.9;--linecap:round;--shadow-opacity:0;--shadow-blur:1;--shadow-x:1;--shadow-y:2;width:var(--size);aspect-ratio:1}.arrow svg{width:100%;height:100%;display:block}.route,.head{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:var(--linecap);stroke-linejoin:round;vector-effect:non-scaling-stroke}.route{stroke-dasharray:var(--dash)}.shadow{opacity:var(--shadow-opacity);filter:url("#arrow-shadow")}.foreground{opacity:var(--opacity)}.shadow .route,.shadow .head{stroke:#111}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="arrow" data-component-class="decoration"><svg viewbox="0 0 790 790" role="img" aria-label="点缀-手绘虚线箭头"><defs><path id="arrow-route" d="M158 39.5 C590 48 610 332 378 335 C135 338 183 137 423 233 C614 310 447 581 647.8 742.6"></path><path id="arrow-tip" d="M569 736.5 L647.8 742.6 L625 667"></path></defs><g data-layer="arrow-shadow" class="shadow"><use href="#arrow-route" class="route"></use><use href="#arrow-tip" class="head"></use></g><g data-layer="arrow-path" class="foreground"><use href="#arrow-route" class="route"></use><use href="#arrow-tip" class="head"></use></g></svg></div></body></html>
````

## 点缀-手绘蝴蝶

逻辑路径：assets/模板库/点缀/点缀-手绘蝴蝶.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0103
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘蝴蝶</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.butterfly{--size:285px;--stroke:5.225;--wing-fill:#adadab;--ink:#303030;--rotation:0deg;width:min(var(--size),82vw,77.9vh);aspect-ratio:.95;transform:rotate(var(--rotation))}.butterfly svg{display:block;width:100%;height:100%;overflow:visible}.wings{fill:var(--wing-fill);stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}.body{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="butterfly" data-component-class="decoration" role="img" aria-label="点缀-手绘蝴蝶"><svg viewbox="0 0 95 100" xmlns="http://www.w3.org/2000/svg"><g class="wings"><path d="M47 49 C35 29 16 18 7 29 C-2 42 7 63 24 67 C8 67 6 82 15 91 C27 102 42 86 49 65 Z"></path><path d="M49 48 C57 29 79 14 88 26 C99 41 89 61 73 65 C89 68 89 83 79 89 C67 96 55 81 49 64 Z"></path></g><g class="body"><path d="M48 43 C45 51 48 61 51 70 C53 77 52 82 49 86"></path><path d="M47 45 C43 31 36 18 26 10 C22 7 18 9 19 13"></path><path d="M49 44 C52 26 61 10 69 5 C74 2 78 5 76 9"></path></g></svg></div></body></html>
````

## 点缀-手绘衣架

逻辑路径：assets/模板库/点缀/点缀-手绘衣架.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0139
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-手绘衣架</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.hanger{--size:288px;--stroke:4.32;--fill:#b7b7b3;--line:#343434;--rotation:0deg;width:min(var(--size),82vw,78.72vh);aspect-ratio:.96;transform:rotate(var(--rotation))}.hanger svg{display:block;width:100%;height:100%;overflow:visible}.outline{fill:var(--fill);fill-rule:evenodd;stroke:var(--line);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}.detail{fill:none;stroke:var(--line);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="hanger" data-component-class="decoration" role="img" aria-label="点缀-手绘衣架"><svg viewbox="0 0 96 100" xmlns="http://www.w3.org/2000/svg"><g class="outline"><path d="M12 24 C7 13 15 3 27 4 C43 3 53 15 51 28 C50 38 39 41 38 49 L30 56 C27 41 32 35 40 29 C47 22 38 12 28 12 C20 11 16 17 19 23 Q20 28 16 29 Q13 29 12 24 Z"></path><path d="M31 49 Q34 47 38 51 L91 85 Q96 89 90 94 L10 66 Q1 63 5 58 L29 50 Q30 49 31 49 Z M33 58 L17 61 L73 81 Z"></path></g><g class="detail"><path d="M20 70 L29 73 M38 77 Q46 80 52 82 M62 86 L69 88"></path><path d="M81 91 L82 91"></path></g></svg></div></body></html>
````

## 点缀-放大引号

逻辑路径：assets/模板库/点缀/点缀-放大引号.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0164
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-放大引号</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.quote{--size:250px;--ink:#606060;--slant:-24deg;--pair-gap:20px;--stroke:0;--variant-rotation:0deg;width:min(var(--size),82vw,102.5vh);aspect-ratio:1.25}.quote[data-variant="closing"]{--variant-rotation:180deg}.quote svg{display:block;width:100%;height:100%;transform:rotate(var(--variant-rotation));overflow:visible}.marks{fill:var(--ink);stroke:var(--ink);stroke-width:var(--stroke);transform:translateX(41px) skewX(var(--slant))}.second{transform:translateX(calc(34px + var(--pair-gap)))}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="quote" data-component-class="decoration" data-variant="opening" role="img" aria-label="点缀-放大引号"><svg viewbox="0 0 125 100" xmlns="http://www.w3.org/2000/svg"><defs><path id="quote-glyph" d="M0 90 V53 C0 29 10 15 31 10 L34 24 C22 28 16 36 16 47 H34 V90 Z"></path></defs><g class="marks"><use href="#quote-glyph"></use><use class="second" href="#quote-glyph"></use></g></svg></div></body></html>
````

## 点缀-断口三角线

逻辑路径：assets/模板库/点缀/点缀-断口三角线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0176
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-断口三角线</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#666664}.triangle{--size:284px;--stroke:1.896;--ink:#e3e3df;--rotation:0deg;width:min(var(--size),78vw,61.62vh);aspect-ratio:.79;transform:rotate(var(--rotation))}.triangle svg{display:block;width:100%;height:100%;overflow:visible}.lines{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:butt;stroke-linejoin:miter}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="triangle" data-component-class="decoration" role="img" aria-label="点缀-断口三角线"><svg viewbox="0 0 79 100" xmlns="http://www.w3.org/2000/svg"><g class="lines"><path d="M26.86 30 L39.5 0 L52.14 30"></path><path d="M16.59 62 L0 98 L31.6 98 M47.4 98 L79 98 L64.78 62"></path></g></svg></div></body></html>
````

## 点缀-方框斜箭头

逻辑路径：assets/模板库/点缀/点缀-方框斜箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0152
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-方框斜箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.arrow{--size:260px;--stroke:5.5;--radius:11px;--ink:#343434;width:min(var(--size),82vw,82vh);aspect-ratio:1}.arrow svg{display:block;width:100%;height:100%;fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}.frame{rx:var(--radius);ry:var(--radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="arrow" data-component-class="decoration" role="img" aria-label="点缀-方框斜箭头"><svg viewbox="0 0 100 100" preserveaspectratio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><rect class="frame" x="3" y="3" width="94" height="94" rx="11"></rect><path d="M29 70 L70 29 M35 29 H70 V65"></path></svg></div></body></html>
````

## 点缀-曲线路径箭头

逻辑路径：assets/模板库/点缀/点缀-曲线路径箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0207
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-曲线路径箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.routes{--size:800px;--stroke:3;--dot-gap:28;--dash-length:10;--dash-gap:18;--ink:#555553;--icon-fill:#424240;--icon-cutout:#eeeeec;--arrow-scale:1;width:min(var(--size),88vw,137.5vh);aspect-ratio:1.5625}.routes svg{width:100%;height:100%;display:block}.route{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round}.dots{stroke-dasharray:0 var(--dot-gap)}.dashes{stroke-dasharray:var(--dash-length) var(--dash-gap)}.segments{stroke-dasharray:52 26}.heads{fill:none;stroke:transparent;stroke-width:var(--stroke)}.transport{fill:var(--icon-fill)}.cutout{fill:var(--icon-cutout)}.small-head{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round;transform:scale(var(--arrow-scale))}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="routes" data-component-class="decoration" role="img" aria-label="点缀-曲线路径箭头"><svg viewbox="0 0 1000 640" xmlns="http://www.w3.org/2000/svg"><defs><marker id="route-arrow" viewbox="0 0 30 30" refx="25" refy="15" markerwidth="30" markerheight="30" markerunits="userSpaceOnUse" orient="auto"><path d="M5 5 L25 15 L5 25" fill="none" stroke="var(--ink)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path></marker><path id="car-route" d="M55 158 C155 158 155 54 285 54 C435 54 420 168 585 168 C755 168 760 72 944 72"></path><path id="boat-route" d="M58 327 C195 240 288 393 438 335 C554 290 529 238 655 249 C781 260 791 369 943 314"></path><path id="plane-route" d="M57 563 C237 567 245 444 421 449 C572 453 548 595 711 581 C840 570 821 451 944 457"></path><symbol id="car" viewbox="0 0 100 60"><path d="M4 34 L10 24 L25 22 L37 6 Q40 3 45 3 H65 Q70 3 73 8 L83 24 L94 29 Q98 31 98 36 V47 H3 V38 Z"></path><path class="cutout" d="M32 23 L42 10 H51 V23 Z M57 10 H65 L74 23 H57 Z"></path><circle cx="23" cy="46" r="12"></circle><circle cx="77" cy="46" r="12"></circle><circle class="cutout" cx="23" cy="46" r="5"></circle><circle class="cutout" cx="77" cy="46" r="5"></circle></symbol><symbol id="boat" viewbox="0 0 100 100"><path d="M10 72 H95 L79 93 H30 Z M50 6 H54 V69 H50 Z M45 14 V65 H7 Z M60 23 L92 65 H60 Z"></path></symbol><symbol id="plane" viewbox="0 0 100 100"><path d="M96 46 Q104 50 96 54 L66 59 L42 91 L29 93 L43 61 L19 64 L8 77 L1 77 L7 53 L1 29 L8 29 L19 42 L43 40 L29 8 L42 10 L66 41 Z"></path></symbol></defs><g class="route"><use href="#car-route" class="dots"></use><use href="#boat-route" class="dashes"></use><use href="#plane-route" class="segments"></use></g><g class="heads"><use href="#car-route" marker-end="url(#route-arrow)"></use><use href="#boat-route" marker-end="url(#route-arrow)"></use><use href="#plane-route" marker-end="url(#route-arrow)"></use><g transform="translate(253 492) rotate(-31)"><path class="small-head" d="M-17 -10 L0 0 L-17 10"></path></g><g transform="translate(544 509) rotate(59)"><path class="small-head" d="M-17 -10 L0 0 L-17 10"></path></g><g transform="translate(816 520) rotate(-58)"><path class="small-head" d="M-17 -10 L0 0 L-17 10"></path></g></g><g class="transport"><g transform="translate(285 54) rotate(0)"><use href="#car" x="-45" y="-45" width="90" height="54"></use></g><g transform="translate(653 249) rotate(5)"><use href="#boat" x="-43" y="-74" width="86" height="86"></use></g><g transform="translate(706 581) rotate(-5)"><use href="#plane" x="-47" y="-47" width="94" height="94"></use></g></g></svg></div></body></html>
````

## 点缀-果冠圆章

逻辑路径：assets/模板库/点缀/点缀-果冠圆章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0108
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-果冠圆章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#f5f5f5}.badge{--size:460px;--rotation:-15deg;--badge-fill:#d4d4d4;--ink:#303030;width:min(var(--size),68vw,76.16vh);aspect-ratio:1.12;transform:rotate(var(--rotation))}.badge svg{display:block;width:100%;height:100%;overflow:visible}.silhouette{fill:var(--badge-fill);stroke:none}.copy{fill:var(--ink);font-family:ui-rounded,'Arial Rounded MT Bold','Microsoft YaHei',sans-serif;font-size:231.84px;font-weight:800;letter-spacing:-.03em;text-anchor:middle}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg viewbox="0 0 1120 1000" role="img" aria-label="点缀-果冠圆章"><g class="silhouette"><path id="badge-base" d="M454 140C704 136 904 305 918 552C932 801 739 992 480 1000C218 1000 8 832 0 578C-1 326 183 145 454 140Z"></path><path id="badge-crown" d="M661 401C709 315 746 204 759 105L832 228L903 0L948 186L1084 40L1033 246L1120 207L1044 360L1091 363C1004 446 893 497 782 530Z"></path></g><text id="badge-copy" class="copy" dominant-baseline="central"><tspan x="464.8" y="438.4">说明文字</tspan><tspan x="464.8" y="651.6">说明文字</tspan></text></svg></div></body></html>
````

## 点缀-果形徽章

逻辑路径：assets/模板库/点缀/点缀-果形徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0107
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-果形徽章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#f5f5f5}.badge{--size:470px;--rotation:-15deg;--fruit-fill:#cacaca;--ink:#292929;width:min(var(--size),68vw,78.2vh);aspect-ratio:1.15;transform:rotate(var(--rotation))}.badge svg{display:block;width:100%;height:100%}.fruit{fill:var(--fruit-fill);stroke:none}text{fill:var(--ink);font-family:ui-rounded,'Arial Rounded MT Bold','Microsoft YaHei',sans-serif;text-anchor:middle;dominant-baseline:central}.name{font-size:276px;font-weight:800;letter-spacing:0}.tagline{font-size:161px;font-weight:700;letter-spacing:0}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg viewbox="0 0 1150 1000" role="img" aria-label="点缀-果形徽章"><path id="badge-crown" class="fruit" d="M724.5 433C770 328 785 239 786 140L861 245L914 20L958 195L1083 67L1047 263L1127 239C1093 351 993 452 862 540Z"></path><path id="badge-body" class="fruit" d="M387 174C543 133 716 184 825 293C937 405 957 584 906 707C844 858 671 954 502 960C310 964 133 874 64 720C-7 560 50 365 188 253C248 204 319 178 387 174Z"></path><text id="badge-name" class="name" x="523.25" y="475">标签</text><text id="badge-tagline" class="tagline" x="540.5" y="695">标题文字</text></svg></div></body></html>
````

## 点缀-格纹蝴蝶结

逻辑路径：assets/模板库/点缀/点缀-格纹蝴蝶结.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0198
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-格纹蝴蝶结</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#f5f5f5}.bow{--size:430px;--cloth:#e8e8e8;--stripe-color:#777;--stripe-width:12.8px;--stripe-opacity:.36;--stroke-width:3.2px;--outline:#444;--crease-opacity:.48;width:min(var(--size),84vw,84vh);aspect-ratio:1}.bow svg{display:block;width:100%;height:100%;overflow:visible}.stripe{stroke:var(--stripe-color);stroke-width:var(--stripe-width);opacity:var(--stripe-opacity)}.piece{stroke:var(--outline);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}.crease{fill:none;stroke:var(--outline);stroke-width:2;opacity:var(--crease-opacity);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="bow" data-component-class="decoration"><svg viewbox="0 0 400 400" role="img" aria-label="点缀-格纹蝴蝶结"><defs><pattern id="gingham" width="34" height="34" patternunits="userSpaceOnUse"><rect width="34" height="34" fill="var(--cloth)"></rect><path class="stripe" d="M17 0V34"></path><path class="stripe" d="M0 17H34"></path></pattern><pattern id="tail-left" href="#gingham" patterntransform="rotate(12) skewX(-7)"></pattern><pattern id="tail-right" href="#gingham" patterntransform="rotate(-13) skewX(8)"></pattern><pattern id="loop-left" href="#gingham" patterntransform="rotate(-8) skewY(7)"></pattern><pattern id="loop-right" href="#gingham" patterntransform="rotate(9) skewY(-6)"></pattern><pattern id="knot-pattern" href="#gingham" patterntransform="rotate(3) scale(.85 1.06)"></pattern></defs><g id="bow-tail"><path class="piece" fill="url(#tail-left)" d="M173 160C161 197 130 231 110 276C92 315 73 351 64 382L112 363L139 400C154 350 179 311 188 261C195 226 205 196 209 169Z"></path><path class="piece" fill="url(#tail-right)" d="M207 162C223 203 246 231 269 269C300 319 326 350 344 380L297 365L278 400C250 366 226 332 211 293C195 252 186 215 185 173Z"></path><path class="crease" d="M177 190C162 240 140 294 116 342M216 194C230 247 261 311 288 344"></path></g><g id="bow-loops"><path class="piece" fill="url(#loop-left)" d="M181 111C139 74 63 19 31 20C9 21 1 50 1.6 83C2 132 14 184 38 205C57 222 102 205 135 185L188 157C175 145 175 127 181 111Z"></path><path class="piece" fill="url(#loop-right)" d="M218 111C262 72 337 21 370 20C391 20 400 51 398.4 86C397 137 386 184 363 205C343 222 299 204 266 185L212 156C225 143 226 127 218 111Z"></path><path class="crease" d="M38 48C74 76 133 111 172 129M41 188C86 174 132 151 172 145M365 48C325 79 266 113 230 130M360 190C313 170 268 150 230 146"></path><path d="M166 113L188 127L188 158L151 178C165 157 171 137 166 113ZM234 113L212 127L212 158L250 178C235 155 229 136 234 113Z" fill="#333" opacity=".12"></path></g><g id="bow-knot"><path class="piece" fill="url(#knot-pattern)" d="M180 92C192 96 209 96 221 93C231 112 232 133 230 153C229 164 226 174 218 180C205 175 191 175 178 179C170 166 168 151 168 136C168 117 172 101 180 92Z"></path><path class="crease" d="M182 103C177 124 178 150 183 168M218 104C223 126 222 149 217 169"></path></g></svg></div></body></html>
````

## 点缀-棋盘条

逻辑路径：assets/模板库/点缀/点缀-棋盘条.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0158
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-棋盘条</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#ededed}.checker{--size:630px;--cell-fill:#494949;--cell-opacity:1;width:min(var(--size),88vw,360vh);aspect-ratio:4.5}.checker svg{display:block;width:100%;height:100%;fill:var(--cell-fill);opacity:var(--cell-opacity);shape-rendering:crispEdges}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="checker" data-component-class="decoration"><svg viewbox="0 0 450 100" role="img" aria-label="点缀-棋盘条"><g id="checker-cells"><path d="M0 0H50V50H0ZM100 0H150V50H100ZM200 0H250V50H200ZM300 0H350V50H300ZM400 0H450V50H400ZM50 50H100V100H50ZM150 50H200V100H150ZM250 50H300V100H250ZM350 50H400V100H350Z"></path></g></svg></div></body></html>
````

## 点缀-椭圆文字章

逻辑路径：assets/模板库/点缀/点缀-椭圆文字章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0132
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-椭圆文字章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#eee}.stamp{--size:550px;--ink:#303030;--stroke-width:26.4px;--word-size:136.125px;width:min(var(--size),86vw,220vh);aspect-ratio:2.75}.stamp svg{display:block;width:100%;height:100%}.ring{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}.word{fill:var(--ink);font-family:ui-rounded,'Arial Rounded MT Bold','Microsoft YaHei',sans-serif;font-size:var(--word-size);font-weight:800;letter-spacing:.04em;text-anchor:middle;dominant-baseline:central}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="stamp" data-component-class="decoration"><svg viewbox="0 0 825 300" role="img" aria-label="点缀-椭圆文字章"><path id="badge-ring" class="ring" d="M810 147C814 222 628 286 415 284C201 294 19 234 15 158C8 81 179 20 397 16C615 7 798 65 810 147Z"></path><text id="badge-word" class="word" x="412.5" y="153">标签</text></svg></div></body></html>
````

## 点缀-横向球网

逻辑路径：assets/模板库/点缀/点缀-横向球网.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0174
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-横向球网</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;overflow:hidden;background:#f2f2f2}.net{--size:828px;--net-base:#535353;--grid-color:#dedede;--grid-step:15.4px;--grid-line:1.8px;--grid-opacity:.8;--band-fill:#bcbcbc;--outline:#303030;--outline-width:6px;--corner-radius:0px;width:min(var(--size),90vw,331.2vh);aspect-ratio:4.14;container-type:inline-size}.net svg{display:block;width:100%;height:100%}.grid-fill{width:100%;height:100%;opacity:var(--grid-opacity);background-image:linear-gradient(to right,var(--grid-color) var(--grid-line),transparent var(--grid-line)),linear-gradient(to bottom,var(--grid-color) var(--grid-line),transparent var(--grid-line));background-size:var(--grid-step) var(--grid-step)}.outline{fill:none;stroke:var(--outline);stroke-width:var(--outline-width);rx:var(--corner-radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="net" data-component-class="decoration"><svg viewbox="0 0 828 200" role="img" aria-label="点缀-横向球网"><defs><clippath id="grid-mask"><rect x="8.28" y="24" width="811.44" height="170"></rect></clippath></defs><rect id="net-base" width="828" height="200" fill="var(--net-base)"></rect><g id="net-grid" clip-path="url(#grid-mask)"><foreignobject x="8.28" y="24" width="811.44" height="170"><div xmlns="http://www.w3.org/1999/xhtml" class="grid-fill"></div></foreignobject></g><rect id="top-band" x="8.28" y="6" width="811.44" height="20" fill="var(--band-fill)"></rect><rect id="outer-line" class="outline" x="3" y="3" width="822" height="194"></rect></svg></div></body></html>
````

## 点缀-水彩云日贴纸

逻辑路径：assets/模板库/点缀/点缀-水彩云日贴纸.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0065
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-水彩云日贴纸</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e7e7e7}.weather{--size:580px;--border-width:20.8px;--border-round:round;--shadow-x:2.9px;--shadow-y:4.6px;--shadow-blur:3.5px;--shadow-alpha:.16;width:min(var(--size),88vw,127.6vh);aspect-ratio:1.45}.weather svg{display:block;width:100%;height:100%;overflow:visible}.paper{fill:#fff;stroke:#fff;stroke-width:var(--border-width);stroke-linejoin:var(--border-round)}.shadow{filter:drop-shadow(var(--shadow-x) var(--shadow-y) var(--shadow-blur) rgb(0 0 0 / var(--shadow-alpha)))}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="weather" data-component-class="decoration" data-role="内容层"><svg viewbox="0 0 580 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-水彩云日贴纸"><defs><radialgradient id="sun"><stop stop-color="#d0d0d0"></stop><stop offset=".62" stop-color="#bcbcbc"></stop><stop offset="1" stop-color="#a4a4a4" stop-opacity=".78"></stop></radialgradient><lineargradient id="cloud" x1="0" y1="0" x2=".15" y2="1"><stop stop-color="#fafafa"></stop><stop offset=".48" stop-color="#e9e9e9"></stop><stop offset="1" stop-color="#bdbdbd"></stop></lineargradient><radialgradient id="wash"><stop stop-color="#999" stop-opacity=".28"></stop><stop offset="1" stop-color="#999" stop-opacity="0"></stop></radialgradient><filter id="edge" x="-8%" y="-8%" width="116%" height="116%"><feturbulence type="fractalNoise" basefrequency=".046" numoctaves="3" seed="11" result="noise"></feturbulence><fedisplacementmap in="SourceGraphic" in2="noise" scale="3.6" xchannelselector="R" ychannelselector="G"></fedisplacementmap></filter><filter id="pigment" x="-5%" y="-5%" width="110%" height="110%"><feturbulence type="fractalNoise" basefrequency=".12" numoctaves="3" seed="9" result="n"></feturbulence><fecolormatrix in="n" type="saturate" values="0"></fecolormatrix><fecomponenttransfer><fefunca type="linear" slope=".16"></fefunca></fecomponenttransfer><fecomposite in2="SourceGraphic" operator="in" result="grain"></fecomposite><feblend in="SourceGraphic" in2="grain" mode="multiply"></feblend></filter><path id="sun-shape" d="M300 148C293 117 300 80 322 55C341 32 375 24 404 29C438 31 467 48 481 76C496 101 496 135 483 160C470 192 442 212 410 217C366 223 314 193 300 148Z"></path><path id="cloud-shape" d="M75 213C49 204 27 223 26 247C18 269 38 289 58 296C52 319 76 340 102 339C125 358 156 354 177 346C201 365 230 362 253 351C284 366 315 362 335 352C363 366 393 359 409 347C437 357 466 343 475 329C505 332 540 316 548 291C563 269 550 236 526 226C533 197 510 174 483 172C471 139 434 130 407 145C391 118 356 106 327 121C296 105 257 117 243 143C216 130 184 144 172 166C137 154 102 172 98 200C89 201 80 205 75 213Z"></path><clippath id="cloud-clip"><use href="#cloud-shape"></use></clippath></defs><g class="shadow"><g filter="url(#edge)" class="paper"><use href="#sun-shape"></use><use href="#cloud-shape"></use></g></g><g filter="url(#edge)"><g filter="url(#pigment)"><use href="#sun-shape" fill="url(#sun)"></use><path d="M324 85C346 44 408 33 443 67C412 44 359 58 338 94Z" fill="#f6f6f6" opacity=".27"></path><use href="#cloud-shape" fill="url(#cloud)"></use><g clip-path="url(#cloud-clip)"><ellipse cx="155" cy="281" rx="135" ry="65" fill="url(#wash)"></ellipse><ellipse cx="371" cy="297" rx="159" ry="65" fill="url(#wash)"></ellipse><path d="M43 277C80 300 107 287 133 302S189 330 226 310S293 332 326 309S408 318 445 293S511 299 549 274" fill="none" stroke="#aaa" stroke-width="13" opacity=".1"></path><ellipse cx="281" cy="197" rx="120" ry="52" fill="#fff" opacity=".18"></ellipse><path d="M103 236C100 186 153 167 181 193M244 174C260 143 298 133 326 150M421 190C451 165 478 181 485 204" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".17"></path></g></g></g></svg></div></body></html>
````

## 点缀-水果徽章

逻辑路径：assets/模板库/点缀/点缀-水果徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0109
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-水果徽章</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#ededed}.badge{--size:400px;--rotation:-12deg;--fruit:#cdcdcd;--ink:#454545;--stroke-width:0px;--round:round;width:min(var(--size),82vw,82vh);aspect-ratio:1}.badge svg{display:block;width:100%;height:100%;overflow:visible}.fruit-group{transform:rotate(var(--rotation));transform-origin:200px 200px}.silhouette{fill:var(--fruit);stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linejoin:var(--round)}text{font-family:ui-rounded,'Arial Rounded MT Bold','Microsoft YaHei',sans-serif;font-weight:700;text-anchor:middle;fill:var(--ink)}.brand{font-size:92px;letter-spacing:-.03em}.tagline{font-size:56px}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="-30 -30 460 460" role="img" aria-label="点缀-水果徽章"><g class="fruit-group"><path class="silhouette" d="M190 108C161 76 109 75 74 96C37 118 20 160 20 211C19 269 47 335 93 366C121 386 165 388 201 374C253 354 298 304 314 252C325 217 320 181 299 157C321 151 345 156 371 168L345 120L388 87L326 89L337 20L284 68L260 8L238 83L197 43L204 110L184 87Z"></path><text class="brand" data-role="内容层" x="172" y="232" textlength="264" lengthadjust="spacingAndGlyphs">说明文字</text><text class="tagline" data-role="内容层" x="178" y="305" textlength="220" lengthadjust="spacingAndGlyphs">说明文字</text></g></svg></div></body></html>
````

## 点缀-水果表情角色

逻辑路径：assets/模板库/点缀/点缀-水果表情角色.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0110
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-水果表情角色</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e9e9e9}.character{--size:335px;--stroke:7px;--ink:#363636;--fruit:#bcbcbc;--leaf:#797979;--face:#f3f3f3;--round:round;width:min(var(--size),80vw,56.3vh);aspect-ratio:.67}.character svg{width:100%;height:100%;display:block;overflow:visible}.line{stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:var(--round);stroke-linejoin:var(--round)}.detail{stroke-width:calc(var(--stroke)*.78)}.body{fill:var(--fruit)}.leaf{fill:var(--leaf)}.skin{fill:var(--face)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="character" data-component-class="decoration" data-role="内容层"><svg xmlns="http://www.w3.org/2000/svg" viewbox="-6 -7 347 518" role="img" aria-label="点缀-水果表情角色"><g class="line"><g id="character-body"><path class="body" d="M82 169C39 180 9 222 5 273C-1 325 13 388 53 423L55 458C44 470 50 483 72 484C94 486 105 475 107 450C137 463 174 465 207 455C217 483 229 491 250 483C271 475 269 461 250 450L246 434C292 409 323 361 329 311C337 253 313 204 267 178C217 150 136 151 82 169Z"></path><g fill="none" opacity=".52" class="detail"><path d="M43 260l10 10 10-10M25 300l10 10 10-10M28 348l11 10 9-9M48 388l10 9 10-10M111 408l10 10 10-10M151 432l10 9 10-10M195 409l10 9 10-10M275 386l9 9 10-10M304 343l8 9 9-9M300 263l9 9 9-9"></path></g></g><g id="character-crown"><path class="leaf" d="M77 192C67 169 42 161 35 124L87 142C57 113 47 72 43 42C72 55 95 76 118 101C114 64 127 34 145 6C160 37 174 72 177 102C190 62 218 25 247 12C247 52 237 88 222 116C247 95 276 75 306 73C293 109 277 136 253 155L292 151C278 177 253 190 228 194C176 179 125 179 77 192Z"></path><path class="detail" fill="none" d="M88 142L117 164M145 49C143 92 153 128 163 163M240 53C218 95 205 130 201 159M273 114L236 151"></path></g><g id="character-face"><path class="skin" stroke="none" d="M104 220C130 196 160 200 181 205C217 188 259 202 281 229C296 252 298 291 278 322C259 351 221 368 181 365C135 365 99 344 86 308C73 274 80 241 104 220Z"></path><path fill="none" class="detail" d="M112 235Q128 220 145 229M222 228Q242 216 257 235"></path><path fill="none" d="M117 267Q131 246 146 266M221 265Q237 243 253 263"></path><ellipse cx="111" cy="295" rx="20" ry="12" fill="#b1b1b1" stroke="none"></ellipse><ellipse cx="264" cy="294" rx="21" ry="12" fill="#b1b1b1" stroke="none"></ellipse><path d="M154 286Q185 305 218 283C221 317 207 344 189 345C170 346 155 320 154 286Z" fill="#454545"></path><path d="M173 331Q189 310 210 326Q201 344 190 344Q180 343 173 331Z" fill="#aaa" stroke="none"></path><path d="M165 293Q185 303 207 291L204 301Q184 311 168 302Z" fill="#fff" stroke="none"></path></g><g id="character-hands"><path class="skin" d="M108 415C94 408 84 391 76 373C69 358 65 338 72 325C78 317 88 325 93 337C83 314 87 301 96 303C105 304 111 324 114 333C105 312 111 298 120 304C130 311 134 334 140 348C149 363 154 380 146 394C140 408 124 423 108 415Z"></path><path class="skin" d="M256 415C276 407 289 389 298 369C306 352 310 333 303 325C295 317 286 331 282 341C293 314 288 301 279 305C270 309 265 326 262 336C267 313 259 300 251 307C243 315 240 335 234 350C225 365 218 383 225 395C232 410 243 420 256 415Z"></path><path class="detail" fill="none" d="M94 348Q99 361 108 369M116 345Q118 358 126 366M279 351Q274 364 267 371M258 348Q255 360 249 367"></path></g></g></svg></div></body></html>
````

## 点缀-波边认证章

逻辑路径：assets/模板库/点缀/点缀-波边认证章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0067
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-波边认证章</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e7e7e7}.seal{--size:430px;--rim-stroke:4.8px;--fine-stroke:1.2px;--round:round;--shadow-blur:14px;--shadow-opacity:.18;--ink:#4b4b4b;width:min(var(--size),80vw,80vh);aspect-ratio:1}.seal svg{width:100%;height:100%;display:block;overflow:visible}.rim{stroke:#a3a3a3;stroke-width:var(--rim-stroke);stroke-linejoin:var(--round)}.shadow{filter:drop-shadow(0 5px var(--shadow-blur) rgb(0 0 0 / var(--shadow-opacity)))}.fine{fill:none;stroke-width:var(--fine-stroke)}text{font-family:'Microsoft YaHei',Arial,sans-serif;fill:var(--ink);text-anchor:middle}.ring-text{font-size:25.2px;font-weight:500}.main-text{font-size:80px;font-weight:700}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="seal" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="-14 -14 428 428" role="img" aria-label="点缀-波边认证章"><defs><lineargradient id="metal" x1=".15" y1="0" x2=".9" y2="1"><stop stop-color="#818181"></stop><stop offset=".13" stop-color="#f7f7f7"></stop><stop offset=".29" stop-color="#b6b6b6"></stop><stop offset=".48" stop-color="#f0f0f0"></stop><stop offset=".67" stop-color="#a1a1a1"></stop><stop offset=".83" stop-color="#d9d9d9"></stop><stop offset="1" stop-color="#8d8d8d"></stop></lineargradient><lineargradient id="band" x1="0" y1="0" x2=".75" y2="1"><stop stop-color="#f8f8f8"></stop><stop offset=".55" stop-color="#d4d4d4"></stop><stop offset="1" stop-color="#b8b8b8"></stop></lineargradient><radialgradient id="disc" cx=".35" cy=".25" r=".85"><stop stop-color="#f3f3f3"></stop><stop offset=".7" stop-color="#dedede"></stop><stop offset="1" stop-color="#c1c1c1"></stop></radialgradient><path id="wave" d="M200 5C225.5 5 247.4 23.7 269.3 32.8C291.2 41.9 319.9 44.1 337.9 62.1C355.9 80.1 358.1 108.8 367.2 130.7C376.3 152.6 395 174.5 395 200C395 225.5 376.3 247.4 367.2 269.3C358.1 291.2 355.9 319.9 337.9 337.9C319.9 355.9 291.2 358.1 269.3 367.2C247.4 376.3 225.5 395 200 395C174.5 395 152.6 376.3 130.7 367.2C108.8 358.1 80.1 355.9 62.1 337.9C44.1 319.9 41.9 291.2 32.8 269.3C23.7 247.4 5 225.5 5 200C5 174.5 23.7 152.6 32.8 130.7C41.9 108.8 44.1 80.1 62.1 62.1C80.1 44.1 108.8 41.9 130.7 32.8C152.6 23.7 174.5 5 200 5Z"></path><path id="ring-path" d="M200 43A157 157 0 1 1 200 357A157 157 0 1 1 200 43"></path></defs><g class="shadow"><use href="#wave" fill="url(#metal)" class="rim"></use></g><g id="seal-rim"><use href="#wave" fill="url(#metal)" class="rim"></use><use href="#wave" transform="translate(200 200) scale(.967) translate(-200 -200)" class="fine" stroke="#fff" opacity=".9"></use><use href="#wave" transform="translate(200 200) scale(.93) translate(-200 -200)" fill="url(#band)" stroke="#8f8f8f" stroke-width="1.2"></use><circle cx="200" cy="200" r="178" class="fine" stroke="#fff" opacity=".8"></circle></g><g id="seal-disc"><circle cx="200" cy="200" r="140" fill="url(#disc)" stroke="#929292" stroke-width="1.8"></circle><circle cx="200" cy="200" r="136.5" class="fine" stroke="#fff" opacity=".8"></circle></g><text class="ring-text" data-role="内容层"><textpath href="#ring-path" startoffset="50%" textlength="925" lengthadjust="spacing">说明文字</textpath></text><text class="main-text" data-role="内容层" x="200" y="189"><tspan x="200">说明文字</tspan><tspan x="200" dy="80">说明文字</tspan></text></svg></div></body></html>
````

## 点缀-液滴徽章

逻辑路径：assets/模板库/点缀/点缀-液滴徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0057
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-液滴徽章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.drop{--size:320px;--stroke:1;--highlight-alpha:.75;--label-shadow-alpha:.5;--label-shadow-blur:2.56px;width:min(var(--size),80vw,calc(82vh * .8));aspect-ratio:.8}svg{display:block;width:100%;height:100%;overflow:visible;font-family:Arial,'Microsoft YaHei',sans-serif}.highlight{opacity:var(--highlight-alpha)}.emphasis-shadow{opacity:var(--label-shadow-alpha);filter:blur(var(--label-shadow-blur))}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="drop" data-component-class="decoration"><svg viewbox="-16 -12 352 440" role="img" aria-label="点缀-液滴徽章"><defs><lineargradient id="liquid" x1=".1" y1=".1" x2=".85" y2="1"><stop stop-color="#aaa"></stop><stop offset=".34" stop-color="#858585"></stop><stop offset=".72" stop-color="#666"></stop><stop offset="1" stop-color="#484848"></stop></lineargradient><lineargradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff" stop-opacity=".1"></stop><stop offset=".45" stop-color="#fff"></stop><stop offset="1" stop-color="#fff" stop-opacity=".15"></stop></lineargradient></defs><g id="drop-body"><path transform="scale(320 400)" d="M .50 0 C .72 .03 1 .47 1 .67 C 1 1 .58 1.08 .28 .96 C -.12 .82 -.02 .54 .13 .28 C .25 .08 .36 0 .50 0 Z" fill="url(#liquid)" stroke="#666" vector-effect="non-scaling-stroke" style="stroke-width:var(--stroke)"></path></g><g id="drop-highlight" class="highlight"><path d="M42 193 C15 251 27 320 73 352 C98 370 128 378 159 377 C121 367 97 355 77 334 C43 300 35 249 42 193Z" fill="url(#shine)"></path></g><g id="drop-label" text-anchor="middle" fill="#f5f5f5"><text x="160" y="190" font-size="36" font-weight="400" data-role="内容层">说明文字</text><text x="160" y="271" font-size="67.2" font-weight="800" data-slot="label-1" data-role="标签槽" style="filter:drop-shadow(3.84px 5.76px 2.56px rgb(0 0 0 / var(--label-shadow-alpha)))">标签</text></g></svg></div></body></html>
````

## 点缀-照片衬纸与胶带

逻辑路径：assets/模板库/点缀/点缀-照片衬纸与胶带.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-照片衬纸与胶带</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-collage { display:grid; grid-template-columns:repeat(var(--vl-collage-columns,12),minmax(0,1fr)); gap:var(--vl-collage-gap,12px); padding:var(--vl-collage-inset,24px); isolation:isolate; }
.vl-collage__item { position:relative; min-width:0; grid-column:var(--vl-col-start,auto)/span var(--vl-col-span,6); grid-row:var(--vl-row-start,auto)/span var(--vl-row-span,1); z-index:var(--vl-stack-order,0); transform:translate(var(--vl-shift-x,0px),var(--vl-shift-y,0px)) rotate(var(--vl-rotate,0deg)); transform-origin:center; overflow-wrap:anywhere; }
:where(.vl-collage__item img) { display:block; max-width:100%; height:auto; }

.vl-paper-mount { position:relative; margin:0; padding:var(--vl-paper-pad,8px) var(--vl-paper-pad,8px) var(--vl-paper-footer,28px); background:var(--vl-tint,transparent); color:var(--vl-ink,#342c23); }
.vl-paper-mount > img { display:block; width:100%; height:auto; }
.vl-paper-mount__tape { position:absolute; z-index:2; left:var(--vl-tape-x,50%); top:var(--vl-tape-y,0px); width:var(--vl-tape-width,64px); height:var(--vl-tape-height,20px); background:var(--vl-tape-color,#e6d2a4); opacity:var(--vl-tape-alpha,.72); transform:translate(-50%,-50%) rotate(var(--vl-tape-angle,-8deg)); pointer-events:none; }
</style></head><body><figure class="vl-paper-mount"><span class="vl-paper-mount__tape" aria-hidden="true"></span><img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiB2aWV3Qm94PSIwIDAgNDAwIDMwMCI+PHJlY3Qgd2lkdGg9IjQwMCIgaGVpZ2h0PSIzMDAiIGZpbGw9IiNlOGU2ZTEiLz48cmVjdCB4PSI0IiB5PSI0IiB3aWR0aD0iMzkyIiBoZWlnaHQ9IjI5MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYTQ5Zjk1IiBzdHJva2UtZGFzaGFycmF5PSI4IDgiLz48cGF0aCBkPSJNMTQwIDEwMGgxMjB2NzVIMTQweiBNMTQ4IDE2NWwyOC0zMiAyNiAxOCAyNi0yMiAyNCAzNiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTI4ZDgzIiBzdHJva2Utd2lkdGg9IjMiLz48dGV4dCB4PSIyMDAiIHk9IjIxMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NTVmNTUiPklNQUdFIFNMT1Q8L3RleHQ+PHRleHQgeD0iMjAwIiB5PSIyNDAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjNjU1ZjU1Ij7nhafniYfntKDmnZA8L3RleHQ+PC9zdmc+" alt="照片说明"><figcaption>简短注释</figcaption></figure>
</body></html>
````

## 点缀-环字徽章

逻辑路径：assets/模板库/点缀/点缀-环字徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0146
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-环字徽章</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#efefed}.badge{--size:400px;--stroke:2.4;--inner-stroke:3;--disc:#575757;--center:#d7d7d7;--ink:#f5f5f2;--art-stroke:3.5;width:min(var(--size),84vw,84vh);aspect-ratio:1}svg{display:block;width:100%;height:100%;font-family:'Arial Rounded MT Bold','Trebuchet MS',Arial,sans-serif}.art{stroke:#414141;stroke-width:var(--art-stroke);stroke-linejoin:round;stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="badge" data-component-class="decoration"><svg viewbox="0 0 400 400" role="img" aria-label="点缀-环字徽章"><defs><path id="circular-copy" d="M200 364 A164 164 0 1 1 200 36 A164 164 0 1 1 200 364"></path></defs><g id="badge-disc" data-role="内容层"><circle cx="200" cy="200" r="198.8" style="fill:var(--disc);stroke:#373737;stroke-width:var(--stroke)"></circle><circle cx="200" cy="200" r="192.5" fill="none" stroke="#fff" stroke-opacity=".23" stroke-width="1"></circle></g><g id="badge-center"><circle cx="200" cy="200" r="132" style="fill:var(--center);stroke:#333;stroke-width:var(--inner-stroke)"></circle><circle cx="200" cy="200" r="125" fill="none" stroke="#f9f9f9" stroke-width="1.5"></circle></g><g id="badge-art" class="art" data-role="内容槽" aria-label="通用内容槽" data-slot="content-1"><path d="M200 103L224 166L291 169L239 211L257 276L200 239L143 276L161 211L109 169L176 166Z" fill="#9b9b9b" stroke="#414141" stroke-width="5" stroke-linejoin="round"></path></g><g id="badge-copy" data-role="内容层"><text font-size="35.2" font-weight="500" letter-spacing="1.408" text-anchor="middle" style="fill:var(--ink)"><textpath href="#circular-copy" startoffset="50%">说明文字</textpath></text></g></svg></div></body></html>
````

## 点缀-短铅笔

逻辑路径：assets/模板库/点缀/点缀-短铅笔.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0215
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-短铅笔</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#eeeeec}.pencil{--size:740px;--stroke:1.5;--radius:23px;--shadow-blur:13.32px;--shadow-opacity:.15;width:min(var(--size),86vw,calc(76vh * 3.7));aspect-ratio:3.7}svg{display:block;width:100%;height:100%;overflow:visible;font-family:Arial,sans-serif}.shadow{filter:blur(var(--shadow-blur));opacity:var(--shadow-opacity)}.eraser{rx:var(--radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="pencil" data-component-class="decoration"><svg viewbox="0 0 740 200" role="img" aria-label="点缀-短铅笔"><defs><lineargradient id="rubber" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#b4b4b4"></stop><stop offset=".2" stop-color="#d3d3d3"></stop><stop offset=".69" stop-color="#b6b6b6"></stop><stop offset="1" stop-color="#919191"></stop></lineargradient><lineargradient id="ferrule" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#717171"></stop><stop offset=".09" stop-color="#ddd"></stop><stop offset=".24" stop-color="#fafafa"></stop><stop offset=".36" stop-color="#b0b0b0"></stop><stop offset=".64" stop-color="#c6c6c6"></stop><stop offset=".82" stop-color="#7a7a7a"></stop><stop offset=".94" stop-color="#b8b8b8"></stop><stop offset="1" stop-color="#666"></stop></lineargradient><lineargradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#e0e0db"></stop><stop offset=".55" stop-color="#c4c4be"></stop><stop offset="1" stop-color="#aaa9a4"></stop></lineargradient><path id="silhouette" d="M23 8 H104 V0 H237 V16 H666 L740 100 L666 184 H237 V200 H104 V192 H23 Q0 192 0 169 V31 Q0 8 23 8Z"></path></defs><g id="pencil-shadow" transform="translate(0 8.88)" class="shadow"><use href="#silhouette" fill="#000"></use></g><g id="pencil-body"><path d="M236.8 16 H666 L673.4 26 V174 L666 184 H236.8Z" fill="#888" stroke="#696969" style="stroke-width:var(--stroke)"></path><path d="M236.8 16 H666 L671 55 H236.8Z" fill="#a0a0a0"></path><path d="M236.8 55 H671 V145 H236.8Z" fill="#898989"></path><path d="M236.8 145 H671 L666 184 H236.8Z" fill="#747474"></path><path d="M245 55 H666" stroke="#d3d3d3" stroke-opacity=".5" stroke-width="2"></path><path d="M246 145 H666" stroke="#525252" stroke-opacity=".45" stroke-width="1.5"></path></g><g id="pencil-eraser"><rect class="eraser" x="0" y="8" width="111" height="184" rx="23" fill="url(#rubber)"></rect><path d="M20 24 Q10 28 10 44 V153" fill="none" stroke="#eee" stroke-opacity=".35" stroke-width="3"></path><path d="M29 176 H101" stroke="#6d6d6d" stroke-opacity=".18"></path></g><g id="pencil-bands"><path d="M110 0 H231 Q237 0 237 6 V194 Q237 200 231 200 H110 Q104 200 104 194 V6 Q104 0 110 0Z" fill="url(#ferrule)" stroke="#777" style="stroke-width:var(--stroke)"></path><g fill="none"><path d="M116 3 V197 M130 3 V197 M211 3 V197 M225 3 V197" stroke="#626262" stroke-opacity=".64" stroke-width="3"></path><path d="M120 3 V197 M134 3 V197 M215 3 V197 M229 3 V197" stroke="#f3f3f3" stroke-opacity=".75" stroke-width="2"></path><path d="M141 30 H202 M141 173 H202" stroke="#fff" stroke-opacity=".35" stroke-width="2"></path></g><g stroke="#656565" stroke-opacity=".36" stroke-width="2"><path d="M151 83 V118 M164 83 V118 M177 83 V118 M190 83 V118"></path></g></g><g id="pencil-tip"><path d="M666 26 L740 100 L666 174 Q674 156 662 145 Q676 122 663 102 Q676 77 663 56 Q674 43 666 26Z" fill="url(#wood)"></path><path d="M665 56 L734 100 L665 145 L674 102Z" fill="#dbdbd6" opacity=".7"></path><path d="M675 54 L721 96 M679 126 L718 105 M675 144 L713 111" stroke="#92928c" stroke-opacity=".38" stroke-width="1.2"></path><path d="M715 75 L740 100 L715 125 Q721 113 715 101 Q722 90 715 75Z" fill="#363636"></path><path d="M718 84 L740 100 L720 101Z" fill="#5b5b5b"></path></g><g id="pencil-mark"><text x="448" y="123" font-size="62.9" font-weight="800" text-anchor="middle" fill="#f0f0ee" letter-spacing="1" data-role="内容层">说明文字</text></g></svg></div></body></html>
````

## 点缀-票纸小屋

逻辑路径：assets/模板库/点缀/点缀-票纸小屋.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0214
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-票纸小屋</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e9e9e6}.houses{--size:580px;--stroke:.8;--paper-opacity:.95;--shadow-opacity:.15;--shadow-blur:1.5px;width:min(var(--size),86vw,calc(82vh * 1.25));aspect-ratio:1.25}svg{display:block;width:100%;height:100%;overflow:visible;font-family:'Courier New',monospace}.paper{opacity:var(--paper-opacity);filter:drop-shadow(1px 1px var(--shadow-blur) rgb(0 0 0 / var(--shadow-opacity)))}.edge{stroke:#92928c;stroke-opacity:.45;stroke-width:var(--stroke)}.patch{filter:drop-shadow(1px 1px 1px #0002)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="houses" data-component-class="decoration"><svg viewbox="0 0 500 400" role="img" aria-label="点缀-票纸小屋"><defs><pattern id="ticket-light" width="112" height="96" patternunits="userSpaceOnUse"><rect width="112" height="96" fill="#deded7"></rect><path d="M0 6H112 M0 9H112 M9 17V83 M103 17V83 M15 61H96 M15 65H96 M15 81H96" stroke="#85857f" stroke-width=".7" opacity=".5"></path><path d="M0 93H112" stroke="#7c7c76" stroke-width="1.1" stroke-dasharray="2 4"></path><g fill="#71716c" opacity=".75"><text x="16" y="28" font-size="8">SAMPLE TEXT</text><text x="15" y="52" font-size="21" font-weight="700">00.00</text><text x="18" y="76" font-size="6">SAMPLE TEXT</text><text x="16" y="89" font-size="5">SAMPLE TEXT</text></g></pattern><pattern id="ticket-mid" width="102" height="83" patternunits="userSpaceOnUse" patterntransform="rotate(-7)"><rect width="102" height="83" fill="#bdbdb5"></rect><rect x="6" y="7" width="90" height="66" fill="none" stroke="#777770" stroke-width="1"></rect><path d="M9 31H93 M9 52H93 M14 60H85 M14 64H70" stroke="#696963" stroke-width=".6" opacity=".65"></path><g fill="#585852" opacity=".68"><text x="12" y="24" font-size="10">SAMPLE TEXT</text><text x="14" y="46" font-size="13">SAMPLE TEXT</text><text x="14" y="70" font-size="6">SAMPLE TEXT</text></g><path d="M0 79H102" stroke="#6c6c66" stroke-dasharray="2 3"></path></pattern><pattern id="ticket-dark" width="120" height="88" patternunits="userSpaceOnUse" patterntransform="rotate(12)"><rect width="120" height="88" fill="#94948e"></rect><g fill="#343430" opacity=".66"><text x="7" y="18" font-size="7">SAMPLE TEXT</text><text x="4" y="45" font-size="25" font-weight="700">00.00</text><text x="8" y="70" font-size="8">SAMPLE TEXT</text></g><path d="M6 25H114 M6 53H114 M6 57H114 M6 76H114" stroke="#484843" stroke-width=".8" opacity=".7"></path><path d="M1 0V88" stroke="#e2e2d9" stroke-dasharray="3 4" stroke-width="2"></path></pattern><pattern id="grain" width="29" height="31" patternunits="userSpaceOnUse"><path d="M3 6h3 M18 2h2 M22 17h4 M7 25h2 M13 13h1" stroke="#34342e" stroke-width=".5" opacity=".18"></path><path d="M1 17h4 M14 27h5 M22 8h4" stroke="#fff" stroke-width=".8" opacity=".35"></path></pattern><path id="left-wall" d="M17 210 L158 210 L159 245 Q152 249 159 253 L160 351 L151 354 L141 352 L131 356 L120 354 L108 356 L98 353 L86 355 L76 352 L65 355 L53 353 L42 356 L30 352 L18 354Z"></path><path id="middle-wall" d="M183 123 L374 123 L373 398 L362 396 L351 400 L339 397 L328 400 L315 398 L302 400 L290 397 L278 400 L266 398 L254 400 L242 397 L229 400 L216 396 L202 399 L184 397 L184 286 Q191 281 184 276Z"></path><path id="right-wall" d="M385 146 L493 146 L493 237 Q486 241 493 245 L492 365 L481 368 L472 365 L462 368 L452 365 L442 368 L432 365 L422 368 L412 365 L401 368 L386 365Z"></path><path id="left-roof" d="M0 222 L87.5 124 L175 222 L166 224 L157 221 L147 225 L138 222 L128 224 L117 221 L106 224 L96 222 L84 224 L73 221 L62 224 L50 222 L39 224 L28 221 L17 224Z"></path><path id="middle-roof" d="M165 132 L277.5 0 L390 132 L377 134 L365 131 L353 134 L339 131 L326 134 L313 131 L299 134 L285 131 L271 134 L257 131 L243 134 L229 131 L215 134 L201 131 L187 134 L175 131Z"></path><path id="right-roof" d="M375 159 L437.5 76 L500 159 L489 161 L479 158 L468 161 L457 158 L446 161 L435 158 L424 161 L413 158 L402 161 L391 158Z"></path><clippath id="all-paper"><use href="#left-wall"></use><use href="#middle-wall"></use><use href="#right-wall"></use><use href="#left-roof"></use><use href="#middle-roof"></use><use href="#right-roof"></use></clippath></defs><g id="house-paper-bases" data-role="内容层"><use class="paper edge" href="#left-wall" fill="url(#ticket-light)"></use><use class="paper edge" href="#middle-wall" fill="url(#ticket-light)"></use><use class="paper edge" href="#right-wall" fill="url(#ticket-mid)"></use></g><g id="house-paper-roofs"><use class="paper edge" href="#left-roof" fill="url(#ticket-mid)"></use><use class="paper edge" href="#middle-roof" fill="url(#ticket-dark)"></use><use class="paper edge" href="#right-roof" fill="url(#ticket-light)"></use></g><g id="house-small-patches"><g class="patch"><path d="M37 244 L76 247 L74 284 L35 281Z" fill="url(#ticket-dark)"></path><path d="M102 300 L135 299 L134 354 L105 355Z" fill="url(#ticket-mid)"></path><path d="M211 192 L255 195 L253 251 L211 249Z" fill="url(#ticket-mid)"></path><path d="M300 194 L342 191 L344 247 L302 250Z" fill="url(#ticket-dark)"></path><path d="M265 311 L278 309 L287 312 L298 309 L316 311 L316 398 L265 398Z" fill="url(#ticket-dark)"></path><path d="M408 184 L450 185 L448 234 L408 235Z" fill="url(#ticket-light)"></path><path d="M444 296 L470 297 L471 366 L443 367Z" fill="url(#ticket-dark)"></path></g><g fill="none" stroke="#eeeeE7" stroke-width="2" opacity=".63"><path d="M55 248L54 281 M37 264L73 265 M232 196V248 M214 220L251 222 M321 196L323 246 M304 220L340 219 M429 188L428 231 M412 209L446 210"></path></g><path d="M222 274 L249 272 L250 285 L224 287Z" fill="#eeeeE7" opacity=".75"></path><text x="227" y="282" font-size="7" fill="#62625e" transform="rotate(-4 227 282)">SAMPLE TEXT</text><rect width="500" height="400" fill="url(#grain)" clip-path="url(#all-paper)"></rect></g></svg></div></body></html>
````

## 点缀-空心长方框

逻辑路径：assets/模板库/点缀/点缀-空心长方框.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0162
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-空心长方框</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#efefed}.outline{--size:215px;--stroke:6.02;--radius:0;--line:#686868;--opacity:1;width:min(var(--size),80vw,calc(84vh * .43));aspect-ratio:.43;overflow:visible}svg{display:block;width:100%;height:100%;overflow:visible}.frame-line{fill:none;stroke:var(--line);stroke-width:var(--stroke);rx:var(--radius);ry:var(--radius);opacity:var(--opacity);pointer-events:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="outline" data-component-class="decoration"><svg viewbox="0 0 172 400" role="img" aria-label="点缀-空心长方框"><rect id="outline" class="frame-line" x="3.01" y="3.01" width="165.98" height="393.98"></rect></svg></div></body></html>
````

## 点缀-竖式小印章

逻辑路径：assets/模板库/点缀/点缀-竖式小印章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0178
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-竖式小印章</title><style>:root{--size:150px;--seal:#515151;--ink:#f5f5f5;--corner:30px;--stroke:3.5px}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e8e8e8}.component{width:min(var(--size),76vw,49vh);aspect-ratio:0.6176}.component svg{display:block;width:100%;height:100%}.base{fill:var(--seal);rx:var(--corner);ry:var(--corner)}.glyph{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 100 161.917" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-竖式小印章"><rect class="base" width="100" height="161.917" rx="30"></rect><g class="glyph" data-slot="content-1" data-placeholder="机构简称" aria-label="通用内容槽" data-role="内容槽"><text x="50" y="42" text-anchor="middle" font-size="31" font-family="serif" font-weight="700" fill="var(--ink)" stroke="none" writing-mode="vertical-rl" letter-spacing="8">标签</text></g></svg></div></body></html>
````

## 点缀-竖长印章

逻辑路径：assets/模板库/点缀/点缀-竖长印章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0088
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-竖长印章</title><style>:root{--size:126px;--ink:#515151;--stroke:5.5px;--wear:1;--corner:12px}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e8e8e8}.component{width:min(var(--size),72vw,33vh);aspect-ratio:0.42}.component svg{width:100%;height:100%;display:block}.carved{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}.wear{opacity:var(--wear)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 100 238.095" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-竖长印章"><defs><mask id="wear" maskunits="userSpaceOnUse" x="0" y="0" width="100" height="239"><rect width="100" height="239" fill="white"></rect><g class="wear" fill="black"><path d="M4 47l5 1-1 3-4-1zM90 99l7-2v3l-7 2zM29 5l3-1 1 5-3 1zM65 230l3-1 1 5h-3zM20 35l4-2 1 5-4 1zM71 58l4 1-2 3-3-1zM28 116l5-1v3l-5 1zM59 144l3-1 1 5-3 1zM21 185l5-1v3l-5 1zM68 198l5-1v3l-5 1z"></path><circle cx="7" cy="176" r="1.5"></circle><circle cx="80" cy="220" r="1.2"></circle><circle cx="47" cy="73" r="1.2"></circle></g></mask></defs><g class="carved" mask="url(#wear)"><path d="M18 7C31 5 64 7 80 6Q92 6 93 19L92 72L94 132L92 217Q93 229 81 231L21 232Q7 232 7 217L8 171L6 104L7 23Q6 10 18 7Z"></path><g data-slot="content-1" aria-label="通用内容槽" data-role="内容槽"><text x="50" y="63" text-anchor="middle" font-size="39" font-family="serif" font-weight="700" fill="var(--ink)" stroke="none" writing-mode="vertical-rl" letter-spacing="14">标签</text></g></g></svg></div></body></html>
````

## 点缀-笑脸小花

逻辑路径：assets/模板库/点缀/点缀-笑脸小花.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0191
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-笑脸小花</title><style>:root{--size:300px;--rotation:-8deg;--petal:#777;--petal-alt:#8b8b8b;--face:#f3f3f3;--ink:#343434;--stroke:5px}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e8e8e8}.component{width:min(var(--size),70vw,70vh);aspect-ratio:1;transform:rotate(var(--rotation))}.component svg{display:block;width:100%;height:100%;overflow:visible}.petal{fill:var(--petal)}.alternate{fill:var(--petal-alt)}.features{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-笑脸小花"><g><path class="petal" d="M83 73C60 64 15 68 6 89C-3 110 22 125 68 124L104 95Z"></path><path class="alternate" d="M80 82C55 90 13 120 16 145C19 171 47 170 68 145L108 99Z"></path><path class="petal" d="M85 89C65 109 37 157 47 178C59 203 81 191 90 163L109 98Z"></path><path class="alternate" d="M88 89C81 117 77 170 86 190C95 207 117 201 122 183C128 160 116 112 109 90Z"></path><path class="petal" d="M105 84C125 104 159 148 157 174C155 199 130 202 118 175L96 99Z"></path><path class="alternate" d="M116 77C145 79 187 113 187 137C188 163 164 171 145 146L99 96Z"></path><path class="petal" d="M118 73C145 63 187 70 195 91C204 115 177 128 148 119L100 96Z"></path></g><ellipse cx="100" cy="53" rx="52" ry="45" fill="var(--face)"></ellipse><g class="features"><path d="M82 44L81 52M117 43L116 51"></path><path d="M78 66C86 82 108 86 123 66"></path></g></svg></div></body></html>
````

## 点缀-笔绘蝴蝶

逻辑路径：assets/模板库/点缀/点缀-笔绘蝴蝶.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0234
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-笔绘蝴蝶</title><style>:root{--size:330px;--wing:#777;--wing-light:#959595;--edge:#363636;--brush:#e4e4e4;--outline:4px;--body-stroke:3px;--brush-opacity:0.94}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e8e8e8}.component{width:min(var(--size),76vw,76vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%;overflow:visible}.outline{fill:none;stroke:var(--edge);stroke-width:var(--outline);stroke-linecap:round;stroke-linejoin:round}.marks{fill:var(--brush);opacity:var(--brush-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-笔绘蝴蝶"><defs><path id="leftWing" d="M88 125C64 119 20 95 12 65C8 47 8 18 21 7C33-4 53 18 66 36C82 57 98 95 88 125Z"></path><path id="rightWing" d="M89 124C99 91 120 37 153 26C174 18 190 26 189 48C189 84 164 111 143 126C159 132 171 150 159 162C140 183 103 151 89 124Z"></path><clippath id="wings"><use href="#leftWing"></use><use href="#rightWing"></use></clippath></defs><g data-palette-role="翼面"><use href="#leftWing" fill="var(--wing)"></use><use href="#rightWing" fill="var(--wing-light)"></use></g><g clip-path="url(#wings)" data-palette-role="笔触"><g class="marks"><path d="M22 19L31 17L37 35L31 32L34 44L27 40Z"></path><path d="M40 28L47 33L66 65L59 61L62 72L53 62Z"></path><path d="M18 48L27 53L32 71L28 69L36 84L28 80L21 65Z"></path><path d="M38 57L44 58L64 86L60 86L71 106L59 99L50 82L46 81Z"></path><path d="M24 87L32 90L49 104L46 107L35 99Z"></path><path d="M72 69L77 75L86 103L81 103L79 90Z"></path><path d="M112 91L123 64L130 58L127 74L118 97Z"></path><path d="M133 53L143 43L153 39L147 52L141 53L133 70L130 67Z"></path><path d="M165 34L177 33L180 41L174 39L173 58L167 64L168 49L164 52Z"></path><path d="M155 62L164 55L157 78L151 87L146 89L148 82L137 101L132 98Z"></path><path d="M169 79L177 70L173 87L157 104L150 104L160 91Z"></path><path d="M112 126L124 132L137 151L130 151L122 141L119 141Z"></path><path d="M137 132L147 136L154 146L150 153L145 146L147 145Z"></path></g><g fill="var(--edge)" opacity=".55"><path d="M14 26L18 23L21 43L17 37Z"></path><path d="M50 21L59 34L57 37L47 25Z"></path><path d="M179 28L185 32L182 53L179 47Z"></path><path d="M146 111L154 108L144 121L136 123Z"></path></g></g><g class="outline" data-palette-role="轮廓"><use href="#leftWing"></use><use href="#rightWing"></use></g><g fill="none" stroke="var(--edge)" stroke-width="var(--body-stroke)" stroke-linecap="round"><path d="M69 101C88 120 102 153 127 172C138 182 149 190 158 193"></path><path d="M69 102C63 94 58 91 54 97M72 102C72 91 76 85 82 86"></path></g><path d="M69 102C78 107 89 124 96 139C87 132 76 115 69 102Z" fill="var(--edge)"></path></svg></div></body></html>
````

## 点缀-简化夹子

逻辑路径：assets/模板库/点缀/点缀-简化夹子.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-简化夹子</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-gradient--linear { --vl-paint:linear-gradient(var(--vl-gradient-angle,135deg),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--radial { --vl-paint:radial-gradient(ellipse var(--vl-gradient-rx,70%) var(--vl-gradient-ry,70%) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--conic { --vl-paint:conic-gradient(from var(--vl-gradient-turn,0deg) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-paint-fill { background-image:var(--vl-paint,none); }

.vl-binder-clip { display:inline-block; position:relative; width:var(--vl-clip-width,48px); aspect-ratio:72 / 80; transform:rotate(var(--vl-rotate,0deg)); filter:drop-shadow(0 2px 2px color-mix(in srgb,#243345 calc(var(--vl-clip-shadow,.18) * 100%),transparent)); }
.vl-binder-clip__body { position:absolute; inset:0; background-image:var(--vl-paint,linear-gradient(110deg,#fffdf1 0%,#e4e0ce 45%,#cacbbf 70%,#fff9df 100%)); mask-image:url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI3MiIgaGVpZ2h0PSI4MCIgdmlld0JveD0iMCAwIDcyIDgwIj48cGF0aCBmaWxsPSJ3aGl0ZSIgZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMjAgMThhMTYgMTYgMCAwIDEgMzIgMHYxNWw2IDE3aDhhNSA1IDAgMCAxIDUgNXYxN2E1IDUgMCAwIDEtNSA1SDZhNSA1IDAgMCAxLTUtNVY1NWE1IDUgMCAwIDEgNS01aDhsNi0xN1YxOHogTTQxIDE3YTUgNSAwIDEgMC0xMCAwYTUgNSAwIDEgMCAxMCAweiIvPjwvc3ZnPg=="); mask-size:100% 100%; mask-repeat:no-repeat; }
</style></head><body><span class="vl-binder-clip vl-gradient--linear" style="--vl-gradient-stops:#ffe1ed 0%,#e88ab8 50%,#ffbcdb 100%" aria-hidden="true"><span class="vl-binder-clip__body"></span></span>
</body></html>
````

## 点缀-粗线小花

逻辑路径：assets/模板库/点缀/点缀-粗线小花.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0096
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-粗线小花</title><style>:root{--size:260px;--stroke:11.7px;--outline:#282828;--petals:#999;--center:#ededed;--leaves:#5e5e5e}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#e8e8e8}.component{width:min(var(--size),72vw,65vh);aspect-ratio:0.9}.component svg{display:block;width:100%;height:100%;overflow:visible}.heavy{stroke:var(--outline);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 180 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-粗线小花"><path class="heavy" d="M99 88C96 115 88 149 84.6 174" fill="none"></path><g class="heavy" fill="var(--leaves)" data-palette-role="叶片填色"><path d="M84.6 185C55 193 14 173 6 120C38 120 71 139 84.6 185Z"></path><path d="M84.6 185C88 150 117 121 174 120C168 165 130 194 84.6 185Z"></path></g><path class="heavy" fill="var(--petals)" data-palette-role="花瓣填色" d="M74 39C61 13 77 5.8 92 5.8C109 5.8 120 19 114 38C136 23 157 34 159 50C162 67 148 79 127 75C148 91 136 110 119 110C105 111 99 99 95 88C90 112 69 117 57 104C45 93 52 78 65 70C43 78 27 65 31 48C34 32 55 28 74 39Z"></path><circle cx="95.4" cy="62" r="13.5" fill="var(--center)" data-palette-role="花心填色"></circle></svg></div></body></html>
````

## 点缀-纸片双眼

逻辑路径：assets/模板库/点缀/点缀-纸片双眼.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0083
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-纸片双眼</title><style>:root{--size:340px;--paper:#f6f6f4;--pupil:#292929;--shadow-opacity:0.24;--fiber-opacity:0.17;--gaze-x:0px;--gaze-y:0px}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#dedede}.component{width:min(var(--size),78vw,110vh);aspect-ratio:1.55}.component svg{display:block;width:100%;height:100%;overflow:visible}.pupils{fill:var(--pupil);transform:translate(var(--gaze-x),var(--gaze-y))}.fibers{opacity:var(--fiber-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 310 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-纸片双眼"><defs><path id="paper" d="M164 111C169 151 146 184 107 191C65 198 15 177 3 142C-8 110 11 66 43 46C76 25 126 38 150 63C161 26 185 1 226 4C270 1 299 32 303 74C307 118 281 155 240 161C209 166 180 151 165 135C166 127 166 119 164 111Z"></path><clippath id="paperClip"><use href="#paper"></use></clippath><filter id="shadow" x="-10%" y="-10%" width="125%" height="130%" color-interpolation-filters="sRGB"><fegaussianblur stddeviation="1.86"></fegaussianblur></filter><filter id="paperGrain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feturbulence type="fractalNoise" basefrequency=".64 .21" numoctaves="3" seed="19"></feturbulence><fecolormatrix type="saturate" values="0"></fecolormatrix></filter></defs><use href="#paper" transform="translate(1.55 3.72)" fill="#000" opacity="var(--shadow-opacity)" filter="url(#shadow)"></use><use href="#paper" fill="var(--paper)"></use><g clip-path="url(#paperClip)"><rect width="310" height="200" filter="url(#paperGrain)" opacity=".095"></rect><g class="fibers" fill="none" stroke="#aaa" stroke-width=".55" stroke-linecap="round"><path d="M18 107l12-5M36 77l7 2M48 52l13-3M66 65l10 3M94 47l9 5M124 74l11 2M15 138l9 4M29 160l16 4M51 133l9-4M61 180l13-2M88 163l11 3M131 151l13-7M139 115l8 3M181 40l13-6M205 19l14 1M242 18l13 5M262 44l10-2M286 67l9 7M180 80l12 3M191 107l8-3M215 130l15 2M264 131l12-7M237 151l12-3M284 103l9-5M54 102l13 2M91 87l8-2M151 84l7 4M219 57l11-5"></path><path d="M23 120q8-3 13-1M76 151q6-5 12-3M160 55q6 1 8-5M198 146q7 4 13 3M271 83q7-2 11 2"></path></g><g stroke="#fff" stroke-width=".7" opacity=".55"><path d="M30 93l20-4M63 167l14 2M106 60l12 3M175 62l15-8M226 28l20 3M270 111l13-8M190 122l15 6"></path></g></g><g class="pupils" data-slot="content-1" data-role="内容槽"><path d="M117.8 93C129 92 137.4 105 138 122C139 141 131 155 120 155C108 156 98.1 143 97.7 126C96.9 108 106 93 117.8 93Z"></path><path d="M254.2 45C265.6 44 274.2 57 274.3 74C275 92 267 106 256 107C244 108 234 95 234.1 78C233.4 60 242 46 254.2 45Z"></path></g></svg></div></body></html>
````

## 点缀-线描叶片

逻辑路径：assets/模板库/点缀/点缀-线描叶片.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0080
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-线描叶片</title><style>:root{--size:540px;--line:#eeeeec;--stroke:1.8;--stage:#595959;--opacity:1}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:var(--stage)}.leaf{width:min(var(--size),86vw,210vh);aspect-ratio:2.5;opacity:var(--opacity)}svg{display:block;width:100%;height:100%;overflow:visible}.drawing{fill:none;stroke:var(--line);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="leaf" data-component-class="decoration"><svg viewbox="0 0 100 40" role="img" aria-label="点缀-线描叶片"><g class="drawing"><path d="M3 5 Q48 6 97 35 Q43 38 3 5 Z"></path><g><path d="M3 5 Q46 24 97 35"></path><path d="M24 13.5 Q22 9 18 6.1 M35 17.9 Q31 19.7 26 19.1 M46 21.8 Q44 15.8 38 10 M57 25.3 Q51 28 46 28 M67 28.4 Q63 22 58 17.2 M77 31 Q72 33 67 32.8 M86 33.1 Q81 28.6 77 25.5"></path></g></g></svg></div></body></html>
````

## 点缀-线描回形针

逻辑路径：assets/模板库/点缀/点缀-线描回形针.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0185
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-线描回形针</title><style>:root{--size:210px;--wire:#303030;--stroke:1.8;--stage:#ededeb;--rotation:0deg;--opacity:1}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:var(--stage)}.clip{width:min(var(--size),76vw,49vh);aspect-ratio:.6;transform:rotate(var(--rotation));transform-origin:50% 50%;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}path{fill:none;stroke:var(--wire);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="clip" data-component-class="decoration"><svg viewbox="0 0 60 100" role="img" aria-label="点缀-线描回形针"><path d="M41 28 L41 71 C41 86 19 86 19 71 L19 22 C19 -2 57 -2 57 22 L57 70 C57 107 3 107 3 70 L3 26"></path></svg></div></body></html>
````

## 点缀-经纬线球体

逻辑路径：assets/模板库/点缀/点缀-经纬线球体.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0169
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-经纬线球体</title><style>:root{--size:270px;--line:#272727;--stroke:6.5;--stage:#e9e9e7;--opacity:1}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:var(--stage)}.globe{width:min(var(--size),80vw,80vh);aspect-ratio:1;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.wire{fill:none;stroke:var(--line);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="globe" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-经纬线球体"><defs><clippath id="sphere-clip"><circle cx="50" cy="50" r="46.5"></circle></clippath></defs><circle class="wire" cx="50" cy="50" r="46.5"></circle><g class="wire" clip-path="url(#sphere-clip)"><ellipse cx="50" cy="50" rx="20.5" ry="46.5"></ellipse><path d="M50 3.5 V96.5 M3.5 50 H96.5 M10 26 Q50 41 90 26 M10 74 Q50 59 90 74"></path></g></svg></div></body></html>
````

## 点缀-编辑器选框与控制柄

逻辑路径：assets/模板库/点缀/点缀-编辑器选框与控制柄.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-编辑器选框与控制柄</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.cv-selection-demo{--cv-demo-width:680px;--cv-selection-color:#245ce5;--cv-selection-stroke:1px;--cv-handle-size:8px;--cv-content-pad:22px;--cv-edge-safe:28px;--cv-handle-reserve:104px;--cv-bezier-width:280px;--cv-bezier-height:80px;box-sizing:border-box;width:var(--cv-demo-width);max-width:100%;padding:var(--cv-edge-safe);background:#f5f2e9;color:#202027;font-family:Arial,'PingFang SC',sans-serif;isolation:isolate}.cv-selection-demo *{box-sizing:border-box}.cv-selection-demo .cv-selection-heading{margin:0 0 12px;font-size:22px;line-height:1.4;overflow-wrap:anywhere}.cv-selection-demo .cv-selection-stage{padding:14px calc(var(--cv-handle-size)/2 + 2px)}.cv-selection-demo .cv-selection-stage[data-cv-handles='on']{padding-top:var(--cv-handle-reserve)}.cv-selection-demo .cv-selection-box{position:relative;min-width:0;border:var(--cv-selection-stroke) solid var(--cv-selection-color);padding:var(--cv-content-pad);background:#fffdf7}.cv-selection-demo .cv-selection-copy{position:relative;z-index:1;min-width:0;overflow-wrap:anywhere}.cv-selection-demo .cv-selection-copy h3{margin:0 0 10px;font-size:28px;line-height:1.15}.cv-selection-demo .cv-selection-copy p{margin:0;font-size:15px;line-height:1.65}.cv-selection-demo .cv-selection-corner{position:absolute;z-index:2;width:var(--cv-handle-size);height:var(--cv-handle-size);border:var(--cv-selection-stroke) solid var(--cv-selection-color);background:#fff;pointer-events:none}.cv-selection-demo .cv-selection-tl{top:0;left:0;transform:translate(-50%,-50%)}.cv-selection-demo .cv-selection-tr{top:0;right:0;transform:translate(50%,-50%)}.cv-selection-demo .cv-selection-bl{bottom:0;left:0;transform:translate(-50%,50%)}.cv-selection-demo .cv-selection-br{bottom:0;right:0;transform:translate(50%,50%)}.cv-selection-demo .cv-selection-bezier{display:none;position:absolute;z-index:2;bottom:calc(100% + 10px);left:50%;transform:translateX(-50%);width:min(var(--cv-bezier-width),calc(100% - 24px));height:var(--cv-bezier-height);color:var(--cv-selection-color);overflow:visible;pointer-events:none}.cv-selection-demo [data-cv-handles='on'] .cv-selection-bezier{display:block}.cv-selection-demo .cv-selection-bezier path,.cv-selection-demo .cv-selection-bezier line,.cv-selection-demo .cv-selection-bezier circle,.cv-selection-demo .cv-selection-bezier rect{stroke:currentColor;stroke-width:var(--cv-selection-stroke);vector-effect:non-scaling-stroke}.cv-selection-demo .cv-selection-bezier path{fill:none}.cv-selection-demo .cv-selection-bezier line{stroke-dasharray:3 3;opacity:.7}.cv-selection-demo .cv-selection-bezier circle,.cv-selection-demo .cv-selection-bezier rect{fill:#fff}
</style></head><body><section class="cv-selection-demo" aria-label="编辑器选框示例"><h2 class="cv-selection-heading">编辑选框 · 个人简介</h2><div class="cv-selection-stage" data-cv-handles="on"><article class="cv-selection-box"><svg class="cv-selection-bezier" viewBox="0 0 280 80" preserveAspectRatio="none" aria-hidden="true" focusable="false"><line x1="12" y1="64" x2="88" y2="12"/><line x1="268" y1="64" x2="192" y2="12"/><path d="M12 64 C88 12 192 12 268 64"/><circle cx="88" cy="12" r="4"/><circle cx="192" cy="12" r="4"/><rect x="8" y="60" width="8" height="8"/><rect x="264" y="60" width="8" height="8"/></svg><span class="cv-selection-corner cv-selection-tl" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-tr" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-bl" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-br" aria-hidden="true"></span><div class="cv-selection-copy" lang="en"><h3>Alex Morgan — Editorial Designer</h3><p>Independent designer working across visual identities, publications and digital experiences. Selected projects combine clear typography with thoughtful art direction.</p></div></article></div></section>
</body></html>
````

## 点缀-缺口圆环

逻辑路径：assets/模板库/点缀/点缀-缺口圆环.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0111
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-缺口圆环</title><style>:root{--size:285px;--fill:#414141;--outline:#292929;--stroke:2.7;--stage:#ececea;--opacity:1;--rotation:0deg}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:var(--stage)}.ring{width:min(var(--size),80vw,80vh);aspect-ratio:1;opacity:var(--opacity);transform:rotate(var(--rotation));transform-origin:center}svg{display:block;width:100%;height:100%}path{fill:var(--fill);stroke:var(--outline);stroke-width:var(--stroke);stroke-linejoin:round;stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="ring" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-缺口圆环"><path d="M12.46 21.72 C21.4 9.7 35.2 2.3 50 3 C65.8 2.5 78.4 10.5 87.1 20.9 C94.4 30.5 97.9 39.7 97 50 C97.4 64.2 90.7 78.1 79.8 86.6 C71.7 93.2 60.6 97.8 49.8 97 C35.3 97.5 22.8 90.1 14.5 81 C5.5 70.8 1.3 57.8 3.35 44.27 L36.1 47.42 C35.5 53.2 38.8 59.3 44.6 61.2 C50.6 63.5 57.2 60.7 60.2 55.6 C63.5 50.4 62.1 43.4 57.4 39 C52.1 34.5 43.9 34.9 38.62 41.18 Z"></path></svg></div></body></html>
````

## 点缀-缺口果环

逻辑路径：assets/模板库/点缀/点缀-缺口果环.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0100
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-缺口果环</title><style>:root{--size:340px;--fill:#b0b0ac;--outline:#252525;--stroke:1.3;--stage:#f1f1ef;--opacity:1;--rotation:0deg}*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:var(--stage)}.fruit-ring{width:min(var(--size),82vw,82vh);aspect-ratio:1;opacity:var(--opacity);transform:rotate(var(--rotation));transform-origin:50% 50%}svg{display:block;width:100%;height:100%}.fill{fill:var(--fill)}.outline{fill:none;stroke:var(--outline);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="fruit-ring" data-component-class="decoration"><svg viewbox="0 0 100 100" role="img" aria-label="点缀-缺口果环"><defs><path id="fruit-contour" d="M12.85 18.82 C16.4 14.4 20.6 10.6 25.9 8 C30.3 5.5 35.2 3.5 40.5 2.6 C44 1.8 47.1 1.1 50.2 1.5 C58.7 1.3 66.4 3.6 74 7.9 C81 11.7 87 17.5 91.8 25.3 C96 32.4 98.9 41 98.5 50.1 C98.7 58.5 96.2 67.1 92 74.4 C88.1 81.5 81.9 87.6 74.8 92 C67.4 96.1 58.6 98.9 50 98.5 C41 98.7 33.1 96.2 25.1 91.8 C17.8 87.8 11.4 81.2 7.8 74.3 C3.8 67.1 1.1 58.8 1.5 50.1 C1.3 47.1 1.7 44.3 2.24 41.58 L35.72 47.98 C35.1 51 35.7 54.3 37 57.1 C38.7 60.4 41.5 62.9 45 64 C48.5 65.3 52.4 65.2 55.7 63.9 C59.6 62.3 62.4 59.5 63.6 55.7 C65 52.1 64.7 48.5 63.5 45.2 C62.2 41.6 59.5 38.6 56 37.4 C52.5 35.8 48.9 35.5 45.5 36.8 C42.7 37.7 40.6 39.2 38.89 41.18 Z"></path></defs><use href="#fruit-contour" class="fill"></use><use href="#fruit-contour" class="outline"></use></svg></div></body></html>
````

## 点缀-罗盘星芒

逻辑路径：assets/模板库/点缀/点缀-罗盘星芒.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0006
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-罗盘星芒</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e9e9e9}.component{--size:520px;--ring-stroke:1.6;--ring-opacity:.35;--foreground-opacity:.85;--background-opacity:.07;--ink:#383838;width:min(var(--size),88vw,88vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%;overflow:visible}.ring{fill:none;stroke:var(--ink);stroke-width:var(--ring-stroke);opacity:var(--ring-opacity)}.rays{fill:var(--ink);fill-opacity:var(--background-opacity)}.facets{opacity:var(--foreground-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 400 400" role="img" aria-label="点缀-罗盘星芒"><g class="ring"><circle cx="200" cy="200" r="152" stroke-dasharray="102 16 47 14 130 18 61 13 105 22 72 16 130 17 62 30" transform="rotate(-18 200 200)"></circle><path d="M200 42V53M347 200H358M200 347V358M42 200H53" stroke-width="1"></path></g><path class="rays" d="M200 16L218.369 155.653L291.075 108.925L244.347 181.631L384 200L244.347 218.369L291.075 291.075L218.369 244.347L200 384L181.631 244.347L108.925 291.075L155.653 218.369L16 200L155.653 181.631L108.925 108.925L181.631 155.653Z"></path><g class="facets"><path fill="#414141" d="M200 200L200 16L218.369 155.653Z"></path><path fill="#bdbdbd" d="M200 200L181.631 155.653L200 16Z"></path><path fill="#696969" d="M200 200L291.075 108.925L244.347 181.631Z"></path><path fill="#c9c9c9" d="M200 200L218.369 155.653L291.075 108.925Z"></path><path fill="#414141" d="M200 200L384 200L244.347 218.369Z"></path><path fill="#bdbdbd" d="M200 200L244.347 181.631L384 200Z"></path><path fill="#696969" d="M200 200L291.075 291.075L218.369 244.347Z"></path><path fill="#c9c9c9" d="M200 200L244.347 218.369L291.075 291.075Z"></path><path fill="#414141" d="M200 200L200 384L181.631 244.347Z"></path><path fill="#bdbdbd" d="M200 200L218.369 244.347L200 384Z"></path><path fill="#696969" d="M200 200L108.925 291.075L155.653 218.369Z"></path><path fill="#c9c9c9" d="M200 200L181.631 244.347L108.925 291.075Z"></path><path fill="#414141" d="M200 200L16 200L155.653 181.631Z"></path><path fill="#bdbdbd" d="M200 200L155.653 218.369L16 200Z"></path><path fill="#696969" d="M200 200L108.925 108.925L181.631 155.653Z"></path><path fill="#c9c9c9" d="M200 200L155.653 181.631L108.925 108.925Z"></path></g></svg></div></body></html>
````

## 点缀-胶囊圆点接头

逻辑路径：assets/模板库/点缀/点缀-胶囊圆点接头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0098
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-胶囊圆点接头</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{background:#ededed;display:grid;place-items:center}.component{--size:560px;--ink:#454545;--stroke:1.8;--capsule-radius:11.1px;--dot-radius:12px;width:min(var(--size),88vw,88vh);aspect-ratio:1}.component svg{width:100%;height:100%;display:block}.arms{fill:none;stroke:var(--ink);stroke-width:var(--stroke)}.arms rect{rx:var(--capsule-radius);ry:var(--capsule-radius)}.dot{fill:var(--ink);r:var(--dot-radius)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 400 400" role="img" aria-label="点缀-胶囊圆点接头"><g class="arms"><rect x="188.9" y="20.9" width="22.2" height="166.2" rx="11.1"></rect><rect x="212.9" y="188.9" width="166.2" height="22.2" rx="11.1"></rect><rect x="188.9" y="212.9" width="22.2" height="142.2" rx="11.1"></rect><rect x="44.9" y="188.9" width="142.2" height="22.2" rx="11.1"></rect></g><circle class="dot" cx="200" cy="200" r="12"></circle></svg></div></body></html>
````

## 点缀-航海罗盘

逻辑路径：assets/模板库/点缀/点缀-航海罗盘.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0205
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-航海罗盘</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{background:#e8e8e8;display:grid;place-items:center}.component{--size:560px;--ink:#353535;--stroke:3.5;--ink-opacity:.7;--wear-opacity:.85;width:min(var(--size),90vw,90vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%;overflow:visible}.print{color:var(--ink);opacity:var(--ink-opacity)}.linework{stroke:currentColor;stroke-width:var(--stroke);fill:none;stroke-linejoin:round;stroke-linecap:round}.directions{fill:currentColor;font-family:Georgia,'Times New Roman',serif;font-weight:600;text-anchor:middle;font-size:30px}.phrase{font-size:13px;letter-spacing:3px}.wear{opacity:var(--wear-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 500 500" role="img" aria-label="点缀-航海罗盘"><defs><filter id="rough" x="-3%" y="-3%" width="106%" height="106%"><feturbulence type="fractalNoise" basefrequency=".075" numoctaves="2" seed="18" result="noise"></feturbulence><fedisplacementmap in="SourceGraphic" in2="noise" scale="1.5" xchannelselector="R" ychannelselector="G"></fedisplacementmap></filter><mask id="wear"><rect width="500" height="500" fill="white"></rect><g class="wear" fill="black"><path d="M142 33l9-3 2 3-9 3zM365 37l7 4-1 3-8-4zM474 176l8 3-1 4-8-2zM16 277l7-2 2 4-8 2zM137 462l9 4-2 4-9-5zM356 460l8-5 2 4-8 4zM224 126l5 3-3 6-4-3zM243 163l5-1 1 8-4 2zM258 205l4 2-1 6-5-2zM273 249l8-2 1 4-7 2zM160 258l7-2 1 4-8 2zM237 303l6 1-1 7-4-1zM249 362l4 1-1 7-4-1zM324 252l7-2 1 4-7 2zM104 245l7-2 2 3-7 3z"></path><circle cx="203" cy="41" r="2.2"></circle><circle cx="294" cy="25" r="2"></circle><circle cx="451" cy="310" r="2.4"></circle><circle cx="52" cy="162" r="2.8"></circle><circle cx="211" cy="236" r="2.1"></circle><circle cx="248" cy="271" r="1.7"></circle><circle cx="285" cy="221" r="1.8"></circle><circle cx="318" cy="320" r="2"></circle><circle cx="249" cy="75" r="2"></circle><circle cx="70" cy="251" r="2"></circle><circle cx="434" cy="247" r="2"></circle><circle cx="251" cy="443" r="2.3"></circle></g></mask><path id="phrase-top" d="M25 250A225 225 0 0 1 475 250"></path><path id="phrase-bottom" d="M25 250A225 225 0 0 0 475 250"></path><g id="ticks" stroke="currentColor" stroke-width="2"><path d="M250 38V49M272.16 39.16L271 50M294.08 42.63L291.8 53.4M315.51 48.38L312.1 58.8M336.23 56.33L331.76 66.38"></path></g><g id="long-needle"><path d="M250 92L276 224L250 250L224 224Z" fill="none" stroke="currentColor" stroke-width="2.5"></path><path d="M250 92L250 250L276 224Z" fill="currentColor"></path></g><g id="short-needle"><path d="M250 128L269 231L250 250L231 231Z" fill="none" stroke="currentColor" stroke-width="2.5"></path><path d="M250 128L250 250L269 231Z" fill="currentColor"></path></g></defs><g class="print" filter="url(#rough)" mask="url(#wear)"><g id="compass-lines"><g class="linework"><circle cx="250" cy="250" r="240"></circle><circle cx="250" cy="250" r="214"></circle><circle cx="250" cy="250" r="151" stroke-width="1.4"></circle><path d="M250 98V402M98 250H402M143 143L357 357M143 357L357 143" stroke-width="1.2"></path></g><g fill="none"><use href="#ticks"></use><use href="#ticks" transform="rotate(30 250 250)"></use><use href="#ticks" transform="rotate(60 250 250)"></use><use href="#ticks" transform="rotate(90 250 250)"></use><use href="#ticks" transform="rotate(120 250 250)"></use><use href="#ticks" transform="rotate(150 250 250)"></use><use href="#ticks" transform="rotate(180 250 250)"></use><use href="#ticks" transform="rotate(210 250 250)"></use><use href="#ticks" transform="rotate(240 250 250)"></use><use href="#ticks" transform="rotate(270 250 250)"></use><use href="#ticks" transform="rotate(300 250 250)"></use><use href="#ticks" transform="rotate(330 250 250)"></use></g><use href="#short-needle" transform="rotate(45 250 250)"></use><use href="#short-needle" transform="rotate(135 250 250)"></use><use href="#short-needle" transform="rotate(225 250 250)"></use><use href="#short-needle" transform="rotate(315 250 250)"></use><use href="#long-needle"></use><use href="#long-needle" transform="rotate(90 250 250)"></use><use href="#long-needle" transform="rotate(180 250 250)"></use><use href="#long-needle" transform="rotate(270 250 250)"></use><circle cx="250" cy="250" r="10" fill="#e8e8e8" stroke="currentColor" stroke-width="3"></circle><circle cx="250" cy="250" r="3" fill="currentColor"></circle></g><g id="compass-directions" class="directions" data-role="内容层"><text x="250" y="82" transform="rotate(-3 250 73)">说明文字</text><text x="432" y="260">说明文字</text><text x="250" y="444" transform="rotate(3 250 433)">说明文字</text><text x="68" y="260">说明文字</text><text x="381" y="129" transform="rotate(45 381 120)">说明文字</text><text x="380" y="389" transform="rotate(-45 380 380)">说明文字</text><text x="120" y="389" transform="rotate(45 120 380)">说明文字</text><text x="120" y="129" transform="rotate(-45 120 120)">说明文字</text><text class="phrase"><textpath href="#phrase-top" startoffset="50%">SAMPLE TEXT</textpath></text><text class="phrase" dy="-3"><textpath href="#phrase-bottom" startoffset="50%">SAMPLE TEXT</textpath></text></g></g></svg></div></body></html>
````

## 点缀-航海邮戳

逻辑路径：assets/模板库/点缀/点缀-航海邮戳.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0206
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-航海邮戳</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#e9e9e9}.component{--size:740px;--ink:#454545;--stroke:4.6;--opacity:.76;--erosion-opacity:.9;width:min(var(--size),92vw,144vh);aspect-ratio:8/5}.component svg{display:block;width:100%;height:100%}.stamp{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-linecap:round;stroke-linejoin:round;opacity:var(--opacity)}.wear{opacity:var(--erosion-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 640 400" role="img" aria-label="点缀-航海邮戳"><defs><filter id="stamp-rough" x="-3%" y="-4%" width="106%" height="108%"><feturbulence type="fractalNoise" basefrequency=".095" numoctaves="3" seed="9" result="grain"></feturbulence><fedisplacementmap in="SourceGraphic" in2="grain" scale="2" xchannelselector="R" ychannelselector="B"></fedisplacementmap></filter><mask id="stamp-wear"><rect width="640" height="400" fill="white"></rect><g class="wear" fill="black"><path d="M21 125l7 2-1 5-8-2zM58 178l5-1 1 5-5 2zM87 253l8-2 2 4-8 2zM123 136l8-2 2 5-9 2zM161 96l8 3-2 5-9-3zM232 37l9-3 1 6-9 3zM330 18l8 2-2 7-8-2zM420 58l8 5-4 5-8-6zM480 172l10 2-1 5-10-1zM461 290l7 4-4 6-7-4zM359 370l9-3 1 6-8 3zM205 343l7 4-3 5-8-4zM530 142l7 2-2 6-7-2zM568 232l9-2 1 5-9 2zM609 287l6 1-1 5-6-1zM258 137l7 2-2 4-7-2zM304 84h6v7h-6zM386 198h7v6h-7zM253 260l6 4-3 4-6-4zM309 290l5-1 1 7-5 1z"></path><circle cx="173" cy="223" r="2.4"></circle><circle cx="383" cy="102" r="2.6"></circle><circle cx="300" cy="222" r="2.2"></circle><circle cx="330" cy="149" r="2"></circle><circle cx="550" cy="188" r="2.4"></circle><circle cx="38" cy="275" r="2.5"></circle><circle cx="409" cy="317" r="2.4"></circle><circle cx="234" cy="206" r="2.8"></circle></g></mask><g id="wheel-spoke"><path d="M307.2 182V104" stroke-width="7"></path><path d="M307.2 108V77" stroke-width="10"></path><path d="M298.2 106H316.2" stroke-width="4"></path><ellipse cx="307.2" cy="75" rx="6" ry="10" fill="#454545" stroke="none"></ellipse></g></defs><g class="stamp" filter="url(#stamp-rough)" mask="url(#stamp-wear)"><g id="postmark-waves"><path d="M7 132C31 115 50 114 74 130S114 147 139 128M7 177C31 160 50 159 74 175S111 192 130 177M7 222C31 205 50 204 74 220S111 237 130 222M7 267C31 250 50 249 74 265S115 282 140 263"></path><path d="M475 130C499 112 518 115 541 132S582 149 605 132S624 121 633 125M484 175C504 160 521 162 541 177S582 194 605 177S624 166 633 170M484 220C504 205 521 207 541 222S582 239 605 222S624 211 633 215M475 265C499 247 518 250 541 267S582 284 605 267S624 256 633 260"></path></g><g id="postmark-rings"><circle cx="307.2" cy="200" r="179.2"></circle><circle cx="307.2" cy="200" r="164" stroke-width="2.5"></circle><circle cx="307.2" cy="200" r="146" stroke-width="4.6" stroke-dasharray=".1 12.65"></circle></g><g id="postmark-wheel"><use href="#wheel-spoke"></use><use href="#wheel-spoke" transform="rotate(45 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(90 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(135 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(180 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(225 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(270 307.2 200)"></use><use href="#wheel-spoke" transform="rotate(315 307.2 200)"></use><circle cx="307.2" cy="200" r="87" stroke-width="8"></circle><circle cx="307.2" cy="200" r="76" stroke-width="2.5"></circle><circle cx="307.2" cy="200" r="18" stroke-width="6"></circle><circle cx="307.2" cy="200" r="5" stroke-width="4"></circle></g></g></svg></div></body></html>
````

## 点缀-花叶剪影簇

逻辑路径：assets/模板库/点缀/点缀-花叶剪影簇.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0225
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-花叶剪影簇</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#777}.component{--size:500px;--leaf:#dedede;--flower:#f6f6f6;--leaf-opacity:.65;--flower-opacity:.95;--stem-width:2;--rotation:0deg;width:min(var(--size),84vw,72vh);aspect-ratio:5/6;transform:rotate(var(--rotation));transform-origin:50% 50%}.component svg{display:block;width:100%;height:100%}.leaves{fill:var(--leaf);opacity:var(--leaf-opacity)}.stems{fill:none;stroke:var(--leaf);stroke-width:var(--stem-width);stroke-linecap:round}.flowers{fill:var(--flower);opacity:var(--flower-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" data-variant="密集花叶簇"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 500 600" role="img" aria-label="点缀-花叶剪影簇"><defs><filter id="soft-edge" x="-2%" y="-2%" width="104%" height="104%"><fegaussianblur stddeviation=".55"></fegaussianblur></filter><path id="leaf" d="M0 0C10-22 36-31 65-23C56-2 30 10 0 0Z"></path><path id="thin-leaf" d="M0 0C14-13 54-21 83-16C58 2 20 8 0 0Z"></path><path id="small-flower" d="M-2-5C-13-10-13-22-5-25C3-29 10-22 7-10C16-21 29-17 27-7C27 0 18 5 10 3C23 8 23 20 14 23C6 26 1 16 0 10C-4 24-16 24-20 15C-24 7-15 2-8 1C-22 2-29-8-23-15C-17-21-8-15-2-5Z"></path><g id="flower-cluster"><use href="#small-flower" transform="translate(-20 2) rotate(-22) scale(.7)"></use><use href="#small-flower" transform="translate(12 -20) rotate(32) scale(.78)"></use><use href="#small-flower" transform="translate(30 12) rotate(68) scale(.61)"></use><use href="#small-flower" transform="translate(0 26) rotate(-15) scale(.65)"></use></g></defs><g data-role="内容层" filter="url(#soft-edge)"><g id="botanical-leaves" class="leaves"><g class="stems"><path d="M244 589C260 494 245 404 224 321S199 156 220 48M243 573C217 455 151 374 116 292S77 160 98 95M248 554C290 445 325 355 348 249S376 117 403 57M249 517C221 451 168 433 112 414S32 363 16 331M260 489C321 454 367 404 412 327S462 249 486 232M227 460C200 359 213 269 275 196S314 111 304 22M242 401C267 334 297 302 336 284M174 404C155 331 161 258 173 208M314 393C365 372 407 376 466 354M122 305C88 287 43 258 14 224M288 457C320 473 365 502 392 536"></path></g><use href="#leaf" transform="translate(224 491) rotate(202) scale(1.12)"></use><use href="#leaf" transform="translate(246 529) rotate(-36) scale(1.18)"></use><use href="#leaf" transform="translate(211 452) rotate(229) scale(1.04)"></use><use href="#leaf" transform="translate(191 419) rotate(173) scale(.92)"></use><use href="#leaf" transform="translate(170 377) rotate(235) scale(1.03)"></use><use href="#leaf" transform="translate(145 340) rotate(-61) scale(.86)"></use><use href="#leaf" transform="translate(121 294) rotate(206) scale(.98)"></use><use href="#leaf" transform="translate(105 249) rotate(-49) scale(.85)"></use><use href="#leaf" transform="translate(91 211) rotate(224) scale(.85)"></use><use href="#leaf" transform="translate(88 169) rotate(-54) scale(.67)"></use><use href="#leaf" transform="translate(89 136) rotate(208) scale(.6)"></use><use href="#leaf" transform="translate(233 389) rotate(-43) scale(1.1)"></use><use href="#leaf" transform="translate(224 331) rotate(195) scale(.86)"></use><use href="#leaf" transform="translate(213 276) rotate(-47) scale(.91)"></use><use href="#leaf" transform="translate(207 225) rotate(208) scale(.87)"></use><use href="#leaf" transform="translate(207 173) rotate(-49) scale(.73)"></use><use href="#leaf" transform="translate(211 124) rotate(221) scale(.65)"></use><use href="#thin-leaf" transform="translate(218 84) rotate(-84) scale(.88)"></use><use href="#leaf" transform="translate(282 471) rotate(9) scale(1.02)"></use><use href="#leaf" transform="translate(292 439) rotate(-68) scale(.96)"></use><use href="#leaf" transform="translate(311 390) rotate(6) scale(1.02)"></use><use href="#leaf" transform="translate(322 344) rotate(218) scale(.95)"></use><use href="#leaf" transform="translate(338 287) rotate(-29) scale(.95)"></use><use href="#leaf" transform="translate(348 248) rotate(234) scale(.79)"></use><use href="#leaf" transform="translate(359 195) rotate(-30) scale(.92)"></use><use href="#leaf" transform="translate(371 149) rotate(230) scale(.76)"></use><use href="#leaf" transform="translate(385 102) rotate(-34) scale(.83)"></use><use href="#thin-leaf" transform="translate(403 63) rotate(-62) scale(.78)"></use><use href="#leaf" transform="translate(263 220) rotate(220) scale(.75)"></use><use href="#leaf" transform="translate(289 177) rotate(-40) scale(.71)"></use><use href="#leaf" transform="translate(305 123) rotate(205) scale(.7)"></use><use href="#thin-leaf" transform="translate(306 74) rotate(-99) scale(.76)"></use><use href="#leaf" transform="translate(101 410) rotate(171) scale(1.17)"></use><use href="#thin-leaf" transform="translate(71 391) rotate(225) scale(.82)"></use><use href="#leaf" transform="translate(129 419) rotate(-69) scale(.82)"></use><use href="#leaf" transform="translate(386 370) rotate(-18) scale(1.15)"></use><use href="#leaf" transform="translate(416 321) rotate(-53) scale(.9)"></use><use href="#leaf" transform="translate(445 277) rotate(211) scale(.77)"></use><use href="#thin-leaf" transform="translate(463 253) rotate(-14) scale(.42)"></use><use href="#leaf" transform="translate(338 491) rotate(-18) scale(.85)"></use><use href="#leaf" transform="translate(365 517) rotate(67) scale(.77)"></use><use href="#leaf" transform="translate(72 269) rotate(213) scale(.88)"></use><use href="#leaf" transform="translate(158 308) rotate(229) scale(.72)"></use><use href="#leaf" transform="translate(164 255) rotate(-70) scale(.71)"></use></g><g id="botanical-flowers" class="flowers"><use href="#flower-cluster" transform="translate(103 109) rotate(-18) scale(.98)"></use><use href="#flower-cluster" transform="translate(166 186) rotate(28) scale(.91)"></use><use href="#flower-cluster" transform="translate(222 69) rotate(7) scale(.76)"></use><use href="#flower-cluster" transform="translate(295 91) rotate(-24) scale(.82)"></use><use href="#flower-cluster" transform="translate(276 181) rotate(23) scale(1.03)"></use><use href="#flower-cluster" transform="translate(395 95) rotate(14) scale(.94)"></use><use href="#flower-cluster" transform="translate(354 201) rotate(-16) scale(.89)"></use><use href="#flower-cluster" transform="translate(211 270) rotate(42) scale(.91)"></use><use href="#flower-cluster" transform="translate(122 285) rotate(-9) scale(1.02)"></use><use href="#flower-cluster" transform="translate(323 288) rotate(12) scale(1.12)"></use><use href="#flower-cluster" transform="translate(407 317) rotate(38) scale(.9)"></use><use href="#flower-cluster" transform="translate(251 379) rotate(-27) scale(.87)"></use><use href="#flower-cluster" transform="translate(152 414) rotate(8) scale(.83)"></use><use href="#flower-cluster" transform="translate(348 451) rotate(-12) scale(.73)"></use><use href="#small-flower" transform="translate(76 374) rotate(35) scale(.57)"></use><use href="#small-flower" transform="translate(377 529) rotate(-18) scale(.7)"></use><use href="#small-flower" transform="translate(215 513) rotate(15) scale(.6)"></use><use href="#small-flower" transform="translate(279 472) rotate(25) scale(.52)"></use></g></g></svg></div></body></html>
````

## 点缀-花叶底边

逻辑路径：assets/模板库/点缀/点缀-花叶底边.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0094
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-花叶底边</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#dedede}.component{--size:1100px;--leaf-dark:#686868;--leaf-light:#999;--petal-light:#f4f4f4;--petal-shade:#c5c5c5;--brush-opacity:.3;--vein-width:1.5;width:min(var(--size),94vw,235vh);aspect-ratio:45/17;overflow:hidden}.component svg{display:block;width:100%;height:100%}.brush{fill:none;stroke:#efefef;stroke-width:var(--vein-width);stroke-linecap:round;opacity:var(--brush-opacity)}.dark-brush{fill:none;stroke:#656565;stroke-width:1;opacity:.19}.petal{stroke:#adadad;stroke-width:.7;stroke-opacity:.4}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 900 340" role="img" aria-label="点缀-花叶底边"><defs><lineargradient id="leaf-shade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#aaa"></stop><stop offset=".48" stop-color="#777"></stop><stop offset="1" stop-color="#5f5f5f"></stop></lineargradient><lineargradient id="petal-shade" x1="0" y1="0" x2=".7" y2="1"><stop stop-color="#fafafa"></stop><stop offset=".6" stop-color="#e5e5e5"></stop><stop offset="1" stop-color="#bdbdbd"></stop></lineargradient><g id="long-leaf"><path d="M0 0C36-22 81-30 124-19C148-13 170-4 190 0C151 9 120 24 81 24C48 23 23 13 0 0Z" fill="url(#leaf-shade)"></path><path class="brush" d="M8 0C63-3 122 2 177 0M35-3L57-18M52-2L78-21M72-1L99-19M91 0L118-16M113 1L139-10M33 3L53 16M52 3L75 20M75 3L97 19M99 3L120 13M124 3L143 8"></path><path class="dark-brush" d="M13 2C76 5 125-1 176 0M46-7L62-17M90 7L105 16M119-4L132-10"></path></g><g id="short-leaf"><path d="M0 0C22-27 53-37 88-26C82-1 44 16 0 0Z" fill="currentColor"></path><path class="brush" d="M5 0Q48-10 80-23M26-6L32-21M39-10L49-28M49-12L68-29M30-4L44 4M48-10L62-2"></path></g><clippath id="edge"><rect width="900" height="340"></rect></clippath><clippath id="flower-outline"><path d="M397 244C367 217 325 173 346 122C357 92 382 77 400 90C424 74 453 92 456 122C471 106 502 116 508 148C552 158 558 205 531 228C558 257 545 296 512 304C512 341 466 355 442 330C412 358 375 346 363 324C326 345 286 326 292 290C255 279 242 246 260 220C242 192 263 155 293 158C292 126 326 113 347 131Z"></path></clippath><filter id="paint-edge" x="-3%" y="-4%" width="106%" height="108%"><feturbulence type="fractalNoise" basefrequency=".075" numoctaves="2" seed="6" result="noise"></feturbulence><fedisplacementmap in="SourceGraphic" in2="noise" scale="1.8" xchannelselector="R" ychannelselector="G"></fedisplacementmap></filter></defs><g clip-path="url(#edge)" data-role="内容层"><g id="leaf-back" filter="url(#paint-edge)"><g fill="none" stroke="#777" stroke-width="3"><path d="M398 362Q203 277-22 195M444 358Q644 257 922 189M347 351Q211 204 92 161M512 355Q695 197 817 166"></path></g><use href="#long-leaf" transform="translate(198 314) rotate(-151) scale(1.45 .94)"></use><use href="#long-leaf" transform="translate(280 328) rotate(-143) scale(1.5 .92)"></use><use href="#long-leaf" transform="translate(347 340) rotate(-134) scale(1.33 .84)"></use><use href="#long-leaf" transform="translate(226 333) rotate(-175) scale(1.45 1.1)"></use><use href="#long-leaf" transform="translate(126 292) rotate(-167) scale(1.08 .94)"></use><use href="#long-leaf" transform="translate(324 348) rotate(-163) scale(1.57 1.02)"></use><use href="#long-leaf" transform="translate(505 347) rotate(-37) scale(1.56 .86)"></use><use href="#long-leaf" transform="translate(565 337) rotate(-24) scale(1.6 1.02)"></use><use href="#long-leaf" transform="translate(661 309) rotate(-37) scale(1.38 .91)"></use><use href="#long-leaf" transform="translate(686 324) rotate(-10) scale(1.39 1.13)"></use><use href="#long-leaf" transform="translate(768 288) rotate(-25) scale(1.1 .85)"></use><use href="#long-leaf" transform="translate(580 353) rotate(-9) scale(1.57 .92)"></use><use href="#long-leaf" transform="translate(371 354) rotate(-113) scale(.86 .69)"></use><use href="#long-leaf" transform="translate(467 358) rotate(-67) scale(.92 .68)"></use></g><g id="flower-front" filter="url(#paint-edge)"><g class="petal"><path d="M395 249C366 218 326 169 346 122C357 92 382 77 400 90C424 74 453 92 456 122C475 170 436 218 413 251Z" fill="url(#petal-shade)"></path><path d="M395 240C359 232 301 206 293 169C284 133 319 111 345 130C369 110 399 137 406 168C414 194 408 220 395 240Z" fill="#ddd"></path><path d="M391 250C347 267 293 264 266 235C239 211 249 177 276 162C301 150 322 163 332 179C373 169 397 205 391 250Z" fill="url(#petal-shade)"></path><path d="M407 245C413 194 449 124 476 118C507 113 522 145 512 164C546 156 560 199 540 222C513 251 453 262 407 245Z" fill="url(#petal-shade)"></path><path d="M410 247C453 216 511 217 538 239C561 260 543 295 513 304C512 337 474 350 449 331C423 311 411 277 410 247Z" fill="#d8d8d8"></path><path d="M400 248C378 226 330 218 293 232C263 241 267 274 292 290C281 323 317 346 350 330C381 321 403 281 400 248Z" fill="url(#petal-shade)"></path><path d="M401 244C364 271 352 300 365 325C376 350 412 357 436 335C466 346 487 318 472 290C457 264 429 250 401 244Z" fill="url(#petal-shade)"></path><path d="M402 253C378 238 363 214 371 198C381 180 401 185 410 203C424 178 451 188 453 208C456 229 430 248 414 255Z" fill="#f4f4f4"></path><path d="M405 252C376 240 358 251 365 269C373 289 395 285 408 272C417 293 445 285 449 271C453 253 431 244 405 252Z" fill="#eaeaea"></path></g><g clip-path="url(#flower-outline)" fill="none" stroke-linecap="round"><g stroke="#fff" stroke-width="2" opacity=".42"><path d="M397 223Q367 157 382 103M403 214Q390 149 404 99M414 215Q431 155 437 115M369 218Q335 190 315 151M361 237Q307 200 274 189M359 246Q305 234 269 229M439 228Q479 179 492 141M450 237Q501 211 532 188M453 259Q496 259 529 276M438 280Q456 311 482 324M397 285Q388 317 406 337M371 281Q334 311 306 309"></path></g><g class="dark-brush"><path d="M391 230Q372 183 365 145M413 234Q443 190 452 153M371 243Q321 223 295 201M431 247Q484 226 521 216M430 272Q463 287 479 311M392 278Q374 306 379 325M357 268Q320 288 301 281"></path><path d="M383 226L379 212M375 207L370 194M366 241L345 232M327 225L313 220M432 235L448 216M459 203L469 191M442 264L463 269M473 273L489 283"></path></g></g><g fill="none" stroke="#8c8c8c" stroke-width="1.5" opacity=".7"><path d="M406 252L392 237M409 252L410 231M414 253L429 238M415 257L434 258M402 257L386 265M406 261L408 278"></path></g><g fill="#858585"><ellipse cx="391" cy="236" rx="3" ry="4" transform="rotate(-35 391 236)"></ellipse><ellipse cx="410" cy="230" rx="2.5" ry="4"></ellipse><ellipse cx="430" cy="237" rx="3.5" ry="2.5" transform="rotate(-40 430 237)"></ellipse><ellipse cx="435" cy="258" rx="3.5" ry="2.3"></ellipse><ellipse cx="384" cy="266" rx="3" ry="2.3"></ellipse><ellipse cx="409" cy="279" rx="2.6" ry="3.6"></ellipse><path d="M401 249L409 245L417 251L413 260L404 261L399 255Z"></path></g><g style="color:var(--leaf-dark)"><use href="#short-leaf" transform="translate(309 351) rotate(-157) scale(1.4 1.06)"></use><use href="#short-leaf" transform="translate(255 352) rotate(-176) scale(1.47 1.04)"></use><use href="#short-leaf" transform="translate(353 358) rotate(-142) scale(1.06 .84)"></use><use href="#short-leaf" transform="translate(495 355) rotate(-21) scale(1.3 1)"></use><use href="#short-leaf" transform="translate(563 353) rotate(-5) scale(1.55 1.13)"></use><use href="#short-leaf" transform="translate(714 355) rotate(-14) scale(1.5 1.12)"></use></g><g style="color:var(--leaf-light)"><use href="#short-leaf" transform="translate(163 354) rotate(-167) scale(1.37 1.1)"></use><use href="#short-leaf" transform="translate(231 355) rotate(-135) scale(.99 .9)"></use><use href="#short-leaf" transform="translate(536 360) rotate(-40) scale(1.03 .8)"></use><use href="#short-leaf" transform="translate(641 360) rotate(-21) scale(1.35 1)"></use><use href="#short-leaf" transform="translate(815 358) rotate(-22) scale(1.18 1.1)"></use></g></g></g></svg></div></body></html>
````

## 点缀-花枝栖鸟

逻辑路径：assets/模板库/点缀/点缀-花枝栖鸟.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0087
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-花枝栖鸟</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:365px;--branch-width:2.4;--ink:#666663;--wash-opacity:.72;width:min(var(--size),86vw,64vh);aspect-ratio: .73;position:relative}.component svg{display:block;width:100%;height:100%;overflow:visible}.branch{fill:none;stroke:var(--ink);stroke-linecap:round;stroke-linejoin:round;stroke-width:var(--branch-width)}.wash{opacity:var(--wash-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-花枝栖鸟"><svg viewbox="0 0 365 500" xmlns="http://www.w3.org/2000/svg"><defs><lineargradient id="birdBody" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#d5d5d1"></stop><stop offset=".5" stop-color="#9a9a96"></stop><stop offset="1" stop-color="#e7e7e3"></stop></lineargradient><lineargradient id="tail" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#666663"></stop><stop offset="1" stop-color="#b8b8b3" stop-opacity=".55"></stop></lineargradient><radialgradient id="petal"><stop stop-color="#a5a5a0" stop-opacity=".65"></stop><stop offset=".6" stop-color="#d3d3cf" stop-opacity=".8"></stop><stop offset="1" stop-color="#ededE9" stop-opacity=".5"></stop></radialgradient><g id="bloom"><path d="M0 0C-13-3-13-15-6-16C1-17 4-9 0 0Z" fill="url(#petal)"></path><path d="M0 0C-2-11 7-19 12-13C17-7 8-1 0 0Z" fill="url(#petal)"></path><path d="M0 0C8-8 20-3 16 4C13 11 5 7 0 0Z" fill="url(#petal)"></path><path d="M0 0C11 5 10 17 3 16C-4 14-4 5 0 0Z" fill="url(#petal)"></path><path d="M0 0C-5 10-18 11-17 3C-16-5-7-5 0 0Z" fill="url(#petal)"></path><path d="M-5-5L0 1 5-6M-7 2L0 1 5 6" fill="none" stroke="#858580" stroke-width=".65"></path><g fill="#777772"><circle r="1.9"></circle><circle cx="-5" cy="-5" r="1"></circle><circle cx="5" cy="-6" r="1"></circle><circle cx="5" cy="6" r=".9"></circle></g></g></defs><g id="branch" class="branch"><path d="M362 0C340 61 334 111 302 157C264 207 190 263 124 317C75 356 37 419 3 498" stroke="#858580" stroke-width="4"></path><path d="M365 145C334 155 302 173 274 174C234 178 214 155 192 148" stroke-width="3"></path><path d="M328 94C301 75 275 60 267 24M288 171C276 143 260 127 235 111M218 240C224 207 211 180 192 148M150 296C111 285 81 264 55 230M121 319C132 351 118 388 104 410M68 388C45 387 18 369 1 352M338 59C352 43 359 28 365 13M245 215C270 218 299 206 319 190"></path><path d="M274 48L253 43M289 69L299 42M254 129L264 106M206 188L181 181M212 212L237 191M98 280L94 248M74 254L47 259M125 358L151 343M113 390L91 376M43 430L63 453M33 379L30 355" stroke-width="1.1"></path><g fill="#a5a5a0" stroke="none" opacity=".65"><path d="M265 107Q251 96 259 84Q269 92 265 107Z"></path><path d="M95 251Q80 242 82 229Q96 234 95 251Z"></path><path d="M150 344Q162 328 168 335Q164 345 150 344Z"></path><path d="M300 43Q295 29 304 22Q309 34 300 43Z"></path><path d="M181 181Q165 185 163 175Q176 171 181 181Z"></path></g></g><g id="bird" aria-label="点缀-花枝栖鸟"><path d="M264 150C248 183 217 226 198 260C220 249 251 213 276 168Z" fill="url(#tail)"></path><path d="M275 158C260 194 230 237 212 263C237 248 269 206 287 166Z" fill="#82827e" opacity=".78"></path><path d="M263 179L211 250M275 178L225 246" fill="none" stroke="#e0e0da" stroke-width="1.1" opacity=".6"></path><path d="M287 157L282 174 270 177M294 158L294 174 304 176M282 174L288 177M294 174L287 177" fill="none" stroke="#64645f" stroke-width="1.8" stroke-linecap="round"></path><path d="M257 154C247 140 258 119 278 109C288 103 287 91 292 82C299 67 319 70 326 84C332 96 324 107 315 115C314 132 305 154 288 163C275 169 264 163 257 154Z" fill="url(#birdBody)"></path><path d="M290 88C292 75 307 68 318 77C323 80 326 84 327 90C315 86 306 93 299 101Z" fill="#61615e"></path><path d="M323 92L339 97 324 101Z" fill="#5b5b57"></path><path d="M299 102C310 98 316 99 323 102C315 110 311 116 307 125C301 119 298 111 299 102Z" fill="#e5e5df" opacity=".85"></path><path d="M282 114C269 117 258 131 259 149C263 158 280 158 291 142C296 134 296 122 294 116Z" fill="#747470" class="wash"></path><path d="M288 120Q275 131 264 148M291 128Q280 144 270 151M288 139L277 153" fill="none" stroke="#d2d2cb" stroke-width="1.3" opacity=".72"></path><path d="M307 124Q304 147 287 157" fill="none" stroke="#efefea" stroke-width="3" opacity=".42"></path><circle cx="317" cy="89" r="3" fill="#333330"></circle><circle cx="317.7" cy="88.2" r=".85" fill="#f4f4ef"></circle></g><g id="flowers"><use href="#bloom" transform="translate(267 25) rotate(-15) scale(.8)"></use><use href="#bloom" transform="translate(253 43) scale(.58)"></use><use href="#bloom" transform="translate(341 64) rotate(22) scale(.72)"></use><use href="#bloom" transform="translate(236 112) rotate(-20) scale(.87)"></use><use href="#bloom" transform="translate(192 148) scale(.95)"></use><use href="#bloom" transform="translate(238 192) rotate(40) scale(.63)"></use><use href="#bloom" transform="translate(320 190) scale(.72)"></use><use href="#bloom" transform="translate(55 231) rotate(-25) scale(.8)"></use><use href="#bloom" transform="translate(94 251) scale(.57)"></use><use href="#bloom" transform="translate(125 319) rotate(15) scale(.72)"></use><use href="#bloom" transform="translate(105 409) scale(.73)"></use><use href="#bloom" transform="translate(30 355) rotate(20) scale(.64)"></use><use href="#bloom" transform="translate(62 452) scale(.6)"></use><g fill="#b0b0aa"><ellipse cx="182" cy="180" rx="3" ry="5" transform="rotate(-40 182 180)"></ellipse><ellipse cx="48" cy="259" rx="4" ry="5"></ellipse><ellipse cx="90" cy="375" rx="3" ry="5"></ellipse></g></g></svg></div></body></html>
````

## 点缀-虚线圈

逻辑路径：assets/模板库/点缀/点缀-虚线圈.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0118
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-虚线圈</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:310px;--stroke:2.3;--dash:12;--gap:14;--ink:#777774;width:min(var(--size),80vw,80vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%}.ring{fill:none;stroke:var(--ink);stroke-width:var(--stroke);stroke-dasharray:var(--dash) var(--gap);stroke-linecap:butt}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-虚线圈"><svg xmlns="http://www.w3.org/2000/svg" viewbox="-1.15 -1.15 102.3 102.3"><circle class="ring" cx="50" cy="50" r="50" transform="rotate(-90 50 50)"></circle></svg></div></body></html>
````

## 点缀-蜡封徽章

逻辑路径：assets/模板库/点缀/点缀-蜡封徽章.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0079
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-蜡封徽章</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:360px;--emboss-width:7.2;--emboss-offset:3.6px;--highlight-opacity:.45;--shade-opacity:.5;--shadow-opacity:.18;--shadow-blur:24px;width:min(var(--size),78vw,78vh);aspect-ratio:1}.component svg{display:block;width:100%;height:100%;overflow:visible}.engraving{fill:none;stroke-width:var(--emboss-width);stroke-linecap:round;stroke-linejoin:round}.light{stroke:#f6f6f1;opacity:var(--highlight-opacity);transform:translate(calc(-1 * var(--emboss-offset)),calc(-1 * var(--emboss-offset)))}.dark{stroke:#292927;opacity:var(--shade-opacity);transform:translate(var(--emboss-offset),var(--emboss-offset))}.groove{stroke:#757570;stroke-width:3.4}.shadow{fill:#222;opacity:var(--shadow-opacity);filter:blur(var(--shadow-blur));transform:translateY(16px)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-蜡封徽章"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 400 400"><defs><radialgradient id="wax" cx="44%" cy="39%" r="62%"><stop offset="0" stop-color="#b8b8b2"></stop><stop offset=".65" stop-color="#a5a59f"></stop><stop offset=".83" stop-color="#777773"></stop><stop offset=".93" stop-color="#bcbcb5"></stop><stop offset="1" stop-color="#656561"></stop></radialgradient><lineargradient id="rim" x1="0" y1="0" x2=".7" y2="1"><stop stop-color="#eeeee7" stop-opacity=".7"></stop><stop offset=".48" stop-color="#a2a29b" stop-opacity=".1"></stop><stop offset="1" stop-color="#3b3b38" stop-opacity=".5"></stop></lineargradient><path id="edge" d="M200 20C215 18 232 22 247 27C262 30 278 35 291 44C307 51 321 63 331 76C344 87 353 104 361 120C367 134 374 148 376 166C380 180 382 194 379 211C380 228 374 244 370 258C365 275 357 288 348 302C338 314 326 327 313 337C299 348 286 354 270 363C255 369 239 375 223 378C207 380 190 382 174 377C157 376 143 370 127 365C112 358 96 351 85 340C70 331 60 318 49 304C40 290 33 277 28 260C24 245 20 230 20 213C18 197 20 181 23 164C28 149 31 133 39 119C46 103 56 89 66 78C78 64 91 54 106 46C119 36 135 31 151 26C167 22 183 19 200 20Z"></path><g id="rings"><circle cx="200" cy="200" r="140"></circle><circle cx="200" cy="200" r="129" stroke-width="3.8"></circle></g><g id="symbol"><path d="M200 111L223 174L289 177L237 218L254 282L200 246L146 282L163 218L111 177L177 174Z"></path></g></defs><use href="#edge" class="shadow"></use><g id="seal-body"><use href="#edge" fill="url(#wax)"></use><use href="#edge" fill="none" stroke="url(#rim)" stroke-width="3"></use><path d="M54 126C79 61 147 34 199 33" fill="none" stroke="#efefe7" stroke-width="5" stroke-linecap="round" opacity=".18"></path><path d="M354 273C326 337 261 364 212 365" fill="none" stroke="#444440" stroke-width="4" stroke-linecap="round" opacity=".17"></path></g><g id="seal-rings" class="engraving"><use href="#rings" class="light"></use><use href="#rings" class="dark"></use><use href="#rings" class="groove"></use></g><g id="seal-symbol" class="engraving" aria-label="点缀-蜡封徽章"><use href="#symbol" class="light"></use><use href="#symbol" class="dark"></use><use href="#symbol" class="groove"></use></g></svg></div></body></html>
````

## 点缀-蜡笔弯箭头

逻辑路径：assets/模板库/点缀/点缀-蜡笔弯箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0229
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-蜡笔弯箭头</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:560px;--stroke-width:22.5;--ink:#91918c;--grain-opacity:.15;--width-jitter:.15;width:min(var(--size),86vw,300vh);aspect-ratio:5}.component svg{width:100%;height:100%;display:block}.stroke{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}.grain{opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-蜡笔弯箭头"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 500 100"><defs><path id="route" d="M23 39C138 75 309 83 473 35M425 17L473 35 445 78"></path><mask id="strokeMask" maskunits="userSpaceOnUse" x="0" y="0" width="500" height="100"><use href="#route" fill="none" stroke="white" stroke-width="22.5" stroke-linecap="round" stroke-linejoin="round"></use></mask><pattern id="crayon" width="39" height="29" patternunits="userSpaceOnUse"><g fill="#fff"><ellipse cx="3" cy="5" rx="1.6" ry=".9"></ellipse><circle cx="15" cy="21" r="1.1"></circle><ellipse cx="28" cy="9" rx="2.4" ry="1.1" transform="rotate(-21 28 9)"></ellipse><circle cx="34" cy="25" r=".7"></circle><path d="M8 13L13 12 12 14 9 15ZM22 24L25 22 27 23 24 25Z"></path></g></pattern></defs><g id="arrow-stroke"><use href="#route" class="stroke" opacity=".92"></use><path d="M26 40C94 61 170 70 234 65M279 65Q381 58 463 35M430 18L469 34" fill="none" stroke="#a4a49e" stroke-width="25" stroke-linecap="round" stroke-linejoin="round" opacity=".3"></path><use href="#route" fill="none" stroke="#73736e" stroke-width="17" stroke-linecap="round" stroke-linejoin="round" opacity=".12"></use><g mask="url(#strokeMask)"><rect width="500" height="100" fill="url(#crayon)" class="grain"></rect><path d="M14 45Q167 90 352 62M331 56L469 25M445 70L465 43" fill="none" stroke="#f5f5f3" stroke-width="1.2" opacity=".15"></path></g></g></svg></div></body></html>
````

## 点缀-蜡笔雨滴

逻辑路径：assets/模板库/点缀/点缀-蜡笔雨滴.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0226
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-蜡笔雨滴</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:360px;--rotation:30deg;--ink:#92928d;--grain-opacity:.2;--grain-size:4px;width:min(var(--size),82vw,82vh);aspect-ratio:1}.component svg{width:100%;height:100%;display:block}.drop{transform:rotate(var(--rotation));transform-origin:180px 180px}.grain{opacity:var(--grain-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-蜡笔雨滴"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 360 360"><defs><path id="dropShape" d="M185 30C184 62 205 115 221 163C232 198 237 229 237 257C237 302 216 330 182 330C146 330 123 305 123 265C123 223 142 174 157 129C170 89 178 51 185 30Z"></path><clippath id="dropClip"><use href="#dropShape"></use></clippath><lineargradient id="dropWash" x1="0" y1="0" x2="1" y2=".5"><stop stop-color="#c3c3bb" stop-opacity=".28"></stop><stop offset=".6" stop-color="#7a7a74" stop-opacity="0"></stop><stop offset="1" stop-color="#5e5e59" stop-opacity=".13"></stop></lineargradient><pattern id="grain" width="31" height="37" patternunits="userSpaceOnUse"><g fill="#fafaf7"><circle cx="4" cy="6" r="1.5"></circle><ellipse cx="19" cy="3" rx="2" ry="1.1"></ellipse><path d="M12 18L15 16 17 18 14 20ZM24 28L28 27 29 30 25 31Z"></path><circle cx="6" cy="32" r="1"></circle><ellipse cx="28" cy="14" rx="1.2" ry="2"></ellipse></g></pattern><pattern id="fineGrain" width="47" height="43" patternunits="userSpaceOnUse"><path d="M8 9L10 13M33 18L35 20M18 36L21 37" stroke="#54544f" stroke-width="1" opacity=".11"></path></pattern></defs><g class="drop"><g id="drop-body"><use href="#dropShape" fill="var(--ink)"></use><use href="#dropShape" fill="url(#dropWash)"></use></g><g id="drop-grain" clip-path="url(#dropClip)"><rect x="120" y="25" width="120" height="310" fill="url(#grain)" class="grain"></rect><rect x="120" y="25" width="120" height="310" fill="url(#fineGrain)"></rect><path d="M176 69C170 137 126 218 132 280M225 214Q242 286 215 312" fill="none" stroke="#f5f5f3" stroke-width="2" stroke-dasharray="3 13 7 19 2 8" opacity=".23"></path></g></g></svg></div></body></html>
````

## 点缀-蝴蝶剪影

逻辑路径：assets/模板库/点缀/点缀-蝴蝶剪影.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0233
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-蝴蝶剪影</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f3}.component{--size:360px;--silhouette-fill:#555552;--rotation:-16deg;--antenna-width:3.4;width:min(var(--size),67vw,67vh);aspect-ratio:1;transform:rotate(var(--rotation));transform-origin:50% 50%}.component svg{display:block;width:100%;height:100%;overflow:visible}.silhouette{fill:var(--silhouette-fill)}.antennae{fill:none;stroke:var(--silhouette-fill);stroke-width:var(--antenna-width);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-蝴蝶剪影"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 320 320"><g id="butterfly-silhouette" class="silhouette"><path d="M154 173C137 141 114 80 78 43C60 24 35 19 21 34C4 53 9 88 20 116C29 141 56 164 82 176C53 177 30 192 31 217C32 244 53 280 79 289C108 298 130 263 147 232L160 200Z"></path><path d="M165 170C176 131 203 72 239 42C259 25 283 24 297 40C311 57 305 92 293 120C281 148 253 164 233 176C262 174 287 190 286 214C285 241 263 276 240 283C211 294 190 262 175 231L159 200Z"></path><path d="M153 141C151 132 155 124 161 124C168 125 172 133 169 141C169 153 172 174 170 195C169 220 165 246 160 261C155 249 151 223 150 199C149 175 152 152 153 141Z"></path><ellipse cx="161" cy="129" rx="7.4" ry="9"></ellipse><path class="antennae" d="M158 125C153 110 145 99 136 99M165 124C170 110 180 100 187 102"></path><circle cx="136" cy="99" r="2.7"></circle><circle cx="187" cy="102" r="2.5"></circle></g></svg></div></body></html>
````

## 点缀-裁边同心圆

逻辑路径：assets/模板库/点缀/点缀-裁边同心圆.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0165
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-裁边同心圆</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#f5f5f4}.component{--size:min(36vmin,210px);--outer:#dededb;--inner:#777774;--inner-ratio:.7;width:var(--size);aspect-ratio:1/2;overflow:hidden;position:relative}.disc{position:absolute;width:200%;height:100%;border-radius:50%;background:var(--outer);left:0;top:0}.disc:after{content:'';position:absolute;width:calc(100% * var(--inner-ratio));height:calc(100% * var(--inner-ratio));left:50%;top:50%;transform:translate(-50%,-50%);border-radius:50%;background:var(--inner)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-裁边同心圆"><div class="disc"></div></div></body></html>
````

## 点缀-规则缝线边

逻辑路径：assets/模板库/点缀/点缀-规则缝线边.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-规则缝线边</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-stitched { position:relative; padding:calc(var(--vl-stitch-inset,8px) + var(--vl-stitch-length,10px) + 12px); background:var(--vl-tint,#edb9d0); color:var(--vl-ink,#631934); }
.vl-stitch { position:absolute; pointer-events:none; z-index:1; }
.vl-stitch--top,.vl-stitch--bottom { left:var(--vl-stitch-inset,8px); right:var(--vl-stitch-inset,8px); height:var(--vl-stitch-length,10px); background:repeating-linear-gradient(calc(90deg - var(--vl-stitch-tilt,8deg)),transparent 0 calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)),var(--vl-stitch-color,#977d62) calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)) var(--vl-stitch-step,12px)); }
.vl-stitch--top { top:var(--vl-stitch-inset,8px); }.vl-stitch--bottom { bottom:var(--vl-stitch-inset,8px); }
.vl-stitch--left,.vl-stitch--right { top:var(--vl-stitch-inset,8px); bottom:var(--vl-stitch-inset,8px); width:var(--vl-stitch-length,10px); background:repeating-linear-gradient(var(--vl-stitch-tilt,8deg),transparent 0 calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)),var(--vl-stitch-color,#977d62) calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)) var(--vl-stitch-step,12px)); }
.vl-stitch--left { left:var(--vl-stitch-inset,8px); }.vl-stitch--right { right:var(--vl-stitch-inset,8px); }
</style></head><body><section class="vl-stitched"><span class="vl-stitch vl-stitch--top" aria-hidden="true"></span><span class="vl-stitch vl-stitch--bottom" aria-hidden="true"></span><span class="vl-stitch vl-stitch--left" aria-hidden="true"></span><span class="vl-stitch vl-stitch--right" aria-hidden="true"></span><p>布面内容</p></section>
</body></html>
````

## 点缀-起伏山丘剪影

逻辑路径：assets/模板库/点缀/点缀-起伏山丘剪影.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0123
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-起伏山丘剪影</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#f5f5f4}.component{--size:min(86vw,900px,400vh);--hill-fill:#676764;width:var(--size);aspect-ratio:1000/210}.component svg{display:block;width:100%;height:100%;fill:var(--hill-fill)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-起伏山丘剪影"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 1000 210"><path d="M0 210 C135 62 278 84 400 90 C520 101 596 -17 741 6 C842 15 842 91 931 115 C984 131 993 166 1000 210 Z"></path></svg></div></body></html>
````

## 点缀-连续卷线

逻辑路径：assets/模板库/点缀/点缀-连续卷线.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0193
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-连续卷线</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#f5f5f4}.component{--size:min(92vw,1100px,750vh);--stroke:#5b5b58;--stroke-width:6.3;--rotation:0deg;width:var(--size);aspect-ratio:1000/90;transform:rotate(var(--rotation))}.component svg{display:block;width:100%;height:100%}.component path{fill:none;stroke:var(--stroke);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-连续卷线"><svg xmlns="http://www.w3.org/2000/svg" viewbox="0 0 1000 90"><path d="M8 62 C25 77 69 77 66 38 C63 3 28 9 33 43 C38 74 127 79 126 39 C125 8 89 10 94 45 C99 78 191 76 188 37 C185 4 149 9 155 43 C161 74 248 77 246 41 C244 10 210 10 214 45 C218 79 312 78 309 38 C306 3 271 8 276 44 C281 76 371 79 369 40 C367 7 331 11 336 45 C341 76 434 76 431 36 C428 2 393 9 398 42 C403 73 491 78 489 40 C487 8 452 10 457 45 C462 78 555 78 552 38 C549 5 514 8 519 43 C524 76 614 78 612 41 C610 9 574 12 579 46 C584 78 676 76 673 37 C670 3 635 8 640 43 C645 74 736 79 734 40 C732 7 696 11 701 45 C706 77 797 77 794 38 C791 5 757 8 761 43 C765 74 858 78 856 39 C854 6 818 10 823 44 C828 76 918 79 916 40 C914 8 879 11 884 46 C889 78 979 76 976 37 C973 4 939 9 944 43 C948 67 974 72 991 59"></path></svg></div></body></html>
````

## 点缀-连续实心箭头警戒带

逻辑路径：assets/模板库/点缀/点缀-连续实心箭头警戒带.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-连续实心箭头警戒带</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-r3-band-demo{--vl-r3-ground:#242420;--vl-r3-warning:#d7dd16;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;--vl-r3-muted:#999781;max-width:658px;padding:42px 0;background:var(--vl-r3-ground);overflow:hidden;font-family:RetroSource,sans-serif}.vl-r3-band{--vl-r3-band-height:52px;--vl-r3-band-angle:-9deg;position:relative;width:110%;height:var(--vl-r3-band-height);margin-left:-5%;transform:rotate(var(--vl-r3-band-angle));background:var(--vl-r3-warning,#d7dd16);overflow:hidden;color:var(--vl-r3-ink,#292a21)}.vl-r3-band__arrows{display:block;width:100%;height:100%;fill:currentColor}.vl-r3-band-demo__label{display:block;margin:32px 24px 0;color:var(--vl-r3-paper);font-size:13px;letter-spacing:.12em}
</style></head><body><div class="vl-r3-band-demo"><div class="vl-r3-band" role="img" aria-label="黄黑连续实心箭头警戒带"><svg class="vl-r3-band__arrows" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><pattern id="vl-r3-chevron-atom" width="94" height="52" patternUnits="userSpaceOnUse" viewBox="0 0 94 52"><path d="M-24 0H23L53 26 23 52H-24L6 26ZM70 0H117L147 26 117 52H70L100 26Z"/></pattern></defs><rect width="100%" height="100%" fill="url(#vl-r3-chevron-atom)"/></svg></div><span class="vl-r3-band-demo__label">ARCHIVE BOUNDARY / 档案现场边界</span></div>
</body></html>
````

## 点缀-连续折箭头

逻辑路径：assets/模板库/点缀/点缀-连续折箭头.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0167
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-连续折箭头</title><style>*{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;background:#f5f5f4}.component{--size:min(78vw,600px,175vh);--front-tone:#595957;--back-tone:#b4b4b0;--stroke-width:51;--rotation:0deg;width:var(--size);aspect-ratio:640/275;transform:rotate(var(--rotation))}.component svg{display:block;width:100%;height:100%}.chevrons{fill:none;stroke-width:var(--stroke-width);stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:5}.front{stroke:var(--front-tone)}.back{stroke:var(--back-tone)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration" role="img" aria-label="点缀-连续折箭头"><svg xmlns="http://www.w3.org/2000/svg" viewbox="-20 -10 640 275"><g class="chevrons"><g class="front" data-slot-role="前半组填色"><path d="M7.68 20.4 L48 127.5 L7.68 234.6"></path><path d="M108.48 20.4 L148.8 127.5 L108.48 234.6"></path><path d="M209.28 20.4 L249.6 127.5 L209.28 234.6"></path></g><g class="back" data-slot-role="后半组填色"><path d="M310.08 20.4 L350.4 127.5 L310.08 234.6"></path><path d="M410.88 20.4 L451.2 127.5 L410.88 234.6"></path><path d="M511.68 20.4 L552 127.5 L511.68 234.6"></path></g></g></svg></div></body></html>
````

## 点缀-连绵山形

逻辑路径：assets/模板库/点缀/点缀-连绵山形.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0126
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-连绵山形</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;overflow:hidden;background:#ededed}.component{--size:560px;--silhouette-fill:#353535;--stroke-width:0;--corner-radius:0;--opacity:1;width:min(var(--size),88vw,366vh);aspect-ratio:100/24;display:flex;align-items:flex-end;justify-content:flex-end;opacity:var(--opacity)}svg{display:block;width:100%;height:100%;fill:var(--silhouette-fill);stroke:var(--silhouette-fill);stroke-width:var(--stroke-width)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 100 24" preserveaspectratio="xMaxYMax meet" role="img" aria-label="点缀-连绵山形"><path d="M0 24 C10 12 16 10 30 11 C46 14 56 0 70 3 C80 3 85 14 94 15 C98 16 99 20 100 24 Z"></path></svg></div></body></html>
````

## 点缀-透明飞蝶

逻辑路径：assets/模板库/点缀/点缀-透明飞蝶.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0055
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-透明飞蝶</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;overflow:hidden;background:#e9e9e9}.component{--size:460px;--rotation:0deg;--wing-opacity:.76;--vein-width:1.05;--edge-width:1.4;--corner-radius:0;--edge-softness:.48px;width:min(var(--size),78vw,103vh);aspect-ratio:320/242;transform:rotate(var(--rotation))}svg{display:block;width:100%;height:100%;overflow:visible}.wings{opacity:var(--wing-opacity)}.membrane{stroke:#8b8b8b;stroke-opacity:.42;stroke-width:var(--edge-width);filter:blur(var(--edge-softness))}.veins{fill:none;stroke:#6e6e6e;stroke-opacity:.36;stroke-width:var(--vein-width);stroke-linecap:round;stroke-linejoin:round}.fine{stroke:#fff;stroke-opacity:.69;stroke-width:.65;fill:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 320 242" role="img" aria-label="点缀-透明飞蝶"><defs><lineargradient id="wing" x1=".13" y1="0" x2=".7" y2="1"><stop stop-color="#fff" stop-opacity=".93"></stop><stop offset=".3" stop-color="#fdfdfd" stop-opacity=".34"></stop><stop offset=".65" stop-color="#a1a1a1" stop-opacity=".3"></stop><stop offset="1" stop-color="#fafafa" stop-opacity=".86"></stop></lineargradient><radialgradient id="lower" cx=".38" cy=".22" r=".86"><stop stop-color="#909090" stop-opacity=".36"></stop><stop offset=".5" stop-color="#fff" stop-opacity=".79"></stop><stop offset="1" stop-color="#b9b9b9" stop-opacity=".22"></stop></radialgradient><lineargradient id="body" x1="0" x2="1"><stop stop-color="#555"></stop><stop offset=".38" stop-color="#d8d8d8"></stop><stop offset=".6" stop-color="#838383"></stop><stop offset="1" stop-color="#494949"></stop></lineargradient><path id="leftTop" d="M155 127 C139 88 95 30 43 18 C24 13 16 23 20 44 C24 63 28 85 41 101 C51 114 66 114 74 126 C90 143 129 145 155 135 Z"></path><path id="rightTop" d="M166 128 C181 89 217 32 274 16 C296 10 303 20 299 43 C296 67 287 93 270 108 C258 118 247 118 239 127 C217 144 183 143 165 136 Z"></path><path id="leftBottom" d="M154 135 C121 129 78 118 60 139 C47 154 55 177 67 180 C62 195 80 207 95 203 C103 220 122 216 134 202 C148 188 154 162 158 144 Z"></path><path id="rightBottom" d="M167 136 C200 128 242 122 260 142 C274 158 264 178 253 182 C257 197 240 209 226 205 C215 221 197 215 186 201 C174 184 169 160 163 145 Z"></path></defs><g class="wings"><g class="membrane"><use href="#leftBottom" fill="url(#lower)"></use><use href="#rightBottom" fill="url(#lower)"></use><use href="#leftTop" fill="url(#wing)"></use><use href="#rightTop" fill="url(#wing)"></use></g><g class="veins"><path d="M154 133 Q103 68 28 27 M148 127 Q105 102 27 55 M147 134 Q99 122 41 99 M105 81 Q95 62 82 34 M106 82 Q68 66 35 43 M123 105 Q74 86 29 76 M104 118 Q76 106 62 76 M132 131 Q88 136 74 126 M168 132 Q223 64 291 25 M174 126 Q220 99 292 54 M174 134 Q225 121 272 104 M218 82 Q229 58 247 29 M219 82 Q259 64 292 40 M199 106 Q247 86 289 77 M218 119 Q246 108 261 77 M190 132 Q226 137 240 126 M153 139 Q110 151 95 203 M151 144 Q127 173 126 207 M148 139 Q88 134 60 152 M139 143 Q97 166 67 180 M121 154 Q103 156 83 154 M166 140 Q210 153 226 205 M169 144 Q192 176 193 207 M173 139 Q231 138 260 153 M181 146 Q225 169 253 182 M202 157 Q224 158 241 156"></path></g><g class="fine"><path d="M149 126 Q102 65 32 25 M172 127 Q223 64 289 23 M149 145 Q111 163 99 201 M172 145 Q211 162 224 201 M26 47 Q30 78 46 96 M295 46 Q292 80 273 98"></path></g><g fill="#fff" opacity=".66"><ellipse cx="48" cy="58" rx="3.5" ry="6" transform="rotate(-26 48 58)"></ellipse><ellipse cx="64" cy="80" rx="2.5" ry="4" transform="rotate(-35 64 80)"></ellipse><ellipse cx="277" cy="57" rx="3.5" ry="6" transform="rotate(26 277 57)"></ellipse><ellipse cx="260" cy="80" rx="2.5" ry="4" transform="rotate(35 260 80)"></ellipse><circle cx="81" cy="183" r="3"></circle><circle cx="101" cy="193" r="2.4"></circle><circle cx="238" cy="184" r="3"></circle><circle cx="221" cy="195" r="2.4"></circle></g></g><g><path d="M157 112 C154 124 156 164 161 182 C167 169 169 126 165 112 Z" fill="url(#body)"></path><ellipse cx="161" cy="119" rx="5.8" ry="12" fill="url(#body)"></ellipse><circle cx="161" cy="104" r="5" fill="#686868"></circle><path d="M158 101 C151 85 149 74 139 69 M164 100 C172 85 176 76 184 72" fill="none" stroke="#696969" stroke-width="1.2" stroke-linecap="round"></path><circle cx="139" cy="69" r="1.4" fill="#767676"></circle><circle cx="184" cy="72" r="1.4" fill="#767676"></circle><path d="M158 133 Q160 136 165 133 M158 141 Q161 144 165 141 M159 150 Q161 152 165 150 M160 160 L164 161" fill="none" stroke="#eee" stroke-opacity=".6" stroke-width=".7"></path><path d="M156 124 L149 137 L143 140 M167 125 L174 138 L181 142" fill="none" stroke="#727272" stroke-width=".8" stroke-linecap="round"></path></g></svg></div></body></html>
````

## 点缀-递增睡眠符号

逻辑路径：assets/模板库/点缀/点缀-递增睡眠符号.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0131
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-递增睡眠符号</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;overflow:hidden;background:#ededed}.component{--size:340px;--ink:#303030;--stroke-width:9;--corner-radius:5;--opacity:1;width:min(var(--size),82vw,106vh);aspect-ratio:1.3;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.glyph{fill:none;stroke:var(--ink);stroke-width:var(--stroke-width);stroke-linecap:round;stroke-linejoin:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 130 100" role="img" aria-label="点缀-递增睡眠符号"><svg x="0" y="68" width="31.2" height="30" viewbox="0 0 40 40" preserveaspectratio="none"><path class="glyph" d="M5 7 Q19 5 34.8 5 L6 34 Q20 33 35 35"></path></svg><svg x="33.8" y="37" width="40.3" height="42" viewbox="0 0 40 40" preserveaspectratio="none"><path class="glyph" d="M5 6 Q19 5 35 5 L5.5 34.5 Q19 33 35 35"></path></svg><svg x="74.1" y="0" width="54.6" height="62" viewbox="0 0 40 40" preserveaspectratio="none"><path class="glyph" d="M5 6 Q20 5 35 5 L5 34 Q20 33 35 35"></path></svg></svg></div></body></html>
````

## 点缀-金属小花

逻辑路径：assets/模板库/点缀/点缀-金属小花.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0212
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-金属小花</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;overflow:hidden;background:#ededed}.component{--size:290px;--outline-width:1;--bevel-width:9;--highlight-opacity:.48;--shadow-opacity:.23;--corner-radius:0;--rotation:0deg;width:min(var(--size),76vw,77vh);aspect-ratio:1.02;transform:rotate(var(--rotation))}svg{display:block;width:100%;height:100%;overflow:visible}.petals{stroke:#737373;stroke-width:var(--outline-width);stroke-linejoin:round}.bevel{stroke-width:var(--bevel-width);fill:none;stroke-linecap:round;opacity:var(--highlight-opacity)}.shadow{opacity:var(--shadow-opacity)}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 204 200" role="img" aria-label="点缀-金属小花"><defs><path id="flower" d="M102 78 C78 64 76 47 83 24 C87 11 95 5 102 5 C116 5 124 22 124 39 C124 57 115 69 114 78 C132 52 151 35 173 40 C190 43 198 55 194 68 C190 84 166 96 124 100 C155 101 182 106 192 124 C201 140 196 152 182 158 C163 167 135 153 114 121 C127 145 130 168 118 186 C109 199 94 198 85 185 C74 168 79 143 90 122 C70 149 45 166 25 158 C9 152 5 140 13 125 C24 105 52 101 80 100 C46 98 19 86 11 70 C5 57 13 44 29 40 C51 34 74 52 90 79 C94 82 98 83 102 78 Z"></path><lineargradient id="metal" x1="28" y1="20" x2="170" y2="177" gradientunits="userSpaceOnUse"><stop stop-color="#fff"></stop><stop offset=".22" stop-color="#d4d4d4"></stop><stop offset=".42" stop-color="#a2a2a2"></stop><stop offset=".57" stop-color="#e6e6e6"></stop><stop offset=".73" stop-color="#a5a5a5"></stop><stop offset="1" stop-color="#5c5c5c"></stop></lineargradient><radialgradient id="bowl" cx=".38" cy=".28" r=".75"><stop stop-color="#fff" stop-opacity=".55"></stop><stop offset=".5" stop-color="#fff" stop-opacity="0"></stop><stop offset="1" stop-color="#333" stop-opacity=".32"></stop></radialgradient><lineargradient id="gem" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff" stop-opacity=".96"></stop><stop offset=".35" stop-color="#eee" stop-opacity=".5"></stop><stop offset=".65" stop-color="#858585" stop-opacity=".85"></stop><stop offset="1" stop-color="#fafafa" stop-opacity=".9"></stop></lineargradient><filter id="shadow" x="-25%" y="-25%" width="150%" height="150%"><fegaussianblur stddeviation="7"></fegaussianblur></filter><clippath id="silhouette"><use href="#flower"></use></clippath></defs><use href="#flower" class="shadow" fill="#222" transform="translate(3.67 5.1)" filter="url(#shadow)"></use><g class="petals"><use href="#flower" fill="url(#metal)"></use><g clip-path="url(#silhouette)" stroke="none"><ellipse cx="102" cy="49" rx="22" ry="42" fill="url(#bowl)"></ellipse><ellipse cx="155" cy="72" rx="43" ry="22" transform="rotate(-30 155 72)" fill="url(#bowl)"></ellipse><ellipse cx="155" cy="131" rx="43" ry="23" transform="rotate(30 155 131)" fill="url(#bowl)"></ellipse><ellipse cx="102" cy="153" rx="23" ry="42" fill="url(#bowl)"></ellipse><ellipse cx="48" cy="130" rx="43" ry="23" transform="rotate(-30 48 130)" fill="url(#bowl)"></ellipse><ellipse cx="49" cy="71" rx="43" ry="23" transform="rotate(30 49 71)" fill="url(#bowl)"></ellipse><g class="bevel" stroke="#fff"><path d="M87 53 C81 32 94 9 104 12 M124 74 C145 43 174 39 184 51 M131 113 C158 109 181 120 185 133 M93 137 C84 157 87 179 99 187 M70 120 C49 147 24 151 19 138 M72 77 C47 45 25 43 18 57"></path></g><g fill="none" stroke="#505050" stroke-opacity=".45" stroke-width="3.2" stroke-linecap="round"><path d="M112 19 Q134 51 109 86 M191 65 Q180 88 126 98 M188 149 Q162 165 119 120 M116 181 Q105 206 88 184 M17 147 Q36 173 82 124 M14 71 Q29 93 76 98"></path></g><g fill="none" stroke="#fafafa" stroke-opacity=".6" stroke-width="1.2"><path d="M101 82 Q92 49 101 26 M119 90 Q147 65 172 60 M122 109 Q153 114 173 136 M104 122 Q113 154 102 177 M85 112 Q58 125 34 141 M85 89 Q52 65 29 60"></path></g></g></g><g><circle cx="102" cy="100" r="22.5" fill="#727272"></circle><circle cx="102" cy="100" r="21.3" fill="none" stroke="#e8e8e8" stroke-width="2.4"></circle><path d="M102 79.6 L116.4 85.6 L122.4 100 L116.4 114.4 L102 120.4 L87.6 114.4 L81.6 100 L87.6 85.6 Z" fill="url(#gem)" stroke="#f4f4f4" stroke-width=".7"></path><path d="M102 79.6 L108 92 L96 92 L87.6 85.6 Z" fill="#fff" opacity=".9"></path><path d="M116.4 85.6 L108 92 L112 103 L122.4 100 Z" fill="#ddd" opacity=".75"></path><path d="M122.4 100 L112 103 L107 110 L116.4 114.4 Z" fill="#626262" opacity=".64"></path><path d="M116.4 114.4 L107 110 L95 109 L102 120.4 Z" fill="#f9f9f9" opacity=".85"></path><path d="M102 120.4 L95 109 L90 101 L87.6 114.4 Z" fill="#868686" opacity=".73"></path><path d="M81.6 100 L90 101 L96 92 L87.6 85.6 Z" fill="#fff" opacity=".8"></path><path d="M96 92 L108 92 L112 103 L107 110 L95 109 L90 101 Z" fill="#f5f5f5" fill-opacity=".46" stroke="#fff" stroke-opacity=".65" stroke-width=".6"></path><path d="M92 85 V95 M87 90 H97" stroke="#fff" stroke-width="1.6" stroke-linecap="round"></path></g></svg></div></body></html>
````

## 点缀-镂刻兽纹

逻辑路径：assets/模板库/点缀/点缀-镂刻兽纹.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0179
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-镂刻兽纹</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;overflow:hidden;background:#ededed}.component{--size:470px;--metal:#666;--engraving:#d9d9d9;--line-width:1.25;--outline-width:.7;--corner-radius:0;--opacity:1;width:min(var(--size),86vw,125vh);aspect-ratio:1.49;opacity:var(--opacity)}svg{display:block;width:100%;height:100%}.art{fill:var(--metal);stroke:#505050;stroke-width:var(--outline-width);stroke-linejoin:round}.engraving{fill:none;stroke:var(--engraving);stroke-width:var(--line-width);stroke-linecap:round;stroke-linejoin:round}.spots{fill:var(--engraving);stroke:none}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 298 200" role="img" aria-label="点缀-镂刻兽纹"><defs><mask id="piercing" maskunits="userSpaceOnUse" x="0" y="0" width="298" height="200"><rect width="298" height="200" fill="white"></rect><g fill="black"><path d="M246 49 C256 34 278 37 278 50 C278 61 263 65 254 59 C267 60 272 54 269 48 C264 42 253 45 246 49 Z"></path><path d="M249 97 Q270 79 283 88 Q268 88 259 101 Z"></path><path d="M206 42 Q223 29 224 20 Q229 34 218 43 Z"></path><path d="M70 40 Q76 24 83 23 Q86 34 78 43 Z"></path><path d="M56 115 Q63 121 58 131 Q50 132 47 124 Z"></path><path d="M181 145 Q187 153 184 162 L176 156 Z"></path></g></mask><lineargradient id="surface" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#7b7b7b"></stop><stop offset=".53" stop-color="#656565"></stop><stop offset="1" stop-color="#555"></stop></lineargradient></defs><g class="art" fill="url(#surface)" mask="url(#piercing)"><path d="M190 106 C211 91 226 73 233 52 C241 27 264 23 282 34 C298 44 294 67 278 75 C266 82 250 77 247 67 C250 83 266 84 280 79 L293 74 C289 88 279 99 262 103 C278 104 286 113 289 124 C272 119 266 131 253 127 C244 124 237 115 235 104 C229 115 216 127 204 131 Z"></path><path d="M115 81 C130 68 150 52 170 49 C181 46 185 33 184 19 C195 25 200 34 199 45 C211 38 223 22 222 8 C235 23 235 40 222 52 C236 44 244 31 244 20 C255 42 242 61 224 70 C239 67 249 60 254 51 C258 72 241 84 218 88 C236 89 245 84 252 78 C249 95 235 104 212 102 C221 111 233 113 240 111 C231 129 210 125 195 115 L158 113 Z"></path><path d="M72 59 C93 48 103 66 121 74 C139 77 164 67 189 72 C208 75 222 88 226 104 C230 121 220 134 202 141 L203 158 L224 171 L225 181 L211 185 L195 179 L184 166 L179 139 C166 145 144 146 129 137 L114 145 L113 170 L126 177 L126 187 L113 190 L92 183 L92 171 L94 146 L83 133 L78 155 L67 169 L69 179 L61 187 L41 183 L42 174 L53 166 L56 147 L55 124 C39 125 31 115 31 104 L21 100 L18 91 L7 88 L5 76 L15 68 L29 65 L33 54 L43 46 L39 32 L49 37 L58 47 C60 34 71 22 86 17 C93 32 87 43 82 50 L89 51 L88 62 Z"></path><path d="M174 130 L167 154 L154 170 L153 180 L164 185 L177 183 L179 176 L174 171 L190 158 L194 140 Z"></path><path d="M46 48 C35 31 30 28 20 31 C26 26 31 23 38 27 C31 15 21 18 16 13 C29 10 40 19 44 30 C45 18 52 13 56 9 C52 26 51 34 60 42 Z"></path><path d="M36 96 C22 105 20 112 10 112 C18 119 33 115 43 106 Z M55 110 C41 127 31 126 25 128 C32 137 51 132 62 117 Z"></path></g><g class="engraving"><path d="M15 76 Q22 72 31 74 Q34 70 34 64 M10 83 Q19 87 29 82 M22 94 Q32 96 38 89 M34 60 Q47 48 58 59 Q64 66 59 73 Q53 78 45 74 Q40 69 44 64 Q49 60 54 65 M42 54 Q36 36 28 32 M65 51 Q63 36 80 25 M69 49 L77 32 M48 83 Q61 81 65 91 Q68 101 58 107 Q49 112 42 105 Q38 100 45 96 Q51 94 53 99 Q55 103 50 103 M33 86 Q37 80 40 80"></path><path d="M80 60 Q69 68 71 81 Q83 77 82 68 M87 66 Q77 89 85 101 Q95 90 90 79 M96 72 Q102 88 94 106 Q109 102 112 85 M73 88 Q69 108 78 122 Q89 114 84 104 M68 105 Q62 112 66 123 M95 113 Q102 129 120 130 M99 119 Q105 118 108 112 M109 126 Q116 120 117 113"></path><path d="M122 87 C143 92 166 76 188 84 C208 91 212 108 201 121 C193 131 177 127 175 117 C173 107 182 101 188 105 C196 110 191 118 184 115 M129 98 Q143 103 158 97 M127 111 Q145 119 164 112 M129 123 Q150 135 171 124 M151 85 Q151 92 146 96 M167 81 Q168 88 161 94"></path><path d="M133 77 Q151 59 176 57 Q192 54 193 37 M150 79 Q171 62 191 62 Q216 60 227 41 M168 77 Q189 65 210 67 Q235 67 244 46 M187 79 Q206 75 222 78 Q242 80 248 67 M204 87 Q220 94 240 88 M211 97 Q222 109 232 113 M171 60 L174 52 M181 57 L184 48 M200 61 L202 53 M214 64 L220 56 M214 78 L220 71"></path><path d="M217 106 Q235 85 242 56 C248 37 271 31 283 44 C294 60 274 75 260 69 M248 74 Q252 92 269 91 M239 89 Q242 109 257 114 Q270 117 278 119 M242 103 Q248 121 260 121 M268 101 Q276 103 280 108"></path><path d="M60 133 L62 151 L60 165 L50 177 L60 179 M76 137 L70 157 L61 170 M103 141 L101 173 L118 181 M96 178 L112 184 M182 144 L177 156 L163 174 L169 179 M193 138 L193 161 L214 177 M205 176 L204 180 M211 178 L211 182 M117 180 L116 186 M57 177 L55 182 M164 177 L163 182"></path><path d="M39 115 Q35 123 31 125 M26 106 L18 110 M114 81 Q120 89 120 98 M119 104 L123 108"></path></g><g class="spots"><path d="M44 67 Q49 62 54 67 Q49 71 44 67 Z"></path><circle cx="49" cy="66.5" r="1.5" fill="#303030"></circle><ellipse cx="17" cy="78" rx="2.5" ry="1.5" fill="#333"></ellipse><circle cx="132" cy="88" r="1.6"></circle><circle cx="140" cy="87" r="1.4"></circle><circle cx="149" cy="84" r="1.5"></circle><circle cx="134" cy="108" r="1.8"></circle><circle cx="143" cy="110" r="1.5"></circle><circle cx="152" cy="108" r="1.8"></circle><circle cx="162" cy="104" r="1.5"></circle><circle cx="143" cy="126" r="1.4"></circle><circle cx="152" cy="128" r="1.6"></circle><circle cx="161" cy="126" r="1.3"></circle><circle cx="204" cy="98" r="1.3"></circle><circle cx="207" cy="106" r="1.4"></circle><circle cx="206" cy="113" r="1.3"></circle><path d="M101 94 l3 5 -4 3 -2 -4 Z M91 110 l3 3 -2 4 -3 -3 Z M231 65 l3 -4 2 4 -3 3 Z M235 75 l3 -3 2 3 -4 3 Z"></path></g></svg></div></body></html>
````

## 点缀-非对称宽幅曲带

逻辑路径：assets/模板库/点缀/点缀-非对称宽幅曲带.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-非对称宽幅曲带</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-sweeping-band { width:100%; height:var(--vl-band-height,420px); background:var(--vl-band-paint,#fff); mask-image:url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAwIDQyMCIgcHJlc2VydmVBc3BlY3RSYXRpbz0ibm9uZSI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0wIDI0MCBDMjQwIDcwIDUwMCAwIDEwMDAgMCBMMTAwMCAyNzAgQzcwMCAyMjAgMjgwIDI4MCAwIDQyMFoiLz48L3N2Zz4="); mask-size:100% 100%; mask-repeat:no-repeat; pointer-events:none; }
</style></head><body><div class="vl-sweeping-band" aria-hidden="true"></div>
</body></html>
````

## 点缀-风铃草花枝

逻辑路径：assets/模板库/点缀/点缀-风铃草花枝.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0199
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-风铃草花枝</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f1f0ee}.component{--size:360px;--outline:1.8;--stem-width:2.6;--petal-opacity:.97;width:min(var(--size),86vw,48vh);aspect-ratio:360/650}.component svg{display:block;width:100%;height:100%;overflow:visible}.stems{fill:none;stroke:#62645f;stroke-width:var(--stem-width);stroke-linecap:round;stroke-linejoin:round}.bells{stroke:#575953;stroke-width:var(--outline);stroke-linejoin:round;opacity:var(--petal-opacity)}.fine{fill:none;stroke:#eeeeea;stroke-width:1.5;stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 360 650" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-风铃草花枝"><defs><lineargradient id="petal" x1="0" y1="0" x2="1" y2=".6"><stop stop-color="#d8d9d4"></stop><stop offset=".5" stop-color="#babcb6"></stop><stop offset="1" stop-color="#92958d"></stop></lineargradient><g id="bell"><path d="M-9 0Q-20 12-20 29Q-20 42-31 48Q-24 49-21 55L-10 51Q-5 63 1 62Q8 61 12 52Q20 57 24 54L29 47Q17 40 18 26Q19 9 8 1Z" fill="url(#petal)"></path><path d="M-29 48Q-18 43-10 51Q1 45 12 52Q19 45 28 47Q17 60 2 62Q-14 57-29 48Z" fill="#777b72"></path><path d="M-29 48Q-19 47-10 53Q-5 61 1 62Q8 60 12 53Q20 57 28 47" fill="none" stroke="#e1e2db"></path><path d="M-9 0L-15 8L-5 5L0 13L5 5L15 9L8 0Q0-5-9 0" fill="#777c70"></path><path d="M-6 11Q-12 27-13 42M2 14Q-2 34 1 46M10 13Q13 28 18 40" fill="none" stroke="#e5e6e0" stroke-width="1.3"></path><path d="M-4 51L-3 58M4 51L4 58" fill="none" stroke="#c9cbc2" stroke-width="1"></path></g><g id="leaf"><path d="M0 0Q-7-36 16-69Q30-32 0 0Z" fill="#92988a" stroke="#606759" stroke-width="1.4"></path><path d="M0 0Q11-29 16-65M8-24L1-40M11-36L23-49" fill="none" stroke="#c4c8bb" stroke-width="1.2"></path></g></defs><g class="stems"><path d="M187 647C181 574 202 525 187 443S169 302 187 224S194 128 187 62"></path><path d="M190 578Q155 518 128 438Q110 397 70 388M193 512Q236 456 257 394Q274 354 309 341M186 449Q130 363 112 301Q96 269 56 258M184 377Q229 326 263 259Q281 228 300 217M176 306Q145 254 120 191Q105 168 79 164M187 241Q227 203 240 142Q246 120 263 109M190 169Q164 123 141 93Q126 74 106 76M189 109Q212 82 224 54Q230 38 246 36"></path><path d="M128 438Q135 410 152 402M257 394Q245 374 231 373M112 301Q136 300 143 318M263 259Q243 249 230 255M120 191Q135 177 150 181M240 142Q219 126 210 137M141 93Q146 61 159 53M187 62Q177 24 187 13"></path></g><g><use href="#leaf" transform="translate(189 584) rotate(-53) scale(1.02)"></use><use href="#leaf" transform="translate(193 547) rotate(38) scale(.88)"></use><use href="#leaf" transform="translate(179 402) rotate(-55) scale(.9)"></use><use href="#leaf" transform="translate(188 466) rotate(50) scale(.93)"></use><use href="#leaf" transform="translate(183 320) rotate(37) scale(.7)"></use><use href="#leaf" transform="translate(168 278) rotate(-52) scale(.61)"></use><use href="#leaf" transform="translate(191 191) rotate(25) scale(.51)"></use><use href="#leaf" transform="translate(126 429) rotate(-53) scale(.66)"></use><use href="#leaf" transform="translate(258 395) rotate(48) scale(.64)"></use></g><g class="bells"><use href="#bell" transform="translate(187 13) rotate(-8) scale(.47)"></use><use href="#bell" transform="translate(159 53) rotate(14) scale(.65)"></use><use href="#bell" transform="translate(246 36) rotate(-21) scale(.7)"></use><use href="#bell" transform="translate(106 76) rotate(23) scale(.85)"></use><use href="#bell" transform="translate(263 109) rotate(-20) scale(.97)"></use><use href="#bell" transform="translate(210 137) rotate(14) scale(.68)"></use><use href="#bell" transform="translate(79 164) rotate(24) scale(1.06)"></use><use href="#bell" transform="translate(150 181) rotate(-9) scale(.76)"></use><use href="#bell" transform="translate(300 217) rotate(-25) scale(1.03)"></use><use href="#bell" transform="translate(230 255) rotate(15) scale(.85)"></use><use href="#bell" transform="translate(56 258) rotate(21) scale(1.1)"></use><use href="#bell" transform="translate(143 318) rotate(-8) scale(.84)"></use><use href="#bell" transform="translate(309 341) rotate(-25) scale(1.1)"></use><use href="#bell" transform="translate(231 373) rotate(15) scale(.85)"></use><use href="#bell" transform="translate(70 388) rotate(27) scale(1.08)"></use><use href="#bell" transform="translate(152 402) rotate(-13) scale(.9)"></use></g><g class="fine" opacity=".75"><path d="M185 635Q182 594 190 557M181 365Q176 340 178 317M196 503Q219 468 233 444M115 311Q121 329 130 346"></path></g></svg></div></body></html>
````

## 点缀-飘动薄纱

逻辑路径：assets/模板库/点缀/点缀-飘动薄纱.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0073
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-飘动薄纱</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#eeedeb}.component{--size:1050px;--fabric-opacity:.83;--thread-width:.55;--edge-width:.9;width:min(var(--size),94vw,166vh);aspect-ratio:1000/540}.component svg{width:100%;height:100%;display:block}.threads{fill:none;stroke-width:var(--thread-width);stroke-linecap:round}.hem{fill:none;stroke:#fbfbfa;stroke-width:var(--edge-width);opacity:.65}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 1000 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-飘动薄纱"><defs><path id="cloth" d="M18 69C174 20 269 138 344 265C419 392 523 474 648 414C767 357 811 175 970 131L982 253C864 268 827 425 695 482C516 557 376 435 294 309C206 173 118 147 24 170Z"></path><clippath id="clip"><use href="#cloth"></use></clippath><lineargradient id="silk" x1="0" y1="0" x2=".2" y2="1"><stop stop-color="#b4b4b4" stop-opacity=".18"></stop><stop offset=".28" stop-color="#fafafa" stop-opacity=".37"></stop><stop offset=".49" stop-color="#939393" stop-opacity=".3"></stop><stop offset=".67" stop-color="#ffffff" stop-opacity=".55"></stop><stop offset=".84" stop-color="#a5a5a5" stop-opacity=".21"></stop><stop offset="1" stop-color="#fafafa" stop-opacity=".14"></stop></lineargradient><lineargradient id="fold" x1="0" y1="0" x2="1" y2=".4"><stop stop-color="#707070" stop-opacity="0"></stop><stop offset=".27" stop-color="#7c7c7c" stop-opacity=".12"></stop><stop offset=".47" stop-color="#ffffff" stop-opacity=".72"></stop><stop offset=".54" stop-color="#818181" stop-opacity=".36"></stop><stop offset=".67" stop-color="#fafafa" stop-opacity=".28"></stop><stop offset="1" stop-color="#8c8c8c" stop-opacity="0"></stop></lineargradient><pattern id="weave" width="4" height="4" patternunits="userSpaceOnUse" patterntransform="rotate(-19)"><path d="M0 0V4M2 0V4" stroke="#ffffff" stroke-opacity=".25" stroke-width=".45"></path><path d="M0 1H4M0 3H4" stroke="#777777" stroke-opacity=".13" stroke-width=".4"></path></pattern></defs><g opacity="var(--fabric-opacity)" data-role="内容层"><use href="#cloth" fill="url(#silk)"></use><g clip-path="url(#clip)"><path d="M-5 102C173 5 292 220 371 322S533 484 664 421S823 221 997 176L1000 218C836 223 782 421 678 459S454 483 348 342S158 115-5 141Z" fill="url(#fold)"></path><path d="M183 57C280 159 300 312 463 450C367 364 385 252 289 144Z" fill="#fafafa" opacity=".32"></path><path d="M258 155C327 260 309 318 423 427C358 360 345 244 280 178Z" fill="#797979" opacity=".17"></path><path d="M593 473C741 463 722 319 851 208C769 298 791 444 646 493Z" fill="#888888" opacity=".2"></path><path d="M642 449C759 397 751 288 907 182C827 243 818 367 730 447Z" fill="#ffffff" opacity=".39"></path><path d="M17 72C177 25 269 138 344 265C419 392 523 474 648 414C767 357 811 175 970 131" fill="none" stroke="#777" stroke-opacity=".15" stroke-width="5"></path><g class="threads" stroke="#fff" opacity=".65"><path d="M15 79C180 28 266 149 341 274S525 480 651 424S817 184 973 141"></path><path d="M15 87C180 37 260 150 338 280S521 486 654 431S819 190 974 150"></path><path d="M15 98C178 47 255 156 332 282S518 494 660 438S821 199 975 160"></path><path d="M15 108C174 62 250 161 329 287S516 501 664 446S828 210 976 171"></path><path d="M15 119C169 72 249 170 323 292S509 509 670 453S831 221 977 184"></path><path d="M15 129C165 85 240 174 318 299S508 516 675 459S839 234 978 196"></path><path d="M15 140C160 96 235 176 312 304S505 521 680 466S845 248 979 210"></path><path d="M15 150C157 109 230 184 307 309S500 527 685 472S852 259 980 225"></path><path d="M15 160C153 123 223 190 301 314S498 532 690 478S858 269 981 239"></path></g><g class="threads" stroke="#727272" opacity=".23"><path d="M58 45Q40 97 53 185M86 45Q70 102 83 178M115 48Q100 115 112 179M146 61Q128 126 144 185M175 78Q152 140 174 196M203 102Q174 154 203 217M230 132Q200 174 234 246M256 167Q226 204 263 280M282 203Q252 237 291 319M307 243Q279 273 327 366M335 283Q312 322 364 405M365 324Q351 367 406 448M402 365Q390 410 453 481M444 404Q433 449 501 506M490 435Q481 477 552 519M539 449Q534 494 597 520M588 445Q595 494 646 513M632 427Q650 471 691 492M673 399Q708 439 735 465M706 362Q749 396 771 433M738 320Q783 350 802 398M770 278Q810 308 833 356M804 239Q843 267 865 318M841 204Q875 232 901 283M883 171Q917 204 938 260M927 145Q954 192 964 251"></path></g><use href="#cloth" fill="url(#weave)"></use></g><use href="#cloth" class="hem"></use><path d="M20 65C176 19 270 137 347 264M25 174C119 152 207 177 291 311M693 486C827 429 866 275 980 257M650 410C766 352 808 172 968 127" class="threads" stroke="#fafafa" opacity=".5"></path></g></svg></div></body></html>
````

## 点缀-飞翔燕子

逻辑路径：assets/模板库/点缀/点缀-飞翔燕子.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0074
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-飞翔燕子</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f0efed}.component{--size:410px;--feather-line:1;--feather-opacity:.55;width:min(var(--size),86vw,80vh);aspect-ratio:410/450}.component svg{display:block;width:100%;height:100%}.detail{fill:none;stroke:#999;stroke-width:var(--feather-line);opacity:var(--feather-opacity);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="0 0 410 450" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-飞翔燕子"><defs><lineargradient id="plume" x1="0" y1="0" x2="1" y2=".6"><stop stop-color="#1b1b1b"></stop><stop offset=".48" stop-color="#515151"></stop><stop offset="1" stop-color="#202020"></stop></lineargradient><lineargradient id="breast" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f1f1ed"></stop><stop offset=".55" stop-color="#d1d1cc"></stop><stop offset="1" stop-color="#818181"></stop></lineargradient></defs><g data-role="内容层"><path d="M209 234C169 232 126 220 97 193Q59 162 26 150C45 180 63 201 89 219L83 218L107 236L100 234L127 251L120 250L149 263L142 263Q176 276 205 260Z" fill="#434343"></path><path d="M196 278Q160 318 120 377Q145 363 170 344C146 382 135 410 133 430C166 390 189 350 222 300Z" fill="#282828"></path><path d="M197 237C217 208 241 186 260 167C272 151 285 145 298 150Q314 153 316 169L334 170L314 179C310 194 300 205 283 212C268 244 249 277 225 299L197 315L185 302Z" fill="#292929"></path><path d="M293 184C284 199 272 214 264 234C254 255 236 282 212 299Q214 272 229 248Q253 209 272 194Z" fill="url(#breast)"></path><path d="M295 178Q303 178 310 173Q306 190 291 198L279 198L279 189Z" fill="#ababA5"></path><path d="M211 253C211 216 183 195 168 163C147 118 153 63 170 17C176 48 183 79 198 103C210 122 222 134 228 157C234 176 234 195 227 220L231 210L229 232L234 224L227 249L230 241L219 267Z" fill="url(#plume)"></path><path d="M169 26C165 83 175 120 194 149Q214 182 217 222C220 185 211 160 196 136C175 102 171 72 169 26Z" fill="#686868" opacity=".48"></path><g class="detail"><path d="M211 241C225 175 162 124 169 28M213 220C219 174 186 135 178 95M217 213C229 179 209 151 195 118M222 211Q233 187 218 149M201 245Q119 236 34 157M186 254Q134 244 89 215M170 257L111 236M191 307Q159 344 131 369M211 308Q158 390 138 419M202 300Q186 327 168 343"></path></g><path d="M216 250Q221 243 222 234M218 260Q231 248 232 239M221 269Q235 256 239 246" fill="none" stroke="#777" stroke-width="1.4"></path><path d="M235 237Q253 211 266 205M231 249Q249 235 255 221" fill="none" stroke="#f2f2ee" stroke-width="1.1" opacity=".65"></path><circle cx="303" cy="165" r="3" fill="#080808"></circle><circle cx="304" cy="164" r=".8" fill="#ddd"></circle><path d="M315 169L334 170L315 174Z" fill="#151515"></path><path d="M276 159Q288 151 298 155" fill="none" stroke="#797979" stroke-width="1.2"></path></g></svg></div></body></html>
````

## 点缀-高光气球

逻辑路径：assets/模板库/点缀/点缀-高光气球.html

````html
<!doctype html><!--
cleaned-library-policy:v1 | component-0106
命中仍按原品类 AI + Coding；模板仅供构图、组件与配色角色，图像槽、样例与参考裁片不是成品或当前任务事实，不扩大 pure-image。
DIT 仅承接配图、场景摄影/插画、复杂材质及有职责的部分点缀；艺术大标题仅按原品类准入，准确与独立可编辑要求优先。正文、规格、价格、日期、表格及受保护准确文字由原生 DOM/CSS/SVG 承担；简单几何不为凑调用生图。
电商 Hero 默认无新增字主图加 DOM，仅明确选择且符合原规则时允许一体文字例外；社媒长图 Hero 沿原例外，三折页全部标题原生。reference-only 资产仅参考，不作成品、身份母版或事实证据。沿用原流程、KV、字体、素材、shot.py 与交付。
完整接入规则：references/templates/cleaned-library.md。
-->
<html lang="zh-CN"><head><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies></style><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>点缀-高光气球</title><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%}body{display:grid;place-items:center;background:#f1f0ee}.component{--size:242px;--body-fill:#b4b4b4;--outline:#303030;--outline-width:9.5;--highlight-width:14.8;--edge-band-width:6.3;--string-width:2.6;width:min(var(--size),70vw,45vh);aspect-ratio:.55}.component svg{display:block;width:100%;height:100%;overflow:visible}.body{fill:var(--body-fill);stroke:var(--outline);stroke-width:var(--outline-width);stroke-linejoin:round}.shine{fill:none;stroke:#f7f7f5;stroke-width:var(--highlight-width);stroke-linecap:round}</style></head><body><!-- 通用组件：示例内容只表达槽位关系。 --><div class="component" data-component-class="decoration"><svg viewbox="-3 -5 226 412" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="点缀-高光气球"><defs><path id="balloon" d="M108 5C48 3 9 56 9 123C9 180 41 235 82 255Q99 267 116 263C139 258 170 229 190 193C213 152 220 93 202 53C185 16 147 5 108 5Z"></path><clippath id="inside"><use href="#balloon"></use></clippath></defs><path d="M127 280C111 298 119 317 146 328C173 339 189 350 185 367C181 383 155 378 154 400" fill="none" stroke="#494949" stroke-width="var(--string-width)" stroke-linecap="round" data-role="内容层"></path><path d="M109 256Q124 254 133 259L146 283Q124 277 101 284L112 263Z" fill="#909090" stroke="var(--outline)" stroke-width="5" stroke-linejoin="round"></path><path d="M117 265L113 278M129 263L136 277" fill="none" stroke="#d1d1ce" stroke-width="2.5"></path><use href="#balloon" class="body" data-role="内容层"></use><g clip-path="url(#inside)"><path d="M181 37C211 79 207 139 184 184C166 221 144 244 119 253" fill="none" stroke="#686868" stroke-width="var(--edge-band-width)" stroke-linecap="round"></path><path class="shine" d="M79 51Q58 66 53 91"></path><path class="shine" d="M50 108Q48 123 51 139"></path><path d="M168 220Q157 235 145 240" fill="none" stroke="#dededb" stroke-width="3.4" stroke-linecap="round"></path></g></svg></div></body></html>
````

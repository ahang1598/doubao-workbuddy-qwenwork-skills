# 配色-HTML合集

按条目检索读取，不整篇加载。

## 配色-冷银墨黑青蓝

逻辑路径：assets/模板库/配色/配色-冷银墨黑青蓝.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>配色-冷银墨黑青蓝</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-r8-palette{--vl-silver:#bdc8c8;--vl-silver-light:#e3e9e8;--vl-silver-deep:#899b9e;--vl-ink:#050707;--vl-paper:#fff;--vl-cyan:#24afd2;--vl-metal-light:#f4f8f8;--vl-metal-mid:#aab7be;--vl-metal-dark:#485158;--vl-ambient-green:#c1d29f;--vl-ambient-pink:#d7c2ce;--vl-spark:#e8c75e;--vl-grain-opacity:.055;color:var(--vl-ink);background-color:var(--vl-silver);font-family:RetroSource,sans-serif;font-weight:400}.vl-r8-palette__demo{box-sizing:border-box;max-width:658px;padding:clamp(20px,5%,36px);background:radial-gradient(ellipse at 100% 0,#c1d29f66,transparent 42%),linear-gradient(120deg,var(--vl-silver-light),var(--vl-silver) 56%,var(--vl-silver-deep))}.vl-r8-palette__demo h2{margin:0 0 12px;font-size:26px;font-weight:700}.vl-r8-palette__demo p{margin:0;font-size:15px;line-height:1.8}.vl-r8-palette__swatches{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:22px}.vl-r8-palette__swatch{padding:22px 3px 10px;text-align:center;font:12px Arial,sans-serif;background:var(--swatch);color:var(--swatch-text,var(--vl-ink));box-shadow:inset 0 0 0 1px #0002}.vl-r8-palette__swatch--silver{--swatch:var(--vl-silver)}.vl-r8-palette__swatch--ink{--swatch:var(--vl-ink);--swatch-text:var(--vl-paper)}.vl-r8-palette__swatch--paper{--swatch:var(--vl-paper)}.vl-r8-palette__swatch--cyan{--swatch:var(--vl-cyan)}
</style></head><body><section class="vl-r8-palette vl-r8-palette__demo"><h2>冷银 · 星光</h2><p>连续冷银底承载墨黑正文，纸白负责反白层级，青蓝只用于优惠券等小面积重点。</p><div class="vl-r8-palette__swatches"><span class="vl-r8-palette__swatch vl-r8-palette__swatch--silver">SILVER</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--ink">INK</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--paper">WHITE</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--cyan">CYAN</span></div></section>
</body></html>
````

## 配色-通用渐变与逐色标透明度

逻辑路径：assets/模板库/配色/配色-通用渐变与逐色标透明度.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>配色-通用渐变与逐色标透明度</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-gradient--linear { --vl-paint:linear-gradient(var(--vl-gradient-angle,135deg),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--radial { --vl-paint:radial-gradient(ellipse var(--vl-gradient-rx,70%) var(--vl-gradient-ry,70%) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--conic { --vl-paint:conic-gradient(from var(--vl-gradient-turn,0deg) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-paint-fill { background-image:var(--vl-paint,none); }
</style></head><body><section class="vl-gradient--linear vl-paint-fill" style="--vl-gradient-angle:90deg;--vl-gradient-stops:#f5ce68 0%,#ee718d 45%,#315fce 100%">多色背景</section>
<span class="vl-gradient--radial vl-paint-fill" style="--vl-gradient-stops:color-mix(in srgb,#dffbff 80%,transparent) 0%,color-mix(in srgb,#2a8ecf 25%,transparent) 50%,transparent 100%">独立装饰层</span>
</body></html>
````

## 配色-酒馆红棕赭纸亮橙

逻辑路径：assets/模板库/配色/配色-酒馆红棕赭纸亮橙.html

````html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>配色-酒馆红棕赭纸亮橙</title><meta name="standalone-template" content="1"><style data-standalone-base>html,body{margin:0;padding:0}</style><style data-compiled-dependencies>.vl-r9-palette{--vl-cabinet:#430f02;--vl-cabinet-deep:#2c0902;--vl-paper:#a87548;--vl-paper-deep:#8a5634;--vl-cream:#e5cda9;--vl-orange:#ff861d;--vl-orange-deep:#ef6810;--vl-ink:#431b0b;--vl-road:#414140;--vl-metal:#86766a;--vl-note:#c9c0ae;--vl-shelf-light:#aa531b;--vl-shelf-mid:#7f310a;--vl-shelf-dark:#3c1004;--vl-slot-housing:#604737;--vl-slot-bevel:#9b8069;--vl-slot-shadow:#20140e;--vl-slot-paper:var(--vl-paper);--vl-slot-ink:var(--vl-cream);color:var(--vl-cream);background-color:var(--vl-cabinet);font-family:RetroSource,sans-serif;font-weight:400}.vl-r9-palette-demo{box-sizing:border-box;max-width:658px;padding:clamp(20px,5%,34px)}.vl-r9-palette-demo h3{margin:0 0 20px;font-size:25px;font-weight:650}.vl-r9-palette-swatches{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.vl-r9-palette-swatch{padding:35px 8px 12px;min-width:0;font-size:13px;line-height:1.6;border-bottom:2px solid currentColor}.vl-r9-palette-swatch:nth-child(1){background:var(--vl-cabinet-deep);color:var(--vl-cream)}.vl-r9-palette-swatch:nth-child(2){background:var(--vl-paper);color:var(--vl-ink)}.vl-r9-palette-swatch:nth-child(3){background:var(--vl-cream);color:var(--vl-ink)}.vl-r9-palette-swatch:nth-child(4){background:var(--vl-orange);color:var(--vl-ink)}.vl-r9-palette-demo p{line-height:1.8;margin:22px 0 0}.vl-r9-palette-demo a{color:var(--vl-orange)}@media(max-width:460px){.vl-r9-palette-swatches{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head><body><section class="vl-r9-palette vl-r9-palette-demo"><h3>街区酒馆 · 语义色板</h3><div class="vl-r9-palette-swatches"><div class="vl-r9-palette-swatch">柜体深底<br>#430F02</div><div class="vl-r9-palette-swatch">赭色纸面<br>#A87548</div><div class="vl-r9-palette-swatch">奶油正文<br>#E5CDA9</div><div class="vl-r9-palette-swatch">行动亮橙<br>#FF861D</div></div><p>深红棕连接整页，赭纸承载规则，亮橙只强调路牌与行动。<a href="#vl-r9-palette-end">查看活动说明</a></p><p id="vl-r9-palette-end">照片保留青蓝霓虹、紫红灯光和植物绿色，不叠加统一褐色滤镜。</p></section>
</body></html>
````

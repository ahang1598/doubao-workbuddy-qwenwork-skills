# 淡雅柔和

状态：已填充。

共用 [语义颜色参数](palettes.md#colors.parameters)，不新增色彩实现。将 overrides 写到目标节点；已有组件会定义自己的默认变量，所以只设在页面祖先上不能覆盖组件默认值。纯页面使用 `background:var(--vl-tint);color:var(--vl-ink)`，不要求套用材质卡片。

<a id="palette.osmanthus-cream"></a>

## 桂香奶金

风格标签：通用。

参考：本批图 6 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

奶油底约 70%，暖金光区约 25%，棕色文字约 5%；柔光强度由质感控制，不通过降低整页透明度实现。

```json
{
  "id": "palette.osmanthus-cream",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#f2eddb",
    "--vl-surface-end": "#dfc99e",
    "--vl-ink": "#514733",
    "--vl-muted-ink": "#746449",
    "--vl-accent": "#a17735",
    "--vl-edge-color": "#ccbb91",
    "--vl-light-color": "#fff9e4",
    "--vl-hue": "40",
    "--vl-shadow-color": "#514733",
    "--vl-label-bg": "#a17735",
    "--vl-label-ink": "#fffaf0"
  }
}
```


<a id="palette.oxide-blue-paper"></a>

## 灰纸靛蓝砖红

风格标签：通用。

视觉近似色值；只描述颜色角色，不单独推断整体风格。渐变使用 [通用渐变](palettes.md#color.gradient)，采用 `vl-oxide-blue-paper vl-gradient--linear vl-paint-fill` 才消费渐变色标。

```css
.vl-oxide-blue-paper {
 --vl-tint:#d4d9d0; --vl-ink:#264a5e; --vl-muted-ink:#4f6268;
 --vl-accent:#9d3029; --vl-accent-2:#758786; --vl-accent-3:#e8e8dc;
 --vl-label-bg:#264a5e; --vl-label-ink:#d4d9d0; --vl-edge-color:#758786;
 --vl-surface-end:#e8e8dc; --vl-light-color:#fff; --vl-shadow-color:#264a5e;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#d4d9d0 0%,#d4d9d0 65%,#e8e8dc 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

主底色、文字与标签成对应用；浅底纸面默认用纯色，渐变不是必选。强色章节需单独切换文字，不能只替换背景。真纸纹、缺墨字形和照片光影从其他原子／素材取得。

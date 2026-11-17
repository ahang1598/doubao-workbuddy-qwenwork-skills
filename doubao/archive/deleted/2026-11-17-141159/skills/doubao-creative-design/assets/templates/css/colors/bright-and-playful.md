# 明快活泼

状态：已填充。共享 [语义颜色参数](palettes.md#colors.parameters)，只新增配色覆盖。颜色为参考估计值，绑定到实际节点后检查对比；三种强调色不要求等量使用。

<a id="palette.primary-pop"></a>

## 红黄蓝纸本撞色

风格标签：通用。

演我大赛参考：米白底、红黄蓝色块与手作装饰。适合作为复古高饱和拼贴的颜色候选；复古字形和纸面关系另由字体、形状与质感负责。

```json
{
  "id": "palette.primary-pop",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#f1efe8",
    "--vl-surface-end": "#e4dfd3",
    "--vl-ink": "#1d2024",
    "--vl-muted-ink": "#555a63",
    "--vl-accent": "#f72d49",
    "--vl-accent-2": "#ffe43b",
    "--vl-accent-3": "#2474df",
    "--vl-edge-color": "#ffffff",
    "--vl-light-color": "#fffaf0",
    "--vl-shadow-color": "#312720",
    "--vl-label-bg": "#2474df",
    "--vl-label-ink": "#ffffff",
    "--vl-hue": "350"
  }
}
```

<a id="palette.sky-lime"></a>

## 晴空蓝青柠

风格标签：通用。

创作小镇及蓝色生活活动参考：蓝底、青柠与粉色点缀。蓝色章节用浅色标题时单独调整 ink，正文面板使用深色 ink。

```json
{
  "id": "palette.sky-lime",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#62bee8",
    "--vl-surface-end": "#2688dc",
    "--vl-ink": "#123b54",
    "--vl-muted-ink": "#24536e",
    "--vl-accent": "#e4ef78",
    "--vl-accent-2": "#ff78a8",
    "--vl-accent-3": "#f6f2db",
    "--vl-edge-color": "#d8f6ff",
    "--vl-light-color": "#f7fdff",
    "--vl-shadow-color": "#153c66",
    "--vl-label-bg": "#176bad",
    "--vl-label-ink": "#ffffff",
    "--vl-hue": "200"
  }
}
```


<a id="palette.coral-paper-ink"></a>

## 珊瑚朱红纸白墨黑

风格标签：通用。

视觉近似色值；只描述颜色角色，不单独推断整体风格。渐变使用 [通用渐变](palettes.md#color.gradient)，采用 `vl-coral-paper-ink vl-gradient--linear vl-paint-fill` 才消费渐变色标。

```css
.vl-coral-paper-ink {
 --vl-tint:#f8f3e7; --vl-ink:#272b28; --vl-muted-ink:#56594d;
 --vl-accent:#b74916; --vl-accent-2:#eb745b; --vl-accent-3:#fffaf0;
 --vl-label-bg:#272b28; --vl-label-ink:#f8f3e7; --vl-edge-color:#eb745b;
 --vl-surface-end:#fffaf0; --vl-light-color:#fff; --vl-shadow-color:#272b28;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#f8f3e7 0%,#f8f3e7 65%,#fffaf0 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

主底色、文字与标签成对应用；浅底纸面默认用纯色，渐变不是必选。强色章节需单独切换文字，不能只替换背景。真纸纹、缺墨字形和照片光影从其他原子／素材取得。

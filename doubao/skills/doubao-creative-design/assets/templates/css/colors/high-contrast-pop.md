# 高对比撞色

状态：已填充。

共用 [语义颜色参数](palettes.md#colors.parameters)，不新增色彩实现。将 overrides 写到目标节点；已有组件会定义自己的默认变量，所以只设在页面祖先上不能覆盖组件默认值。纯页面使用 `background:var(--vl-tint);color:var(--vl-ink)`，不要求套用材质卡片。

<a id="palette.charcoal-rose"></a>

## 炭黑玫粉

风格标签：通用。

参考：本批图 3 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

炭黑约 70%，浅色比较区约 20%，粉色数字和光晕约 10%；浅区应显式切换为深色文字。

```json
{
  "id": "palette.charcoal-rose",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#171415",
    "--vl-surface-end": "#302729",
    "--vl-ink": "#f7eded",
    "--vl-muted-ink": "#c9b9be",
    "--vl-accent": "#e7a4bd",
    "--vl-edge-color": "#ad8995",
    "--vl-light-color": "#fff0f5",
    "--vl-hue": "338",
    "--vl-shadow-color": "#090b09",
    "--vl-label-bg": "#e7a4bd",
    "--vl-label-ink": "#171415"
  }
}
```

<a id="palette.cobalt-acid"></a>

## 钴蓝荧绿

风格标签：通用。

追剧活动与蓝色音乐参考：白与钴蓝成片切换；荧绿只作小面积强调。深蓝区用 label-bg / label-ink 成对切换。

```json
{
  "id": "palette.cobalt-acid",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#f3f4f1",
    "--vl-surface-end": "#d6e4f3",
    "--vl-ink": "#153a95",
    "--vl-muted-ink": "#53678f",
    "--vl-accent": "#225ee8",
    "--vl-accent-2": "#c5f441",
    "--vl-accent-3": "#44c4ed",
    "--vl-edge-color": "#a8c6ff",
    "--vl-light-color": "#ffffff",
    "--vl-shadow-color": "#0a2257",
    "--vl-label-bg": "#225ee8",
    "--vl-label-ink": "#ffffff",
    "--vl-hue": "224"
  }
}
```

<a id="palette.neon-cyan"></a>

## 黑底电光青

风格标签：通用。

演唱会战报参考：黑底、电光青和黄绿数字；背景光团与彩色噪点分别选择质感原子。

```json
{
  "id": "palette.neon-cyan",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#080f18",
    "--vl-surface-end": "#063a52",
    "--vl-ink": "#d1f8f6",
    "--vl-muted-ink": "#91cbcf",
    "--vl-accent": "#04d3dc",
    "--vl-accent-2": "#d9f244",
    "--vl-accent-3": "#317bbc",
    "--vl-edge-color": "#5ffaff",
    "--vl-light-color": "#dcffff",
    "--vl-shadow-color": "#000911",
    "--vl-label-bg": "#08b3bf",
    "--vl-label-ink": "#072c39",
    "--vl-hue": "184"
  }
}
```

## 已有配色的局部变体

女性电影参考复用 [炭黑玫粉](#palette.charcoal-rose)：仅对强调区覆盖 `--vl-accent:#e33e86;--vl-label-bg:#bb2b68;--vl-label-ink:#fff4fa`，无需新增一套完整配色。深蓝二次元章节可在钴蓝配方上局部覆盖 `--vl-tint:#091d59;--vl-ink:#f4fbff;--vl-muted-ink:#c2e5ff`；不能只改背景不改文字。


<a id="palette.industrial-silver-lime"></a>

## 炭黑银灰荧黄

风格标签：通用。

视觉近似色值；只描述颜色角色，不单独推断整体风格。渐变使用 [通用渐变](palettes.md#color.gradient)，采用 `vl-industrial-silver-lime vl-gradient--linear vl-paint-fill` 才消费渐变色标。

```css
.vl-industrial-silver-lime {
 --vl-tint:#080a0c; --vl-ink:#f1f2eb; --vl-muted-ink:#c0c3be;
 --vl-accent:#ebf377; --vl-accent-2:#8d969b; --vl-accent-3:#2a2d2d;
 --vl-label-bg:#f1f2eb; --vl-label-ink:#080a0c; --vl-edge-color:#8d969b;
 --vl-surface-end:#2a2d2d; --vl-light-color:#fff; --vl-shadow-color:#000000;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#080a0c 0%,#080a0c 65%,#2a2d2d 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

主底色、文字与标签成对应用；浅底纸面默认用纯色，渐变不是必选。强色章节需单独切换文字，不能只替换背景。真纸纹、缺墨字形和照片光影从其他原子／素材取得。

# 清新自然

状态：已填充。

共用 [语义颜色参数](palettes.md#colors.parameters)，不新增色彩实现。将 overrides 写到目标节点；已有组件会定义自己的默认变量，所以只设在页面祖先上不能覆盖组件默认值。纯页面使用 `background:var(--vl-tint);color:var(--vl-ink)`，不要求套用材质卡片。

<a id="palette.bamboo-olive"></a>

## 竹林深绿

风格标签：通用。

参考：本批图 5 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

深绿约 65%，橄榄过渡约 25%，米白文字约 10%；沉静是检索标签，不另建分类。

```json
{
  "id": "palette.bamboo-olive",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#203a2e",
    "--vl-surface-end": "#454d34",
    "--vl-ink": "#efeedb",
    "--vl-muted-ink": "#c4ccb8",
    "--vl-accent": "#bec49a",
    "--vl-edge-color": "#78876d",
    "--vl-light-color": "#f4f1da",
    "--vl-hue": "145",
    "--vl-shadow-color": "#090b09",
    "--vl-label-bg": "#bec49a",
    "--vl-label-ink": "#171415"
  }
}
```

<a id="palette.moss-letter"></a>

## 苔绿信笺

风格标签：通用。

参考：本批图 7 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

浅纸约 65%，苔绿章节约 25%，深绿文字约 10%；与竹林分支共享语义角色，但明度关系不同。

```json
{
  "id": "palette.moss-letter",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#f0f1df",
    "--vl-surface-end": "#e0e6c9",
    "--vl-ink": "#405332",
    "--vl-muted-ink": "#657153",
    "--vl-accent": "#608043",
    "--vl-edge-color": "#aab38c",
    "--vl-light-color": "#ffffee",
    "--vl-hue": "90",
    "--vl-shadow-color": "#405332",
    "--vl-label-bg": "#608043",
    "--vl-label-ink": "#fffaf0"
  }
}
```


<a id="palette.botanical-green-gold"></a>

## 植萃绿金

风格标签：通用。

参考绿色宠物营养详情页。与竹林深绿共用颜色角色，但本组绿更明亮、深浅反差更大，金色承担副标题与数字。下列色值为估计，不照抄展示板上与色块不一致的文字标注。

```css
.vl-botanical-light {
 --vl-tint:#f5f5e9; --vl-ink:#233d13; --vl-muted-ink:#4c593f;
 --vl-accent:#4f711e; --vl-accent-2:#83a941; --vl-accent-3:#c5a767;
 --vl-label-bg:#36521c; --vl-label-ink:#fff; --vl-edge-color:#ccd4b9;
 --vl-surface-end:#c5d49a; --vl-shadow-color:#182a10; --vl-light-color:#fffde5;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#fafaf3 0%,#e9eed6 40%,#b6cd76 73%,#52751f 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
.vl-botanical-dark {
 --vl-tint:#14220f; --vl-ink:#fffef4; --vl-muted-ink:#dfe5cc;
 --vl-accent:#ddc789; --vl-accent-2:#8aaf3f; --vl-accent-3:#c5a767;
 --vl-label-bg:#e4d49d; --vl-label-ink:#233414; --vl-edge-color:#7d9650;
 --vl-surface-end:#4d701e; --vl-shadow-color:#081207; --vl-light-color:#fffde5;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#14220f 0%,#263c12 45%,#50741f 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

浅色长渐变的下部已经变深，不能让深绿正文跨越到这个区域。将文字安排在稳定浅区，或在暗区单独绑定白色文字；暗底金字采用较亮 accent，装饰可用 accent-3。色标位置可移动，不能靠整个 section 的 opacity 调整。实际草地、肉类、奶酪和流体为图片，绿色渐变只承担空场、衔接与辅助光色。

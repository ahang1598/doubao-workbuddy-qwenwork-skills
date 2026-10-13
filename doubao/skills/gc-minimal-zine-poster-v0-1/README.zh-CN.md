# GC Minimal Zine Poster

[English](README.md) · **简体中文** · [日本語](README.ja.md)

这是一个 Codex 技能：它会把主题、句子、物件、情绪、文章构想、照片或内容简报，转化为一张安静、极简的 ZINE 风格编辑海报所需的提示词，并生成对应的位图图像。

调用名称为 `gc-minimal-zine-poster-v0-1`。

## 视觉方向

这个技能会把每个请求编排成一张留白充足的竖版纸张海报，具有以下特征：

- 3:5 比例的仿旧纸张画布
- 70%–90% 的留白
- 一个小型、可被清楚表现的主体或视觉组合
- 衬线、打字机或等宽字体
- 一个清晰可见的高饱和度色彩锚点
- 复印、孔版印刷、网点、凸版印刷或扫描纸张的瑕疵与质感
- 安静的日式／韩式独立 ZINE 或极简编辑设计氛围

它会避开商业广告式布局、光亮样机、电影感布光、3D 渲染、霓虹、密集拼贴簿，以及大段整齐的文字。

## 示例

| Night Door | Yellow Step |
| --- | --- |
| ![Night Door](examples/night-door.jpeg) | ![Yellow Step](examples/yellow-step.jpeg) |

| Shore Pause | Pause Map |
| --- | --- |
| ![Shore Pause](examples/shore-pause.jpeg) | ![Pause Map](examples/pause-map.jpeg) |

| Typhoon Memory | Moon Tide |
| --- | --- |
| ![Typhoon Memory](examples/typhoon-memory.jpeg) | ![Moon Tide](examples/moon-tide.jpeg) |

## 安装

把公开仓库直接克隆到 Codex 的技能目录：

```bash
git clone https://github.com/LiamGvchi/gc-minimal-zine-poster.git \  ~/.codex/skills/gc-minimal-zine-poster-v0-1
```

如果技能没有立即出现，请重启 Codex。

## 使用方法

按名称调用技能，并提供主题或简报：

```text
用 $gc-minimal-zine-poster-v0-1 制作一张“雨天旧书店”主题的海报
```

也可以提供一句话、文章构想、物件、情绪或参考图片。

## 输出

每次生成时，这个技能会返回：

1. 生成的位图海报图像
2. 最终的图像生成提示词
3. 所选变化方案，以及一段简短的诠释说明

工作流默认采用 Standard Mode，并会直接生成图片。只有在你明确要求“只要提示词”时，它才会停在仅输出提示词的阶段。

## 仓库结构

- `SKILL.md`：完整的 Codex 技能说明
- `README.md`：英文概览与安装说明
- `LICENSE`：MIT 许可证
- `examples/`：精选的已生成海报

这个仓库只发布这一个独立技能。其他私有仓库可能会集中备份多个本地技能，但私有备份自动化和无关技能不会放在这里。

## 许可证

MIT。详见 `LICENSE`。

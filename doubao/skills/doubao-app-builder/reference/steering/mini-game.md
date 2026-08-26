---
name: mini-game
description: 创建有胜负、挑战目标或玩法循环的小游戏（休闲 / 益智 / 街机 / 答题 / 反应类）。触发词：game, 游戏, 小游戏, 玩法, 街机, 益智, 关卡, playable。产品界面与流程演示用 interactive-prototype；无胜负的系统模拟不适用。
metadata:
  display-names:
    zh-CN: 小游戏
    en-US: Mini Game
---

# 小游戏

为有胜负 / 挑战目标 / 玩法循环的小游戏做玩法与工程决策。视觉方向仍由 `frontend-design` 先行确立；本 skill 条款与通用规则冲突时，以本 skill 为准。

**边界**：产品界面与流程演示 → `interactive-prototype`；无胜负的系统模拟（元胞自动机 / 流体 / 粒子沙盒）与 3D 沉浸漫游 → 不套用本 skill。

## Quick Reference

| 决策 | 默认 | 例外 |
|---|---|---|
| 渲染层 | 回合 + 离散网格 → DOM Grid；实时连续 → Canvas 2D | 用户指定时尊重 |
| 主循环 | 实时类 `requestAnimationFrame` | 回合类事件驱动，无主循环 |
| 输入 | 桌面键鼠 + 移动 touch 同时支持 | 用户明确单端 |
| 再来一局 | 真 reset 全部状态 | — |
| 最高分 | localStorage 持久化 | 用户明确不要 |
| 库 | 原生 Canvas / DOM / 原生 JS | 白名单按需行（物理 / 3D） |

## 交互契约

- 「再来一局」必须重置全部状态（分数 / 棋盘 / 计时器），禁 `location.reload()` 充当重启。
- 报分、结束、确认一律游戏内 UI 面板，禁 `alert()` / `confirm()` / `prompt()`。
- 结束面板至少含：本局分数、最高分、「再来一局」按钮。
- 暂停必须真停主循环（`cancelAnimationFrame`），不是 dt 置 0 空转；监听 `visibilitychange`，切后台自动暂停。
- 实时类主循环用 `requestAnimationFrame`，禁 `setInterval`；回合类事件驱动即可，不为「像游戏」硬塞 rAF。
- 最高分读写 `localStorage` 包 `try/catch`（隐私模式会抛错）。

## 渲染层

- 回合驱动 + 离散网格（2048 / 三消 / 棋盘 / 卡牌 / 答题）→ DOM + CSS Grid（`grid-template-columns: repeat(N, 1fr)`），移动 / 合并动画走 `transform` + `transition`。不默认上 Canvas——会丢掉免费的过渡动画与清晰文字；也不要 `position: absolute` + 像素 left/top 排格子。
- 实时连续运动（跑酷 / 弹幕 / 打砖块）→ Canvas 2D。

## 双端输入

- 桌面键鼠 + 移动 touch 必须同时支持（产物常在飞书容器内用手机打开），用户明确单端时除外。
- 优先 Pointer Events 统一两端；键盘方向类操作在移动端补虚拟方向键或 swipe 手势。
- 游戏容器设 `user-select: none; touch-action: none;`，防长按选中与手势拖动页面；触控目标 ≥ 44×44px。

## 素材

- 需要精灵 / 角色 / 背景图时用环境提供的图片生成能力（返回的 CDN URL 直接引用），prompt 尾缀固定：`game asset, transparent background, flat icon, no text overlay`。写「epic / cinematic scene」会产出电影海报而非可用素材。
- 纯数字 / 色块 / 几何即可成立的玩法（2048 类）不生图。

## 难度

- 进度感至少满足一种：得分递增 / 速度递增 / 关卡推进。禁从头到尾单一难度、单一速度。

## 库白名单（CDN 锁定）

| 用途 | 选型 | 默认/按需 | 引入方式 |
|---|---|---|---|
| 游戏渲染 | 原生 Canvas 2D / DOM / SVG | 默认 | 无需引入 |
| 交互 / 动画 | 原生 JS + rAF / 原生 CSS | 默认 | 无需引入 |
| 2D 物理 | Matter.js | 按需：真实刚体（抛体 / 碰撞堆叠 / 铰链）；简单弹跳自己写积分 | `<script src="https://cdn.jsdelivr.net/npm/matter-js@0.20.0/build/matter.min.js" integrity="sha384-ZRKYEXtLBVeqs9z1WxyeKutCqnkqolS/r1EUWuoUpG4ZKbnRAIXnHhHdnNuiB6CL" crossorigin="anonymous"></script>` |
| 3D 游戏 | Three.js r147 UMD | 按需：用户明确要 3D。引入前先读同目录 `three-js.md` | `<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js" integrity="sha384-vV17nr/rMaJqmeZkFUzXLpHdQ+ME5QHKdydaqqN+3Ga39RJlNrTatJxHwGV4ml2C" crossorigin="anonymous"></script>` |

- CDN URL 与 integrity 原样复制，不自行替换版本号。明确不引入：Phaser 等游戏引擎（原生 Canvas 替代）、GSAP（原生 CSS / rAF 替代）。`three-js.md` 中主库之外的 addon 文件与主库同源同版本，不逐个加 SRI。
- 游戏主体用原生 JS 组织（本链路全程原生 JS，无 React，见 html-develop.md「硬性技术栈约束」）。
- 音效仅在用户要求时做：Web Audio 合成，首次用户手势后 `AudioContext.resume()` 解锁，并提供静音开关。

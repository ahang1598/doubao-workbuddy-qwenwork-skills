# 汇总层文件命名规范

> 本文件定义汇总层资产的命名规则和 video-director 的定位逻辑。
> 读取时机：asset-vault 执行工作流 2 Phase 3（归类写入）时参考；video-director 需要读取资产时参考定位路径。
> ⚠️ 以下为初步方案，最终命名需与 video-director 对焦确认。

---

## 核心原则

- video-director 在读取资产时，通过「固定路径」或「行业/平台名拼接」即可精准定位，不需要遍历
- 归类原则：汇总资产按 video-director 的步骤维度组织，方便其在对应步骤精准读取

---

## 命名规则

| 目录 | 命名方式 | 示例 |
|------|---------|------|
| `patterns/methodologies/` | **固定文件名**（4 个） | `brief_analysis.md`、`video_analysis.md` |
| `patterns/script-structures/` | **类型名** | `产品测评型.md`、`剧情反转型.md` |
| `patterns/hooks/` | **Hook 类型名** | `数据对比型.md`、`悬念型.md` |
| `patterns/selling-points/` | **卖点类型名** | `功能型.md`、`情感型.md` |
| `patterns/platform-rules/` | **平台名** | `抖音.md`、`小红书.md`、`B站.md` |
| `patterns/creative-techniques/` | **技巧名** | `反转叙事.md`、`情绪递进.md` |
| `industry/{行业名}/` | **行业名作为目录，子文件固定名** | `科技/what_works.md` |

---

## video-director 定位逻辑

video-director 在步骤 1 拆解出 `行业` 和 `平台` 后，后续步骤的资产路径可直接拼接：

```
步骤 2-1 → patterns/methodologies/video_analysis.md       （固定路径）
         → industry/{行业}/what_works.md                  （行业名拼接）

步骤 2-2 → patterns/methodologies/selling_point_extraction.md （固定路径）
         → patterns/selling-points/_summary.md              （固定路径）

步骤 3   → patterns/methodologies/script_generation.md      （固定路径）
         → patterns/script-structures/_summary.md           （固定路径）
         → patterns/hooks/_summary.md                      （固定路径）
         → patterns/platform-rules/{平台}.md               （平台名拼接）
```

---

## `_summary.md` 的作用

每个子目录下的 `_summary.md` 是精简的概览索引，video-director 读它即可知道"库里有什么"：

```markdown
# 脚本结构总览

当前收录：3 种

| 类型 | 适用场景 | 案例数 | 置信度 |
|------|---------|--------|--------|
| 产品测评型 | 科技/效率类产品 | 4 | 规律 |
| 剧情反转型 | 情感/生活类内容 | 2 | 初步发现 |
| 教程型 | 工具类产品 | 1 | 初步发现 |
```

如需深入某个类型，再读对应的 `{类型名}.md`。

---

## 归类判断顺序

asset-vault 在 Phase 3 写入汇总层时，按以下顺序判断归类：

1. 先看目标目录下的 `_summary.md` → 是否已有相关类型
2. 再扫目录下已有文件的标题 → 是否有可合并的目标
3. 做出判断：合并已有 or 新建文件

---

## 写入规则

- 已有相关文件 → 合并（追加案例、更新结论）
- 无相关文件 → 按模板新建（模板见 `references/templates.md`）
- 方法论文件 → 迭代更新（非追加案例，而是优化方法论本身）
- 新建文件后必须同步更新对应的 `_summary.md`

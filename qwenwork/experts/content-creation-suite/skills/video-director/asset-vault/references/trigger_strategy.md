# 触发时机与策略

> 本文件定义 asset-vault 所有触发条件和策略。
> 读取时机：video-director 需要判断是否触发 asset-vault 时参考；asset-vault 执行工作流 1 Phase 0 时参考。
> 核心原则：以"交付"为锚点触发，不追踪"会话结束"。
> 执行机制：优先通过子智能体后台执行（按 video-director §0 平台适配表），降级为读取 `asset-vault/WORKFLOW.md` 内联执行。

---

## 触发类型总表

| 触发类型 | 触发条件 | 执行方式 | 处理范围 |
|---------|---------|---------|---------|
| **即时触发** | video-director 交付（status=delivered） | 优先子智能体后台执行，降级为内联 | 该项目产物 + inbox + knowledge_notes |
| **即时触发** | 用户说"帮我存一下" | 内联执行工作流 2 | 用户指定的内容 |
| **兜底触发** | 下次 video-director 启动 | 启动检查发现待处理项，优先子智能体，降级为内联 | interrupted 项目、in_progress 超 24h 的项目、inbox 待处理、knowledge_notes 待处理 |
| **累积触发** | inbox ≥ 3 个 或 knowledge_notes ≥ 5 条 | 提示用户确认后执行（优先子智能体，降级为内联） | 对应的待处理项 |
| **手动触发** | 用户说"帮我整理一下资产库" | 内联执行工作流 3 | 全量整理 |

---

## 即时触发（标准流程）

video-director 完成最终脚本交付时触发：

```
video-director 写入 final_script.md
  → 更新 metadata.json status = "delivered"
  → 清除 active_project.json
  → 告知用户"脚本已交付"
  → 执行资产沉淀：优先子智能体后台执行工作流 1（Phase 0-5），降级为内联
  → 完成后向用户简要转述沉淀结果
```

---

## 兜底触发（处理遗留）

video-director 下次启动时执行以下检查：

1. 扫描 `projects/` 下 status = `"interrupted"` 的项目，或 status = `"in_progress"` 且 metadata.json 的 `updated_at` 超过 24h 的项目
2. 检查 `inbox/` 是否有未处理素材（`_log/writes.jsonl` 中 project=null 且 analyzed=false）
3. 检查 `_log/knowledge_notes.jsonl` 是否有 `analyzed=false` 的条目
4. 如有待处理项 → 提示用户，确认后执行资产汇总（优先子智能体，降级为内联；Phase 6 补做）

---

## 累积触发（主动提示）

当 video-director 检测到（可在任意步骤间隙检查）：
- `inbox/` 中未处理素材 ≥ 3 个，或
- `knowledge_notes.jsonl` 中未处理条目 ≥ 5 条

主动提示用户：
> "你有 {N} 个素材/知识还没归档，要现在处理吗？"

用户确认后 → 执行资产汇总（优先子智能体，降级为内联）。
用户说"不用" → 跳过，下次再提示。

---

## 中断项目的处理策略

| 状态 | 含义 | 处理方式 |
|------|------|---------|
| `"in_progress"` + 超 24h 未更新 | 大概率不会继续 | 兜底触发时对已有产物做轻量分析 |
| `"in_progress"` + 未超 24h | 可能还在进行 | 不处理，等待 |
| `"abandoned"` | 用户明确放弃 | 对已有产物做轻量分析 |
| `"delivered"` + 未分析 | 正常交付但分析未执行（异常） | 兜底触发时补做完整分析 |

**轻量分析**：只执行 Phase 2-3，不要求所有文件都存在，有什么分析什么，不因缺失文件而跳过整个项目。

---

## 不触发的情况

以下情况**不**触发 asset-vault：
- 闲聊、与内容创作无关的对话
- video-director 工作流中途暂停（用户可能还会回来继续）
- 只做了前几步就切换话题（status 仍为 in_progress，等兜底处理）
- 用户明确说"不用存"、"不需要分析"

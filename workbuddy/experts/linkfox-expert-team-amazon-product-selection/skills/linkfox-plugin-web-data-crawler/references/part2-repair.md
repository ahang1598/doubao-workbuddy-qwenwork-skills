# Part 2 — Diagnose & Repair (Max 3 Retries)

本文档仅在 Part 1 采集失败时加载。不要主动加载此文件。

## 三层递进修复

```
Step Failure（AI 收到 FAILED + errorMsg）
    │
    ├─ 第 1 层：读取错误诊断（读一次 HTTP 响应）
    │   → 安全类错误（captcha/403/登录/客户端不在线）→ STOP，报告用户
    │   → timeout → 可重试
    │   → 其他采集错误 → 进入第 2 层，按失败症状匹配修复策略
    │
    ├─ 第 2 层：AI 分析失败原因，分类型修复（1-2 次往返）
    │   AI 根据 errorMsg + partialResults 判断失败类型，选择对应策略。
    │   具体工具用法见 tools/INDEX.md 对应的 actionCode 独立文档。
    │   修复准则：
    │     - selector 过期 → 追加新值，不替换旧值
    │     - 元素天然不存在 → allowFailure: true
    │     - 交互结构缺陷 → 调整步骤结构（LOOP / nth-of-type / 多步 CLICK）
    │
    └─ 最多 4 次总尝试（原始 + 最多 3 次重试）。
       全部失败 → 报告诊断摘要给用户
```

## Step 1 — 读取 errorMsg，按信号分类

collectTask API 失败时 `errorMsg` 包含诊断信息。根据 `errorMsg` 判断下一步：

| 信号 | 诊断 | 动作 |
|---|---|---|
| `errorMsg` 含 "captcha"/"验证码"/"robot check" | 反爬拦截 | **STOP.** 提示用户手动打开浏览器检查 |
| `errorMsg` 含 "403"/"access denied" | 站点拦截请求 | **STOP.** 建议换 IP/区域 |
| `errorMsg` 含 "sign in"/"请登录" | 需要登录 | **STOP.** 提示用户登录该站点 |
| `errorMsg` 含 "客户端不在线" | 插件未连接 | **STOP.** 提示用户打开浏览器插件并登录 |
| `errorMsg` 含 "timeout"/"超时" | 等待超时 | 可重试，最多 3 次，退避 1s→2s→4s |
| 其他不明错误 | 未知 | 进入 Step 2，按失败症状诊断 |

## Step 2 — 按失败症状匹配修复策略

根据 `errorMsg` 中的失败信息 + `partialResults` 已有数据，判断失败类型并选择对应策略：

| 失败症状 | 诊断 | 修复策略 |
|---|---|---|
| EXTRACT "Element not found"，partialResults 中同类字段有值 | selector 过期（其他页面可能仍有效） | VERIFY_SELECTOR → GET_DOM 查看 DOM → 追加候选 selector 到数组头部 → 重试（**追加不替换**） |
| EXTRACT "Element not found"，同类产品页面天然无此元素（如翻新产品无 ranking、非服装无尺码表） | 元素不存在 | 为对应 step 加 `allowFailure: true`。需求侧: 更新 base-full.json 时一并追加 |
| CLICK 只命中一个，但页面有多个可点击目标 | 单次 CLICK 不够（如折叠面板有 N 个 `.common-entry__top`，CLICK 只点第一个） | 先用 VERIFY_SELECTOR 统计数量，再通过 LOOP + `nth-of-type(N)` 逐个点击。LOOP 未上线时用 `nth-of-type` + `allowFailure` 覆盖。需求侧: 更新 base-full.json 时替换为 LOOP 结构 |
| SCROLL / WAIT 后目标区域仍为空 | 动态渲染未触发或等待时间不足 | 调整 SCROLL 目标位置或延长 WAIT 时长。探索: GET_DOM 确认区域是否已渲染 |

工具文档（GET_PAGE_INFO / GET_DOM / VERIFY_SELECTOR / FIND_SELECTOR / LOOP）见 `tools/INDEX.md` 对应的 actionCode 独立文档。

## Step 3 — Selector Repair Rule（不可违反）

🔴 **修复 selector 时，绝不可删除旧选择器。**

| 操作 | ❌ 禁止 | ✅ 正确 |
|---|---|---|
| 单值失效，追加新值 | 直接替换为 `"new"` | `"old"` → `["new", "old"]` |
| 数组内某个失效，追加头部 | 删除失效项 | `["a", "b"]` → `["new", "a", "b"]` |

**原因**：旧选择器可能仅在当前产品页面不匹配，其他产品页面仍然有效。删除等于丢弃已验证的 fallback。

## Step 4 — 发送修复

🔴 **重试前，必须从 workflow 中剥离 OPEN_TAB 步骤。** 失败时页面仍然开着且 URL 仍是目标商品页面，重新 OPEN_TAB 等于硬刷新页面 → 触发人机验证。唯一的例外：错误信息包含 "未找到活动标签页" / "Tab was closed" / "No tab found"。

修复后的 workflow 写入临时文件，通过 `send --file` 发送：

```bash
python scripts/run_crawl.py send --site <key> --file /tmp/repaired.json
```

## Step 5 — 重试计数器

最多 4 次总尝试（含原始执行）。达到上限后退出：

```
❌ 采集失败，已尝试 3 次修复，均未成功。

失败步骤: <step description>
错误信息: <error message>
建议: 打开浏览器访问目标页面确认页面结构是否变更。
```

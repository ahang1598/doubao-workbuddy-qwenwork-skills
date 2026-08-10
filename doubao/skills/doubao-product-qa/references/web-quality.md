# Web 质量专项

## 目录

- [启用原则](#启用原则)
- [性能与 Core Web Vitals](#性能与-core-web-vitals)
- [可访问性](#可访问性)
- [视觉回归](#视觉回归)
- [负载与容量](#负载与容量)
- [报告要求](#报告要求)

## 启用原则

专项按风险启用，不把工具列表当成完成标准：

- 营销、内容、搜索和交易入口：性能与视觉风险高；
- 表单、后台、公共服务和核心任务：键盘与可访问性风险高；
- 大促、开放 API、消息高峰：容量和可靠性风险高；
- 设计系统、跨浏览器重构：视觉回归价值高。

先读取项目已有工具和基线。已有 Lighthouse CI、axe、Percy/Chromatic、Playwright snapshots 或 k6 时沿用项目配置。

## 性能与 Core Web Vitals

### 单页面实验室检查

使用 Lighthouse 检查 performance、accessibility、best practices 等。公开页面可用 CLI；需要登录的页面优先使用 Chrome DevTools、持久化浏览器会话或项目既有 Lighthouse CI 流程。

```bash
npx lighthouse "$TARGET_URL" \
  --output=json \
  --output=html \
  --output-path=qa-results/feature/evidence/lighthouse/report
```

记录 Chrome/Lighthouse 版本、设备模拟、网络/CPU throttling、次数和中位数。不同机器、浏览器版本或 throttling 配置的结果不能直接做回归结论。

### 浏览器指标

关注与需求相关的 LCP、INP、CLS、FCP、TTFB 和关键业务操作耗时。阈值优先来自产品 SLO、历史基线或项目预算；没有基线时先采样，不伪造“行业标准即验收标准”。小样本、单次 Lighthouse 或 baseline-only 结果统一记为 `validation_scope=precheck`；只能形成待确认或补证动作，不能直接创建正式性能 Bug。

Lighthouse 是实验室诊断，不能替代真实用户监控。报告区分 lab、synthetic 和 RUM 数据。

## 可访问性

Playwright 项目可使用 `@axe-core/playwright`：

```ts
import AxeBuilder from '@axe-core/playwright';
import { test, expect } from '@playwright/test';

test('TC-A11Y-001 首页无自动可检出的 A/AA 问题', async ({ page }) => {
  await page.goto('/');
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(result.violations).toEqual([]);
});
```

扫描页面的稳定业务状态，而不是 skeleton/loading。对弹窗、菜单、错误提示等交互后状态单独扫描。

自动化只覆盖可机器判定的问题，至少补：

- 全键盘完成关键旅程；
- 焦点顺序、焦点陷阱和关闭后焦点恢复；
- 表单 label、错误关联和动态提示；
- 缩放、文字放大、颜色以外的信息表达；
- 代表性屏幕阅读器检查（范围要求时）。

报告保存违反规则、影响节点、页面状态、严重程度和复现步骤；`incomplete` 项进入人工检查，不直接算通过。

需要独立可运行工程时复制 `assets/web-a11y-starter/`。该 starter 提供页面路由扫描、critical/serious 可配置门禁、带到期时间的豁免清单、JSON/Markdown/JUnit 报告和 `incomplete` 人工检查项。默认不截图；只有用户已选择允许截图时才设置 `QA_CAPTURE_SCREENSHOTS=1`。

## 视觉回归

视觉回归本身需要生成基线与实际截图。用户请求视觉回归但未说明是否允许截图时，先明确说明该依赖并获得确认；用户选择不截图时，将视觉回归标为未执行而不是静默改成普通 DOM 检查。

优先 Playwright `toHaveScreenshot()`，只为高价值稳定页面建立基线：

```ts
await expect(page.getByTestId('checkout-summary')).toHaveScreenshot(
  'checkout-summary.png',
  { animations: 'disabled', mask: [page.getByTestId('current-time')] },
);
```

规则：

- 基线按浏览器、OS、视口和 DPR 隔离；
- 固定字体、数据、语言、时区、动画和网络状态；
- 屏蔽时间、随机 ID、广告和个性化区域，但不能屏蔽被测功能；
- 第一次基线和大范围更新必须人工审查；
- 不因 diff 失败就直接更新 snapshot，先判断产品变化是否被批准；
- 组件级/局部截图优先于整页截图，减少无关噪声。

## 负载与容量

执行前必须明确目标环境、允许流量、时间窗口、测试数据、限流策略、停止阈值和联系人。默认不对生产运行负载测试。

选择方式：

- 协议级 k6：生成大部分负载，验证吞吐、延迟、错误率和容量；
- k6 browser：少量浏览器 VU，观察前端和 Core Web Vitals；
- 混合：协议级承担主要流量，浏览器层验证用户体验。

阈值必须来自 SLO/需求，例如错误率、p95/p99、业务成功率和资源水位。测试期间关联服务端监控、数据库、队列、缓存和第三方指标。

出现错误率快速上升、数据破坏、共享环境受影响或达到预设资源阈值时停止。负载结果不能由单次平均值概括。

需要生成 k6 工程时复制 `assets/k6-starter/`。该 starter 提供：

- `smoke/load/stress/spike/soak` 场景；
- VU、arrival rate、ramp、duration 环境配置；
- HTTP 失败率、p95 和业务成功率门禁；
- 自定义业务成功率与业务耗时指标；
- `handleSummary()` 生成 JSON 和 Markdown 摘要；
- 写请求显式授权。

没有已确认 SLO/预算时使用 `QA_BASELINE_ONLY=1` 采样并建立基线，execution 使用 `validation_scope=precheck`，不输出“达到行业标准”或正式 Bug。阈值模式必须显式配置 `QA_P95_MS`、`QA_ERROR_RATE` 和 `QA_BUSINESS_SUCCESS_RATE`。

## 报告要求

每个专项说明：

- 为什么启用、测试范围和未覆盖项；
- 工具/浏览器/运行环境和版本；
- 数据、基线、阈值及来源；
- 原始报告和证据路径；
- 结果、波动范围和是否可复现；
- 阻断问题、改进建议和复测方式。

专项未执行时写“未执行及原因”，不写“无性能/可访问性/视觉问题”。

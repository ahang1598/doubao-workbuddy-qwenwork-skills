import fs from 'node:fs/promises'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type TestInfo } from '@playwright/test'
import type { AxeResults } from 'axe-core'

type Impact = 'minor' | 'moderate' | 'serious' | 'critical' | null
type AllowItem = { ruleId: string; targetPattern?: string; reason: string; expires: string }

const routes = (process.env.QA_A11Y_ROUTES || '/').split(',').map((value) => value.trim()).filter(Boolean)
const gateImpacts = new Set((process.env.QA_A11Y_GATE_IMPACTS || 'critical,serious').split(',').map((value) => value.trim()))

async function loadAllowlist(): Promise<AllowItem[]> {
  return JSON.parse(await fs.readFile('a11y-allowlist.json', 'utf8')) as AllowItem[]
}

function isAllowed(ruleId: string, targets: string[], item: AllowItem, now: Date): boolean {
  if (item.ruleId !== ruleId || new Date(`${item.expires}T23:59:59Z`) < now) return false
  if (!item.targetPattern) return true
  return targets.some((target) => target.includes(item.targetPattern as string))
}

async function writeReport(route: string, results: AxeResults, info: TestInfo) {
  const allowlist = await loadAllowlist()
  const now = new Date()
  const rows = results.violations.flatMap((violation) => violation.nodes.map((node) => {
    const targets = node.target.map(String)
    const exemption = allowlist.find((item) => isAllowed(violation.id, targets, item, now))
    return {
      ruleId: violation.id,
      impact: violation.impact as Impact,
      target: targets,
      helpUrl: violation.helpUrl,
      failureSummary: node.failureSummary,
      exempt: Boolean(exemption),
      exemptionReason: exemption?.reason,
      exemptionExpires: exemption?.expires,
      html: process.env.QA_A11Y_INCLUDE_HTML === '1' ? node.html : undefined,
    }
  }))
  const incomplete = results.incomplete.flatMap((item) => item.nodes.map((node) => ({ ruleId: item.id, impact: item.impact, target: node.target.map(String), helpUrl: item.helpUrl })))
  const slug = route.replace(/[^a-zA-Z0-9]+/g, '-') || 'root'
  const directory = path.join('artifacts', 'a11y')
  await fs.mkdir(directory, { recursive: true })
  const payload = { route, scannedAt: now.toISOString(), gateImpacts: [...gateImpacts], violations: rows, manualReview: incomplete }
  const jsonPath = path.join(directory, `${slug}.json`)
  const mdPath = path.join(directory, `${slug}.md`)
  await fs.writeFile(jsonPath, JSON.stringify(payload, null, 2))
  await fs.writeFile(mdPath, [
    `# 可访问性报告 ${route}`,
    '',
    `- 自动违规节点：${rows.length}`,
    `- 已批准豁免：${rows.filter((row) => row.exempt).length}`,
    `- 需人工检查：${incomplete.length}`,
    '',
    ...rows.map((row) => `- [${row.exempt ? '豁免' : row.impact || 'unknown'}] ${row.ruleId} — ${row.target.join(', ')}${row.exemptionExpires ? `（至 ${row.exemptionExpires}）` : ''}`),
    '',
    '## 人工检查',
    ...incomplete.map((row) => `- ${row.ruleId} — ${row.target.join(', ')}`),
    '',
  ].join('\n'))
  await info.attach(`a11y-${slug}`, { path: jsonPath, contentType: 'application/json' })
  return rows
}

for (const route of routes) {
  test(`TC-A11Y-${route} 自动扫描并输出人工检查项`, async ({ page }, info) => {
    test.skip(!process.env.QA_BASE_URL, '必须显式设置 QA_BASE_URL')
    await page.goto(route)
    await page.waitForLoadState('domcontentloaded')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze()
    const rows = await writeReport(route, results, info)
    const blocking = rows.filter((row) => !row.exempt && row.impact && gateImpacts.has(row.impact))
    expect(blocking, `发现 ${blocking.length} 个门禁级可访问性问题`).toEqual([])
  })
}

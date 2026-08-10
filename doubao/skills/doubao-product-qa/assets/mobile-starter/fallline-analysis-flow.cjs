const fs = require('node:fs/promises')
const path = require('node:path')
const { remote } = require('webdriverio')

class ProductFailure extends Error {}

function errorCause(error) {
  const cause = error && typeof error === 'object' ? error.cause : null
  if (!cause) return null
  return {
    name: cause.name || null,
    message: cause.message || String(cause),
    code: cause.code || null,
    stack: cause.stack || null,
  }
}

function required(name) {
  const value = process.env[name]
  if (!value) throw new Error(`缺少环境变量 ${name}`)
  return value
}

function normalizeWebdriverRequest(request) {
  // 由 undici 根据最终请求体计算，避免 Node 26 + WebdriverIO 9 的显式长度校验异常。
  request.headers?.delete?.('content-length')
  return request
}

function screenshotPolicy() {
  if (process.env.QA_SCREENSHOT_POLICY) return process.env.QA_SCREENSHOT_POLICY
  return process.env.QA_CAPTURE_SCREENSHOTS === '1' ? 'every-step' : 'off'
}

function shouldScreenshot(kind) {
  const policy = screenshotPolicy()
  return policy === 'every-step' || policy === kind || (policy === 'key' && kind === 'key')
}

async function evidence(driver, artifactDir, step, kind = 'key') {
  const source = await driver.getPageSource().catch(() => '')
  await fs.writeFile(path.join(artifactDir, `${step}.xml`), source)
  if (shouldScreenshot(kind)) {
    const screenshot = await driver.takeScreenshot()
    await fs.writeFile(path.join(artifactDir, `${step}.png`), screenshot, 'base64')
  }
}

async function displayed(driver, selectors, timeout = 15000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    for (const selector of selectors) {
      const elements = await driver.$$(selector).catch(() => [])
      for (const element of elements) {
        if (await element.isDisplayed().catch(() => false)) return { element, selector }
      }
    }
    await driver.pause(300)
  }
  throw new Error(`等待元素超时：${selectors.join(' | ')}`)
}

async function click(driver, selectors, timeout = 15000) {
  const found = await displayed(driver, selectors, timeout)
  await found.element.click()
  return found.selector
}

async function exists(driver, selectors, timeout = 1000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    for (const selector of selectors) {
      const elements = await driver.$$(selector).catch(() => [])
      for (const element of elements) {
        if (await element.isExisting().catch(() => false)) return true
      }
    }
    await driver.pause(200)
  }
  return false
}

async function tapRatio(driver, xRatio, yRatio) {
  const rect = await driver.getWindowRect()
  const x = Math.round(rect.width * xRatio)
  const y = Math.round(rect.height * yRatio)
  await driver.execute('mobile: tap', { x, y })
  return { x, y }
}

async function ensureAnalysisHome(driver, actions) {
  const homeSelectors = ['~选择滑雪视频', '-ios predicate string:label == "选择滑雪视频"']
  if (await exists(driver, homeSelectors, 1500)) return
  const tab = await displayed(driver, ['~分析', '-ios predicate string:label == "分析"'], 5000)
  await tab.element.click()
  actions.push({ action: 'restore-start-state', method: 'analysis-tab', selector: tab.selector })
}

async function selectFirstVideo(driver, actions) {
  const selectors = [
    '-ios predicate string:(label CONTAINS[c] "0:14" OR name CONTAINS[c] "0:14") AND visible == 1',
    '-ios predicate string:(label CONTAINS[c] "视频" OR name CONTAINS[c] "视频") AND visible == 1',
  ]
  for (const selector of selectors) {
    try {
      const items = await driver.$$(selector)
      for (const item of items) {
        if (!await item.isDisplayed().catch(() => false)) continue
        const rect = await item.getRect().catch(() => null)
        if (rect && rect.y < 200) continue
        await item.click()
        actions.push({ action: 'select-video', method: 'selector', selector })
        return
      }
    } catch {
      // 尝试下一种稳定定位。
    }
  }
  const point = await tapRatio(driver, 0.16, 0.46)
  actions.push({ action: 'select-video', method: 'system-picker-coordinate-fallback', point })
}

async function swipeReport(driver) {
  try {
    await driver.execute('mobile: swipe', { direction: 'up' })
  } catch {
    await driver.execute('mobile: scroll', { direction: 'down' })
  }
}

function capabilities(target) {
  const value = {
    platformName: 'iOS',
    'appium:automationName': 'XCUITest',
    'appium:udid': target,
    'appium:newCommandTimeout': 180,
    'appium:noReset': process.env.QA_RESET !== '1',
    'appium:autoAcceptAlerts': false,
    'appium:waitForIdleTimeout': 5,
  }
  if (process.env.QA_APP_PATH) value['appium:app'] = path.resolve(process.env.QA_APP_PATH)
  if (process.env.QA_APP_ID) value['appium:bundleId'] = process.env.QA_APP_ID
  if (!value['appium:app'] && !value['appium:bundleId']) {
    throw new Error('FallLine Appium 测试需要 QA_APP_PATH 或 QA_APP_ID')
  }
  return value
}

async function main() {
  const platform = required('QA_PLATFORM').toLowerCase()
  if (platform !== 'ios') throw new Error(`FallLine 当前只有 iOS App，收到 QA_PLATFORM=${platform}`)
  const target = required('QA_TARGET_ID')
  const artifactDir = path.resolve(process.env.QA_ARTIFACT_DIR || 'artifacts/fallline-ios')
  await fs.mkdir(artifactDir, { recursive: true })
  const startedAt = new Date().toISOString()
  const actions = []
  const assertions = []
  let driver
  let failureKind = 'infra_error'

  try {
    driver = await remote({
      hostname: process.env.APPIUM_HOST || '127.0.0.1',
      port: Number(process.env.APPIUM_PORT || 4723),
      path: process.env.APPIUM_BASE_PATH || '/',
      logLevel: process.env.WDIO_LOG_LEVEL || 'info',
      connectionRetryTimeout: Number(process.env.QA_WEBDRIVER_TIMEOUT || 120000),
      connectionRetryCount: Number(process.env.QA_WEBDRIVER_RETRIES || 2),
      transformRequest: normalizeWebdriverRequest,
      capabilities: capabilities(target),
    })

    await ensureAnalysisHome(driver, actions)
    await displayed(driver, ['~选择滑雪视频', '-ios predicate string:label == "选择滑雪视频"'], 30000)
    await evidence(driver, artifactDir, '01-home', 'key')
    actions.push({ action: 'home-ready' })

    const selectSelector = await click(driver, ['~选择滑雪视频', '-ios predicate string:label == "选择滑雪视频"'])
    actions.push({ action: 'open-photo-picker', selector: selectSelector })
    await displayed(driver, ['~取消', '-ios predicate string:label == "取消"'], 15000)
    await evidence(driver, artifactDir, '02-photo-picker', 'key')

    await selectFirstVideo(driver, actions)
    await displayed(driver, ['~确认分析', '-ios predicate string:label == "确认分析"'], 30000)
    await evidence(driver, artifactDir, '03-confirmation', 'key')

    const startSelector = await click(driver, ['~开始 AI 分析', '-ios predicate string:label == "开始 AI 分析"'])
    actions.push({ action: 'start-analysis', selector: startSelector })
    await evidence(driver, artifactDir, '04-analysis-started', 'key')

    await displayed(driver, ['~分析中', '-ios predicate string:label == "分析中"'], 10000).catch(() => null)
    await evidence(driver, artifactDir, '05-analysis-progress', 'key')

    await displayed(driver, ['~分析报告', '-ios predicate string:label == "分析报告"'], Number(process.env.QA_ANALYSIS_TIMEOUT || 120000))
    await evidence(driver, artifactDir, '06-report-top', 'key')
    actions.push({ action: 'report-opened' })

    const videoMissing = await exists(driver, ['~视频文件未找到', '-ios predicate string:label == "视频文件未找到"'])
    assertions.push({ id: 'report-video-available', ok: !videoMissing, actual: videoMissing ? '视频文件未找到' : '视频区域可用' })
    const noPose = await exists(driver, ['~未检测到人体', '-ios predicate string:label == "未检测到人体"'])
    assertions.push({ id: 'analysis-has-pose-result', ok: !noPose, actual: noPose ? '未检测到人体' : '存在姿态结果' })

    await swipeReport(driver)
    await driver.pause(500)
    await evidence(driver, artifactDir, '07-report-details', 'key')

    await click(driver, ['~关闭', '-ios predicate string:label == "关闭"'])
    await displayed(driver, ['~选择滑雪视频', '-ios predicate string:label == "选择滑雪视频"'], 15000)
    await evidence(driver, artifactDir, '08-home-after-analysis', 'key')

    await click(driver, ['~记录', '-ios predicate string:label == "记录"'])
    await displayed(driver, ['~训练记录', '-ios predicate string:label == "训练记录"'], 15000)
    await evidence(driver, artifactDir, '09-history', 'key')
    assertions.push({ id: 'history-entry-saved', ok: await exists(driver, ['-ios predicate string:label CONTAINS[c] "5.mp4" OR name CONTAINS[c] "5.mp4"'], 3000) })

    try {
      await click(driver, ['-ios predicate string:label CONTAINS[c] "5.mp4" OR name CONTAINS[c] "5.mp4"'], 5000)
      actions.push({ action: 'open-history-report', method: 'selector' })
    } catch {
      const point = await tapRatio(driver, 0.5, 0.25)
      actions.push({ action: 'open-history-report', method: 'coordinate-fallback', point })
    }
    await displayed(driver, ['~分析报告', '-ios predicate string:label == "分析报告"'], 15000)
    await evidence(driver, artifactDir, '10-history-report', 'key')
    assertions.push({ id: 'history-report-reopens', ok: true })

    const historyVideoMissing = await exists(driver, ['~视频文件未找到', '-ios predicate string:label == "视频文件未找到"'])
    assertions.push({ id: 'history-video-available', ok: !historyVideoMissing, actual: historyVideoMissing ? '视频文件未找到' : '视频区域可用' })

    const failedAssertions = assertions.filter((item) => !item.ok)
    if (failedAssertions.length) {
      failureKind = 'product_failure'
      throw new ProductFailure(`FallLine 业务断言失败：${failedAssertions.map((item) => item.id).join(', ')}`)
    }

    await fs.writeFile(path.join(artifactDir, 'result.json'), JSON.stringify({
      schemaVersion: 1,
      caseId: 'TC-IOS-FALLLINE-001',
      ok: true,
      status: 'passed',
      platform,
      target,
      startedAt,
      endedAt: new Date().toISOString(),
      screenshotPolicy: screenshotPolicy(),
      actions,
      assertions,
    }, null, 2))
  } catch (error) {
    if (driver) await evidence(driver, artifactDir, '99-failure', 'failure').catch(() => {})
    await fs.writeFile(path.join(artifactDir, 'result.json'), JSON.stringify({
      schemaVersion: 1,
      caseId: 'TC-IOS-FALLLINE-001',
      ok: false,
      status: 'failed',
      failureKind: error instanceof ProductFailure ? 'product_failure' : failureKind,
      platform,
      target,
      startedAt,
      endedAt: new Date().toISOString(),
      screenshotPolicy: screenshotPolicy(),
      actions,
      assertions,
      error: String(error.stack || error),
      errorCause: errorCause(error),
    }, null, 2))
    throw error
  } finally {
    if (driver) await driver.deleteSession().catch(() => {})
  }
}

main().catch((error) => {
  console.error(error.stack || error)
  process.exitCode = 1
})

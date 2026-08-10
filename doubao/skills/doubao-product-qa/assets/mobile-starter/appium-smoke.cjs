const fs = require('node:fs/promises')
const path = require('node:path')
const { remote } = require('webdriverio')

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

function safeCapabilities(value) {
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      /password|token|secret/i.test(key) ? '<REDACTED>' : item,
    ]),
  )
}

async function main() {
  const platform = required('QA_PLATFORM').toLowerCase()
  const target = required('QA_TARGET_ID')
  const artifactDir = path.resolve(process.env.QA_ARTIFACT_DIR || 'artifacts/appium-smoke')
  await fs.mkdir(artifactDir, { recursive: true })

  let capabilities
  if (platform === 'ios') {
    capabilities = {
      platformName: 'iOS',
      'appium:automationName': 'XCUITest',
      'appium:udid': target,
      'appium:newCommandTimeout': 120,
      'appium:noReset': process.env.QA_RESET !== '1',
    }
    if (process.env.QA_APP_PATH) capabilities['appium:app'] = path.resolve(process.env.QA_APP_PATH)
    if (process.env.QA_APP_ID) capabilities['appium:bundleId'] = process.env.QA_APP_ID
    if (!capabilities['appium:app'] && !capabilities['appium:bundleId']) {
      throw new Error('iOS 需要 QA_APP_PATH 或 QA_APP_ID')
    }
  } else if (platform === 'android') {
    capabilities = {
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:udid': target,
      'appium:newCommandTimeout': 120,
      'appium:noReset': process.env.QA_RESET !== '1',
      'appium:autoGrantPermissions': process.env.QA_AUTO_GRANT_PERMISSIONS === '1',
    }
    if (process.env.QA_APP_PATH) capabilities['appium:app'] = path.resolve(process.env.QA_APP_PATH)
    if (process.env.QA_APP_ID) capabilities['appium:appPackage'] = process.env.QA_APP_ID
    if (process.env.QA_APP_ACTIVITY) capabilities['appium:appActivity'] = process.env.QA_APP_ACTIVITY
    if (!capabilities['appium:app'] && !capabilities['appium:appPackage']) {
      throw new Error('Android 需要 QA_APP_PATH 或 QA_APP_ID')
    }
  } else {
    throw new Error(`QA_PLATFORM 只支持 ios/android，收到 ${platform}`)
  }

  await fs.writeFile(
    path.join(artifactDir, 'capabilities.json'),
    JSON.stringify(safeCapabilities(capabilities), null, 2),
  )

  let driver
  const startedAt = new Date().toISOString()
  try {
    driver = await remote({
      hostname: process.env.APPIUM_HOST || '127.0.0.1',
      port: Number(process.env.APPIUM_PORT || 4723),
      path: process.env.APPIUM_BASE_PATH || '/',
      logLevel: process.env.WDIO_LOG_LEVEL || 'info',
      connectionRetryTimeout: Number(process.env.QA_WEBDRIVER_TIMEOUT || 120000),
      connectionRetryCount: Number(process.env.QA_WEBDRIVER_RETRIES || 2),
      transformRequest: normalizeWebdriverRequest,
      capabilities,
    })
    if (process.env.QA_CAPTURE_SCREENSHOTS === '1') {
      const screenshot = await driver.takeScreenshot()
      await fs.writeFile(path.join(artifactDir, 'launch.png'), screenshot, 'base64')
    }
    const source = await driver.getPageSource()
    if (!source || source.length < 10) throw new Error('Appium 会话未返回有效页面树')
    await fs.writeFile(path.join(artifactDir, 'page-source.xml'), source)
    await fs.writeFile(
      path.join(artifactDir, 'result.json'),
      JSON.stringify({ ok: true, platform, target, startedAt, endedAt: new Date().toISOString() }, null, 2),
    )
  } catch (error) {
    await fs.writeFile(
      path.join(artifactDir, 'result.json'),
      JSON.stringify(
        { ok: false, platform, target, startedAt, endedAt: new Date().toISOString(), error: String(error.stack || error) },
        null,
        2,
      ),
    )
    throw error
  } finally {
    if (driver) await driver.deleteSession()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})

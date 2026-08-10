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

async function maybeScreenshot(driver, directory, name) {
  if (process.env.QA_CAPTURE_SCREENSHOTS !== '1') return
  const value = await driver.takeScreenshot()
  await fs.writeFile(path.join(directory, `${name}.png`), value, 'base64')
}

async function clickVisible(driver, selector) {
  const element = await driver.$(selector)
  try {
    await element.waitForDisplayed({ timeout: 5000 })
  } catch (error) {
    const platform = required('QA_PLATFORM').toLowerCase()
    for (let attempt = 0; attempt < 4; attempt += 1) {
      if (platform === 'android') {
        const rect = await driver.getWindowRect()
        await driver.execute('mobile: scrollGesture', {
          left: Math.round(rect.width * 0.1),
          top: Math.round(rect.height * 0.2),
          width: Math.round(rect.width * 0.8),
          height: Math.round(rect.height * 0.6),
          direction: 'down',
          percent: 0.7,
        })
      } else {
        await driver.execute('mobile: scroll', { direction: 'down' })
      }
      if (await element.isDisplayed().catch(() => false)) break
    }
    await element.waitForDisplayed({ timeout: 5000 })
  }
  await element.click()
}

function capabilities(platform, target) {
  if (platform === 'android') {
    const value = {
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:udid': target,
      'appium:appPackage': process.env.QA_APP_ID || 'com.saucelabs.mydemoapp.android',
      'appium:appActivity': process.env.QA_APP_ACTIVITY || 'com.saucelabs.mydemoapp.android.view.activities.SplashActivity',
      'appium:noReset': process.env.QA_RESET !== '1',
      'appium:newCommandTimeout': 120,
    }
    if (process.env.QA_APP_PATH) value['appium:app'] = path.resolve(process.env.QA_APP_PATH)
    return value
  }
  if (platform === 'ios') {
    const value = {
      platformName: 'iOS',
      'appium:automationName': 'XCUITest',
      'appium:udid': target,
      'appium:bundleId': process.env.QA_APP_ID || 'com.saucelabs.mydemo.app.ios',
      'appium:noReset': process.env.QA_RESET !== '1',
      'appium:newCommandTimeout': 120,
    }
    if (process.env.QA_APP_PATH) value['appium:app'] = path.resolve(process.env.QA_APP_PATH)
    return value
  }
  throw new Error(`QA_PLATFORM 只支持 android/ios，收到 ${platform}`)
}

async function androidProductToCart(driver) {
  const appId = process.env.QA_APP_ID || 'com.saucelabs.mydemoapp.android'
  await (await driver.$(`id=${appId}:id/productRV`)).waitForDisplayed({ timeout: 15000 })
  await clickVisible(driver, 'android=new UiSelector().text("Sauce Labs Backpack")')
  await (await driver.$(`id=${appId}:id/productTV`)).waitForDisplayed({ timeout: 10000 })
  await clickVisible(driver, `id=${appId}:id/cartBt`)
  await clickVisible(driver, `id=${appId}:id/cartRL`)
  await (await driver.$('android=new UiSelector().text("Sauce Labs Backpack")')).waitForDisplayed({ timeout: 10000 })
}

async function iosProductToCart(driver) {
  await clickVisible(driver, '~Product Name')
  await (await driver.$('~Sauce Labs Backpack - Black')).waitForDisplayed({ timeout: 10000 })
  await clickVisible(driver, '~Add To Cart')
  await clickVisible(driver, '~Cart-tab-item')
  await (await driver.$('~Sauce Labs Backpack - Black')).waitForDisplayed({ timeout: 10000 })
}

async function main() {
  const platform = required('QA_PLATFORM').toLowerCase()
  const target = required('QA_TARGET_ID')
  const artifactDir = path.resolve(process.env.QA_ARTIFACT_DIR || `artifacts/${platform}-product-to-cart`)
  await fs.mkdir(artifactDir, { recursive: true })
  const startedAt = new Date().toISOString()
  let driver
  try {
    driver = await remote({
      hostname: process.env.APPIUM_HOST || '127.0.0.1',
      port: Number(process.env.APPIUM_PORT || 4723),
      path: process.env.APPIUM_BASE_PATH || '/',
      logLevel: process.env.WDIO_LOG_LEVEL || 'info',
      connectionRetryTimeout: Number(process.env.QA_WEBDRIVER_TIMEOUT || 120000),
      connectionRetryCount: Number(process.env.QA_WEBDRIVER_RETRIES || 2),
      transformRequest: normalizeWebdriverRequest,
      capabilities: capabilities(platform, target),
    })
    if (platform === 'android') await androidProductToCart(driver)
    else await iosProductToCart(driver)
    await maybeScreenshot(driver, artifactDir, 'TC-MOBILE-CART-001-passed')
    await fs.writeFile(path.join(artifactDir, 'result.json'), JSON.stringify({ caseId: 'TC-MOBILE-CART-001', ok: true, platform, target, startedAt, endedAt: new Date().toISOString() }, null, 2))
  } catch (error) {
    if (driver) {
      await fs.writeFile(path.join(artifactDir, 'failure-page-source.xml'), await driver.getPageSource().catch(() => ''))
      await maybeScreenshot(driver, artifactDir, 'TC-MOBILE-CART-001-failed').catch(() => {})
    }
    await fs.writeFile(path.join(artifactDir, 'result.json'), JSON.stringify({ caseId: 'TC-MOBILE-CART-001', ok: false, platform, target, startedAt, endedAt: new Date().toISOString(), error: String(error.stack || error) }, null, 2))
    throw error
  } finally {
    if (driver) await driver.deleteSession()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})

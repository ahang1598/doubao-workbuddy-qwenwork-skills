const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

function commandResult(command, args, options = {}) {
  const result = spawnSync(command, args, {
    encoding: 'utf8',
    timeout: options.timeout || 20000,
    env: process.env,
    shell: process.platform === 'win32',
  })
  return {
    ok: result.status === 0,
    status: result.status,
    stdout: String(result.stdout || '').trim(),
    stderr: String(result.stderr || '').trim(),
    error: result.error ? String(result.error.message || result.error) : null,
  }
}

function failureText(result) {
  const value = result.stderr || result.error || result.stdout || '命令失败'
  return value.split(/\r?\n/).slice(0, 4).join('\n').slice(0, 1200)
}

function appiumBinary() {
  const candidates = [
    process.env.QA_APPIUM_BIN,
    path.join(__dirname, 'node_modules', '.bin', process.platform === 'win32' ? 'appium.cmd' : 'appium'),
    'appium',
  ].filter(Boolean)
  for (const candidate of candidates) {
    if (candidate === 'appium' || fs.existsSync(candidate)) {
      const result = commandResult(candidate, ['--version'])
      if (result.ok) return { path: candidate, version: result.stdout || result.stderr }
    }
  }
  return null
}

function installedDrivers(binary) {
  if (!binary) return { ok: false, names: [], error: '未找到 Appium core' }
  const result = commandResult(binary.path, ['driver', 'list', '--installed', '--json'])
  if (!result.ok) return { ok: false, names: [], error: failureText(result) }
  try {
    const payload = JSON.parse(result.stdout)
    const names = Array.isArray(payload) ? payload : Object.keys(payload)
    return { ok: true, names: names.map(String).sort() }
  } catch (error) {
    return { ok: false, names: [], error: `driver JSON 解析失败：${error.message}`, raw: result.stdout }
  }
}

function iosTarget(target) {
  const result = commandResult('xcrun', ['simctl', 'list', 'devices', '--json'])
  if (!result.ok) return { ok: false, error: failureText(result) }
  try {
    const payload = JSON.parse(result.stdout)
    for (const [runtime, devices] of Object.entries(payload.devices || {})) {
      for (const device of devices) {
        if (device.udid === target) {
          return {
            ok: device.isAvailable !== false,
            name: device.name,
            state: device.state,
            runtime,
            available: device.isAvailable !== false,
          }
        }
      }
    }
    return { ok: false, error: `未找到 iOS Simulator：${target}` }
  } catch (error) {
    return { ok: false, error: `simctl JSON 解析失败：${error.message}` }
  }
}

function androidTarget(target) {
  const result = commandResult('adb', ['devices', '-l'])
  if (!result.ok) return { ok: false, error: failureText(result) }
  const line = result.stdout.split(/\r?\n/).find((item) => item.trim().startsWith(`${target}\t`))
  if (!line) return { ok: false, error: `adb 未找到目标：${target}` }
  const state = line.trim().split(/\s+/)[1]
  return { ok: state === 'device', state, line }
}

function main() {
  const platform = String(process.env.QA_PLATFORM || '').toLowerCase()
  const target = process.env.QA_TARGET_ID || ''
  const appPath = process.env.QA_APP_PATH ? path.resolve(process.env.QA_APP_PATH) : null
  const appId = process.env.QA_APP_ID || null
  const appium = appiumBinary()
  const drivers = installedDrivers(appium)
  const blockers = []

  if (!['ios', 'android'].includes(platform)) blockers.push('QA_PLATFORM 必须是 ios 或 android')
  if (!target) blockers.push('缺少 QA_TARGET_ID')
  if (!appPath && !appId) blockers.push('至少提供 QA_APP_PATH 或 QA_APP_ID')
  if (appPath && !fs.existsSync(appPath)) blockers.push(`QA_APP_PATH 不存在：${appPath}`)
  if (!appium) blockers.push('未找到 Appium core；先在 mobile-starter 执行 npm install')

  let targetInfo = null
  if (target && platform === 'ios') {
    targetInfo = iosTarget(target)
    if (!targetInfo.ok) blockers.push(`iOS 目标不可用：${targetInfo.error || targetInfo.state}`)
    if (!drivers.names.some((name) => name.toLowerCase().includes('xcuitest'))) {
      blockers.push('Appium 未安装 xcuitest driver')
    }
  } else if (target && platform === 'android') {
    targetInfo = androidTarget(target)
    if (!targetInfo.ok) blockers.push(`Android 目标不可用：${targetInfo.error || targetInfo.state}`)
    if (!drivers.names.some((name) => name.toLowerCase().includes('uiautomator2'))) {
      blockers.push('Appium 未安装 uiautomator2 driver')
    }
  }

  const report = {
    schemaVersion: 1,
    ready: blockers.length === 0,
    platform,
    target,
    appPath,
    appId,
    appium,
    drivers,
    targetInfo,
    appiumHome: process.env.APPIUM_HOME || null,
    blockers,
  }
  const output = JSON.stringify(report, null, 2)
  if (process.env.QA_PREFLIGHT_OUT) {
    const outputPath = path.resolve(process.env.QA_PREFLIGHT_OUT)
    fs.mkdirSync(path.dirname(outputPath), { recursive: true })
    fs.writeFileSync(outputPath, output)
  }
  process.stdout.write(`${output}\n`)
  process.exitCode = report.ready ? 0 : 2
}

main()

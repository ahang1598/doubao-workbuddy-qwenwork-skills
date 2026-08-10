const fs = require('node:fs/promises')
const path = require('node:path')
const assert = require('node:assert/strict')
const automator = require('miniprogram-automator')

function required(name) {
  const value = process.env[name]
  if (!value) throw new Error(`缺少环境变量 ${name}`)
  return value
}

async function openMiniProgram() {
  if (process.env.MINIPROGRAM_WS_ENDPOINT) {
    return {
      connectionMode: 'connect',
      miniProgram: await automator.connect({ wsEndpoint: process.env.MINIPROGRAM_WS_ENDPOINT }),
    }
  }
  const cliPath = required('WECHAT_CLI_PATH')
  const projectPath = path.resolve(required('MINIPROGRAM_PROJECT_PATH'))
  return {
    connectionMode: 'launch',
    miniProgram: await automator.launch({ cliPath, projectPath }),
  }
}

async function main() {
  const pagePath = required('MINIPROGRAM_PAGE')
  const artifactDir = path.resolve(process.env.QA_ARTIFACT_DIR || 'artifacts/miniprogram-smoke')
  await fs.mkdir(artifactDir, { recursive: true })

  let miniProgram
  let connectionMode
  const startedAt = new Date().toISOString()
  try {
    const connection = await openMiniProgram()
    miniProgram = connection.miniProgram
    connectionMode = connection.connectionMode
    const page = await miniProgram.reLaunch(pagePath)
    assert.ok(page, `无法打开页面 ${pagePath}`)
    const current = await miniProgram.currentPage()
    assert.ok(current, '无法读取当前页面')
    if (process.env.QA_CAPTURE_SCREENSHOTS === '1') {
      await miniProgram.screenshot({ path: path.join(artifactDir, 'launch.png') })
    }
    await fs.writeFile(
      path.join(artifactDir, 'result.json'),
      JSON.stringify({ ok: true, connectionMode, pagePath, startedAt, endedAt: new Date().toISOString() }, null, 2),
    )
  } catch (error) {
    await fs.writeFile(
      path.join(artifactDir, 'result.json'),
      JSON.stringify(
        { ok: false, connectionMode, pagePath, startedAt, endedAt: new Date().toISOString(), error: String(error.stack || error) },
        null,
        2,
      ),
    )
    throw error
  } finally {
    if (miniProgram) await miniProgram.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})

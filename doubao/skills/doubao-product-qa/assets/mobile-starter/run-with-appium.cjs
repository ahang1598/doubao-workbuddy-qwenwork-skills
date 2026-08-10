const fs = require('node:fs')
const path = require('node:path')
const { spawn, spawnSync } = require('node:child_process')

function appiumBinary() {
  const candidates = [
    process.env.QA_APPIUM_BIN,
    path.join(__dirname, 'node_modules', '.bin', process.platform === 'win32' ? 'appium.cmd' : 'appium'),
    'appium',
  ].filter(Boolean)
  for (const candidate of candidates) {
    if (candidate === 'appium' || fs.existsSync(candidate)) {
      const probe = spawnSync(candidate, ['--version'], {
        encoding: 'utf8',
        env: process.env,
        shell: process.platform === 'win32',
      })
      if (probe.status === 0) return candidate
    }
  }
  throw new Error('未找到 Appium core；先执行 npm install，或设置 QA_APPIUM_BIN')
}

function statusUrl(host, port, basePath) {
  const prefix = basePath === '/' ? '' : `/${basePath.replace(/^\/+|\/+$/g, '')}`
  return `http://${host}:${port}${prefix}/status`
}

async function serverReady(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(1500) })
    if (!response.ok) return false
    const payload = await response.json()
    return payload.value?.ready !== false
  } catch {
    return false
  }
}

async function waitForServer(url, child, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (child && child.exitCode !== null) throw new Error(`Appium server 提前退出：${child.exitCode}`)
    if (await serverReady(url)) return
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`Appium server 在 ${timeoutMs}ms 内未就绪：${url}`)
}

function runTest(scriptPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [scriptPath], {
      cwd: __dirname,
      env: process.env,
      stdio: 'inherit',
    })
    child.once('error', reject)
    child.once('exit', (code, signal) => resolve({ code, signal }))
  })
}

async function stopServer(child) {
  if (!child || child.exitCode !== null) return
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    })
    return
  }
  child.kill('SIGINT')
  const exited = await Promise.race([
    new Promise((resolve) => child.once('exit', () => resolve(true))),
    new Promise((resolve) => setTimeout(() => resolve(false), 4000)),
  ])
  if (!exited && child.exitCode === null) child.kill('SIGKILL')
}

async function main() {
  const scriptArg = process.argv[2]
  if (!scriptArg) throw new Error('用法：node run-with-appium.cjs <test-script.cjs>')
  const scriptPath = path.resolve(__dirname, scriptArg)
  if (!fs.existsSync(scriptPath)) throw new Error(`测试脚本不存在：${scriptPath}`)

  const artifactDir = path.resolve(process.env.QA_ARTIFACT_DIR || 'artifacts/appium-run')
  fs.mkdirSync(artifactDir, { recursive: true })
  const host = process.env.APPIUM_HOST || '127.0.0.1'
  const port = Number(process.env.APPIUM_PORT || 4723)
  const basePath = process.env.APPIUM_BASE_PATH || '/'
  const url = statusUrl(host, port, basePath)
  let server = null
  let logStream = null
  const reused = await serverReady(url)

  try {
    if (!reused) {
      const binary = appiumBinary()
      logStream = fs.createWriteStream(path.join(artifactDir, 'appium-server.log'), { flags: 'w' })
      server = spawn(binary, [
        '--address', host,
        '--port', String(port),
        '--base-path', basePath,
        '--log-no-colors',
      ], {
        cwd: __dirname,
        env: process.env,
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: process.platform === 'win32',
        windowsHide: true,
      })
      server.stdout.pipe(logStream)
      server.stderr.pipe(logStream)
      await waitForServer(url, server, Number(process.env.QA_APPIUM_START_TIMEOUT || 60000))
    }

    fs.writeFileSync(
      path.join(artifactDir, 'server-session.json'),
      JSON.stringify({ url, reused, startedByRunner: !reused, startedAt: new Date().toISOString() }, null, 2),
    )
    const result = await runTest(scriptPath)
    process.exitCode = result.code === 0 ? 0 : (result.code || 1)
  } finally {
    await stopServer(server)
    if (logStream) logStream.end()
  }
}

main().catch((error) => {
  console.error(error.stack || error)
  process.exitCode = 1
})

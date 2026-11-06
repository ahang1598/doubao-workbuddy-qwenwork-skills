#!/usr/bin/env node
/**
 * dock-cli —— 工作台插件 agent 通道命令行客户端（方案 dock-plugin-framework §6.4 / 协议 §7）。
 *
 * 约定（协议 §7.4）：
 *  - 输出 JSON（--query 点路径过滤）；错误统一 {ok:false,error:{code,message,hint}}；
 *  - 会话头自动携带：CLAW_CONVERSATION_ID 环境变量（jiuwenswarm shell 链注入），
 *    缺失时可用 --conversation 显式提供；两者都缺 → 拒绝发送（代理会 fail-closed）；
 *  - 全局命令：help [surface]（命令目录）、state（本会话页签概览）；
 *  - surface 命令：dock-cli <surface> <command> [--tab-id X] [--ref R] [--k v ...]；
 *  - 退出码：0 成功；1 业务失败（模型可恢复）；2 用法/传输错误（勿重试）。
 */
import http from 'node:http'

// 管道名经字符构造，避免任何中间层的转义歧义（\\\\.\\pipe\\claw-dock）
const PIPE_PATH = `\\\\.\\pipe\\claw-dock`

function emit(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`)
}

function fail(code, message, hint, exitCode = 1) {
  emit({ ok: false, error: hint ? { code, message, hint } : { code, message } })
  process.exit(exitCode)
}

function parseArgs(argv) {
  const positional = []
  const flags = {}
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg.startsWith('--')) {
      const eq = arg.indexOf('=')
      if (eq > 0) {
        flags[arg.slice(2, eq)] = arg.slice(eq + 1)
      } else {
        const next = argv[i + 1]
        if (next !== undefined && !next.startsWith('--')) {
          flags[arg.slice(2)] = next
          i += 1
        } else {
          flags[arg.slice(2)] = true
        }
      }
    } else {
      positional.push(arg)
    }
  }
  return { positional, flags }
}

function request(path, body, { token, conversation }) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body ?? {})
    const req = http.request(
      {
        socketPath: PIPE_PATH,
        path,
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'x-claw-conversation': conversation,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }
      },
      (res) => {
        const chunks = []
        res.on('data', (c) => chunks.push(c))
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8')
          let parsed
          try {
            parsed = JSON.parse(text)
          } catch {
            reject(new Error(`响应不是合法 JSON（HTTP ${res.statusCode}）`))
            return
          }
          resolve({ status: res.statusCode ?? 0, body: parsed })
        })
      }
    )
    req.on('error', reject)
    req.setTimeout(45000, () => {
      req.destroy(new Error('请求超时（45s）'))
    })
    req.end(payload)
  })
}

/** --query 点路径过滤：'tabs.0.tabId' / 'catalog' */
function pickQuery(value, query) {
  if (!query) return value
  let current = value
  for (const segment of query.split('.')) {
    if (current === null || current === undefined) return null
    current = current[segment]
  }
  return current ?? null
}

async function main() {
  const { positional, flags } = parseArgs(process.argv.slice(2))
  const token = process.env.CLAW_SKILL_TOKEN ?? ''
  const conversation = typeof flags.conversation === 'string' ? flags.conversation : (process.env.CLAW_CONVERSATION_ID ?? '')
  const query = typeof flags.query === 'string' ? flags.query : undefined

  if (positional[0] === 'help' || (positional.length === 1 && positional[0] === 'state')) {
    // 无参帮助也允许：本地打印用法（不打管道）
    if (!positional[0]) {
      emit({
        ok: true,
        usage: 'dock-cli <surface> <command> [flags] | dock-cli help [surface] | dock-cli state [--query q]'
      })
      process.exit(0)
    }
  }

  if (!token) fail('DOCK_PROXY_UNAVAILABLE', '缺少 CLAW_SKILL_TOKEN 环境变量', '由小艺Work 注入，勿手工伪造', 2)
  if (!conversation) fail('DOCK_PROXY_UNAVAILABLE', '缺少 CLAW_CONVERSATION_ID 环境变量（也未提供 --conversation）', '由执行链注入', 2)

  if (positional[0] === 'help') {
    const surface = typeof positional[1] === 'string' ? positional[1] : typeof flags.surface === 'string' ? flags.surface : undefined
    const { status, body } = await request('/dock/help', { ...(surface ? { surface } : {}) }, { token, conversation }).catch(
      (error) => fail('DOCK_PROXY_UNAVAILABLE', String(error.message ?? error), '确认小艺Work 正在运行', 2)
    )
    if (status !== 200 || !body?.ok) fail(body?.error?.code ?? 'DOCK_PROXY_UNAVAILABLE', body?.error?.message ?? `HTTP ${status}`, body?.error?.hint)
    const entries = surface ? (body.catalog ?? []).filter((e) => e.surface === surface) : body.catalog ?? []
    emit({ ok: true, revision: body.revision, catalog: entries, ...(query ? { query: pickQuery(body, query) } : {}) })
    process.exit(0)
  }

  if (positional[0] === 'state') {
    const { status, body } = await request('/dock/state', {}, { token, conversation }).catch((error) =>
      fail('DOCK_PROXY_UNAVAILABLE', String(error.message ?? error), '确认小艺Work 正在运行', 2)
    )
    if (status !== 200 || !body?.ok) fail(body?.error?.code ?? 'DOCK_PROXY_UNAVAILABLE', body?.error?.message ?? `HTTP ${status}`, body?.error?.hint)
    const filtered = query ? pickQuery(body, query) : body.tabs ?? []
    emit({ ok: true, tabs: body.tabs ?? [], ...(query ? { query: filtered } : {}) })
    process.exit(0)
  }

  const [surface, command] = positional
  if (!surface || !command) {
    emit({
      ok: false,
      error: { code: 'DOCK_PROXY_UNAVAILABLE', message: '用法：dock-cli <surface> <command> [flags]；dock-cli help 查看命令目录' }
    })
    process.exit(2)
  }
  const reserved = new Set(['conversation', 'query'])
  const args = {}
  for (const [key, value] of Object.entries(flags)) {
    if (reserved.has(key) || value === true) continue
    args[key] = value
  }
  const tabId = typeof flags['tab-id'] === 'string' ? flags['tab-id'] : undefined

  const { status, body } = await request(
    '/dock/execute',
    { surface, command, args, ...(tabId ? { tabId } : {}) },
    { token, conversation }
  ).catch((error) => fail('DOCK_PROXY_UNAVAILABLE', String(error.message ?? error), '确认小艺Work 正在运行', 2))

  if (status !== 200 || !body?.ok) {
    fail(body?.error?.code ?? 'DOCK_PROXY_UNAVAILABLE', body?.error?.message ?? `HTTP ${status}`, body?.error?.hint)
  }
  const result = query ? pickQuery(body.result ?? body, query) : body.result ?? {}
  emit({ ok: true, result })
  process.exit(0)
}

main().catch((error) => {
  fail('DOCK_PROXY_UNAVAILABLE', String(error?.message ?? error), undefined, 2)
})

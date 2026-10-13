// universal-workbench 通用骨架 —— 零 npm 依赖（Node 22 内置模块）
// 数据层：Supabase REST（QW Pages 运行时注入 SUPABASE_URL / SUPABASE_ANON_KEY）
// 定制点：只改 CONFIG 区（TABLES / VIEW_API_PREFIX / DEFAULT_MEMBER_VIEWS / GRANTABLE_VIEWS / APP_NAME）
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/* ============ CONFIG（唯一需要改的区域） ============ */
const APP_NAME = '通用工作台';

// 业务表白名单：name=表名 view=所属视图(权限门卫用) columns=读写白名单 order=列表排序
const TABLES = [
  { name: 'clients', view: 'clients', columns: ['id', 'name', 'owner', 'stage', 'amount', 'created_at'], order: 'created_at.desc' },
  { name: 'followups', view: 'clients', columns: ['id', 'client_id', 'note', 'owner', 'created_at'], order: 'created_at.desc' },
  // ↑ 示例：改成你的业务实体。列类型只用 text/number/bool/date
];

// 视图 → API 前缀映射（权限门卫核心）
const VIEW_API_PREFIX = {
  clients: ['/api/clients', '/api/followups'],
  stats: ['/api/stats'],
};
const ADMIN_ONLY_PATHS = ['/api/users', '/api/admin'];
// member 默认可见视图 / 管理员可额外授权的视图
const DEFAULT_MEMBER_VIEWS = ['clients'];
const GRANTABLE_VIEWS = ['stats'];
const ALL_VIEWS = Object.keys(VIEW_API_PREFIX);

/* ============ 以下勿动 ============ */
const PORT = Number(process.env.PORT || 8081);
const HOST = process.env.HOST || '0.0.0.0';
const SB_URL = (process.env.SUPABASE_URL || '').replace(/\/+$/, '');
const SB_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-in-prod';
const COOKIE = 'wb_session', TTL = 7 * 24 * 3600e3;

// —— scrypt 密码 ——
const hashPw = pw => { const s = crypto.randomBytes(16).toString('hex'); return s + ':' + crypto.scryptSync(pw, s, 64).toString('hex'); };
const verifyPw = (pw, stored) => {
  if (!stored || !stored.includes(':')) return false;
  const [s, h] = stored.split(':'); const t = crypto.scryptSync(pw, s, 64).toString('hex');
  const a = Buffer.from(h, 'hex'), b = Buffer.from(t, 'hex');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
};
// —— HMAC 签名 cookie session（重启不失效） ——
const b64u = buf => Buffer.from(buf).toString('base64').replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
const b64ud = s => { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; return Buffer.from(s, 'base64').toString('utf8'); };
const sign = p => { const b = b64u(JSON.stringify(p)); return b + '.' + b64u(crypto.createHmac('sha256', SESSION_SECRET).update(b).digest()); };
const verify = t => {
  if (!t || !t.includes('.')) return null;
  const [b, s] = t.split('.');
  if (b64u(crypto.createHmac('sha256', SESSION_SECRET).update(b).digest()) !== s) return null;
  try { const o = JSON.parse(b64ud(b)); return o.exp > Date.now() ? o : null; } catch { return null; }
};

// —— Supabase REST ——
async function sb(method, table, opts = {}) {
  const headers = { apikey: SB_KEY, Authorization: 'Bearer ' + SB_KEY, Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  if (opts.prefer) headers.Prefer = opts.prefer;
  let qs = '';
  if (opts.select || opts.filters || opts.order || opts.limit) {
    const p = new URLSearchParams();
    if (opts.select) p.set('select', opts.select);
    (opts.filters || []).forEach(f => p.append(f[0], f[1]));
    if (opts.order) p.set('order', opts.order);
    if (opts.limit) p.set('limit', String(opts.limit));
    qs = '?' + p.toString();
  }
  const res = await fetch(SB_URL + '/rest/v1/' + table + qs, {
    method, headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined
  });
  if (res.status === 204) return [];
  const data = (res.headers.get('content-type') || '').includes('json') ? await res.json() : await res.text();
  if (!res.ok) throw Object.assign(new Error((data && data.message) || 'supabase ' + res.status), { status: res.status });
  return data;
}

// —— 权限门卫 ——
function apiToView(p) {
  for (const [v, prefixes] of Object.entries(VIEW_API_PREFIX))
    if (prefixes.some(pre => p === pre || p.startsWith(pre + '/'))) return v;
  return null;
}
const canView = (u, v) => u && (u.role === 'admin' || DEFAULT_MEMBER_VIEWS.includes(v) || (u.permissions || []).includes(v));

// —— HTTP 工具 ——
const json = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(obj)); };
const ok = (res, data) => json(res, 200, { ok: true, data });
const bad = (res, code, msg) => json(res, code, { ok: false, error: msg });
function readBody(req) {
  return new Promise(r => { let b = ''; req.on('data', c => b += c); req.on('end', () => { try { r(b ? JSON.parse(b) : {}); } catch { r({}); } }); });
}
const parsePerms = raw => { try { const v = JSON.parse(raw || '[]'); return Array.isArray(v) ? v : []; } catch { return []; } };

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const p = u.pathname;
  // session 解析
  const cookies = {}; (req.headers.cookie || '').split(/;\s*/).forEach(kv => { const i = kv.indexOf('='); if (i > 0) cookies[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
  const sess = verify(cookies[COOKIE]);
  const me = sess ? { id: sess.uid, username: sess.username, name: sess.name, role: sess.role, permissions: sess.permissions || [] } : null;
  const setCookie = payload => res.setHeader('Set-Cookie', `${COOKIE}=${encodeURIComponent(sign({ ...payload, exp: Date.now() + TTL }))}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${TTL / 1000}`);

  try {
    // ---- 静态 ----
    if (req.method === 'GET' && !p.startsWith('/api/') && !p.startsWith('/auth/')) {
      const file = p === '/' ? 'index.html' : p.replace(/^\//, '');
      const fp = path.join(__dirname, 'public', file);
      if (fp.startsWith(path.join(__dirname, 'public')) && fs.existsSync(fp) && fs.statSync(fp).isFile()) {
        const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' }[path.extname(fp)] || 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': mime }); res.end(fs.readFileSync(fp)); return;
      }
      if (p === '/' || !path.extname(p)) { res.writeHead(302, { Location: '/login' }); res.end(); return; }
      res.writeHead(404); res.end(); return;
    }

    // ---- 认证 ----
    if (p === '/auth/login' && req.method === 'POST') {
      const { username, password } = await readBody(req);
      if (!username || !password) return bad(res, 400, '账号和密码必填');
      const rows = await sb('GET', 'users', { select: '*', filters: [['username', 'eq.' + String(username).trim()]] });
      const u = rows[0];
      if (!u || !verifyPw(String(password), u.password_hash || '')) return bad(res, 401, '账号或密码错误');
      if (u.status !== 'approved') return bad(res, 403, u.status === 'pending' ? '账号待管理员审核' : '账号已被禁用');
      setCookie({ uid: u.id, username: u.username, name: u.nick || u.username, role: u.role, permissions: parsePerms(u.permissions) });
      return ok(res, { id: u.id, username: u.username, role: u.role });
    }
    if (p === '/auth/register' && req.method === 'POST') {
      const { username, password, nick } = await readBody(req);
      if (!username || !password || String(username).length < 2 || String(password).length < 6) return bad(res, 400, '账号≥2位，密码≥6位');
      const ex = await sb('GET', 'users', { select: 'id', filters: [['username', 'eq.' + String(username).trim()]] });
      if (ex[0]) return bad(res, 409, '账号已存在');
      await sb('POST', 'users', { body: { username: String(username).trim(), password_hash: hashPw(String(password)), nick: (nick || username).trim(), role: 'member', status: 'approved', permissions: '[]' } });
      return ok(res, { message: '注册成功，请登录' });
    }
    if (p === '/auth/logout' && req.method === 'POST') { res.setHeader('Set-Cookie', COOKIE + '=; Path=/; Max-Age=0'); return ok(res, true); }

    // ---- /api 全区门卫 ----
    if (p.startsWith('/api/')) {
      if (!me) return bad(res, 401, 'unauthorized');
      const isAdmin = me.role === 'admin';
      if (ADMIN_ONLY_PATHS.some(ap => p === ap || p.startsWith(ap + '/')) && !isAdmin) return bad(res, 403, 'admin only');
      const view = apiToView(p);
      if (view && !canView(me, view)) return bad(res, 403, '无权访问，需管理员授权');

      if (p === '/api/me') return ok(res, { user: me, allowed_views: isAdmin ? ALL_VIEWS.concat(['users']) : [...new Set([...DEFAULT_MEMBER_VIEWS, ...me.permissions])] });

      // ---- 用户管理（admin） ----
      if (p === '/api/users' && req.method === 'GET') {
        const rows = await sb('GET', 'users', { select: 'id,username,nick,role,status,permissions,last_login_at,created_at', order: 'created_at.desc' });
        return ok(res, rows.map(r => ({ ...r, permissions: parsePerms(r.permissions) })));
      }
      let m = /^\/api\/users\/(\d+)$/.exec(p);
      if (m) {
        const id = m[1], body = await readBody(req);
        const patch = {};
        if ('status' in body && ['pending', 'approved', 'disabled'].includes(body.status)) patch.status = body.status;
        if ('role' in body && ['admin', 'member'].includes(body.role)) patch.role = body.role;
        if ('permissions' in body && Array.isArray(body.permissions)) patch.permissions = JSON.stringify(body.permissions.filter(v => GRANTABLE_VIEWS.includes(v)));
        if ('nick' in body) patch.nick = String(body.nick || '').trim();
        if ('password' in body && body.password) patch.password_hash = hashPw(String(body.password));
        if (!Object.keys(patch).length) return bad(res, 400, 'nothing to update');
        if (req.method === 'PATCH') { await sb('PATCH', 'users?id=eq.' + id, { body: patch, prefer: 'return=minimal' }); return ok(res, true); }
        if (req.method === 'DELETE') { if (String(me.id) === id) return bad(res, 400, '不能删除自己'); await sb('DELETE', 'users?id=eq.' + id, { prefer: 'return=minimal' }); return ok(res, true); }
      }

      // ---- 管理后台：泛型数据浏览器 ----
      if (p === '/api/admin/tables' && req.method === 'GET') {
        const out = [];
        for (const t of TABLES) {
          const rows = await sb('GET', t.name, { select: '*', order: t.order, limit: 50 });
          out.push({ table: t.name, columns: t.columns, rows });
        }
        return ok(res, out);
      }

      // ---- 泛型业务 CRUD（按 TABLES 白名单自动路由） ----
      for (const t of TABLES) {
        if (p === '/api/' + t.name || p.startsWith('/api/' + t.name + '/')) {
          const cols = t.columns.filter(c => c !== 'id' && c !== 'created_at');
          if (p === '/api/' + t.name && req.method === 'GET') return ok(res, await sb('GET', t.name, { select: '*', order: t.order, limit: 200 }));
          if (p === '/api/' + t.name && req.method === 'POST') {
            const b = await readBody(req);
            const row = {}; cols.forEach(c => { if (c in b) row[c] = b[c]; });
            if (!Object.keys(row).length) return bad(res, 400, 'no valid fields');
            const rows = await sb('POST', t.name, { body: row, prefer: 'return=representation' });
            return ok(res, { id: rows[0] && rows[0].id });
          }
          const m2 = /^\/api\/\w+\/(\d+)$/.exec(p);
          if (m2) {
            if (req.method === 'PATCH') {
              const b = await readBody(req); const patch = {}; cols.forEach(c => { if (c in b) patch[c] = b[c]; });
              if (!Object.keys(patch).length) return bad(res, 400, 'nothing to update');
              await sb('PATCH', t.name + '?id=eq.' + m2[1], { body: patch, prefer: 'return=minimal' }); return ok(res, true);
            }
            if (req.method === 'DELETE') { await sb('DELETE', t.name + '?id=eq.' + m2[1], { prefer: 'return=minimal' }); return ok(res, true); }
          }
        }
      }
      return bad(res, 404, 'not found');
    }
    return bad(res, 404, 'not found');
  } catch (e) {
    console.error('[err]', p, e.message);
    return bad(res, e.status && e.status >= 400 ? e.status : 500, e.message || 'server error');
  }
});

server.listen(PORT, HOST, () => console.log(APP_NAME + ' listening on ' + HOST + ':' + PORT));

# 高德问店网关接入与认证规范（套件共享）

本文件被套件内全部技能共享引用。技能内引用路径：`./references/gateway-auth.md`

---

## 请求地址

`${YT_GATEWAY_BASE_URL}/proxy/yt-xd-lite/openapi/v1/gateway`

- `YT_GATEWAY_BASE_URL` 优先取环境变量，未设置时使用缺省值 `https://yt-gateway.amap.com`
- 所有能力均为 POST 调用，请求体形如 `{"action": "xxx", "params": {...}}`

---

## 认证方式：OAuth

本套件运行在 wukong 客户端环境，**固定使用 OAuth 认证路径**。

### 认证 Header

| Header | 值来源 | 说明 |
|--------|--------|------|
| `X-Session-Token` | YTOSS 文件中 `sessions.wukong.session_token` | 必传 |
| `X-Skill-Id` | `amap-store-location-assistant` | 必传，套件内四个技能统一使用该值 |

**禁止传** `X-Access-Key` / `X-Tenant-Id` / `X-User-Id`（这些由网关侧反查注入，技能层不需要持有）。

> **X-Skill-Id 说明**：该值是网关侧已登记的标识，套件拆分为四个技能后仍统一沿用，不要改成各技能自己的目录名，否则会导致鉴权与配额校验失败。

### 请求格式

```bash
curl -k "${YT_GATEWAY_BASE_URL:-https://yt-gateway.amap.com}/proxy/yt-xd-lite/openapi/v1/gateway" \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: ${SESSION_TOKEN}" \
  -H "X-Skill-Id: amap-store-location-assistant" \
  -d '{"action": "xxx", "params": {...}}'
```

> **注意**：curl 必须带 `-k` 跳过 TLS 证书校验。

---

## Session Token 获取流程

**每次发起网关请求前，必须先执行以下步骤：**

1. **先读取 YTOSS 文件**：按优先级依次尝试读取（哪个先找到就用哪个）：
   - 优先（macOS/Linux）：`~/.config/yt/oss.json`
   - 优先（Windows）：`%APPDATA%\yt\oss.json`
   - 降级（全平台）：当前工作目录下的 `.yt/oss.json`（沙箱环境备选路径）
2. **检查是否有有效 token**：解析 JSON，查看 `sessions.wukong.session_token` 字段是否存在且以 `gwst_` 开头
3. **判定走向**：
   - ✅ 有有效 token → 直接使用该 token 作为 `X-Session-Token` 发起请求
   - ❌ 文件不存在 / 无 wukong 条目 / token 不以 `gwst_` 开头 → 执行下方 OAuth 登录脚本获取新 token

```
读取 YTOSS 文件（按优先级）：
  macOS/Linux: ~/.config/yt/oss.json
  Windows:     %APPDATA%\yt\oss.json
  降级(全平台): ./.yt/oss.json
  ├─ 文件存在且 sessions.wukong.session_token 以 gwst_ 开头 → 直接使用
  └─ 文件不存在 / 无有效 token → 执行 OAuth 登录脚本 → 落盘后使用
```

> **重要**：禁止跳过文件读取直接执行 OAuth 登录，已有有效 token 时重复登录会浪费用户操作。

---

## YTOSS 文件规范

**路径（按优先级，写入时也按此顺序尝试）**：

| 优先级 | 路径 | 平台 | 适用场景 |
|--------|------|------|---------|
| 1（首选） | `~/.config/yt/oss.json` | macOS / Linux | 标准环境，无沙箱限制 |
| 1（首选） | `%APPDATA%\yt\oss.json` | Windows | 标准环境（`%APPDATA%` 通常为 `C:\Users\xxx\AppData\Roaming`） |
| 2（降级） | `${WORKSPACE}/.yt/oss.json` | 全平台 | 沙箱环境，无法写入上述首选路径时使用工作目录 |

> **跨平台路径判断**：使用 Python 时可通过 `os.path.expanduser('~')` 或 `os.environ.get('APPDATA')` 获取正确路径，不要硬编码。

**写入降级逻辑**：
```
判断操作系统 → 确定首选路径（macOS/Linux: ~/.config/yt/  Windows: %APPDATA%\yt\）
尝试写入首选路径
  ├─ 成功 → 完成
  └─ 失败（权限不足/沙箱限制）→ 写入 ${WORKSPACE}/.yt/oss.json
```

> **注意**：如果环境存在沙箱权限限制（如无法在 `~/.config` 下创建文件），必须降级到工作目录，**禁止因写入失败而中止整个流程**。

**权限**：`chmod 600`（在支持的环境下），禁止存放在 iCloud/OneDrive/Dropbox 等同步目录

**格式**：
```json
{
  "sessions": {
    "wukong": {
      "session_token": "gwst_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "created_at": "2026-06-04T10:30:00+08:00"
    }
  }
}
```

读取时若发现顶层直接有 `session_token` 的旧格式，自动迁移为上述新格式后使用。

**禁止存放**：`access_token` / `refresh_token` / `mobile` / `expires_in`（仅网关侧持有）

---

## OAuth 登录脚本（无有效 token 时执行）

> **跨平台说明**：
> - 此脚本基于 bash，Windows 环境需通过 Git Bash / WSL 运行，或由 wukong 运行时自动适配为等价 PowerShell/cmd 命令
> - Windows 上 `python3` 可能需替换为 `python`（取决于安装方式）
> - Windows 路径分隔符为 `\`，但在 bash/Python 中使用 `/` 同样有效

```bash
#!/bin/bash
set -euo pipefail

APP_ID="wukong"
GW_HOST="${YT_GATEWAY_BASE_URL:-https://yt-gateway.amap.com}"
# 跨平台路径：macOS/Linux 用 ~/.config/yt/，Windows 用 $APPDATA/yt/
if [ -n "${APPDATA:-}" ]; then
  YTOSS_PATH="$APPDATA/yt/oss.json"
else
  YTOSS_PATH="${HOME}/.config/yt/oss.json"
fi
YTOSS_FALLBACK_PATH="${PWD}/.yt/oss.json"
TIMEOUT=120
PORT=$((RANDOM % 55000 + 10000))

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

# 1. 启动一次性本地 HTTP 监听（one-shot，收到 callback 后立即退出）
python3 -c "
import http.server, urllib.parse, json

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(qs))
        with open('${TMPFILE}', 'w') as f:
            json.dump(params, f)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'<html><body><h2>Login successful!</h2><p>You can close this tab.</p></body></html>')
    def log_message(self, *_): pass

s = http.server.HTTPServer(('127.0.0.1', ${PORT}), H)
s.timeout = ${TIMEOUT}
s.handle_request()
" &
SERVER_PID=$!

# 2. 构造登录 URL 并拉起浏览器
RETURN_URL="http://127.0.0.1:${PORT}/cb"
ENCODED_RETURN=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${RETURN_URL}'))")
LOGIN_URL="${GW_HOST}/auth/oauth/login?return=${ENCODED_RETURN}&app_id=${APP_ID}"

if command -v open &>/dev/null; then
  open "${LOGIN_URL}"
elif command -v xdg-open &>/dev/null; then
  xdg-open "${LOGIN_URL}"
elif command -v start &>/dev/null; then
  start "${LOGIN_URL}"
elif [ -n "${APPDATA:-}" ]; then
  # Windows 环境 fallback
  rundll32 url.dll,FileProtocolHandler "${LOGIN_URL}"
else
  echo "Please open this URL in your browser:"
  echo "${LOGIN_URL}"
fi

# 3. 等待 callback
wait $SERVER_PID 2>/dev/null || true

if [ ! -s "$TMPFILE" ]; then
  echo "ERROR: Login timed out (no callback within ${TIMEOUT}s)" >&2; exit 1
fi

# 4. 解析并校验
SESSION_TOKEN=$(python3 -c "import json; print(json.load(open('${TMPFILE}')).get('session_token',''))")
CB_APP_ID=$(python3 -c "import json; print(json.load(open('${TMPFILE}')).get('app_id','${APP_ID}'))")

if [[ ! "$SESSION_TOKEN" =~ ^gwst_ ]]; then
  echo "ERROR: Invalid session_token (missing gwst_ prefix)" >&2; exit 1
fi

# 5. 落盘 YTOSS（保留其他 app_id 条目，支持降级路径）
mkdir -p "$(dirname "$YTOSS_PATH")" 2>/dev/null || mkdir -p "$(dirname "$YTOSS_FALLBACK_PATH")"
python3 -c "
import json, os
from datetime import datetime, timezone

# 尝试主路径，失败则降级
primary = '${YTOSS_PATH}'
fallback = '${YTOSS_FALLBACK_PATH}'

# 判断主路径是否可写
try:
    os.makedirs(os.path.dirname(primary), exist_ok=True)
    path = primary
except (PermissionError, OSError):
    os.makedirs(os.path.dirname(fallback), exist_ok=True)
    path = fallback

data = {'sessions': {}}
if os.path.exists(path):
    try:
        existing = json.load(open(path))
        if 'session_token' in existing and 'sessions' not in existing:
            old_app = existing.get('app_id', 'unknown')
            data['sessions'][old_app] = {
                'session_token': existing['session_token'],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        elif 'sessions' in existing:
            data = existing
    except: pass

data['sessions']['${CB_APP_ID}'] = {
    'session_token': '${SESSION_TOKEN}',
    'created_at': datetime.now(timezone.utc).isoformat()
}
with open(path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
try:
    os.chmod(path, 0o600)
except: pass
print(f'Token saved to: {path}')
"

echo "OK: Login successful (app_id=${CB_APP_ID})"
```

**关键约束**：
- 本地监听是 one-shot（`handle_request()`，非 `serve_forever`），callback 收到后立即退出
- 超时 120s，超时后 exit 1，提示用户重试
- `return` 参数中 host 必须是 `127.0.0.1`（禁 `localhost`），path 必须是 `/cb`（精确匹配）

---

## 错误处理与降级路径

**业务调用阶段错误码**：

| HTTP | code | 含义 | 处理 |
|------|------|------|------|
| 401 | `19002` | SESSION_INVALID（过期/撤销/不存在） | 删 YTOSS 中 wukong 条目 → 重走 OAuth 登录（**仅 1 次**）|
| 401 | `1001` | UNAUTHORIZED | 同 19002 处理 |
| 401 | `19003` | AK_FROZEN（管理员冻结） | 提示"账号已被管理员冻结，请联系管理员"，**不重登** |
| 200 | `2001` | PAYMENT_REQUIRED | 提示充值，session 仍有效，不重登 |
| 200 | `1004` | RATE_LIMIT_EXCEEDED | 退避重试 |
| 502 | `5001`/`5002` | 网关上游异常 | 透传错误，session 仍有效 |

**自动重登约束**：
- 仅 `19002` 和 `1001` 触发自动重登，且**仅重试 1 次**——第二次仍失败则中止报错
- `19003` / `2001` / `5001` / `5002` 不重登

**登录阶段错误**（`/auth/oauth/login` 返回 400）：

| body 关键字 | 含义 | 处理 |
|------------|------|------|
| `app_id 参数不可为空` / `app_id 参数格式非法` | 编码错误 | 修代码 |
| `app_id 不合法` | yt_app 未注册或已禁用 | 提示"该应用未开通登录服务，请联系运维"，不重试 |
| `return URL 不在白名单内` | return 参数格式不符 | 修代码 |
| `state 已过期` / `state 签名校验失败` | 用户停留 >5min 或 URL 被篡改 | 提示"会话已过期"，重新发起 OAuth |

### 数据不可用时的降级原则（不得直接中断）

| 情况 | 降级动作 |
|------|---------|
| 网关不可达 / 502 持续 | 明确告知"选址数据服务暂时不可用"，说明已完成到哪一步，建议稍后重试；**不得用常识编造五维分数** |
| 登录超时 / 用户放弃授权 | 说明"未完成授权，无法获取选址数据"，询问是否改为仅做定性建议（并声明无数据支撑） |
| POI 检索不到 | 反问更精确的店名/商场名/详细地址，不要自行猜一个相近的 POI |
| 某个 module 无返回 | 只解读已返回模块，缺失维度标注"该维度数据本次未返回"，不推断补全 |
| 配额不足（2001） | 提示充值，并说明已消耗的查询不会重复扣费（同参数 MD5 幂等） |

---

## 重要约束

- **禁止向用户索要鉴权信息**：不得通过对话询问用户提供 token 等参数，自动执行 OAuth 流程，唯一需要用户参与的是在浏览器中完成登录
- **禁止硬编码 session_token**：必须从 YTOSS 文件中读取
- **curl 必须带 `-k`**：跳过 TLS 证书校验
- **强制数据一致性**：输出的所有数据必须严格来源于接口实际返回结果，不得修改、换算、补全、推断或生成接口未返回的数据
- **禁止调用异步接口**：所有场景使用在线同步计算接口
- **配额管理**：使用请求参数 MD5 作为幂等 key，同一参数组合仅扣一次配额

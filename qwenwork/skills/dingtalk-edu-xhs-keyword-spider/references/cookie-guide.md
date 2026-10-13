# Cookie 获取指南

## 获取方式：Playwright 自动化浏览器

使用 Playwright 启动有头浏览器（Chromium），引导用户登录小红书后，通过 `context.cookies()` 获取完整 Cookie（**包括 httpOnly 的 `web_session`**）。

> **为什么用 Playwright：** 小红书的 `web_session` Cookie 设置了 `httpOnly`，`document.cookie` 无法读取。Playwright 的 `context.cookies()` 可直接获取包括 httpOnly 在内的所有 Cookie，无需从网络请求头中手动提取。

## 完整流程

### 步骤1：运行Cookie获取脚本

```bash
python3 SKILL_DIR/scripts/xhs_cookie.py -o SKILL_DIR/cookies.json
```

脚本会自动：

1. 启动 Chromium 有头浏览器
2. 导航到 `https://www.xiaohongshu.com`
3. 等待用户在浏览器中完成登录

### 步骤2：在浏览器中登录

脚本打开浏览器后，请在浏览器中完成小红书登录：

- 扫码登录（推荐，最快捷）
- 手机号登录
- 微信登录

脚本会自动轮询检测 `web_session` Cookie，登录成功后自动继续。

### 步骤3：Cookie自动保存

登录成功后，脚本自动：

1. 通过 `context.cookies()` 获取所有 Cookie（包括 httpOnly）
2. 过滤小红书相关域名的 Cookie
3. 验证 `web_session` 和 `a1` 等关键字段
4. 保存到 `cookies.json` 文件

输出示例：

```json
{
  "success": true,
  "cookie_file": "/path/to/cookies.json",
  "cookie_count": 15,
  "has_web_session": true,
  "has_a1": true
}
```

### 步骤4：验证Cookie有效性

```bash
python3 SKILL_DIR/scripts/xhs_search.py search \
  -q "测试" -n 1 -c SKILL_DIR/cookies.json
```

如果返回 `success: true`，则Cookie有效。

## 命令参数

| 参数               | 类型   | 说明                                              |
| ------------------ | ------ | ------------------------------------------------- |
| `--output` / `-o`  | string | Cookie文件输出路径（默认 SKILL_DIR/cookies.json） |
| `--timeout` / `-t` | int    | 登录等待超时秒数（默认300）                       |

## 常见问题

### 登录超时

默认等待300秒，可增加超时时间：

```bash
python3 SKILL_DIR/scripts/xhs_cookie.py -o SKILL_DIR/cookies.json -t 600
```

### Playwright 未安装

```bash
pip3 install playwright && playwright install chromium
```

或通过环境安装脚本：

```bash
bash SKILL_DIR/scripts/setup_env.sh
```

## Cookie 格式要求

- 必须包含 `web_session` 字段（登录态的关键标识，httpOnly）
- 必须包含 `a1`、`webId` 字段（签名算法需要）
- Cookie 为分号分隔的键值对字符串，如：`a1=xxx; webId=xxx; web_session=xxx`

## Cookie 过期处理

- 小红书Cookie有效期通常为 7-30 天
- 搜索接口返回错误时，首先检查Cookie是否过期
- 过期后重新运行 `xhs_cookie.py` 即可
- **禁止**使用他人Cookie，仅使用本人账号登录获取的Cookie

## 安全合规要求

- Cookie 仅用于搜索接口调用，禁止用于任何其他用途
- 禁止将 Cookie 分享、上传或存储到公开位置
- 仅抓取公开可访问的小红书笔记信息
- 遵守小红书robots.txt协议
- 控制请求频率，建议搜索间隔 ≥ 3秒
- 数据仅用于教育场景分析，禁止商业用途

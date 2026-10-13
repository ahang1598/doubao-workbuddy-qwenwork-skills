# 错误码与故障排查

## 常见错误

### E001: Cookie 无效或过期

**表现：** 搜索接口返回 `success: false`，错误信息包含"登录"或"认证"相关字样

**修复步骤：**

1. 重新通过浏览器登录小红书
2. 提取新Cookie并保存到 `cookies.json`
3. 重新执行搜索

### E001a: Cookie 获取失败

**表现：** `xhs_cookie.py` 返回 `success: false`，登录超时或 Cookie 缺少 `web_session` 字段

**修复步骤：**

1. 重新运行 `xhs_cookie.py`，用 `-t` 参数增加超时时间：`python3 SKILL_DIR/scripts/xhs_cookie.py -t 600`
2. 确保在浏览器中完成登录后再等待脚本检测
3. 如反复失败，检查网络是否能正常访问 xiaohongshu.com

### E002: Python 依赖缺失

**表现：** `ImportError: No module named 'execjs'` 或 `ModuleNotFoundError: No module named 'playwright'`

**修复步骤：**

1. 运行 `bash SKILL_DIR/scripts/setup_env.sh` 重新安装依赖
2. 或手动安装：`pip3 install -r SKILL_DIR/scripts/requirements.txt`

### E003: Playwright 浏览器缺失

**表现：** `xhs_cookie.py` 报错 `playwright._impl._api_types.Error: BrowserType.launch: Executable doesn't exist`

**修复步骤：**

1. 安装浏览器二进制：`playwright install chromium`
2. 或运行 `bash SKILL_DIR/scripts/setup_env.sh` 完整安装
3. 重新运行 `xhs_cookie.py`

### E004: Node.js 依赖缺失

**表现：** 签名算法执行失败，返回空结果或签名错误

**修复步骤：**

1. 进入技能根目录：`cd SKILL_DIR`
2. 安装 Node 依赖：`npm install`
3. 重新执行搜索

### E005: 请求频率限制

**表现：** 搜索返回空结果或被限流提示

**修复步骤：**

1. 降低搜索频率，每次搜索间隔 ≥ 3秒
2. 减少单次搜索数量（--num 参数）
3. 等待几分钟后重试

### E006: 笔记详情获取失败

**表现：** `detail` 命令返回 `success: false`

**修复步骤：**

1. 确认URL格式正确（需包含 xsec_token 参数）
2. 检查Cookie是否有效
3. 笔记可能已被删除或设为私密，跳过该条

### E007: 网络连接失败

**表现：** `requests.exceptions.ConnectionError` 或超时

**修复步骤：**

1. 检查网络连接是否正常
2. 确认能访问 `edith.xiaohongshu.com`
3. 如使用代理，检查代理配置

### E008: 报告生成失败

**表现：** `generate_report.sh` 执行报错，HTML 文件未生成

**修复步骤：**

1. 检查输入 JSON 文件路径是否正确
2. 确认 JSON 格式合法（无中文引号、未转义字符）
3. 检查 `notes` 数组是否非空
4. 确认 `interact_info` 中各字段为字符串类型
5. 修正 JSON 后重新运行 `generate_report.sh`

### E009: HTML 报告异常（文件过小）

**表现：** 生成的 HTML 文件 < 1KB，页面内容不完整

**修复步骤：**

1. 查看 `generate_report.sh` 输出的诊断信息
2. 检查 `notes` 数组是否为空但 `total` > 0 → 详情获取步骤可能丢失数据
3. 检查 `interact_info` 中 `liked_count`/`collected_count` 等是否为字符串类型
4. 检查 `tag_list` 格式是否正确（应为字符串数组）
5. 修正后重新生成，最多重试 2 次
6. 仍失败 → 直接输出搜索结果 JSON 文本摘要作为替代

## 排查优先级

遇到错误时，按以下顺序排查：

1. **Cookie** — 是否过期？重新登录
2. **环境** — 依赖是否安装？运行 `setup_env.sh`
3. **网络** — 能否正常访问小红书？
4. **参数** — 命令参数是否正确？
5. **限流** — 是否请求过快？降低频率
6. **报告** — JSON格式是否正确？运行 `generate_report.sh` 是否报错？

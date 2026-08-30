# 废弃说明：xhs-content-reader (CDP 方案)

**废弃时间**: 2026-04-15
**替换方案**: `browser_use` + `understand_media` (OCR)

## 废弃原因
1. **维护成本高**: CDP 协议对 Chrome 版本依赖性强，且需要复杂的登录状态管理（check-login, search-feeds 等）。
2. **稳定性问题**: 小红书网页版反爬机制严密，API 注入易失效，且存在严重的登录墙拦截。
3. **内容完整性**: 旧方案主要提取 DOM 文本，难以精准获取博主以图片形式发布的长文干货。

## 新方案优势
- **视觉双轨**: 通过 `screenshot` + `understand_media` 实现图文内容的完整提取。
- **操作简化**: 统一使用 `browser_use` 导航和交互，逻辑更直观。
- **安全规范**: 遇到登录墙立即停止并引导用户手动处理，符合自动化安全边界。

## 文件清单
本目录下保留了原 `skills/xhs-content-reader` 的所有脚本和配置，仅供历史参考或极端情况下的回滚测试。
- `scripts/cli.py`: 原命令行入口
- `scripts/chrome_launcher.py`: 原浏览器启动器
- `scripts/xhs/`: 原 CDP 通信与解析逻辑
- `pyproject.toml`: 原依赖配置

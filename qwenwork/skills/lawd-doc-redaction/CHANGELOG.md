# CHANGELOG

## v1.1.1 (2026-09-04)

上架合规整改（静态评测 93 分 → 修掉全部必修/建议项）。

- 显示名变更：「文件脱敏」→「超安全文件脱敏」（英文名 Ultra-Secure File Redaction，仅用于上架表单；frontmatter slug `lawd-doc-redaction` 不变），SKILL.md/README/操作指南同步；工具页 `template.html` 顶栏品牌与标签页标题同步并经 `build.py` 重建（产物仅 +6 字符，vendor/CMap 内联不变）
- 新增 `LICENSES/`（NOTICE + Apache-2.0/MIT 许可全文）：pdf.js、pdf-lib、SheetJS、JSZip、docx-preview 第三方再分发合规；README 许可声明同步区分自研/第三方
- 新增 `.skill-metadata.yaml`：技能卡片 4 条推荐 query（zh/en）
- SKILL.md：新增「触发与不触发」分流表；frontmatter 补 `allowed-tools`（仅预授权 `open_tool.py`）、`license`、`compatibility`；阶段三交接改为封闭枚举白名单（lawd-contract-review / lawd-legal-translation / lawd-evidence-timeline-generator）并明令禁止对原件路径调用文件类技能；脱敏凭证安全级别统一为「agent 禁读」；补 `<本技能目录>` 取路径说明与"坚持要 agent 读原件"的终局拒绝话术；description 去粗体符号并压缩与正文重复的流程细节
- `package.py`：白名单加入 `LICENSES` 与 `.skill-metadata.yaml`，"无隐藏文件"检查按规范豁免后者

## v1.1.0 (2026-09-02)

交互改版 + 自动打开。

- 布局改版：载入后移除侧栏入口卡；空载态改为全屏居中 Hero 大入口；「不经大模型 · 无网络传输 · 数据不出本机」改为入口下方动效徽章
- 导出按钮上移到顶栏右上角（紧凑胶囊式），新增「重新发起脱敏」按钮与脱敏统计/原文对照表快捷图标
- agent 可自动打开工具页面：新增 `scripts/open_tool.py`（系统默认浏览器弹出，零依赖，不读任何文件内容；云端/无桌面环境自动失败并回落为给路径）
- 修复审批系统导出的 PDF 预览无文字（worker 脚本编码声明 + FontFace 注册前净化兜底）
- 真机修复·改名：「复查」更名为「敏感信息复查」并改为结果区顶部横条，命名与功能对齐（`src/style.css`）
- 真机修复·覆盖缺口：docx 图表（`word/charts/*`）与 SmartArt（`word/diagrams/*`）内文字纳入涂抹/替换覆盖，逐 `a:t` 文本节点处理（`src/office.js`）
- 真机修复·闭环：复查面板漏检词条新增「脱敏此词」一键动作——加入手动补充词、精确全文匹配重扫、复查条目随之消解（`src/app.js` + `src/core.js`）

## v1.0.0 (2026-09-01)

首版发布。

- 五路输入：粘贴文本 / PDF / Word(docx) / Excel(xlsx) / 图片
- 敏感字段库 23 条规则（固定格式 / 合同标签 / 特征 / 金额与日期场景开关）
- 客体清单确认制：逐条勾选、替代词可编辑、实体全文一致编号（某公司A/B、某人甲/乙）
- 逐条撤销（点击脱敏块浮出「撤销」）+ 撤销上一步 + 清空全部
- 框选补漏 / 涂抹（PDF 与图片）
- 残留漏检扫描（脱敏后自动复查可疑特征）
- 双出口：脱敏文本/Word/Excel（原文删除）+ PDF 栅格化（防恢复）；处理凭证自动生成（不含原文）；映射表受控导出（含原文+警告）
- 隐私设计：零网络请求、断网可用、原件只读、docx/xlsx 元数据清理、外链清洗

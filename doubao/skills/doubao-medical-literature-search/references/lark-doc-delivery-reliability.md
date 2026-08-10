# 平台飞书文档交付

本文件只管完整文献报告如何调用平台已配置的 Skill，以及飞书正文是否真正交付。检索、筛选、证据评价、综合和图表规则仍以本 Skill 其他 reference 为准。

## 1. 直接使用平台 Skill

创建或编辑飞书在线文档时，直接调用平台已配置的 `lark-doc` Skill，由它路由到 `online-doc`。不要为了寻找 Skill 执行：

- `which lark-cli`
- `lark-cli skills read lark-doc`
- `lark-cli docs skills read lark-doc`
- 反复查看 CLI 帮助或猜测未在 `lark-doc` 中出现的命令和参数

Trace 出现 `unknown command` 或 `unknown flag` 时立即停止该分支，不换排列方式继续试。平台未加载 `lark-doc` 时，保留经过校验的本地 XML 草稿并明确说明在线文档不可用。

其他产物按平台已配置 Skill 路由：

- 飞书在线文档：`lark-doc` 的 `online-doc`
- Word/docx：`lark-doc` 的 `office-word`
- PPT/飞书幻灯片：`lark-ppt`
- Mermaid 画板：按 `lark-doc` 规则由主 Agent 插入
- 复杂画板或已有画板更新：按 `lark-doc` 路由到 `lark-whiteboard`

## 2. 使用真实的 lark-doc 规则

当前平台 `lark-doc/online-doc` 使用 v2。所有 `docs +create`、`docs +fetch`、`docs +update` 必须显式传 `--api-version v2`。执行前由 `lark-doc` 读取创建、XML、style、fetch 和 update 对应 reference；语法或参数冲突时，以平台 `lark-doc` 为准。

## 3. 本地报告预检

1. 先生成一份完整报告 XML；对本次将写入飞书的同一文件依次运行 `node scripts/sanitize-feishu-report.js <report.xml>` 和 `node scripts/validate-report-whiteboards.js <report.xml>`，两者退出码均为 0 才能继续。不得用目测或“等价检查”替代；修复后必须重跑。
2. 允许 citation 引用组件；禁止原始、转义、双重转义、数字实体或样式化 HTML 上标。
3. XML 已含 `<title>` 时不得再传 `--title`；标题只能有一个来源。
4. `<callout>` 不得使用平台 XML schema 未支持的 `type` 属性。
5. `--content @file` 只使用当前工作目录下的相对路径；不得传绝对 `@file`，也不要使用 `--content "$(cat file)"`。
6. 写入和回读结果必须保留完整 JSON，不用 `head`、`tail` 截断。

## 4. 写入策略：整篇一次创建优先

默认把已经通过校验的完整 XML 一次创建：

`lark-cli docs +create --api-version v2 --content @report.xml`

创建响应通过硬闸门后，只做一次完整 fetch，确认本次 XML 计划中的全部章节、正文链接、参考文献以及实际使用的白板均存在。未指定结构时，默认计划可包含以下章节：

0. 不编号“总结”高亮块
1. 根据用户 Query 提炼的回答型专业小标题
2. 证据脉络与研究关系
3. 指南与专家共识
4. 系统综述与关键研究
5. 其他相关研究
6. 最新进展、热点、争议与空白
7. 学习、课题或论文写作建议
8. 检索策略与证据范围
9. 完整参考文献（含链接）
10. 免责声明

回读完整即完成在线文档写入，不因“文献多”或“章节多”预先走骨架流程。

## 5. 三块兜底

只有整篇创建明确因载荷、长度或服务限制失败，且没有留下可用文档时，才启用三块兜底：

1. 按标准目录把完整 XML 切成 3 个连续、篇幅大致均衡的大块；保留标题后的“总结”高亮块，选择本次动态第一章标题、第四章和第八章作为可见锚点，用户指定核心交付物随第一章进入第一块。
2. 创建只含唯一标题、“总结”高亮块和这 3 个锚点标题的骨架，再 fetch outline 一次取得 block ID。
3. 最多执行 3 次正文更新；每块写入对应锚点后的连续内容，块内不重复锚点标题。
4. 三个锚点均来自同一次 outline fetch。只有 `degrade_code=1002`、需要新插入 block ID，或结构发生替换/删除时才重新 fetch。
5. 每个 update 检查完整 JSON；三个大块全部写完后统一做一次完整 fetch，不在每章后重复回读。

不得把三块继续展开成十章十次更新。只有某个大块本身明确触发长度限制时，才允许只把该失败大块拆成两个子块。`append` 只用于真正追加到文档末尾，不得用于填充中间 section。

整篇创建若返回 document ID 但结果失败、存在 warning 或回读不完整，先 fetch 该文档确认实际状态；不要未经检查再创建第二份文档，也不要通过批量删除重复标题、重排层级或整篇 overwrite 修复可避免的骨架冲突。

## 6. 每次操作的硬闸门

每次创建、更新和回读都检查完整 JSON，可使用：

`node scripts/validate-lark-doc-result.js --operation create|update|fetch lark-result.json`

判定规则：

- create：`ok=true`，document_id/url 存在，warnings 为空
- update：`ok=true`，`data.result=success`，warnings 为空，`updated_blocks_count` 大于 0
- fetch：`ok=true`，并回读到本次计划中的全部章节、链接、参考文献及实际使用的白板
- `permission_grant` 存在时必须为 `status=granted`

`failed`、`partial_success`、任意 warning、预期更新数为 0 或回读缺失都阻断下一步。URL 和 `revision_id` 不能单独证明成功。

常见问题：

- `degrade_code=1017`：同时使用 `--title` 与 XML `<title>`；保留一种标题来源后重新执行。
- `degrade_code=5002` 且指向 `<callout type=...>`：删除不支持的 `type` 属性并重新校验。
- `degrade_code=1002`：先回读最新结构，确认内容未落盘，再用新鲜显式 block ID 重试一次；不要改成逐章写入。

## 7. 状态消息和失败停止

- 正常完整报告只发送一次开始状态和最终结果。
- create、fetch 和三块兜底属于内部操作，不逐次发送“我计划”“继续写入”“当前 section”“block ID”等旁白。
- 只有整篇创建失败并切换三块兜底，或最终出现阻断时，才额外发送一句有价值的状态。
- fetch 超时可对同一读取最多重试 2 次；期间不执行新写操作。连续超时后停止更新。
- 未知命令、未知参数、warning 或失败时，不尝试相似命令排列。

## 8. 完成条件

只有以下条件同时满足，才可声称“飞书文档交付完成”：

- 正文一次创建通过硬闸门；或三块兜底的所有 update 通过硬闸门。
- 完整回读存在本次计划中的全部章节、关键链接、参考文献及实际使用的白板。
- 无未处理 warning、partial success、权限失败或未验证步骤。

正文成功但权限或回读失败时，只能说明正文已创建、相应验证或权限交付未完成。

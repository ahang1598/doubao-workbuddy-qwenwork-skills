---
name: dock-workbench-win
description: 小艺Work 工作台插件访问工具：读取/操作右侧工作台当前任务里的页签内容——文件预览页签中用户拾取的元素（inspect：单元格/段落/图表引用）、页签清单（state：文件/表格/幻灯/网页标签概览）。当用户消息尾部出现「工作台元素」上下文块（用户在文件/表格/文档中拾取了元素）、或需要查询任务里打开的文件页签内容时使用。触发关键词：工作台、文件页签、拾取元素、单元格、选中内容、页签列表。浏览器页签的打开/点击/表单操作请用 xiaoyiwork-browser-control-win 技能（本技能不含浏览器操作）。
---

# 小艺Work 工作台插件访问 Skill

读取/操作右侧工作台**当前任务**的页签与拾取元素。所有动作只作用于当前任务的页签——
其它任务的页签不可见也不可操作（任务隔离；跨任务访问返回 `TAB_WRONG_CONVERSATION`，
此时应提示用户先切换到目标任务）。

## 环境初始化（始终最先执行此步骤）

```bash
NODE_CMD=""
# 小艺 Work 会注入已验证的托管 Node；独立运行时再回退系统 Node。
if [ -n "${CLAW_NODE_EXE:-}" ] && "$CLAW_NODE_EXE" -v 2>/dev/null; then
  NODE_CMD="$CLAW_NODE_EXE"
fi
if [ -z "$NODE_CMD" ] && command -v node &>/dev/null; then NODE_CMD="node"; fi
if [ -z "$NODE_CMD" ]; then
  echo '{"ok":false,"error":{"code":"DOCK_CLI_NO_RUNTIME","message":"未找到 Node 运行时"}}'
  exit 1
fi
```

> 检查完成后，后续所有命令用 `"$NODE_CMD" scripts/dock-cli.mjs …` 调用
> （工作目录 = 本技能根目录；脚本位于 `scripts/` 相对路径）。

## 操作入口

| 操作 | 命令 |
|------|------|
| 命令目录（发现全部命令） | `"$NODE_CMD" scripts/dock-cli.mjs help` |
| 当前任务页签概览 | `"$NODE_CMD" scripts/dock-cli.mjs state` |
| 读拾取元素内容 | `"$NODE_CMD" scripts/dock-cli.mjs files inspect --tab-id {tab_id} --ref {ref}` |

## 通用约定

1. **输出 JSON**；可加 `--query tabs`（点路径）只取需要的字段。
2. **错误形状统一**：`{"ok":false,"error":{"code","message","hint"}}`；错误码重试语义：
   - `DOCK_UI_NOT_READY`：可稍后重试；
   - `NO_SUCH_TAB` / `STALE_REF`：`state` 重枚举 / 重新拾取后重试；
   - `DOCK_PROXY_UNAVAILABLE` / `DOCK_CLI_NO_RUNTIME` / `TAB_WRONG_CONVERSATION`：勿重试。
3. **tab_id / ref 来源**：用户消息尾部「工作台元素」块的「标签页」「引用」字段；
   没有该块时先 `state` 查看当前任务的页签。
4. **任务隔离**：`state` 只返回当前任务的页签；引用其它任务的 `tab_id` 会被拒绝
   （`TAB_WRONG_CONVERSATION`）——引导用户切换任务，不要反复重试。
5. 每条命令的可复制示例见 `help` 目录中的 `example` 字段。

## 与浏览器技能的分工

- 浏览器页签（网页打开/点击/填表/快照）→ 使用 **xiaoyiwork-browser-control-win** 技能（技能市场安装）；
- 文件/表格/文档页签与其中的拾取元素 → 使用**本技能**；
- 两套描述不重叠：一个「浏览器标签」请求永远不要用本技能，一个「文件内容」请求
  永远不要用 xiaoyiwork-browser-control-win。

# 团队台账安装指引（install-notice）

> 分享团队台账后，必须把安装指引发给被分享者，否则对方打开表格也不会用。
> 测试阶段发 `.zip` 安装包；上架后改发插件市场引导，不再发文件。
> 打包格式遵循《千问办公-生态接入白皮书》：仅 `.zip`，包内必须存在 `<技能名>/SKILL.md` 精确路径（压缩整个 `agent-task-hub/` 目录，不要只压目录内文件），≤ 10 MB、条目数 < 1000。

## 发送前提

- 已确定目标团队群，并解析出群 `openconversation_id`：

```bash
dws chat search --query "<团队群名>" --format json
# 或列出我的群
dws chat my-groups --format json
```

- 发送是**真实消息**，调用前确认内容和接收对象无误，不可测试调用。

## 测试阶段：发 .zip 安装包 + 说明文案

```bash
# ① 打包（在包含 agent-task-hub/ 目录的上一级目录下执行；不写死安装路径）
#    关键：带外层目录一起压缩，保证包内路径是 agent-task-hub/SKILL.md
cd <agent-task-hub/ 所在目录的上一级> && zip -r /tmp/agent-task-hub.zip agent-task-hub -x "*.DS_Store" -x "*__pycache__*" -x "*/__tests__/*" -x "*/__tests__"

# ② 发 .zip 文件到群
dws chat message send --group <openconversation_id> --msg-type file --file-path /tmp/agent-task-hub.zip

# ③ 发安装说明文案
dws chat message send --group <openconversation_id> --text "<下方文案>"
```

测试阶段文案（把 `<BASE_ID>` / `<BASE_URL>` 换成真实值；`<BASE_URL>` 形如 `https://alidocs.dingtalk.com/i/nodes/<BASE_ID>`）：

```
**千问办公任务台账**技能包已发群里，装好后**交接 / 续接 / 认领**都走团队台账。

团队台账：<BASE_URL>

**安装三步**

1. 下载群里的 `agent-task-hub.zip`，在千问办公「技能 → 安装技能」拖入该 zip 即可

2. 新建会话，说「接续团队任务」

3. 首次接入选团队模式 → 已有表格 → 填 baseId `<BASE_ID>`

```

## 上架后：引导去插件市场下载

上架到千问办公技能市场后，**不发 zip 文件**，只发一段引导：

```bash
dws chat message send --group <openconversation_id> --text "<下方文案>"
```

上架后文案（把 `<BASE_ID>` / `<BASE_URL>` 换成真实值）：

```
请先安装**千问办公任务台账**技能：在千问办公里搜索 `agent-task-hub` 并安装。

团队台账：<BASE_URL>

装好后新建会话，选团队模式接入（baseId `<BASE_ID>`）。
```

## 硬规则

- **仅 `.zip`**：客户端安装入口与上架校验都只认 zip（不支持 .skill/.tar.gz/.rar/.7z）；也不要在 Finder 里右键压缩目录内文件（会丢失外层目录导致找不到 `agent-task-hub/SKILL.md`）。
- **文案是固定模板**：只替换 `<BASE_ID>` / `<BASE_URL>` 后逐字发送，不要改写、扩写、调整结构或换措辞。
- 测试阶段用 `.zip`；上架后用技能市场，二者二选一，不要混发。
- 群 `openconversation_id` 现场解析，不硬编码。
- 发送前必须确认群和文案正确；`message send` 会真实触达。
- 钉钉 IM 文本**支持 Markdown**：用加粗、换行、有序列表突出重点；但链接一律发裸 `https://...`，**不要**写 `[文字](url)` Markdown 链接——钉钉会自动把裸链接解析成卡片。
- 发送前确认文案中没有残留 `<BASE_ID>` / `<BASE_URL>` 占位符。

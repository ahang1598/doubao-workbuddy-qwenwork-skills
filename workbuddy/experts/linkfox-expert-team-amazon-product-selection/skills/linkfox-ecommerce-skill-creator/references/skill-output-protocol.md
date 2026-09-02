# Skill 输出协议对接文档

> 适用对象：编写 LinkFox skill 脚本的开发同学
> 适用版本：acpx-bridge 2026-05 之后

---

## 概述

acpx-bridge 会自动识别 skill 脚本的 stdout 输出，将符合协议的内容转换为前端可渲染的 `tool_call` 通知。你的 skill 不需要直接操作 WebSocket，只需在 stdout 中按规范输出即可。

支持的产物类型：

| 类型 | 用途 | 前端呈现 |
|------|------|----------|
| 文件输出 | 生成单个 JSON 结果文件 | 文件资源链接 |
| 媒体数组 | 生成图片/视频等媒体文件 | 媒体资源链接 |

---

## 1. 文件输出

### 场景

skill 执行完毕后，将结构化结果写入 JSON 文件，并在 stdout 中打印标准格式的落盘行。

### 输出格式

stdout 中包含以下格式的行（示意为代码模板，实际 stdout 必须使用真实已存在文件路径）：

```python
if not os.path.isfile(abs_json_path):
    raise RuntimeError(f"output file not found: {abs_json_path}")
print(f"Saved full response: {abs_json_path} ({size_bytes} bytes)")
```

### 要求

- 路径必须是绝对路径
- 文件名必须匹配 `linkfox-<slug>-<数字>.json`
- 括号中的字节数仅用于人读，bridge 不解析

### 转换效果

- `title` 设为 `<slug>(bash)`
- 追加一个 `resource_link` content block 指向该文件（mimeType: `application/json`）

### 示例

```bash
# 将结果写入文件
OUTPUT_PATH="/Users/xxx/acpx-workspaces/member1/linkfox-amazon-search-1718000000.json"
echo "$JSON_RESULT" > "$OUTPUT_PATH"

# 打印标准落盘行（bridge 会识别并转换）
BYTES=$(wc -c < "$OUTPUT_PATH")
echo "Saved full response: $OUTPUT_PATH ($BYTES bytes)"
```

---

## 2. 媒体数组输出

### 场景

skill 生成了图片、视频等媒体文件。

### 输出格式

stdout 中包含（示意为代码模板，实际 stdout 必须使用真实已存在文件路径）：

```python
missing = [p for p in abs_media_paths if not os.path.isfile(p)]
if missing:
    raise RuntimeError(f"media file not found: {missing[0]}")
print("Saved full response: " + json.dumps(abs_media_paths, ensure_ascii=False))
```

### 要求

- 必须是 JSON 数组格式
- 每个元素为绝对路径字符串，且文件必须已存在
- 文件扩展名必须在支持列表中
- 禁止把 `<YYYY-MM-DD>`、`<session>`、`linkfox-generated-media-123.png` 等文档占位符原样输出
- `resolve_media_path()` 只分配路径，不会写文件；必须先把媒体内容写入该路径并校验 `os.path.isfile(path)`，再输出给 bridge

### 支持的媒体格式

| 扩展名 | MIME |
|--------|------|
| `.png` | image/png |
| `.jpg` / `.jpeg` | image/jpeg |
| `.gif` | image/gif |
| `.webp` | image/webp |
| `.bmp` | image/bmp |
| `.svg` | image/svg+xml |
| `.mp4` | video/mp4 |
| `.webm` | video/webm |
| `.mov` | video/quicktime |
| `.mp3` | audio/mpeg |
| `.wav` | audio/wav |

### 转换效果

- `title` 设为 `<slug>(bash)`（slug 从文件名 `linkfox-<slug>-<数字>` 提取）
- 每个媒体文件追加一个 `resource_link` content block

### 示例

```bash
# 生成图片后打印
echo 'Saved full response: ["/tmp/workdir/linkfox-multimodal-generate-image-1718000000.png"]'
```

---

## 3. 注意事项

### 文件名规范

文件名必须符合 `linkfox-<slug>-<数字>.json`（或对应媒体扩展名）格式，其中：
- `<slug>` 是 skill 的标识，只能包含小写字母、数字和连字符
- `<数字>` 通常用时间戳

### 文件路径要求

路径必须是**绝对路径**。bridge 会将其转为 `file://` URI 发送给前端。

### stdout 中可以有其他内容

bridge 只匹配 `Saved full response:` 开头的行，其他 stdout 内容不受影响。skill 可以正常打印日志和调试信息。

### 优先级

如果同一个 Bash tool 输出同时命中文件输出和媒体数组，只有第一个匹配的生效：

```
文件输出 > 媒体数组
```

---

## 4. 快速选型

```
结果是结构化数据（商品列表、关键词分析等）？
  → 写入 JSON 文件，打印 Saved full response 行

结果是图片/视频？
  → 打印 Saved full response + JSON 数组格式的路径列表
```

---

## 5. 调试技巧

1. 本地启动 acpx-bridge（`pnpm dev`），连接 WebSocket 后触发 skill
2. 观察终端日志中 `[sessionUpdate]` 相关输出
3. 检查前端收到的 `session/update` 消息中 `params.update.content` 和 `params.update.title` 是否符合预期
4. 确认 stdout 中有且仅有一行匹配 `Saved full response:` 格式
5. 确认文件名符合 `linkfox-<slug>-<数字>` 规范

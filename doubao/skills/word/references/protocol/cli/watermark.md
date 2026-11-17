---
keyword: watermark
---

**功能**：文字或图片水印读取与更新

# 本地 Word：水印领域命令

## 按需读取

自动目录另查 `table_of_contents`。

写入公共参数见 `local-update`。

水印使用 `lark-cli docs +local-update` 的领域命令及对应 option，不写 DocxXML 标签。仅通过 `lark-cli` 调用，不构造包含 `document_id`、`format`、`revision_id`、`command_params` 等字段的内部请求，也不直调私有接口。

命令须提供顶层 `--revision-id`，接受 `-1` 或非负安全整数；优先传入同一次读取返回的文档版本，不得放进业务 option。后续操作需要新 ID 或文档版本时再读；完整规则见 revision 规则。

## 水印 `watermark`

写前必须 Fetch `watermarks`，确认作用域、共享 Header 引用和当前配置，并把同次结果的 `state_fingerprint` 写入 `expected_state_fingerprint`；不得省略或复用旧指纹。

`--watermark-option` 接受单层 JSON object，必填 `action=set_text|set_image|clear`：

- `set_text`：新建必填非空 `text`，其余外观字段可省略并使用 Bear 默认值；更新传最新 `target_id`，只提交需要修改的非空 patch 字段。`font_size` 为 `auto` 或 `1..1000` 数值，`transparency` 为 `0..100` 数值，强调开关为 boolean，`direction=horizontal|diagonal`；`color` 为不透明 Hex/RGB，不接受 `auto`、命名色或真实透明色。
- `set_image`：新建必填 `box_token,name,mime_type`，`washout`、`scale` 可省略并使用 Bear 默认值；更新传最新 `target_id`，可只修改 `washout` 或 `scale`，也可提供完整资源三元组替换图片。`washout` 为 boolean，`scale` 为 `auto` 或 `1..1000` 数值。
- 新建允许省略外观字段，已有水印更新采用 patch 语义；不得为了“补全参数”用默认值覆盖当前未要求修改的属性。
- `clear` 必填 `clear_kind=all|text|image`；无匹配项是成功 no-op。
- 可选作用域为 `target_id,header_ids,text_target_ids,image_target_ids`。ID 必须来自当前 Fetch 结果并去重；不得从 DocxXML、文件路径或 block ID 推导水印 ID。省略作用域表示覆盖 root 与各节 header 引用，不等于只改当前页。

```bash
lark-cli docs +local-update --doc "<token>" \
  --revision-id "<revision_id_from_same_fetch>" \
  --command watermark \
  --watermark-option '{"action":"set_text","expected_state_fingerprint":"<state_fingerprint>","text":"机密","font_family":"Arial","font_size":48,"bold":false,"italic":false,"underline":false,"color":"#BFBFBF","transparency":60,"direction":"diagonal"}'
```

---

## 写前定位与边界

- **先核实读取契约**：水印必须通过 `--scope watermarks` 读取身份、作用域和状态指纹；水印及 header 作用域 ID 只能取自当前 CLI 返回的明确领域身份。
- 图片水印新资源的 `box_token/name/mime_type` 必须来自当前已公开的资源流程；不把普通图片 `file_token` 自行转换或拼接为 `box_token`。这一资源要求不适用于保留原资源的属性更新。
- 先完成会影响分页或共享 header 的正文/布局修改，再重新读取身份并更新水印。

## 回执

`data.command_result` 返回 `action`、`changed` 和 `new_revision_id`。`changed=false` 且 `updated_blocks_count=0` 表示调用成功，水印没有变化。公共回执见 `local-update`。

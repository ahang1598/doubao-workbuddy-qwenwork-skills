# drive +html-image-upload

上传一张本地图片，生成可在 HTML 中引用的图片链接。

## 用法

```bash
lark-cli drive +html-image-upload --file ./image.png
```

`--file` 必填，指定当前工作目录下可读取、非空的图片文件相对路径，无需文档或文件夹 token。

确认返回 `ok: true` 后，将 `data.url` 用作 HTML 中 `<img>` 的 `src`。同时返回 `data.file_token`、`data.file_name` 和 `data.size`。

## 注意

- 命令只上传图片，不解析或修改 HTML；链接访问遵循服务端权限规则。
- 不超过 20 MiB 时直传，超过时自动走分片接口，无需额外参数；服务端仍可能限制图片格式或大小。
- 可用 `--dry-run` 预览上传流程，或 `--help` 查看参数。
- 上传失败时保留错误信息与 `log_id`，不要生成或使用虚构链接；提示上传可能已完成时，不要自动重复上传。

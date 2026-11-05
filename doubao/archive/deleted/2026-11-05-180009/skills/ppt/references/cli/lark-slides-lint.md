# slides +lint

## 用途

对完整 `<presentation>` XML 或单个 `<slide>` 片段执行服务端 lint；只读，不创建或修改幻灯片。此 shortcut 只接收 XML 内容，不接收 `--presentation`、Slides URL 或 `slide_id`。

输入与完整响应文件都放在当前工作目录 `<CWD>` 下。复杂 XML 必须用 `@文件` 传入，并保留 stdout 和 stderr 的完整 JSON；终端截断后的片段无法用 `lint_inspect.py` 补全。

## 命令

### 检查本地完整 XML

```bash
lark-cli slides +lint \
  --content @./presentation.xml \
  --json > ./lint-response.json \
  2> ./lint-error.json
```

### 检查本地单页 XML

```bash
lark-cli slides +lint \
  --content @./slide-01.xml \
  --json > ./slide-01-lint-response.json \
  2> ./slide-01-lint-error.json
```

## 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--content` | 是 | XML 内容；支持直接传值、`@文件` 和 `-` stdin。也支持 `--xml`、`--slide-xml`、`--slide-content`、`--content-xml`、`--slide` 别名。空内容报 `--content cannot be empty`。 |
| `--json` | 否 | `--format json` 的简写；示例中显式传入，以便保存完整 JSON。 |

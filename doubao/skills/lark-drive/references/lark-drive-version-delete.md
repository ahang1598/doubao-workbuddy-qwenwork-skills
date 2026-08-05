# drive +version-delete

删除指定的历史版本。

## 命令

```bash
lark-cli drive +version-delete \
  --file-token boxcnxxxxxxxx \
  --version 7633658129540910621 \
  --yes
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--file-token` | 是 | 目标文件 token |
| `--version` | 是 | `drive +version-history` 返回的长数字 `version` 字段，不是 `tag` |
| `--yes` | 是 | 确认执行高风险删除操作 |

## 返回值

无额外业务字段，以命令成功 / 失败为准。

## 参考

- [lark-drive](../SKILL.md) -- 云空间（云盘/云存储）全部命令

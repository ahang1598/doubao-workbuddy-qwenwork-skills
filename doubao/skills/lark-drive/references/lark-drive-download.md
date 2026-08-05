
# drive +download

从飞书云空间（云盘/云存储）下载文件到本地。

## 命令

```bash
# 下载到指定路径
lark-cli drive +download --file-token boxbc_xxx --output ./report.pdf

# 只提供 token，默认保存为当前目录下同名文件
lark-cli drive +download --file-token boxbc_xxx
```

## URL 解析

从飞书文件 URL 提取 token：

```
https://xxx.feishu.cn/drive/file/boxbc_xxx
                                  ^^^^^^^^^
                                  file_token
```

## 参考

- [lark-drive](../SKILL.md) -- 云空间（云盘/云存储）全部命令

# 小宇宙播客爆款拆解

**触发词**：提取播客内容、小宇宙转录、播客说了什么、获取播客文字

> ✅ 无需登录，无需浏览器，完全公开接口

## 默认执行命令

```bash
python3 scripts/cli.py extract-xiaoyuzhou \
  --url "https://www.xiaoyuzhoufm.com/episode/6761711b7d8426f692d99dfd" \
  --output-dir ~/.content-breakdown/output
```

## 内部执行步骤

1. HTTP 请求 episode 页面，解析 `__NEXT_DATA__` 获取节目信息（标题、简介、音频直链）
2. 下载音频文件（MP3/M4A）
3. 必剪云端 ASR 转录（与抖音完全相同的流程）
4. 生成 Markdown 报告（节目信息 + 转录文本）

## 仅获取节目信息（不转录）

```bash
python3 scripts/cli.py extract-xiaoyuzhou \
  --url "https://www.xiaoyuzhoufm.com/episode/6761711b7d8426f692d99dfd" \
  --skip-transcript \
  --output-dir ~/.content-breakdown/output
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--url` | 小宇宙 episode 链接（必填） | `https://www.xiaoyuzhoufm.com/episode/xxx` |
| `--skip-transcript` | 跳过音频下载和 ASR 转录，仅提取文字信息 | — |
| `--output-dir` | 输出目录 | `~/.content-breakdown/output` |

## 执行完成后

命令执行成功后，读取结果中的 `transcript` 字段（或 `description` 若跳过转录），**按 `references/output-format.md` 的格式输出给用户**。

## 预计耗时

~20-40s（含音频下载和 ASR 转录）；`--skip-transcript` 时 ~3s

# 本地渲染脚本（仅维护）

本文件只保留仓库脚本的维护入口，不参与作品生产。HTML 创建与编辑的默认预览必须使用 [shot.py 预览策略](html-preview.md)；不得在该能力缺失时用本地浏览器截图冒充通过。

`scripts/maintenance/render_html.py` 与 `scripts/maintenance/capture_canvas.cjs` 仅用于维护脚本本身、运行回归样页或排查实现问题。执行结果不替代 `shot.py` 状态、`FileBatchUpload`、顶层 HTML Item 创建或 `+get` 回读，也不通过 `present_files` 交付。

维护命令以各脚本 `--help` 为准：

```bash
python3 scripts/maintenance/render_html.py --help
node --check scripts/maintenance/capture_canvas.cjs
```


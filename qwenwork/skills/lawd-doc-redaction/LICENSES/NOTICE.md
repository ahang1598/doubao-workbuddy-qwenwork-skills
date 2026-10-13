# THIRD-PARTY NOTICES

本技能的工具页面 `assets/redaction-studio.html` 由 `build.py` 将以下第三方开源库**原样内联**（仅压缩/嵌入，未修改源码）构建而成。各库按下列许可再分发，许可全文见本目录 `Apache-2.0.txt` / `MIT.txt`。

| 库 | 版本 | 版权 | 许可 | 用途 |
|---|---|---|---|---|
| pdf.js（`pdf.min.js`、`pdf.worker.min.js`、`cmaps/`） | 2023 构建 | Copyright 2023 Mozilla Foundation | Apache-2.0 | PDF 渲染与文字层解析 |
| pdf-lib（https://github.com/Hopding/pdf-lib） | 1.x | Copyright (c) 2017 Andrew Nedville | MIT（min 构建未内嵌许可头，以上游仓库 LICENSE 为准）；内含 tslib（Apache-2.0, Copyright (c) Microsoft Corporation） | PDF 编辑与导出 |
| SheetJS（`xlsx.full.min.js`） | 0.18.5 | Copyright (C) 2013-present SheetJS LLC | Apache-2.0 | Excel 读写 |
| JSZip | 3.10.1 | Copyright (c) 2009-2016 Stuart Knightley | MIT（原始为 MIT/GPLv3 双许可，本项目按 MIT 使用）；内含 pako（MIT, © 2014-2017 Vitaly Puzrin & Andrey Sitnik） | docx/xlsx 解压打包 |
| docx-preview | 0.6.x | Copyright Volodymyr Baydalka | Apache-2.0 | Word 文档预览 |

Apache-2.0 要求：notices 文件见本目录；许可文本副本随包分发（`Apache-2.0.txt`）。
MIT 要求：上述版权与许可声明保留在各库文件头注释中，并汇总于本文件（`MIT.txt` 为许可全文）。

本技能自研部分（SKILL.md、脚本、样式、应用逻辑）的许可声明见 `README.md`。

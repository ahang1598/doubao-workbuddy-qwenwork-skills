#!/usr/bin/env python3
"""海报静态站点生成器。

将人格结果海报图打包成一个可独立访问的静态页面目录，
供平台部署能力获取公开 URL 后展示给用户。

用法：
  python3 scripts/prepare_poster_site.py --image_relative_path "assets/images/IMFW.png"

输出：
  JSON，包含 site_dir、poster_file、index_path、poster_path 四个字段。
"""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path


def _skill_root() -> Path:
    """返回技能包根目录（scripts/ 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description="海报静态站点生成器")
    ap.add_argument(
        "--image_relative_path",
        required=True,
        help="海报图相对于技能根目录的路径，例如 assets/images/IMFW.png",
    )
    ap.add_argument(
        "--output_dir",
        default="",
        help="可选输出目录，默认为 <技能根目录>/temp/poster_site/<uuid>/",
    )
    args = ap.parse_args()

    root = _skill_root()
    img_path = (root / args.image_relative_path).resolve()

    if not img_path.exists() or not img_path.is_file():
        raise FileNotFoundError(f"海报图片不存在：{img_path}")

    # 构建输出目录
    out_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else (root / "temp" / "poster_site" / uuid.uuid4().hex)
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # 复制海报图到输出目录
    ext = img_path.suffix.lower() or ".png"
    poster_file = f"poster{ext}"
    poster_path = out_dir / poster_file
    shutil.copyfile(img_path, poster_path)

    # 生成 HTML 展示页面
    index_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SBTI 人格测试结果</title>
  <style>
    body {{ margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', Arial; background: #0b0d12; color: #fff; }}
    .wrap {{ max-width: 900px; margin: 0 auto; text-align: center; }}
    img {{ width: 100%; height: auto; border-radius: 16px; box-shadow: 0 12px 48px rgba(0,0,0,.5); }}
    .caption {{ opacity: .55; margin-top: 16px; font-size: 13px; letter-spacing: .02em; }}
  </style>
</head>
<body>
  <div class="wrap">
    <img src="{poster_file}" alt="SBTI 人格测试结果海报" />
    <div class="caption">由钉钉自动生成 · 基于你的近期言行记录</div>
  </div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "site_dir": str(out_dir),
                "poster_file": poster_file,
                "poster_path": str(poster_path),
                "index_path": str(out_dir / "index.html"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AI导购 CLI 入口

跨平台统一入口脚本，自动检测并安装依赖，无需依赖 uv。
在 Windows / macOS / Linux 上均可直接使用 python 运行。

使用方式：
  python scripts/cli.py try-on <command> [options]
  python scripts/cli.py qrcode [options]

示例：
  python scripts/cli.py try-on run --corp-id xxx --name "白衬衫" ...
  python scripts/cli.py try-on init --corp-id xxx
  python scripts/cli.py qrcode --url "https://..." --output qr.png
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

REQUIRED_PACKAGES = {
    "qrcode": "qrcode>=7.4.2",
    "PIL": "pillow>=10.0.0",
}

SCRIPT_MAP = {
    "try-on": SCRIPTS_DIR / "try_on_cli.py",
    "qrcode": SCRIPTS_DIR / "gen_qrcode.py",
    "style-note": SCRIPTS_DIR / "style_note_generator.py",
}


def ensure_dependencies() -> None:
    """检测并自动安装缺失的 Python 依赖包。"""
    missing_packages = []
    for import_name, install_spec in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(install_spec)

    if not missing_packages:
        return

    print(f"⏳ 正在安装缺失的依赖: {', '.join(missing_packages)}", flush=True)
    install_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet"] + missing_packages,
    )
    if install_result.returncode != 0:
        print("❌ 依赖安装失败，请手动运行以下命令安装：", file=sys.stderr, flush=True)
        print(f"   {sys.executable} -m pip install {' '.join(missing_packages)}", file=sys.stderr, flush=True)
        sys.exit(1)
    print("✅ 依赖安装完成", flush=True)


def main() -> None:
    ensure_dependencies()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: python scripts/cli.py <script> [args...]")
        print()
        print("可用脚本:")
        print("  try-on      AI导购 CLI（子命令: init / upload / run / store-update / sku-source / orders-list / order-update-status）")
        print("              store-update 支持参数: --shop-name --wechat --shop-address --slogan --shop-image-url --shop-video-url --shop-logo-url")
        print("              sku-source   支持参数: --aitable-url --source (mongodb/aitable)")
        print("              orders-list  无额外参数，返回当前店铺所有订单")
        print("              order-update-status 支持参数: --order-id --status (pending/confirmed/shipping/completed/cancelled)")
        print("  qrcode      二维码生成")
        print("  style-note  穿搭笔记素材收集（唤起H5页面选择衣服和填写素材）")
        print()
        print("示例:")
        print("  python scripts/cli.py try-on run --corp-id xxx --name '白衬衫' ...")
        print("  python scripts/cli.py qrcode --url 'https://...' --output qr.png")
        sys.exit(0 if sys.argv[1:] else 2)

    script_name = sys.argv[1]
    forward_args = sys.argv[2:]

    target_script = SCRIPT_MAP.get(script_name)
    if target_script is None:
        print(f"❌ 未知脚本: {script_name!r}", file=sys.stderr, flush=True)
        print(f"   可用脚本: {', '.join(SCRIPT_MAP.keys())}", file=sys.stderr, flush=True)
        sys.exit(2)

    if not target_script.exists():
        print(f"❌ 脚本文件不存在: {target_script}", file=sys.stderr, flush=True)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(target_script)] + forward_args,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

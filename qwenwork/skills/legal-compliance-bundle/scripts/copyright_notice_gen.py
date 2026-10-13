#!/usr/bin/env python3
"""
copyright_notice_gen.py — 版权声明生成 (Skill #29)
生成版权声明/许可协议文本。

用法: python copyright_notice_gen.py --owner "某某公司" --type mit|apache|proprietary --year 2026
"""

import sys
from datetime import datetime

LICENSES = {
    "mit": {
        "name": "MIT License",
        "template": """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
    },
    "apache2": {
        "name": "Apache License 2.0",
        "template": """Copyright {year} {owner}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
    },
    "proprietary": {
        "name": "版权所有（闭源）",
        "template": """版权所有 © {year} {owner}

本软件/作品的所有权利保留。未经版权所有者书面许可，任何人不得以任何形式
（包括但不限于复制、修改、传播、发布、展示、表演、分发、许可或销售）
使用本软件/作品的任何部分。

侵权者将依法追究法律责任，包括但不限于停止侵害、消除影响、赔礼道歉、
赔偿损失等民事责任。"""
    },
    "gpl3": {
        "name": "GNU General Public License v3.0",
        "template": """Copyright (C) {year} {owner}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>."""
    }
}


def generate_notice(owner: str, license_type: str = "mit", year: int = None) -> str:
    """生成版权声明"""
    year = year or datetime.now().year
    lic = LICENSES.get(license_type)
    if not lic:
        return f"未知许可证类型: {license_type}\n\n可选类型: {', '.join(LICENSES.keys())}"

    report = f"# 版权声明\n\n"
    report += f"**版权所有者**: {owner}\n"
    report += f"**许可证类型**: {lic['name']}\n"
    report += f"**年份**: {year}\n\n"
    report += "---\n\n"
    report += f"## 许可证全文\n\n```\n{lic['template'].format(year=year, owner=owner)}\n```\n\n"
    report += "---\n\n"
    report += "## 📋 使用说明\n\n"
    report += f"- 将上述许可证文本放入项目根目录的 LICENSE 文件中\n"
    report += f"- 在源代码文件头部添加简短版权声明\n"
    report += f"- 中国法律下，著作权自作品完成时自动产生，但明确声明有助于维权\n"

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="版权声明生成")
    parser.add_argument("--owner", required=True, help="版权所有者")
    parser.add_argument("--type", default="mit", choices=list(LICENSES.keys()))
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    result = generate_notice(args.owner, args.type, args.year)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 已保存至: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()

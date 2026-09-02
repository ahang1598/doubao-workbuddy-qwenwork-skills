#!/usr/bin/env python3
"""文件上传 - LinkFox Skill
把一个或多个本地文件上传到阿里云 OSS，返回可公开访问的 HTTPS URL。

底层走 ../../_shared/linkfox_paths 的 get_sts_voucher() + upload_file()：
  - 自动获取 STS 临时上传凭证（POST /oss/getStsVoucherByAPI）
  - 上传后把 URL 登记进会话 _meta.json（deliverables）
  - 校验文件大小 / 类型是否在 OSS 允许范围

Usage:
  python file_upload.py <local_path> [<local_path> ...]

输出：JSON 数组，每个元素是成功结果 {url,path,name,size,ext,localPath} 或失败项 {error,input,message}。
     其中 localPath 是本地文件绝对路径。JSON 之后再为每个成功项打印两行：
     "Saved full response: <公开URL> (<size> bytes)"，供 ACP 识别产出文件；
     "Uploaded <本地绝对路径> -> <公开URL>"，方便控制台/前端识别。
任一文件失败时进程以非零码退出（成功项仍会输出）。
"""

import json
import os
import sys


def _paths():
    """通过 ../../_shared 导入共享 linkfox_paths（装载后 _shared 与 skill 同级）。"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_shared"))
    import linkfox_paths
    return linkfox_paths


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: file_upload.py <local_path> [<local_path> ...]", file=sys.stderr)
        sys.exit(1)

    lp = _paths()
    results = []
    voucher = None          # 复用同一份 STS 凭证，避免每个文件都取一次
    had_error = False

    for path in args:
        if not os.path.isfile(path):
            results.append({"error": True, "input": path, "message": "文件不存在"})
            had_error = True
            continue
        try:
            if voucher is None:
                voucher = lp.get_sts_voucher()
            res = lp.upload_file(path, voucher=voucher)
            res["localPath"] = os.path.abspath(path)   # 本地文件绝对路径
            results.append(res)
        except Exception as e:
            # 凭证可能过期/失效，下个文件重新获取
            voucher = None
            results.append({"error": True, "input": path, "message": str(e)})
            had_error = True

    print(json.dumps(results, ensure_ascii=False, indent=2))
    for r in results:
        if not r.get("error"):
            print(f"Saved full response: {r['url']} ({r['size']} bytes)")
            print(f"Uploaded {r['localPath']} -> {r['url']}")
    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()

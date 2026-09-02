#!/usr/bin/env python3
"""
腾讯云知识引擎文档解析脚本（COS 上传 + SSE 流式响应）。

能力：
1) 将本地文件上传到 COS 临时存储
2) 调用 ReconstructDocumentSSE 接口，流式接收解析进度
3) 下载返回的结果 zip 到本地
4) 清理 COS 临时文件

依赖：
    pip install tencentcloud-sdk-python>=3.0.1334 cos-python-sdk-v5>=1.9.35 requests

配置来源（从 .env）：
    TENCENT_SECRET_ID / TENCENT_SECRET_KEY / TENCENT_REGION
    TENCENT_COS_REGION / TENCENT_COS_BUCKET

参考：
    https://cloud.tencent.com/document/product/1772/115340

安装为库：
    pip install -e .  # 从本地安装
    from tencent_doc_parser import DocumentProcessor  # 作为库使用
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, Optional

import requests
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.lkeap.v20240522 import lkeap_client, models

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
try:
    import paths as _PATHS  # type: ignore
except ImportError:
    _repo_scripts = _SCRIPT_DIR.parent.parent.parent / "scripts"
    if _repo_scripts.is_dir() and str(_repo_scripts) not in sys.path:
        sys.path.insert(0, str(_repo_scripts))
    import paths as _PATHS  # type: ignore


# 支持的文件类型映射
SUPPORTED_FILE_TYPES = {
    "pdf": "PDF", "doc": "DOC", "docx": "DOCX", "ppt": "PPT", "pptx": "PPTX",
    "md": "MD", "txt": "TXT", "xls": "XLS", "xlsx": "XLSX", "csv": "CSV",
    "png": "PNG", "jpg": "JPG", "jpeg": "JPEG", "bmp": "BMP", "gif": "GIF",
    "webp": "WEBP", "heic": "HEIC", "tiff": "TIFF",
}

# 文件大小限制
FILE_SIZE_LIMITS = {
    "PDF": 100 * 1024 * 1024, "DOC": 100 * 1024 * 1024, "DOCX": 100 * 1024 * 1024,
    "PPT": 100 * 1024 * 1024, "PPTX": 100 * 1024 * 1024,
    "MD": 10 * 1024 * 1024, "TXT": 10 * 1024 * 1024,
    "XLS": 10 * 1024 * 1024, "XLSX": 10 * 1024 * 1024, "CSV": 10 * 1024 * 1024,
    "DEFAULT": 20 * 1024 * 1024,
}


def _load_dotenv(env_path: pathlib.Path) -> Dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f".env 文件不存在: {env_path}")

    env_map: Dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key.strip()] = value.strip().strip('"').strip("'")
    return env_map


def _require(env: Dict[str, str], key: str) -> str:
    value = env.get(key) or os.getenv(key)
    if not value:
        raise ValueError(f"缺少必要配置: {key}")
    return value


class DocumentProcessor:
    """文档解析处理器：COS 上传 + SSE 流式解析"""

    def __init__(self, secret_id: str, secret_key: str, region: str,
                 cos_region: str, cos_bucket: str):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.cos_region = cos_region
        self.cos_bucket = cos_bucket

        cos_config = CosConfig(
            Region=cos_region,
            SecretId=secret_id,
            SecretKey=secret_key,
        )
        self.cos_client = CosS3Client(cos_config)

    def _get_file_type(self, file_path: str) -> tuple[str, str]:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        file_type = SUPPORTED_FILE_TYPES.get(ext)
        if not file_type:
            raise ValueError(f"不支持的文件类型: {ext}")
        return file_type, ext

    def _check_file_size(self, file_path: str, file_type: str) -> None:
        size = os.path.getsize(file_path)
        limit = FILE_SIZE_LIMITS.get(file_type, FILE_SIZE_LIMITS["DEFAULT"])
        if size > limit:
            raise ValueError(
                f"文件大小超过限制: {size/1024/1024:.2f}MB > {limit/1024/1024}MB"
            )

    def upload_to_cos(self, file_content: bytes, file_extension: str) -> Dict[str, str]:
        timestamp = int(time.time())
        file_name = f"temp_doc_{timestamp}.{file_extension}"

        self.cos_client.put_object(
            Bucket=self.cos_bucket,
            Body=file_content,
            Key=file_name,
            EnableMD5=False,
        )
        file_url = f"https://{self.cos_bucket}.cos.{self.cos_region}.myqcloud.com/{file_name}"
        print(f"[cos] 上传成功: {file_url}", flush=True)
        return {"url": file_url, "key": file_name}

    def delete_from_cos(self, file_key: str) -> bool:
        try:
            self.cos_client.delete_object(Bucket=self.cos_bucket, Key=file_key)
            print(f"[cos] 已删除临时文件: {file_key}", flush=True)
            return True
        except Exception as e:
            print(f"[cos] 删除失败: {e}", flush=True)
            return False

    def _create_lkeap_client(self) -> lkeap_client.LkeapClient:
        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile(endpoint="lkeap.tencentcloudapi.com")
        http_profile.reqTimeout = 600  # 单次请求10分钟
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        return lkeap_client.LkeapClient(cred, self.region, client_profile)

    def reconstruct_document_sse(
        self,
        file_url: str,
        file_type: str,
        image_response_type: str = "0",
    ):
        """调用 SSE 接口解析文档，返回流式事件"""
        client = self._create_lkeap_client()

        params = {
            "FileType": file_type,
            "FileUrl": file_url,
            "EnableOCR": True,
            "Config": {
                "MarkdownImageResponseType": image_response_type,
            },
        }

        req = models.ReconstructDocumentSSERequest()
        req.from_json_string(json.dumps(params))
        return client.ReconstructDocumentSSE(req)

    def parse_document(
        self,
        file_path: str,
        output_zip: str,
        image_response_type: str = "0",
    ) -> bool:
        """解析单个文档，返回结果zip路径"""
        print(f"[parse] 开始解析: {file_path}", flush=True)
        cos_file: Optional[Dict[str, str]] = None
        total_start = time.time()

        try:
            # 检查文件
            file_type, file_extension = self._get_file_type(file_path)
            self._check_file_size(file_path, file_type)

            # 读取本地文件
            with open(file_path, "rb") as f:
                file_content = f.read()
            print(
                f"[input] size={len(file_content)/1024/1024:.2f}MiB "
                f"type={file_type}",
                flush=True,
            )

            # 上传到 COS
            cos_file = self.upload_to_cos(file_content, file_extension)

            # 调用 SSE 解析
            print("[api] 发起 ReconstructDocumentSSE 请求...", flush=True)
            events = self.reconstruct_document_sse(
                cos_file["url"], file_type, image_response_type
            )

            # 处理 SSE 事件流
            final_result_url: Optional[str] = None
            event_count = 0
            last_log_time = time.time()

            for event in events:
                event_count += 1
                if isinstance(event, dict) and "data" in event:
                    try:
                        data = json.loads(event["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue

                    response_type = data.get("ResponseType")
                    # 定期打印进度
                    now = time.time()
                    if now - last_log_time >= 3:
                        elapsed = now - total_start
                        progress = data.get("Progress", "")
                        print(
                            f"[sse] events={event_count} type={response_type} "
                            f"progress={progress} elapsed={elapsed:.1f}s",
                            flush=True,
                        )
                        last_log_time = now

                    # TASK_RSP 或 "2" 表示最终结果
                    if response_type in ("TASK_RSP", "2"):
                        final_result_url = data.get("DocumentRecognizeResultUrl")
                        usage = data.get("Usage", {})
                        failed_pages = data.get("FailedPages", [])
                        print(
                            f"[sse] 解析完成: usage={usage} "
                            f"failed_pages={len(failed_pages)}",
                            flush=True,
                        )
                        break

            if not final_result_url:
                raise RuntimeError(f"未获取到解析结果URL (共收到 {event_count} 个事件)")

            # 下载结果 ZIP
            print(f"[download] 开始下载结果包...", flush=True)
            output_path = pathlib.Path(output_zip)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            resp = requests.get(final_result_url, timeout=180, stream=True)
            if resp.status_code != 200:
                raise RuntimeError(f"下载结果文件失败: HTTP {resp.status_code}")

            total_bytes = 0
            with output_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

            total_elapsed = time.time() - total_start
            print(
                f"[done] result_zip={output_path.resolve()} "
                f"size={total_bytes/1024/1024:.2f}MiB "
                f"total_elapsed={total_elapsed:.1f}s",
                flush=True,
            )
            return True

        except Exception as e:
            print(f"[error] 解析失败: {e}", flush=True)
            raise
        finally:
            if cos_file:
                self.delete_from_cos(cos_file["key"])


def build_args() -> argparse.Namespace:
    # 默认 .env 路径：本 Skill 目录下的 .env（与脚本就近放置，便于维护）
    # 注意：.env 不纳入共享 Home，仍保留在 Skill1 目录内
    default_env = pathlib.Path(__file__).resolve().parent.parent / ".env"

    parser = argparse.ArgumentParser(
        description="腾讯云知识引擎文档解析（COS + SSE）"
    )
    parser.add_argument(
        "--env-file",
        default=str(default_env),
        help=f".env 文件路径（默认 {default_env}）",
    )
    parser.add_argument("--file-type", required=True, help="文件类型：PDF/DOCX/PPTX 等")
    parser.add_argument("--file-path", required=True, help="本地文件路径")
    parser.add_argument(
        "--output-zip",
        default="",
        help="解析结果 zip 输出路径；如不传且同时提供 --bank-short/--period，则自动落到 extracted_text/<bank>/<bank>_<period>_docparse.zip",
    )
    parser.add_argument(
        "--bank-short",
        default="",
        help="银行中文简称（如 某某 / 某甲）；与 --period 一起用于推导标准输出路径",
    )
    parser.add_argument(
        "--period",
        default="",
        help="报告期（如 2025年度 / 2025H1 / 2025Q3）；与 --bank-short 一起用于推导标准输出路径",
    )
    parser.add_argument(
        "--image-response-type",
        choices=["0", "1"],
        default="0",
        help="图片返回形式：0-链接(默认), 1-文本内容",
    )
    return parser.parse_args()


def resolve_output_zip(output_zip: str, bank_short: str, period: str) -> pathlib.Path:
    if output_zip:
        return pathlib.Path(output_zip).expanduser().resolve()
    if bank_short and period:
        return (_PATHS.EXTRACTED_TEXT_DIR / bank_short / f"{bank_short}_{period}_docparse.zip").resolve()
    return (_PATHS.EXTRACTED_TEXT_DIR / "_tmp" / "tencent_doc_parse_result.zip").resolve()


def main() -> None:
    args = build_args()
    env = _load_dotenv(pathlib.Path(args.env_file))
    output_zip = resolve_output_zip(args.output_zip, args.bank_short.strip(), args.period.strip())

    processor = DocumentProcessor(
        secret_id=_require(env, "TENCENT_SECRET_ID"),
        secret_key=_require(env, "TENCENT_SECRET_KEY"),
        region=_require(env, "TENCENT_REGION"),
        cos_region=_require(env, "TENCENT_COS_REGION"),
        cos_bucket=_require(env, "TENCENT_COS_BUCKET"),
    )

    processor.parse_document(
        file_path=args.file_path,
        output_zip=str(output_zip),
        image_response_type=args.image_response_type,
    )


if __name__ == "__main__":
    main()

"""智能图片压缩模块 —— 解决钉钉移动端 HTML 渲染 2MB 阈值限制。

核心策略：按原始大小比例动态分配压缩配额，避免小图过度压缩、大图质量不足。

依赖：Pillow (PIL)
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_TOTAL_BUDGET_KB = 1900.0  # 1.9 MB
DEFAULT_TEXT_BUFFER_KB = 400.0    # 预留文字+CSS空间
DEFAULT_MIN_QUALITY = 30
DEFAULT_MAX_QUALITY = 95
DEFAULT_MIN_TARGET_KB = 50.0


@dataclass
class CompressionTarget:
    """单张图片的压缩目标与结果。"""

    resource_id: str
    original_data: bytes
    original_size_kb: float
    target_size_kb: float = 0.0
    quality: int = 65
    compressed_data: bytes = field(default=b"", repr=False)
    compressed_size_kb: float = 0.0


def compress_jpeg_image(
    image_data: bytes,
    quality: int = 65,
    optimize: bool = True,
    max_dimension: int = 0,
) -> Tuple[bytes, float]:
    """压缩单张图片为 JPEG 格式。

    Args:
        image_data: 原始图片二进制数据（支持 JPEG/PNG/WebP 等 PIL 可读格式）
        quality: JPEG 质量参数 (1-100)
        optimize: 是否启用 Huffman 优化
        max_dimension: 最大边长限制（像素），0 表示不缩放

    Returns:
        (compressed_data, compressed_size_kb)
    """
    from PIL import Image

    img = Image.open(io.BytesIO(image_data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # 分辨率缩放（保持比例）
    if max_dimension > 0:
        w, h = img.size
        if w > max_dimension or h > max_dimension:
            ratio = min(max_dimension / w, max_dimension / h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=optimize)
    compressed = output.getvalue()
    return compressed, len(compressed) / 1024


def estimate_quality_for_size(
    image_data: bytes,
    target_size_kb: float,
    min_quality: int = DEFAULT_MIN_QUALITY,
    max_quality: int = DEFAULT_MAX_QUALITY,
    max_iterations: int = 5,
) -> int:
    """通过二分法估算达到目标大小所需的 JPEG 质量参数。

    Args:
        image_data: 原始图片数据
        target_size_kb: 目标大小 (KB)
        min_quality: 搜索下界
        max_quality: 搜索上界
        max_iterations: 最大迭代次数

    Returns:
        最接近目标大小的质量参数
    """
    # 快速基准测试
    _, test_size = compress_jpeg_image(image_data, quality=65)

    # 已经接近目标 (误差 < 20 KB)
    if abs(test_size - target_size_kb) < 20:
        return 65

    # 确定搜索方向
    if test_size > target_size_kb:
        low, high = min_quality, 64
    else:
        low, high = 66, max_quality

    best_quality = 65
    best_diff = abs(test_size - target_size_kb)

    for _ in range(max_iterations):
        if low > high:
            break
        mid = (low + high) // 2
        _, size = compress_jpeg_image(image_data, quality=mid)
        diff = abs(size - target_size_kb)

        if diff < best_diff:
            best_diff = diff
            best_quality = mid

        if size > target_size_kb:
            high = mid - 1
        else:
            low = mid + 1

        # 足够接近，提前终止
        if diff < 10:
            break

    return best_quality


def calculate_compression_targets(
    images: Dict[str, bytes],
    total_budget_kb: float = DEFAULT_TOTAL_BUDGET_KB,
    text_buffer_kb: float = DEFAULT_TEXT_BUFFER_KB,
    min_quality: int = DEFAULT_MIN_QUALITY,
    max_quality: int = DEFAULT_MAX_QUALITY,
    prevent_enlargement: bool = True,
    min_target_size_kb: float = DEFAULT_MIN_TARGET_KB,
) -> List[CompressionTarget]:
    """核心算法：根据原始大小比例动态分配压缩配额。

    Args:
        images: resourceId → 原始图片数据
        total_budget_kb: HTML 文件总预算 (KB)
        text_buffer_kb: 预留文字+CSS空间 (KB)
        min_quality: 最低质量参数
        max_quality: 最高质量参数
        prevent_enlargement: 禁止压缩后变大
        min_target_size_kb: 单张图片最小目标大小 (KB)

    Returns:
        CompressionTarget 列表
    """
    if not images:
        return []

    # 步骤 1: 计算图片可用预算
    image_budget_kb = total_budget_kb - text_buffer_kb
    if image_budget_kb <= 0:
        logger.warning(
            "预算不足: 总预算 %.0f KB - 文字缓冲 %.0f KB = %.0f KB",
            total_budget_kb, text_buffer_kb, image_budget_kb,
        )
        image_budget_kb = total_budget_kb * 0.8  # 降级：用 80% 做图片

    # 步骤 2: 计算原始总大小
    total_original_kb = sum(len(data) / 1024 for data in images.values())
    if total_original_kb == 0:
        return []

    # 如果原始总大小已经在预算内，无需压缩
    if total_original_kb <= image_budget_kb:
        targets = []
        for res_id, data in images.items():
            original_kb = len(data) / 1024
            targets.append(CompressionTarget(
                resource_id=res_id,
                original_data=data,
                original_size_kb=original_kb,
                target_size_kb=original_kb,
                quality=max_quality,  # 不压缩，保持高质量
            ))
        return targets

    # 步骤 3: 按比例分配目标大小
    targets: List[CompressionTarget] = []
    for res_id, data in images.items():
        original_kb = len(data) / 1024
        ratio = original_kb / total_original_kb
        target_kb = image_budget_kb * ratio

        # 保护：禁止越压越大
        if prevent_enlargement and target_kb > original_kb:
            target_kb = original_kb

        # 保护：最小尺寸限制
        if target_kb < min_target_size_kb:
            target_kb = min_target_size_kb

        targets.append(CompressionTarget(
            resource_id=res_id,
            original_data=data,
            original_size_kb=original_kb,
            target_size_kb=target_kb,
        ))

    # 步骤 4: 估算每张图的质量参数
    for target in targets:
        # 如果目标大小 >= 原始大小，不需要压缩
        if target.target_size_kb >= target.original_size_kb:
            target.quality = max_quality
        else:
            target.quality = estimate_quality_for_size(
                target.original_data,
                target.target_size_kb,
                min_quality=min_quality,
                max_quality=max_quality,
            )

    return targets


def execute_compression(
    targets: List[CompressionTarget],
) -> List[CompressionTarget]:
    """执行压缩并填充 compressed_data / compressed_size_kb。

    对于不需要压缩的图片（quality >= 95），直接保留原始数据。
    """
    for target in targets:
        if target.quality >= 95 and target.target_size_kb >= target.original_size_kb:
            # 无需压缩
            target.compressed_data = target.original_data
            target.compressed_size_kb = target.original_size_kb
        else:
            compressed, size_kb = compress_jpeg_image(
                target.original_data, quality=target.quality
            )
            # 防止越压越大
            if size_kb > target.original_size_kb:
                target.compressed_data = target.original_data
                target.compressed_size_kb = target.original_size_kb
                target.quality = -1  # 标记为未压缩
            else:
                target.compressed_data = compressed
                target.compressed_size_kb = size_kb

    return targets


def smart_compress(
    images: Dict[str, bytes],
    total_budget_kb: float = DEFAULT_TOTAL_BUDGET_KB,
    text_buffer_kb: float = DEFAULT_TEXT_BUFFER_KB,
    min_quality: int = DEFAULT_MIN_QUALITY,
    max_quality: int = DEFAULT_MAX_QUALITY,
    prevent_enlargement: bool = True,
    min_target_size_kb: float = DEFAULT_MIN_TARGET_KB,
    max_retries: int = 2,
    quality_decay: float = 0.85,
) -> List[CompressionTarget]:
    """一站式接口：计算目标 + 执行压缩 + 自适应降级。

    如果首次压缩后总大小仍超出预算，自动降低质量重试。

    Args:
        images: resourceId → 原始数据
        total_budget_kb: 文件总预算
        text_buffer_kb: 文字缓冲
        min_quality/max_quality: 质量范围
        prevent_enlargement: 禁止越压越大
        min_target_size_kb: 单张最小目标
        max_retries: 降级重试次数
        quality_decay: 每次重试质量衰减系数

    Returns:
        压缩完成的 CompressionTarget 列表
    """
    image_budget_kb = total_budget_kb - text_buffer_kb
    current_min_q = min_quality
    current_max_q = max_quality

    for attempt in range(max_retries + 1):
        targets = calculate_compression_targets(
            images,
            total_budget_kb=total_budget_kb,
            text_buffer_kb=text_buffer_kb,
            min_quality=current_min_q,
            max_quality=current_max_q,
            prevent_enlargement=prevent_enlargement,
            min_target_size_kb=min_target_size_kb,
        )
        targets = execute_compression(targets)

        total_compressed = sum(t.compressed_size_kb for t in targets)
        if total_compressed <= image_budget_kb:
            return targets

        # 自适应降级：降低质量
        if attempt < max_retries:
            current_max_q = int(current_max_q * quality_decay)
            current_min_q = max(20, int(current_min_q * quality_decay))
            logger.info(
                "压缩后 %.0f KB 仍超预算 %.0f KB，降级重试 (quality %d-%d)",
                total_compressed, image_budget_kb, current_min_q, current_max_q,
            )

    # 最终降级：质量降级无效时，通过缩小分辨率强制压到预算内
    total_compressed = sum(t.compressed_size_kb for t in targets)
    if total_compressed > image_budget_kb:
        logger.info(
            "质量降级后 %.0f KB 仍超预算 %.0f KB，启用分辨率缩放降级",
            total_compressed, image_budget_kb,
        )
        targets = _resize_fallback(targets, image_budget_kb, min_quality)

    return targets


def _resize_fallback(
    targets: List[CompressionTarget],
    budget_kb: float,
    min_quality: int,
) -> List[CompressionTarget]:
    """最终降级：逐步缩小分辨率直到总大小在预算内。

    从 max_dimension=1200 开始，每轮缩小 200px，最低 600px。
    """
    dimensions = [1200, 1000, 800, 600]

    for max_dim in dimensions:
        for target in targets:
            compressed, size_kb = compress_jpeg_image(
                target.original_data,
                quality=max(min_quality, target.quality),
                max_dimension=max_dim,
            )
            if size_kb < target.compressed_size_kb:
                target.compressed_data = compressed
                target.compressed_size_kb = size_kb

        total = sum(t.compressed_size_kb for t in targets)
        if total <= budget_kb:
            logger.info("分辨率降级成功 (max_dim=%d): %.0f KB", max_dim, total)
            return targets

    return targets

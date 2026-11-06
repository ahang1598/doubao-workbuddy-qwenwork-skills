#!/usr/bin/env python3
"""
根据任务ID查询并下载视频生成结果

使用示例:
  python3 query_video_task.py --task-id your_task_id
  python3 query_video_task.py --task-id your_task_id --output /path/to/video.mp4
"""

import os
import sys
import argparse

# 导入 generate_video 中的函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_video import query_video_generation_task
from config import Config


def main():
    parser = argparse.ArgumentParser(
        description="根据任务ID查询并下载视频生成结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查询并下载指定任务ID的视频
  python3 query_video_task.py --task-id your_task_id

  # 指定输出文件路径
  python3 query_video_task.py --task-id your_task_id --output /path/to/video.mp4

  # 自定义轮询间隔和超时时间
  python3 query_video_task.py --task-id your_task_id --poll-interval 5 --timeout 600
        """,
    )

    parser.add_argument(
        "--task-id",
        required=True,
        help="视频生成任务ID",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出视频文件路径（可选，默认保存到 ~/.openclaw/workspace/generated-videos/）",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="轮询查询间隔时间（秒，默认10秒）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1200,
        help="任务超时时间（秒，默认1200秒/20分钟）",
    )

    args = parser.parse_args()

    # 显示任务信息
    print(f"\n{'='*60}")
    print(f"🔍 视频任务查询工具")
    print(f"{'='*60}")
    print(f"任务ID: {args.task_id}")
    if args.output:
        print(f"输出路径: {args.output}")
    else:
        print(f"输出路径: 默认路径（~/.openclaw/workspace/generated-videos/）")
    print(f"轮询间隔: {args.poll_interval_s if hasattr(args, 'poll_interval_s') else args.poll_interval}秒")
    print(f"超时时间: {args.timeout}秒")
    print(f"{'='*60}\n")

    try:
        # 调用 generate_video.py 中的查询方法
        cfg = Config.load()
        result = query_video_generation_task(
            task_id=args.task_id,
            output_file=args.output,
            poll_interval_s=args.poll_interval,
            cfg=cfg,
            max_wait_time=args.timeout,
        )

        # 处理结果
        if result and result.get("video_path"):
            print(f"\n{'='*60}")
            print(f"✅ 视频下载成功!")
            print(f"{'='*60}")
            print(f"📁 文件路径: {result['video_path']}")
            print(f"🆔 任务ID: {result['task_id']}")
            if result.get('video_url'):
                print(f"🔗 视频URL: {result['video_url']}")
            print(f"{'='*60}\n")
            sys.exit(0)
        else:
            print(f"\n{'='*60}")
            print(f"❌ 视频下载失败")
            print(f"{'='*60}")
            print(f"🆔 任务ID: {args.task_id}")
            print(f"原因: 任务未成功返回视频文件")
            print(f"{'='*60}\n")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ 发生错误")
        print(f"{'='*60}")
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Join prepared, equal-width image segments vertically without resizing."""
import argparse
import json
from pathlib import Path
import sys


def stitch(paths, output):
    from PIL import Image
    if len(paths) < 2:
        raise ValueError('At least two segments are required')
    output = Path(output)
    if output.suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    images = []
    try:
        for path in paths:
            with Image.open(path) as source:
                if getattr(source, 'n_frames', 1) != 1:
                    raise ValueError(f'Animated inputs are not supported: {path}')
                if source.getexif().get(274, 1) != 1:
                    raise ValueError(f'Normalize EXIF orientation before stitching: {path}')
                source.load()
                images.append(source.convert('RGBA'))
        width = images[0].width
        if any(im.width != width for im in images):
            raise ValueError('Segment widths differ; prepare equal-width inputs without stretching')
        height = sum(im.height for im in images)
        if width * height > Image.MAX_IMAGE_PIXELS:
            raise ValueError('Combined image exceeds Pillow pixel limit; use an appropriate large-image tool')
        canvas = Image.new('RGBA', (width, height))
        try:
            y = 0
            for im in images:
                canvas.paste(im, (0, y))
                y += im.height
            # Exclusive creation prevents accidental overwrite, including a race.
            with output.open('xb') as stream:
                canvas.save(stream, format='PNG')
        finally:
            canvas.close()
        return {'output': str(output.resolve()), 'width': width, 'height': height,
                'segments': [str(Path(p).resolve()) for p in paths],
                'visual_validation': 'not_performed'}
    finally:
        for im in images:
            im.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('segments', nargs='+')
    args = parser.parse_args()
    try:
        result = stitch(args.segments, args.output)
    except (ImportError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

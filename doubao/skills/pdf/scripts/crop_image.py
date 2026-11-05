"""Crop a rectangular pixel region from an image with Pillow."""

import argparse

from PIL import Image


def crop_image(input_path, output_path, box):
    """Crop a left-top-right-bottom pixel box."""
    with Image.open(input_path) as image:
        image.crop(box).save(output_path)

    print(f"Saved crop to {output_path}")


def main():
    """Parse command-line arguments and crop the requested image region."""
    parser = argparse.ArgumentParser(
        description="Crop an image using left-top-right-bottom pixel coordinates."
    )
    parser.add_argument("input_image")
    parser.add_argument("output_image")
    parser.add_argument("left", type=int)
    parser.add_argument("top", type=int)
    parser.add_argument("right", type=int)
    parser.add_argument("bottom", type=int)
    args = parser.parse_args()

    crop_image(
        args.input_image,
        args.output_image,
        (args.left, args.top, args.right, args.bottom),
    )


if __name__ == "__main__":
    main()

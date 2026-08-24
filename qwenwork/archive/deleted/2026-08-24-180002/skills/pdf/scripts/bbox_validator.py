"""CLI: validate annotation bounding boxes before stamping text.

Flags two classes of problems in a ``fields.json`` file:
1. label/entry boxes that overlap another box on the same page
2. entry boxes shorter than the font size they must hold

Checks abort once 20 messages accumulate to keep output readable.

Usage: python bbox_validator.py [fields.json]
"""

from dataclasses import dataclass
import json
import sys

_MESSAGE_CAP = 20
_DEFAULT_FONT_SIZE = 14


@dataclass
class Box:
    rect: list
    role: str  # "label" or "entry"
    field: dict


def _overlaps(a, b) -> bool:
    """True when rectangles ``a`` and ``b`` share any area."""
    apart_x = a[0] >= b[2] or a[2] <= b[0]
    apart_y = a[1] >= b[3] or a[3] <= b[1]
    return not (apart_x or apart_y)


def _flatten_boxes(form_fields):
    """Yield one Box per label rect and one per entry rect."""
    boxes = []
    for field in form_fields:
        boxes.append(Box(field["label_bounding_box"], "label", field))
        boxes.append(Box(field["entry_bounding_box"], "entry", field))
    return boxes


def audit_boxes(fields_json_stream):
    """Return a list of human-readable audit messages for the given stream."""
    document = json.load(fields_json_stream)
    boxes = _flatten_boxes(document["form_fields"])

    messages = [f"Read {len(document['form_fields'])} fields"]
    healthy = True

    def capped():
        if len(messages) >= _MESSAGE_CAP:
            messages.append("Aborting further checks; fix bounding boxes and try again")
            return True
        return False

    for i, current in enumerate(boxes):
        for other in boxes[i + 1:]:
            same_page = current.field["page_number"] == other.field["page_number"]
            if same_page and _overlaps(current.rect, other.rect):
                healthy = False
                if current.field is other.field:
                    messages.append(
                        "FAILURE: intersection between label and entry bounding "
                        f"boxes for `{current.field['description']}` "
                        f"({current.rect}, {other.rect})"
                    )
                else:
                    messages.append(
                        f"FAILURE: intersection between {current.role} bounding box "
                        f"for `{current.field['description']}` ({current.rect}) and "
                        f"{other.role} bounding box for "
                        f"`{other.field['description']}` ({other.rect})"
                    )
                if capped():
                    return messages

        if current.role == "entry" and "entry_text" in current.field:
            font_size = current.field["entry_text"].get("font_size", _DEFAULT_FONT_SIZE)
            entry_height = current.rect[3] - current.rect[1]
            if entry_height < font_size:
                healthy = False
                messages.append(
                    f"FAILURE: entry bounding box height ({entry_height}) for "
                    f"`{current.field['description']}` is too short for the text "
                    f"content (font size: {font_size}). Increase the box height or "
                    "decrease the font size."
                )
                if capped():
                    return messages

    if healthy:
        messages.append("SUCCESS: All bounding boxes are valid")
    return messages


def main(argv):
    if len(argv) != 2:
        print("Usage: bbox_validator.py [fields.json]")
        sys.exit(1)
    with open(argv[1]) as handle:
        for message in audit_boxes(handle):
            print(message)


if __name__ == "__main__":
    main(sys.argv)

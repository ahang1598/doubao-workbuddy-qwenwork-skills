"""Markdown AIGC metadata and visible footer, preserving existing frontmatter."""
import json
import os
import re
import tempfile

from decorators.common import get_aigc_signature, is_aigc_complete, canonical_signature, AIGC_FIELDS

TEXT = "内容由AI生成"
FRONTMATTER = re.compile(r"\A(?:\ufeff)?---[^\S\n]*\r?\n(.*?)\r?\n---[^\S\n]*(?:\r?\n|$)", re.DOTALL)
AIGC_BLOCK = re.compile(r"(?m)^AIGC:[^\S\n]*(?:\r?\n(?:[ \t]+[^\n]*|[ \t]*))*(?:\r?\n|$)")


class MdAigcDecorator:
    def _get_aigc_data(self, file_path):
        with open(file_path, encoding="utf-8") as source:
            text = source.read()
        front = FRONTMATTER.match(text)
        if front is None:
            return None
        blocks = list(AIGC_BLOCK.finditer(front.group(1) + "\n"))
        if len(blocks) != 1:
            return None
        block = blocks[0]
        result = {}
        for line in block.group().splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.strip().split(":", 1)
            value = value.strip()
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                value = value.strip("'\"")
            result[key] = value
        return result or None

    def decorate(self, file_path, content, add_visible_mark=True):
        with open(file_path, encoding="utf-8") as source:
            text = source.read()
        front = FRONTMATTER.match(text)
        if front and len(list(AIGC_BLOCK.finditer(front.group(1) + "\n"))) > 1:
            raise ValueError("Duplicate Markdown AIGC records; resolve provenance first")
        existing = self._get_aigc_data(file_path)
        if is_aigc_complete(existing) and all(k in existing for k in AIGC_FIELDS) and (not add_visible_mark or text.rstrip().endswith(TEXT)):
            return
        metadata = json.loads(canonical_signature(existing, content))
        front = FRONTMATTER.match(text)
        if front:
            preserved = AIGC_BLOCK.sub("", front.group(1) + "\n").rstrip("\r\n")
            body = text[front.end():]
        else:
            preserved = ""
            body = text.lstrip("\ufeff")
        block = "AIGC:\n" + "\n".join(f"  {key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items())
        header = "---\n" + (preserved + "\n" if preserved else "") + block + "\n---\n"
        marked = header + body
        if add_visible_mark and not body.rstrip().endswith(TEXT):
            marked = marked.rstrip("\r\n") + "\n\n" + TEXT + "\n"
        fd, temporary = tempfile.mkstemp(prefix=".aigc-", suffix=".md", dir=os.path.dirname(os.path.abspath(file_path)))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(marked)
            os.replace(temporary, file_path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
"""Uniform PDF read backend for the verifier CLI.

One document object exposes everything the ``pdf`` family and
``file extract-text`` need: page count, page geometry, page text, embedded
font names, image counts.

Three interchangeable backends, tried in this order:

``pymupdf`` (``import fitz``)
    Preferred. Single dependency that covers all four capabilities, and it is
    the library already present in the rollout VM image.
``pdfplumber``
    Text extraction is the strongest here; geometry and images also available.
``pypdf``
    Last resort; pure metadata walking.

Callers only see :func:`open_pdf` and the ``PdfDoc`` protocol, so adding or
reordering backends never changes subcommand output shape.
"""
from __future__ import annotations

import importlib
from typing import Any

from . import _common as C

_PDF_EXTS = (".pdf",)

# Font BaseFont substrings that indicate a CJK-capable font.
CJK_FONT_MARKERS = (
    "SimSun", "SimHei", "STSong", "STHeiti", "STKaiti", "STFangsong",
    "PingFang", "MS-", "MingLiU", "FangSong", "YaHei", "Hei", "Kai",
    "GBK", "GB2312", "Adobe-GB1", "Adobe-CNS1", "Adobe-Japan1",
    "Adobe-Korea1", "CJK", "Noto Sans CJK", "NotoSansCJK", "Source Han",
    "SourceHan", "WenQuanYi", "Droid Sans Fallback", "DroidSansFallback",
)


class PdfDoc:
    """Backend-agnostic PDF handle. Use as a context manager."""

    backend = "?"

    def __init__(self, path: str) -> None:
        self.path = path

    # -- required interface ------------------------------------------------
    @property
    def page_count(self) -> int:
        raise NotImplementedError

    def page_size(self, i: int) -> tuple[float, float]:
        """0-based page index -> (width, height) in points."""
        raise NotImplementedError

    def page_text(self, i: int) -> str:
        raise NotImplementedError

    def page_fonts(self, i: int) -> list[str]:
        """BaseFont names referenced by page ``i``. Empty list when unavailable."""
        return []

    def page_image_count(self, i: int) -> int:
        return 0

    def close(self) -> None:
        pass

    # -- shared conveniences ----------------------------------------------
    def __enter__(self) -> "PdfDoc":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def orientation(self, i: int) -> str:
        w, h = self.page_size(i)
        return "landscape" if w > h else "portrait"


class _PyMuPdfDoc(PdfDoc):
    backend = "pymupdf"

    def __init__(self, path: str, fitz: Any) -> None:
        super().__init__(path)
        self._doc = fitz.open(path)

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def _page(self, i: int):
        return self._doc.load_page(i)

    def page_size(self, i: int) -> tuple[float, float]:
        r = self._page(i).rect
        return float(r.width), float(r.height)

    def page_text(self, i: int) -> str:
        return self._page(i).get_text() or ""

    def page_fonts(self, i: int) -> list[str]:
        out: list[str] = []
        try:
            # get_fonts() rows: (xref, ext, type, basefont, name, encoding, ...)
            for row in self._page(i).get_fonts(full=True):
                if len(row) > 3 and row[3]:
                    out.append(str(row[3]))
        except Exception:
            return out
        return out

    def page_image_count(self, i: int) -> int:
        try:
            return len(self._page(i).get_images(full=True))
        except Exception:
            return 0

    def close(self) -> None:
        try:
            self._doc.close()
        except Exception:
            pass


class _PlumberDoc(PdfDoc):
    backend = "pdfplumber"

    def __init__(self, path: str, pdfplumber: Any) -> None:
        super().__init__(path)
        self._doc = pdfplumber.open(path)

    @property
    def page_count(self) -> int:
        return len(self._doc.pages)

    def page_size(self, i: int) -> tuple[float, float]:
        p = self._doc.pages[i]
        return float(p.width), float(p.height)

    def page_text(self, i: int) -> str:
        return self._doc.pages[i].extract_text() or ""

    def page_fonts(self, i: int) -> list[str]:
        try:
            return sorted({str(c.get("fontname"))
                           for c in self._doc.pages[i].chars if c.get("fontname")})
        except Exception:
            return []

    def page_image_count(self, i: int) -> int:
        try:
            return len(self._doc.pages[i].images or [])
        except Exception:
            return 0

    def close(self) -> None:
        try:
            self._doc.close()
        except Exception:
            pass


class _PyPdfDoc(PdfDoc):
    backend = "pypdf"

    def __init__(self, path: str, pypdf: Any) -> None:
        super().__init__(path)
        self._fh = open(path, "rb")
        self._doc = pypdf.PdfReader(self._fh)

    @property
    def page_count(self) -> int:
        return len(self._doc.pages)

    def page_size(self, i: int) -> tuple[float, float]:
        box = self._doc.pages[i].mediabox
        return float(box.width), float(box.height)

    def page_text(self, i: int) -> str:
        return self._doc.pages[i].extract_text() or ""

    def page_fonts(self, i: int) -> list[str]:
        out: list[str] = []
        try:
            res = self._doc.pages[i].get("/Resources")
            fonts = res.get("/Font") if hasattr(res, "get") else None
            if not fonts:
                return out
            for k in fonts.keys():
                fobj = fonts[k]
                base = fobj.get("/BaseFont") if hasattr(fobj, "get") else None
                if base:
                    out.append(str(base))
        except Exception:
            return out
        return out

    def page_image_count(self, i: int) -> int:
        try:
            res = self._doc.pages[i].get("/Resources")
            xo = res.get("/XObject") if hasattr(res, "get") else None
            if not xo:
                return 0
            n = 0
            for key in xo.keys():
                try:
                    if str(xo[key].get("/Subtype")) == "/Image":
                        n += 1
                except Exception:
                    continue
            return n
        except Exception:
            return 0

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


# Ordered (module to import, factory) pairs.
_BACKENDS: tuple[tuple[str, Any], ...] = (
    ("fitz", _PyMuPdfDoc),
    ("pdfplumber", _PlumberDoc),
    ("pypdf", _PyPdfDoc),
)

# Distribution names to suggest when nothing is importable.
_DISTS = ("pymupdf", "pdfplumber", "pypdf")


def available_backends() -> list[str]:
    """Names of PDF backends importable right now."""
    out = []
    for mod, factory in _BACKENDS:
        try:
            importlib.import_module(mod)
        except Exception:
            continue
        out.append(factory.backend)
    return out


def open_pdf(path: str) -> PdfDoc:
    """Open ``path`` with the first available backend.

    Raises ``VerifierError(FILE_NOT_FOUND | NOT_A_FILE | BAD_EXT)`` for bad
    input, ``DEP_MISSING`` when no backend is importable, and
    ``PARSE_ERROR`` when every importable backend fails to parse the file.
    """
    abs_path = C.require_file(path, _PDF_EXTS)
    parse_errors: list[str] = []
    tried_any = False
    for mod, factory in _BACKENDS:
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        tried_any = True
        try:
            doc = factory(abs_path, m)
        except Exception as e:
            parse_errors.append(f"{factory.backend}: {type(e).__name__}: {e}")
            continue
        doc.path = abs_path
        return doc
    if not tried_any:
        raise C.VerifierError(
            C.ErrCode.DEP_MISSING,
            "no PDF backend available (tried pymupdf, pdfplumber, pypdf) — "
            + C.install_hint(*_DISTS),
        )
    raise C.VerifierError(
        C.ErrCode.PARSE_ERROR,
        f"could not open {abs_path} with any available PDF backend; "
        + "; ".join(parse_errors),
    )


def is_cjk_font(name: str) -> bool:
    return any(marker in name for marker in CJK_FONT_MARKERS)

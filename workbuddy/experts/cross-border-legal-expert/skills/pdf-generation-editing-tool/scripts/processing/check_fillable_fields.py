import sys
import importlib.util


def ensure_deps():
    missing = [p for p in ("pypdf",) if importlib.util.find_spec(p) is None]
    if missing:
        sys.stderr.write("[deps] missing required package(s): "
                         + " ".join(missing)
                         + " | install manually, e.g.: pip install "
                         + " ".join(missing) + "\n")
        sys.exit(4)

ensure_deps()

from pypdf import PdfReader


# Script for Claude to run to determine whether a PDF has fillable form fields. See forms.md.


reader = PdfReader(sys.argv[1])
if (reader.get_fields()):
    print("This PDF has fillable form fields")
else:
    print("This PDF does not have fillable form fields; you will need to visually determine where to enter data")

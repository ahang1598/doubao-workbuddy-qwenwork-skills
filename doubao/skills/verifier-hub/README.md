# verifier-hub

Deterministic artifact verifier CLI. Used for pre-delivery self-checks by any
agent, and for evidence collection in questionnaire judging mode.

This hub is **read-only / inspection-only**. It never creates or modifies the
files it inspects. It opens xlsx / docx / pdf / pptx / text / zip files and
reports structural and content facts as JSON, so an agent can collect evidence
without parsing binary formats itself or guessing content from a flattened
text trajectory.

## Layout

```
verifier-hub/
├── SKILL.md                        # agent-facing entry point (kept short on purpose)
├── references/
│   ├── subcommands.md              # all 58 subcommands, args + examples
│   └── questionnaire.md            # judge-mode workflow (harness-provided scripts)
├── bin/verifier                    # single CLI dispatcher (argparse, 2-level subparsers)
├── lib/
│   ├── _common.py                  # JSON protocol, error codes, paths, file URIs,
│   │                               # cross-platform binary lookup, install hints
│   ├── _pdf_backend.py             # pymupdf / pdfplumber / pypdf behind one interface
│   ├── file_io.py                  # 4  cmds: artifact-list / validate / extract-text / count
│   ├── xlsx.py                     # 12 cmds: get-value / assert-value / eval-formula / ...
│   ├── docx.py                     # 12 cmds: outline / section-text / page-count / ...
│   ├── pdf.py                      # 4  cmds: pages / text-dump / cjk-check / count-images
│   ├── pptx.py                     # 4  cmds: list-slides / slide-text / find-slide / count-images
│   ├── text.py                     # 9  cmds: must-contain / count-matches / date-extract / ...
│   ├── archive.py                  # 2  cmds: zip-list / zip-check-entries
│   └── rubric.py                   # 11 high-level DSL primitives
├── requirements.txt
└── README.md
```

## Output protocol

Every invocation writes exactly one JSON object to stdout, including bad
arguments and unknown family names:

```json
{"ok": true,  "tool": "xlsx.get-value", "result": {...}, "evidence": {...}}
{"ok": false, "tool": "xlsx.get-value", "error": {"code": "FILE_NOT_FOUND", "msg": "..."}}
```

`ok` reports whether the tool ran. The check verdict lives in `result.passed`,
so a file that fails its check is `ok: true` + `result.passed: false`.
`--help` is the only invocation that prints prose instead of JSON.

`evidence` is meant to be quoted verbatim; it always references the file and
locator that produced the finding, so the quote carries its own provenance.

## PDF backends

`lib/_pdf_backend.py` tries `pymupdf`, then `pdfplumber`, then `pypdf`, and
records the winner in each result's `backend` field. Only one of the three
needs to be installed. pymupdf is preferred because it is already present in
the rollout VM image and covers geometry, text, fonts and images on its own.

## Platform support

Linux and macOS. Windows is not supported: `bin/verifier` is an extension-less
shebang script, so `cmd.exe` and PowerShell cannot execute it directly. The
Python code itself is portable (no POSIX-only syscalls, all file I/O is
explicitly utf-8, all paths go through `pathlib`/`os.path`, `file://` URIs are
built with `as_uri()`), so `python bin/verifier ...` does work if you need it.

## Local development

```bash
cd verifier-hub
pip install -r requirements.txt
./bin/verifier --help
./bin/verifier xlsx --help
./bin/verifier xlsx get-value sample.xlsx --sheet Sheet1 --cell A1
```

## Packaging

The zip published to TOS contains `bin/`, `lib/`, `references/`, `SKILL.md`,
`requirements.txt` and `README.md` at the top level — no wrapper directory,
because the installer creates the per-skill directory from the zip name.
`__pycache__` and test fixtures are excluded: the VM runs Python 3.10 and
would ignore bytecode compiled elsewhere anyway.

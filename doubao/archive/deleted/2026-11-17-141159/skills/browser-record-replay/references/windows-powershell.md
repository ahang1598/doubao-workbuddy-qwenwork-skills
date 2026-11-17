# Windows PowerShell execution

Apply this contract before generating or executing any RPA Dev Local command
on Windows. These rules override Bash-oriented examples in `SKILL.md`.

## Run the native CLI directly

Resolve the platform-projected `rpa-dev-local.exe` from `PATH` and invoke it with a PowerShell
argument array. Never use `python -c`, `py -c`, or another script interpreter
as a CLI launcher. Do not generate a command string and do not pass
`shell=True` to a child-process wrapper.

## Pass structured input by file

Never pass JSON directly through PowerShell command text or a PowerShell
argument array, including `--param-json '{"keyword":"中文"}'`. Write the value
to a UTF-8 file and pass only its absolute path to the native executable:

```powershell
$rpaDev = (Get-Command "rpa-dev-local.exe").Source
$project = (Resolve-Path $projectPath).Path
$paramPath = Join-Path $env:TEMP "rpa-dev-local-params.json"
$params = @{ categories = @("纯电动") } | ConvertTo-Json -Depth 20 -Compress
[IO.File]::WriteAllText($paramPath, $params, [Text.UTF8Encoding]::new($false))
$arguments = @("local", "run", "--project", $project, "--param-file", $paramPath)
& $rpaDev @arguments
```

Use the matching file option for every structured or multiline value:
`--param-file`, `--default-param-file`, `--spec-file`, `--params-file`,
`--files-file`, `--expression-file`, and `--prd-file`. The CLI reads these
files as UTF-8 and accepts an optional UTF-8 BOM.

To inspect a JSON file, use the helper's strict UTF-8 reader. It returns
structured content or a read error without modifying the file:

```powershell
& "$skillRoot\references\windows-run.ps1" -JsonFile $paramPath
```

Keep PowerShell launcher scripts ASCII-only when possible. Windows PowerShell
5.1 does not reliably decode a UTF-8 `.ps1` file without a BOM; if a launcher
must contain non-ASCII text, save that `.ps1` as UTF-8 with BOM. JSON,
JavaScript, Markdown, and other CLI input files should remain UTF-8 without BOM.

Keep the executable and project paths absolute. For a long-lived command,
place the same native invocation in the detached worker described next.

## Detach long-lived commands and poll files

Commands such as `local run` can take two or three minutes. Use the bundled
`references/windows-run.ps1` helper instead of generating a worker. It starts a
hidden native process, preserves stdout/stderr bytes, and writes a durable
completion record after the child exits and both output streams finish.

Write a UTF-8 JSON job specification with an absolute executable path, working
directory, a string argument array, and a fresh output directory:

```powershell
$jobFile = Join-Path $env:TEMP ("rpa-job-" + [guid]::NewGuid().ToString('N') + ".json")
$job = @{
    executable = $rpaDev
    cwd = $project
    args = @("local", "run", "--project", $project, "--param-file", $paramPath)
    output_dir = Join-Path $project (".rpa-dev/jobs/" + [guid]::NewGuid().ToString('N'))
}
[IO.File]::WriteAllText($jobFile, ($job | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
$receipt = & "$skillRoot\references\windows-run.ps1" -SpecFile $jobFile | ConvertFrom-Json
$receipt
```

For an exported Skill, set `executable` to `(Get-Command node.exe).Source`,
`cwd` to that Skill's absolute directory, and `args` to the absolute
`scripts/run.js` path followed by `--param-file` and its absolute path. Use the
helper from the installed browser automation Skill; do not rewrite the export.

Query the job with the same helper; it checks worker identity and decodes
completed output as UTF-8, keeping execution and output-read errors separate:

```powershell
& "$skillRoot\references\windows-run.ps1" -JobDirectory $receipt.output_dir
```

`terminal=true` means the completion record is available. Inspect the native
exit code and business result. `unknown` or `interrupted` is not success and
must not trigger an automatic business retry. Output over 1 MiB is reported
with its path and `OUTPUT_LIMIT_EXCEEDED`; raise `-MaxOutputBytes` if needed
(up to 16 MiB). A zero launcher or query exit does not prove business success.

Do not use `cmd /c` or construct a shell command string. In particular,
`Start-Process -ArgumentList` joins its array into a command line; an unquoted
path containing `User Data` is split into separate arguments. The bundled
helper handles native quoting, including empty strings, quotes, trailing
backslashes and Chinese paths, without shell expansion. Keep launcher errors
from the calling tool when no receipt is returned; do not start polling a job
that was never acknowledged.

## Do not capture a collapsed background Workspace

On Windows, never run `local debug screenshot`, generate business code that
calls `api.screenshot()`, or invoke `Page.captureScreenshot` through
`api.cdp()` while the Workspace is in background mode. Chromium surface
capture can remain pending when the blue Tab Group is collapsed and then hold
the serialized browser-command queue. Use existing recording screenshots,
`snapshot`, `inspect-selector`, or a bounded JSON-safe `evaluate` expression.

The extension fails these Windows background calls immediately with
`LOCAL_SCREENSHOT_UNAVAILABLE_IN_BACKGROUND`. Treat that error as a capability
boundary: do not retry the screenshot, expand the Tab Group, or bring its Tab
to the foreground. Visible recording and an explicit human-only action remain
eligible for screenshot capture. This restriction does not apply to macOS.

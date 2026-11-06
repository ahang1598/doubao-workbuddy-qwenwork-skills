"""Windows Microsoft Office COM adapter.

Uses the system PowerShell runtime to drive an installed Word/PowerPoint, so the
skill does not need pywin32. LibreOffice remains a fallback when available.
"""

import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .soffice_adapter import BaseAdapter


_PROBE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
if ([type]::GetTypeFromProgID($env:CLAW_OFFICE_PROGID, $false)) { exit 0 }
exit 1
"""


_WORD_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$app = $null
$document = $null
try {
  $app = New-Object -ComObject Word.Application
  $app.Visible = $false
  $app.DisplayAlerts = 0
  $document = $app.Documents.Open($env:CLAW_DOC_CONVERT_INPUT, $false, $true)
  if ($env:CLAW_DOC_CONVERT_TARGET -eq 'pdf') {
    $document.ExportAsFixedFormat($env:CLAW_DOC_CONVERT_OUTPUT, 17)
  } elseif ($env:CLAW_DOC_CONVERT_TARGET -eq 'docx') {
    $document.SaveAs2($env:CLAW_DOC_CONVERT_OUTPUT, 16)
  } else {
    throw "Unsupported Word target: $env:CLAW_DOC_CONVERT_TARGET"
  }
} finally {
  if ($null -ne $document) { $document.Close($false) }
  if ($null -ne $app) { $app.Quit() }
  if ($null -ne $document) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
  if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
"""


_POWERPOINT_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$app = $null
$presentation = $null
try {
  $app = New-Object -ComObject PowerPoint.Application
  $app.DisplayAlerts = 1
  $presentation = $app.Presentations.Open($env:CLAW_DOC_CONVERT_INPUT, $true, $false, $false)
  if ($env:CLAW_DOC_CONVERT_TARGET -eq 'pdf') {
    $presentation.SaveAs($env:CLAW_DOC_CONVERT_OUTPUT, 32)
  } elseif ($env:CLAW_DOC_CONVERT_TARGET -eq 'pptx') {
    $presentation.SaveAs($env:CLAW_DOC_CONVERT_OUTPUT, 24)
  } else {
    throw "Unsupported PowerPoint target: $env:CLAW_DOC_CONVERT_TARGET"
  }
} finally {
  if ($null -ne $presentation) { $presentation.Close() }
  if ($null -ne $app) { $app.Quit() }
  if ($null -ne $presentation) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($presentation) }
  if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
"""


class OfficeComAdapter(BaseAdapter):
    """Convert documents through locally installed Microsoft Office on Windows."""

    name = "office-com"
    SUPPORTED = {
        ('doc', 'docx'),
        ('doc', 'pdf'),
        ('docx', 'pdf'),
        ('ppt', 'pptx'),
        ('ppt', 'pdf'),
        ('pptx', 'pdf'),
    }

    def __init__(self) -> None:
        self._availability: dict[str, bool] = {}

    def supports(self, source: str, target: str) -> bool:
        return (source.lower().lstrip('.'), target.lower().lstrip('.')) in self.SUPPORTED

    def check_dependencies(self, source: str = '', target: str = '') -> tuple[bool, str]:
        if sys.platform != 'win32':
            return False, 'Microsoft Office COM is only available on Windows.'
        powershell = self._powershell()
        if not powershell:
            return False, 'Windows PowerShell not found.'

        app = self._office_app(source, target)
        if not app:
            return False, 'This conversion is not supported by Microsoft Office COM.'
        if app not in self._availability:
            env = os.environ.copy()
            env['CLAW_OFFICE_PROGID'] = 'Word.Application' if app == 'word' else 'PowerPoint.Application'
            try:
                result = self._run_powershell(powershell, _PROBE_SCRIPT, env, timeout=20)
                self._availability[app] = result.returncode == 0
            except (OSError, subprocess.SubprocessError):
                self._availability[app] = False
        if not self._availability[app]:
            display = 'Microsoft Word' if app == 'word' else 'Microsoft PowerPoint'
            return False, f'{display} is not installed or its COM component is unavailable.'
        return True, ''

    def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
        source = Path(input_path).suffix.lower().lstrip('.')
        target = Path(output_path).suffix.lower().lstrip('.')
        if not self.supports(source, target):
            raise RuntimeError(f'Office COM does not support conversion: {source} -> {target}')
        available, error = self.check_dependencies(source, target)
        if not available:
            raise RuntimeError(error)

        source_path = Path(input_path).resolve()
        output = Path(output_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f'Input file not found: {source_path}')
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()

        app = self._office_app(source, target)
        script = _WORD_SCRIPT if app == 'word' else _POWERPOINT_SCRIPT
        env = os.environ.copy()
        env.update({
            'CLAW_DOC_CONVERT_INPUT': str(source_path),
            'CLAW_DOC_CONVERT_OUTPUT': str(output),
            'CLAW_DOC_CONVERT_TARGET': target,
        })
        result = self._run_powershell(self._powershell() or 'powershell.exe', script, env, timeout=180)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[-500:]
            raise RuntimeError(f'Microsoft Office conversion failed: {detail or "unknown error"}')
        if not output.exists():
            raise RuntimeError(f'Microsoft Office did not create expected output file: {output}')
        return True

    @staticmethod
    def _office_app(source: str, target: str) -> str | None:
        pair = (source.lower().lstrip('.'), target.lower().lstrip('.'))
        if pair in {('doc', 'docx'), ('doc', 'pdf'), ('docx', 'pdf')}:
            return 'word'
        if pair in {('ppt', 'pptx'), ('ppt', 'pdf'), ('pptx', 'pdf')}:
            return 'powerpoint'
        return None

    @staticmethod
    def _powershell() -> str | None:
        return shutil.which('powershell.exe') or shutil.which('powershell')

    @staticmethod
    def _run_powershell(
        executable: str,
        script: str,
        env: dict[str, str],
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        return subprocess.run(
            [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )

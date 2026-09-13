[CmdletBinding(DefaultParameterSetName='Run')]
param(
    [Parameter(Mandatory=$true,ParameterSetName='Run')][string]$SpecFile,
    [Parameter(ParameterSetName='Run')][switch]$Worker,
    [Parameter(Mandatory=$true,ParameterSetName='Status')][string]$JobDirectory,
    [Parameter(Mandatory=$true,ParameterSetName='ReadJSON')][string]$JsonFile,
    [ValidateRange(1,16777216)][int]$MaxOutputBytes = 1048576
)

# ASCII-only launcher for Windows PowerShell 5.1 and PowerShell 7.
# No cmd.exe, shell command strings, or console transcoding of child output.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$utf8 = [Text.UTF8Encoding]::new($false, $true)
[Console]::OutputEncoding = $utf8

function Read-Output([string]$Path, [bool]$ParseJSON) {
    $result = @{path=$Path; encoding='utf-8'; readable=$false}
    try {
        $file = Get-Item -LiteralPath $Path -ErrorAction Stop
        $result.bytes = $file.Length
        if ($file.Length -gt $MaxOutputBytes) {
            $result.error_code = 'OUTPUT_LIMIT_EXCEEDED'
            return $result
        }
        # Decode bytes directly: ReadAllText also recognizes non-UTF-8 BOMs.
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $text = $utf8.GetString($bytes).TrimStart([char]0xfeff)
        if ($ParseJSON) {
            if ([string]::IsNullOrWhiteSpace($text)) { throw 'Empty JSON document.' }
            $result.value = ConvertFrom-Json -InputObject $text -ErrorAction Stop
        } else { $result.text = $text }
        $result.readable = $true
    } catch {
        $result.error_code = 'OUTPUT_READ_INVALID'
        $result.error = $_.Exception.Message
    }
    return $result
}

if ($PSCmdlet.ParameterSetName -eq 'ReadJSON') {
    $result = Read-Output $JsonFile $true
    $result | ConvertTo-Json -Depth 100
    if (-not $result.readable) { exit 1 }
    exit 0
}

if ($PSCmdlet.ParameterSetName -eq 'Status') {
    $directory = (Resolve-Path -LiteralPath $JobDirectory).Path
    $completion = Join-Path $directory 'completion.json'
    $started = Join-Path $directory 'started.json'
    $result = @{status='unknown'; output_dir=$directory; terminal=$false}
    if (Test-Path -LiteralPath $completion) {
        $record = Read-Output $completion $true
        $result.completion = $record
        if ($record.readable -and $record.value.status -in @('completed','failed')) {
            $result.status = $record.value.status
            $result.terminal = $true
            $result.stdout = Read-Output (Join-Path $directory 'stdout.json') $true
            $result.stderr = Read-Output (Join-Path $directory 'stderr.txt') $false
        }
    } elseif (Test-Path -LiteralPath $started) {
        $record = Read-Output $started $true
        $result.started = $record
        if ($record.readable -and $record.value.PSObject.Properties['worker_started_at']) {
            $process = Get-Process -Id $record.value.worker_pid -ErrorAction SilentlyContinue
            try {
                # PowerShell 7 decodes ISO JSON timestamps as DateTime; 5.1
                # leaves strings. Compare UTC ticks, never formatted strings.
                $recordedStart = $record.value.worker_started_at
                if ($recordedStart -is [DateTime]) {
                    $recordedTicks = $recordedStart.ToUniversalTime().Ticks
                } elseif ($recordedStart -is [string]) {
                    $recordedTicks = [DateTimeOffset]::Parse($recordedStart, [Globalization.CultureInfo]::InvariantCulture).UtcDateTime.Ticks
                } else { throw 'Invalid worker start time.' }
                if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $recordedTicks) {
                    $result.status = 'running'
                } else { $result.status = 'interrupted' }
            } catch {
                $result.status = 'unknown'
                $result.error = $_.Exception.Message
            }
        }
    }
    $result | ConvertTo-Json -Depth 100
    exit 0
}

function Quote-NativeArgument([string]$Value) {
    if ($Value.Contains([char]0)) { throw 'An argument contains a NUL character.' }
    '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}

function Write-Record([string]$Path, $Value) {
    $temporary = $Path + '.tmp'
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 20), $utf8)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

$SpecFile = (Resolve-Path -LiteralPath $SpecFile).Path
$spec = [IO.File]::ReadAllText($SpecFile, $utf8) | ConvertFrom-Json
foreach ($field in @('executable', 'cwd', 'output_dir')) {
    if (-not ($spec.$field -is [string]) -or -not [IO.Path]::IsPathRooted($spec.$field)) {
        throw "$field must be an absolute path."
    }
}
if (-not ($spec.args -is [Array])) { throw 'args must be a JSON array of strings.' }
foreach ($argument in $spec.args) {
    if (-not ($argument -is [string])) { throw 'args must contain only strings.' }
}
if ([IO.Path]::GetExtension($spec.executable) -ne '.exe') { throw 'executable must name a native .exe.' }
$outputDir = [IO.Path]::GetFullPath($spec.output_dir)
$completionPath = Join-Path $outputDir 'completion.json'
$startedPath = Join-Path $outputDir 'started.json'

if (-not $Worker) {
    if (Test-Path -LiteralPath $outputDir) { throw 'output_dir already exists; use a fresh directory for each run.' }
    [IO.Directory]::CreateDirectory($outputDir) | Out-Null
    $specSnapshot = Join-Path $outputDir 'job.json'
    [IO.File]::WriteAllText($specSnapshot, ($spec | ConvertTo-Json -Depth 20), $utf8)
    $hostExecutable = (Get-Process -Id $PID).Path
    $launchArgs = @('-NoProfile', '-NonInteractive', '-File', $PSCommandPath, '-SpecFile', $specSnapshot, '-Worker')
    $launch = [Diagnostics.ProcessStartInfo]::new()
    $launch.FileName = $hostExecutable
    $launch.Arguments = (($launchArgs | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $launch.UseShellExecute = $false
    $launch.CreateNoWindow = $true
    # Startup diagnostics are written by the worker once PowerShell has parsed it.
    $process = [Diagnostics.Process]::Start($launch)
    $workerStartedAt = $process.StartTime.ToUniversalTime().ToString('o')
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while (-not (Test-Path -LiteralPath $startedPath) -and -not (Test-Path -LiteralPath $completionPath)) {
        if ($process.HasExited) {
            Write-Record $completionPath @{status='failed'; phase='worker_start'; exit_code=$process.ExitCode; error='Worker exited before producing a start record.'}
            break
        }
        if ([DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Milliseconds 100
    }
    $status = 'starting'
    if (Test-Path -LiteralPath $startedPath) { $status = 'running' }
    if (Test-Path -LiteralPath $completionPath) { $status = ([IO.File]::ReadAllText($completionPath) | ConvertFrom-Json).status }
    @{status=$status; worker_pid=$process.Id; worker_started_at=$workerStartedAt; output_dir=$outputDir; started_file=$startedPath; completion_file=$completionPath; query_args=@('-File', $PSCommandPath, '-JobDirectory', $outputDir)} | ConvertTo-Json -Depth 10
    $process.Dispose()
    exit 0
}

$watch = [Diagnostics.Stopwatch]::StartNew()
$child = $null
$stdout = $null
$stderr = $null
$record = @{status='failed'; phase='process_start'; exit_code=$null; worker_pid=$PID}
try {
    $stdout = [IO.File]::Open((Join-Path $outputDir 'stdout.json'), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $stderr = [IO.File]::Open((Join-Path $outputDir 'stderr.txt'), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $spec.executable
    $start.WorkingDirectory = $spec.cwd
    $start.Arguments = (($spec.args | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $child = [Diagnostics.Process]::Start($start)
    $child.StandardInput.Close()
    Write-Record $startedPath @{status='running'; worker_pid=$PID; worker_started_at=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o'); child_pid=$child.Id; started_at=[DateTime]::UtcNow.ToString('o')}
    $record.phase = 'execution'
    $copyOut = $child.StandardOutput.BaseStream.CopyToAsync($stdout)
    $copyErr = $child.StandardError.BaseStream.CopyToAsync($stderr)
    $child.WaitForExit()
    $copyOut.GetAwaiter().GetResult()
    $copyErr.GetAwaiter().GetResult()
    $record.exit_code = $child.ExitCode
    $record.status = if ($child.ExitCode -eq 0) { 'completed' } else { 'failed' }
} catch {
    $record.error = $_.Exception.Message
    [IO.File]::WriteAllText((Join-Path $outputDir 'worker-error.txt'), ($_ | Out-String), $utf8)
} finally {
    if ($stdout) { $stdout.Dispose() }
    if ($stderr) { $stderr.Dispose() }
    if ($child) { $child.Dispose() }
    $record.duration_ms = $watch.ElapsedMilliseconds
    $record.finished_at = [DateTime]::UtcNow.ToString('o')
    Write-Record $completionPath $record
}

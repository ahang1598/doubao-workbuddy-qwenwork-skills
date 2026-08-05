# Enterprise Skill Installation Script (Windows PowerShell)
# Downloads, validates, and installs an enterprise skill from a ZIP URL.
# Usage: install-skill.ps1 -Name <skillName> -Url <downloadUrl> [-TargetDir <dir>]

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9_-]+$')]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Url,

    [Parameter(Mandatory = $false)]
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    $TargetDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

# ─── Variables ──────────────────────────────────────────────────────────────────
# 使用系统 API 生成唯一临时目录，避免路径冲突
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
$TempZip = Join-Path $TempDir "skill.zip"
$InstallPath = "$TargetDir\$Name"

# ─── Cleanup helper ─────────────────────────────────────────────────────────────
function Invoke-Cleanup {
    # 临时目录由系统管理，不做递归删除
}

# ─── Frontmatter helper ────────────────────────────────────────────────────────
# 将 SKILL.md 的 YAML frontmatter 注入或更新 install_source 字段，
# 用于在「已安装技能」列表中标记此技能来源为 skill-market。
function Set-SkillInstallSourceField {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$SourceValue
    )

    # 以 UTF8 读取，按行处理，避免破坏原有换行风格
    $lines = [System.IO.File]::ReadAllLines($FilePath)

    # 首行不是 --- 时，视为缺失 frontmatter，前置一个最小 frontmatter 块
    if ($lines.Length -eq 0 -or $lines[0].Trim() -ne "---") {
        $newLines = @("---", "install_source: $SourceValue", "---") + $lines
        [System.IO.File]::WriteAllLines($FilePath, $newLines)
        return
    }

    $output = New-Object System.Collections.Generic.List[string]
    $output.Add($lines[0])
    $injected = $false
    $closed = $false

    for ($i = 1; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]

        if (-not $closed) {
            # 遇到 frontmatter 结束符
            if ($line.Trim() -eq "---") {
                if (-not $injected) {
                    $output.Add("install_source: $SourceValue")
                    $injected = $true
                }
                $output.Add($line)
                $closed = $true
                continue
            }

            # 已存在 install_source 字段，直接替换
            if ($line -match '^\s*install_source\s*:') {
                $output.Add("install_source: $SourceValue")
                $injected = $true
                continue
            }
        }

        $output.Add($line)
    }

    [System.IO.File]::WriteAllLines($FilePath, $output)
}

# ─── Step 1: Download ───────────────────────────────────────────────────────────
Write-Host "Downloading skill package from: $Url"
try {
    Invoke-WebRequest -Uri $Url -OutFile $TempZip -MaximumRedirection 5 -UseBasicParsing
} catch {
    Write-Error "Failed to download skill package from '$Url': $_"
    Invoke-Cleanup
    exit 1
}

if (-not (Test-Path $TempZip)) {
    Write-Error "Download completed but ZIP file not found at: $TempZip"
    Invoke-Cleanup
    exit 1
}

# ─── Step 2: Extract ────────────────────────────────────────────────────────────
Write-Host "Extracting skill package..."
try {
    Expand-Archive -Path $TempZip -DestinationPath $TempDir -Force
} catch {
    Write-Error "Failed to extract skill package. The ZIP file may be corrupted: $_"
    Invoke-Cleanup
    exit 1
}

# ─── Step 3 & 4: Validate and locate SKILL.md（大小写不敏感）────────────────────
Write-Host "Validating skill package..."
# 使用正则匹配进行大小写不敏感查找，兼容 skill.md / Skill.md / SKILL.md 等变体
$SkillMdFile = Get-ChildItem -Path $TempDir -Recurse -File |
    Where-Object { $_.Name -match '(?i)^skill\.md$' -and $_.FullName -notmatch '__MACOSX' -and $_.FullName -notmatch '[\\\/]\.' } |
    Select-Object -First 1

if (-not $SkillMdFile) {
    Write-Error "Invalid skill package - SKILL.md not found (已尝试大小写不敏感匹配)."
    Invoke-Cleanup
    exit 1
}

$SkillDir = $SkillMdFile.DirectoryName
# 提取实际找到的文件名，后续引用均使用该变量
$SkillMdName = $SkillMdFile.Name
Write-Host "Found skill root at: $SkillDir (SKILL.md=$SkillMdName)"

# ─── Step 5: Remove old version (backup to temp) ────────────────────────────────
if (Test-Path $InstallPath) {
    $Timestamp = [int][double]::Parse((Get-Date -UFormat %s))
    $BackupPath = "$env:TEMP\.skill-replaced-$Name-$Timestamp"
    Write-Host "Moving existing version to: $BackupPath"
    Move-Item -Path $InstallPath -Destination $BackupPath -Force
}

# ─── Step 6: Install ────────────────────────────────────────────────────────────
Write-Host "Installing skill to: $InstallPath"
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}
Move-Item -Path $SkillDir -Destination $InstallPath -Force

# ─── Step 7: Inject install_source field into frontmatter ──────────────────────
# 在 SKILL.md frontmatter 中写入 install_source=skill-market，标记技能来源
Write-Host "Tagging skill install_source as 'skill-market' in $SkillMdName frontmatter..."
try {
    Set-SkillInstallSourceField -FilePath "$InstallPath\$SkillMdName" -SourceValue "skill-market"
} catch {
    Write-Error "Failed to inject install_source field into $SkillMdName frontmatter: $_"
    Invoke-Cleanup
    exit 1
}

# ─── Step 8: Verify ─────────────────────────────────────────────────────────────
if (-not (Test-Path "$InstallPath\$SkillMdName")) {
    Write-Error "Verification failed - $SkillMdName not found at install path."
    Invoke-Cleanup
    exit 1
}

# ─── Step 9: Cleanup ────────────────────────────────────────────────────────────
Invoke-Cleanup

Write-Host ""
Write-Host "OK Skill '$Name' installed successfully to: $InstallPath" -ForegroundColor Green
Write-Host "  The skill is immediately available for use."
exit 0

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Distribution = "Ubuntu-22.04",
    [string]$WslUser = "root",
    [string]$RepoPath = "/home/ahang/ai/demo/zpc/doubao-skills",
    [string]$DailyAt = "18:00"
)

$ErrorActionPreference = "Stop"

function Quote-BashSingle {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value.Contains("'")) {
        throw "Single quotes are not supported in bash paths for this script: $Value"
    }
    return "'$Value'"
}

function Register-PlatformTask {
    param(
        [Parameter(Mandatory = $true)][string]$TaskName,
        [Parameter(Mandatory = $true)][string]$Platform,
        [Parameter(Mandatory = $true)][string]$LogName
    )

    $repo = Quote-BashSingle -Value $RepoPath
    $bashCommand = "cd $repo && mkdir -p logs && python3 scripts/sync_platform.py --platform $Platform --commit --push >> logs/$LogName 2>&1"
    $escapedBashCommand = $bashCommand.Replace('"', '\"')
    $arguments = "-d $Distribution -u $WslUser -- bash -lc `"$escapedBashCommand`""
    $action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($DailyAt, "HH:mm", $null))
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    $description = "Daily sync for $Platform data into the AI skills archive repository."

    if ($PSCmdlet.ShouldProcess($TaskName, "Register or update scheduled task")) {
        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description $description `
            -Force | Out-Null
        Write-Host "Registered scheduled task '$TaskName'."
    } else {
        Write-Host "Skipped registering scheduled task '$TaskName'."
    }

    Write-Host "Schedule: daily at $DailyAt"
    Write-Host "Action: wsl.exe $arguments"
}

Register-PlatformTask -TaskName "DoubaoSkillsDailySync" -Platform "doubao" -LogName "doubao-sync.log"
Register-PlatformTask -TaskName "WorkbuddySkillsDailySync" -Platform "workbuddy" -LogName "workbuddy-sync.log"
Register-PlatformTask -TaskName "QwenworkSkillsDailySync" -Platform "qwenwork" -LogName "qwenwork-sync.log"

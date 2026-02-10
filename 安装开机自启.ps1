param(
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$taskName = "AutoStart-SimilarKLine"
$taskPath = "\"
$fullTaskName = "$taskPath$taskName"

$autostartScriptName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("5byA5py66Ieq5ZCv5Lu75YqhLnBzMQ=="))
$autostartScript = Join-Path $ProjectRoot $autostartScriptName
if (-not (Test-Path -LiteralPath $autostartScript)) {
    throw "Autostart script not found: $autostartScript"
}

try {
    $backupXml = Join-Path $LogDir "autostart-task.backup.xml"
    schtasks /query /tn $fullTaskName /xml 2>$null | Out-File -LiteralPath $backupXml -Encoding Unicode
} catch {
    # ignore
}

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$autostartScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Auto start SimilarKLine at logon" -Force | Out-Null

Write-Host "Installed/updated scheduled task: $fullTaskName"
Write-Host "Task script: $autostartScript"
Write-Host "Logs: $(Join-Path $LogDir 'autostart.log')"

if ($RunNow) {
    Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath
    Write-Host "Triggered once: $fullTaskName"
}

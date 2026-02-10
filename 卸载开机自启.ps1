$ErrorActionPreference = "Stop"

$taskName = "AutoStart-SimilarKLine"
$taskPath = "\"
$fullTaskName = "$taskPath$taskName"

try {
    Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false -ErrorAction Stop | Out-Null
    Write-Host "Removed scheduled task: $fullTaskName"
} catch {
    Write-Host "Scheduled task not found or remove failed: $fullTaskName"
}

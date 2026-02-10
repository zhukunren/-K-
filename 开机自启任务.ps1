$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8
}

function Test-PortListening {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

$ProjectRoot = $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir "autostart.log"

try {
    $battery = Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($battery) {
        Write-Log "AutoStart task triggered (user=$env:USERNAME, batteryStatus=$($battery.BatteryStatus), charge=$($battery.EstimatedChargeRemaining)%)"
    } else {
        Write-Log "AutoStart task triggered (user=$env:USERNAME)"
    }
} catch {
    Write-Log "AutoStart task triggered (user=$env:USERNAME)"
}

$backendPort = 8001
$frontendPort = 5173

$servicePids = [ordered]@{
    Timestamp = (Get-Date).ToString("o")
    Backend   = $null
    Frontend  = $null
}

try {
    if (Test-PortListening -Port $backendPort) {
        Write-Log "Backend port $backendPort already in use; skip starting backend"
    } else {
        $backendExe = Join-Path $ProjectRoot "venv\\Scripts\\python.exe"
        $backendWork = Join-Path $ProjectRoot "backend"
        $backendEntrypoint = Join-Path $backendWork "api_full.py"

        if (-not (Test-Path -LiteralPath $backendEntrypoint)) {
            Write-Log "Backend entry not found: $backendEntrypoint"
        } elseif (-not (Test-Path -LiteralPath $backendExe)) {
            Write-Log "Backend python not found: $backendExe"
        } else {
            $backendOut = Join-Path $LogDir "autostart-backend.out.log"
            $backendErr = Join-Path $LogDir "autostart-backend.err.log"
            $backendProc = Start-Process -FilePath $backendExe -ArgumentList "api_full.py" -WorkingDirectory $backendWork -WindowStyle Hidden -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
            $servicePids.Backend = $backendProc.Id
            Write-Log "Backend started (pid=$($backendProc.Id))"
        }
    }
} catch {
    Write-Log "Backend start failed: $($_.Exception.Message)"
}

try {
    if (Test-PortListening -Port $frontendPort) {
        Write-Log "Frontend port $frontendPort already in use; skip starting frontend"
    } else {
        $frontendWork = Join-Path $ProjectRoot "frontend"
        $frontendOut = Join-Path $LogDir "autostart-frontend.out.log"
        $frontendErr = Join-Path $LogDir "autostart-frontend.err.log"

        $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
        $npmCandidates = @()
        if ($npmCommand -and $npmCommand.Source) {
            $npmSource = $npmCommand.Source
            if ([IO.Path]::GetExtension($npmSource) -ieq ".ps1") {
                $npmCandidates += [IO.Path]::ChangeExtension($npmSource, ".cmd")
                $npmCandidates += [IO.Path]::ChangeExtension($npmSource, ".exe")
            }
            $npmCandidates += $npmSource
        }

        $npmCandidates += (Join-Path $env:ProgramFiles "nodejs\\npm.cmd")
        $npmCandidates += (Join-Path ${env:ProgramFiles(x86)} "nodejs\\npm.cmd")
        $npmCandidates += (Join-Path $env:ProgramFiles "nodejs\\npm.exe")
        $npmCandidates += (Join-Path ${env:ProgramFiles(x86)} "nodejs\\npm.exe")

        $npmPathCandidates = $npmCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique
        $npmPath = $npmPathCandidates | Select-Object -First 1
        if (-not $npmPath) {
            Write-Log "npm not found; frontend not started"
        } elseif ([IO.Path]::GetExtension($npmPath) -ieq ".ps1") {
            $frontendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $npmPath, "run", "dev" -WorkingDirectory $frontendWork -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
            $servicePids.Frontend = $frontendProc.Id
            Write-Log "Frontend started via npm.ps1 (pid=$($frontendProc.Id))"
        } else {
            $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "`"$npmPath`" run dev" -WorkingDirectory $frontendWork -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
            $servicePids.Frontend = $frontendProc.Id
            Write-Log "Frontend started (pid=$($frontendProc.Id))"
        }
    }
} catch {
    Write-Log "Frontend start failed: $($_.Exception.Message)"
}

try {
    $pidFile = Join-Path $LogDir "service_pids.json"
    $servicePids | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $pidFile -Encoding UTF8
} catch {
    Write-Log "Failed to write PID file: $($_.Exception.Message)"
}

# ============================================
# 股票预测系统 - 服务停止脚本
# Stock Prediction System - Stop Script
# ============================================

$ErrorActionPreference = "Continue"

# 颜色输出函数
function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet('Info', 'Success', 'Warning', 'Error', 'Title')]
        [string]$Type = 'Info'
    )

    switch ($Type) {
        'Info'    { Write-Host $Message -ForegroundColor Cyan }
        'Success' { Write-Host "[✓] $Message" -ForegroundColor Green }
        'Warning' { Write-Host "[!] $Message" -ForegroundColor Yellow }
        'Error'   { Write-Host "[✗] $Message" -ForegroundColor Red }
        'Title'   { Write-Host "`n$Message" -ForegroundColor Magenta }
    }
}

# 显示标题
Clear-Host
Write-ColorOutput "============================================" -Type Title
Write-ColorOutput "   股票预测系统 - 服务停止脚本" -Type Title
Write-ColorOutput "   Stock Prediction System - Stop Services" -Type Title
Write-ColorOutput "============================================" -Type Title

# 获取项目根目录
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-ColorOutput "`n正在停止服务..." -Type Info

# 方法1: 尝试从保存的PID文件中读取进程ID
$pidFile = "logs\service_pids.json"
$stoppedCount = 0

if (Test-Path $pidFile) {
    Write-Host "`n  从PID文件读取进程信息... " -NoNewline
    try {
        $pids = Get-Content $pidFile | ConvertFrom-Json

        # 停止后端进程
        if ($pids.Backend) {
            $process = Get-Process -Id $pids.Backend -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $pids.Backend -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "已停止后端进程 (PID: $($pids.Backend))" -Type Success
                $stoppedCount++
            }
        }

        # 停止前端进程
        if ($pids.Frontend) {
            $process = Get-Process -Id $pids.Frontend -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $pids.Frontend -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "已停止前端进程 (PID: $($pids.Frontend))" -Type Success
                $stoppedCount++
            }
        }

        # 删除PID文件
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

    } catch {
        Write-ColorOutput "读取失败，使用备用方法" -Type Warning
    }
}

# 方法2: 通过端口查找进程
Write-Host "`n  检查端口占用... " -NoNewline

# 停止占用8001端口的进程（后端）
$backendProcess = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($backendProcess) {
    $processId = $backendProcess.OwningProcess | Select-Object -First 1
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Write-ColorOutput "已停止后端进程 (PID: $processId)" -Type Success
    $stoppedCount++
}

# 停止占用5173端口的进程（前端）
$frontendProcess = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($frontendProcess) {
    $processId = $frontendProcess.OwningProcess | Select-Object -First 1
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Write-ColorOutput "已停止前端进程 (PID: $processId)" -Type Success
    $stoppedCount++
}

# 方法3: 查找并停止项目相关的进程
Write-Host "`n  清理项目相关进程... " -NoNewline

# 停止项目目录下的Python进程
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$ProjectRoot*" -or $_.CommandLine -like "*api_full*"
}
foreach ($process in $pythonProcesses) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Write-ColorOutput "已停止Python进程 (PID: $($process.Id))" -Type Success
    $stoppedCount++
}

# 停止项目目录下的Node进程
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*$ProjectRoot*" -or $_.CommandLine -like "*vite*"
}
foreach ($process in $nodeProcesses) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Write-ColorOutput "已停止Node进程 (PID: $($process.Id))" -Type Success
    $stoppedCount++
}

# 停止cmd窗口
$cmdProcesses = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*股票预测*"
}
foreach ($process in $cmdProcesses) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    $stoppedCount++
}

Start-Sleep -Seconds 2

# 显示结果
Write-ColorOutput "`n============================================" -Type Title
if ($stoppedCount -gt 0) {
    Write-ColorOutput "   ✓ 所有服务已停止！" -Type Title
    Write-ColorOutput "   共停止 $stoppedCount 个进程" -Type Title
} else {
    Write-ColorOutput "   没有找到运行中的服务" -Type Warning
}
Write-ColorOutput "============================================" -Type Title

Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

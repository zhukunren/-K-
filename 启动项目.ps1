# Stock Prediction System - Startup Script
# Simplified version without encoding issues

$ErrorActionPreference = "Continue"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Stock Prediction System - Starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    pause
    exit 1
}

# Check Node.js
Write-Host "[2/6] Checking Node.js..." -ForegroundColor Yellow
node --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Node.js not found!" -ForegroundColor Red
    pause
    exit 1
}

# Check venv
Write-Host "[3/6] Checking Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Check Python dependencies
Write-Host "[4/6] Checking Python dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    & venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Check frontend dependencies
Write-Host "[5/6] Checking frontend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    Set-Location $ProjectRoot
}

# Clean old processes
Write-Host "[6/6] Cleaning old processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start backend
Write-Host ""
Write-Host "Starting backend API..." -ForegroundColor Green
Set-Location backend
Start-Process cmd -ArgumentList "/k", "..\venv\Scripts\python.exe", "api_full.py" -WindowStyle Minimized
Set-Location $ProjectRoot
Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend..." -ForegroundColor Green
Set-Location frontend
Start-Process cmd -ArgumentList "/k", "npm", "run", "dev" -WindowStyle Minimized
Set-Location $ProjectRoot
Start-Sleep -Seconds 3

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:  http://localhost:8001" -ForegroundColor Cyan
Write-Host "API Docs:     http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "Frontend:     http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit (services will continue running)..." -ForegroundColor Gray
pause

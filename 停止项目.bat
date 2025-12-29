@echo off
chcp 65001 >nul

title 股票预测系统 - 停止服务

echo.
echo ============================================
echo    正在停止所有服务...
echo ============================================
echo.

:: 停止端口占用的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo 停止后端服务 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo 停止前端服务 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

:: 停止相关进程
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

timeout /t 2 >nul

color 0A
echo.
echo ============================================
echo    所有服务已停止！
echo ============================================
echo.
pause

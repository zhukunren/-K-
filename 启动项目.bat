@echo off
chcp 65001 >nul
setlocal

title 股票预测系统启动

echo ============================================
echo    股票预测系统 - 启动中...
echo ============================================
echo.

cd /d "%~dp0"

:: 检查环境
echo [1/4] 检查环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python
    pause
    exit /b 1
)

node --version
if errorlevel 1 (
    echo 错误: 未找到 Node.js
    pause
    exit /b 1
)

:: 创建虚拟环境
echo.
echo [2/4] 准备虚拟环境...
if not exist "venv\Scripts\python.exe" (
    echo 创建虚拟环境...
    python -m venv venv
)

:: 安装依赖
echo.
echo [3/4] 检查依赖...
if not exist "venv\Lib\site-packages\fastapi" (
    echo 安装 Python 依赖...
    venv\Scripts\python.exe -m pip install -r requirements.txt -q
)

if not exist "frontend\node_modules" (
    echo 安装前端依赖...
    cd frontend
    npm install
    cd ..
)

:: 清理旧进程
echo.
echo [4/4] 清理旧进程...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 >nul

:: 启动服务
echo.
echo 正在启动服务...
echo.

cd backend
start "后端API" /min cmd /k "..\venv\Scripts\python.exe api_full.py"
cd ..

timeout /t 3 >nul

cd frontend
start "前端界面" /min cmd /k "npm run dev"
cd ..

timeout /t 3 >nul

cls
color 0A
echo.
echo ============================================
echo    启动成功！
echo ============================================
echo.
echo 后端 API:  http://localhost:8001
echo API 文档:  http://localhost:8001/docs
echo 前端界面:  http://localhost:5173
echo.
echo 提示: 关闭这个窗口不会停止服务
echo       使用 停止项目.bat 来关闭服务
echo.

set /p OPEN="打开浏览器? (Y/N): "
if /i "%OPEN%"=="Y" start http://localhost:5173

echo.
pause

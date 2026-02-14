@echo off
REM 智能会议助手系统 - 前端快速启动脚本（Windows）

echo.
echo ========================================
echo   智能会议助手系统 - 前端启动向导
echo ========================================
echo.

REM 进入前端目录
cd /d "%~dp0frontend"

REM 检查 Node.js
echo [1/3] 检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到 Node.js
    echo 请从 https://nodejs.org 下载并安装 Node.js
    pause
    exit /b 1
)
echo ✓ Node.js 已安装

REM 检查依赖
echo.
echo [2/3] 检查依赖项...
if not exist "node_modules" (
    echo 正在安装依赖包，请稍候...
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)
echo ✓ 依赖已就绪

REM 启动开发服务器
echo.
echo [3/3] 启动开发服务器...
echo.
echo ========================================
echo ✓ 前端应用将在以下地址启动：
echo   http://localhost:3000
echo.
echo ✓ 后端 API 地址：
echo   http://localhost:8000
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

call npm run dev

pause

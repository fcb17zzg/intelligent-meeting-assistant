@echo off
REM Hugging Face Token设置工具
echo ==================================================
echo  Hugging Face Token 设置工具
echo ==================================================
echo.

set /p HF_TOKEN="your_token"

if "%HF_TOKEN%"=="" (
    echo 错误: Token不能为空
    pause
    exit /b 1
)

REM 设置为用户环境变量
setx HF_TOKEN "%HF_TOKEN%"

echo.
echo ✅ HF_TOKEN已设置为用户环境变量
echo.
echo 注意：
echo   1. 需要重启终端或重新登录使环境变量生效
echo   2. 当前会话可以临时设置：set HF_TOKEN=%HF_TOKEN%
echo.
echo 验证设置：
echo   在PowerShell中运行：echo $env:HF_TOKEN
echo   在CMD中运行：echo %HF_TOKEN%
echo.

pause
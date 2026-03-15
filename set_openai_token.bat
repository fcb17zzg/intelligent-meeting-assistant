@echo off
REM OpenAI API Key 设置工具
echo ==================================================
echo  OpenAI API Key 设置工具
echo ==================================================
echo.

set /p OPENAI_API_KEY="请输入 OPENAI_API_KEY: "

if "%OPENAI_API_KEY%"=="" (
    echo 错误: API Key 不能为空
    pause
    exit /b 1
)

set /p OPENAI_MODEL="请输入 OPENAI_MODEL（直接回车默认 gpt-4o-mini）: "
if "%OPENAI_MODEL%"=="" set OPENAI_MODEL=gpt-4o-mini

set /p OPENAI_BASE_URL="请输入 OPENAI_BASE_URL（如不需要可直接回车）: "

REM 设置为用户环境变量
setx OPENAI_API_KEY "%OPENAI_API_KEY%"
setx OPENAI_MODEL "%OPENAI_MODEL%"

if not "%OPENAI_BASE_URL%"=="" (
    setx OPENAI_BASE_URL "%OPENAI_BASE_URL%"
)

echo.
echo OpenAI 相关环境变量已设置为用户环境变量
echo.
echo 注意：
echo   1. 需要重启终端或重新登录使环境变量生效
echo   2. 当前 CMD 会话可临时设置：set OPENAI_API_KEY=%OPENAI_API_KEY%
echo   3. 当前 PowerShell 会话可临时设置：$env:OPENAI_API_KEY="你的Key"
echo.
echo 验证设置：
echo   在 PowerShell 中运行：echo $env:OPENAI_MODEL
echo   在 PowerShell 中运行：[string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY) -eq $false
echo.
pause

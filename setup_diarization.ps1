# pyannote.audio Windows PowerShell配置脚本
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  会议语音识别模块 - Windows环境配置" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Python环境
Write-Host "[1/6] 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python已安装: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python未找到"
    }
} catch {
    Write-Host "错误: Python未安装或不在PATH中" -ForegroundColor Red
    Write-Host "请安装Python 3.10+ 并确保已添加到系统PATH" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按Enter退出"
    exit 1
}

# 2. 检查pip
Write-Host "`n[2/6] 检查pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ pip已安装" -ForegroundColor Green
    } else {
        throw "pip未找到"
    }
} catch {
    Write-Host "正在尝试修复pip..." -ForegroundColor Yellow
    python -m ensurepip --upgrade
}

# 3. 安装依赖包
Write-Host "`n[3/6] 安装依赖包..." -ForegroundColor Yellow

Write-Host "正在安装 pyannote.audio..." -ForegroundColor Gray
pip install pyannote.audio==3.1.1

Write-Host "正在安装 PyTorch..." -ForegroundColor Gray
# 自动检测CUDA
$hasCuda = $false
try {
    $cudaInfo = nvidia-smi 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "检测到NVIDIA GPU，安装CUDA版本..." -ForegroundColor Green
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
        $hasCuda = $true
    }
} catch {
    Write-Host "未检测到CUDA，安装CPU版本..." -ForegroundColor Yellow
    pip install torch torchaudio
}

Write-Host "正在安装其他依赖..." -ForegroundColor Gray
$packages = @(
    "huggingface-hub",
    "pydub",
    "librosa",
    "soundfile",
    "noisereduce",
    "pydantic-settings",
    "fastapi",
    "celery",
    "redis",
    "pytest",
    "pytest-asyncio"
)

foreach ($package in $packages) {
    Write-Host "  安装 $package..." -ForegroundColor DarkGray
    pip install $package
}

# 4. 创建目录结构
Write-Host "`n[4/6] 创建目录结构..." -ForegroundColor Yellow
$directories = @(
    "test_audio",
    "logs",
    "cache\audio",
    "temp",
    "models",
    "cache\audio\diarization",
    "cache\audio\transcription",
    "temp\audio_chunks",
    "temp\processed"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  创建目录: $dir" -ForegroundColor DarkGray
    }
}
Write-Host "✅ 目录创建完成！" -ForegroundColor Green

# 5. 检查Hugging Face Token
Write-Host "`n[5/6] 配置Hugging Face Token..." -ForegroundColor Yellow
$hfToken = [System.Environment]::GetEnvironmentVariable("HF_TOKEN", "User")
if ($hfToken) {
    Write-Host "✅ HF_TOKEN环境变量已设置" -ForegroundColor Green
} else {
    Write-Host "⚠️  HF_TOKEN环境变量未设置" -ForegroundColor Red
    Write-Host ""
    Write-Host "请执行以下步骤：" -ForegroundColor Yellow
    Write-Host "1. 访问 https://huggingface.co/settings/tokens" -ForegroundColor Cyan
    Write-Host "2. 创建新Token（选择Read权限）" -ForegroundColor Cyan
    Write-Host "3. 设置环境变量：" -ForegroundColor Cyan
    Write-Host ""
    
    $choice = Read-Host "是否现在设置HF_TOKEN？(y/n)"
    if ($choice -eq 'y' -or $choice -eq 'Y') {
        $token = Read-Host "请输入你的Hugging Face Token"
        if ($token) {
            [System.Environment]::SetEnvironmentVariable("HF_TOKEN", $token, "User")
            Write-Host "✅ HF_TOKEN已设置为用户环境变量" -ForegroundColor Green
            Write-Host "  需要重启终端或重新登录使环境变量生效" -ForegroundColor Yellow
        }
    }
}

# 6. 模型使用协议提醒
Write-Host "`n[6/6] 模型使用协议..." -ForegroundColor Yellow
Write-Host "请手动访问以下链接接受协议：" -ForegroundColor Cyan
Write-Host "  - https://huggingface.co/pyannote/speaker-diarization-3.1" -ForegroundColor Cyan
Write-Host "  - https://huggingface.co/pyannote/segmentation-3.0" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问每个链接，点击 'Agree and access repository' 按钮" -ForegroundColor Yellow

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "  环境配置完成！" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor Yellow
Write-Host "1. 重启终端使环境变量生效" -ForegroundColor White
Write-Host "2. 接受模型使用协议（点击上面链接）" -ForegroundColor White
Write-Host "3. 运行测试: python test_diarization_manual.py" -ForegroundColor White
Write-Host "4. 或运行单元测试: pytest tests\test_diarization.py -v" -ForegroundColor White
Write-Host ""
Write-Host "测试音频准备：" -ForegroundColor Yellow
Write-Host "如需录制测试音频，可以使用系统录音机或以下命令：" -ForegroundColor White
Write-Host "  下载示例音频: powershell -Command \"Invoke-WebRequest -Uri 'https://example.com/sample.wav' -OutFile 'test_audio\sample.wav'\"" -ForegroundColor Gray
Write-Host ""

Read-Host "按Enter退出"
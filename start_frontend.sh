#!/bin/bash

# 智能会议助手系统 - 前端快速启动脚本（macOS/Linux）

echo ""
echo "========================================"
echo "  智能会议助手系统 - 前端启动向导"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 进入前端目录
cd "$SCRIPT_DIR/frontend" || exit 1

# 检查 Node.js
echo "[1/3] 检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到 Node.js"
    echo "请从 https://nodejs.org 下载并安装 Node.js"
    exit 1
fi
echo "✓ Node.js 已安装"

# 检查依赖
echo ""
echo "[2/3] 检查依赖项..."
if [ ! -d "node_modules" ]; then
    echo "正在安装依赖包，请稍候..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
fi
echo "✓ 依赖已就绪"

# 启动开发服务器
echo ""
echo "[3/3] 启动开发服务器..."
echo ""
echo "========================================"
echo "✓ 前端应用将在以下地址启动："
echo "  http://localhost:3000"
echo ""
echo "✓ 后端 API 地址："
echo "  http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "========================================"
echo ""

npm run dev

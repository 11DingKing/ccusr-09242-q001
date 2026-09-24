#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}

echo "📦 检查 Python 环境 ..."
$PYTHON --version

echo "📦 安装依赖 ..."
$PYTHON -m pip install --upgrade pip > /dev/null
$PYTHON -m pip install -r requirements.txt

echo "🌱 初始化并植入示例数据 ..."
$PYTHON seed_data.py

echo "🚀 启动后端服务（端口 8000）..."
echo "   Swagger UI:  http://127.0.0.1:8000/docs"
echo "   ReDoc   UI:  http://127.0.0.1:8000/redoc"
echo ""
$PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

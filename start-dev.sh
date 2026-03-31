#!/bin/bash
echo "========================================"
echo "AI小说拆书系统 - 开发环境启动"
echo "========================================"
echo ""

echo "[1/2] 启动 Mock Server (端口 3001)..."
cd backend
python mock_server.py &
MOCK_PID=$!
sleep 2

echo "[2/2] 启动前端静态服务 (端口 8080)..."
cd ..
python -m http.server 8080 &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "服务已启动:"
echo "- Mock API: http://localhost:3001"
echo "- Mock API文档: http://localhost:3001/docs"
echo "- 前端页面: http://localhost:8080"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $MOCK_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

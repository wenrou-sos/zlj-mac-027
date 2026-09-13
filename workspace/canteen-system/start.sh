#!/usr/bin/env bash
# 一键启动脚本：后端 :8000 + 前端 :5173
set -e
cd "$(dirname "$0")"

echo "▶ 启动后端 (FastAPI :8000)..."
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "▶ 启动前端 (Vite :5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
echo "✅ 系统已启动：http://localhost:5173  (API文档: http://localhost:8000/docs)"
wait

#!/bin/bash
set -e
# 若挂载后 frontend/node_modules 为空，用镜像内预装的依赖填充，避免每次装包
if [ ! -d /app/frontend/node_modules/.bin ] || [ ! -f /app/frontend/node_modules/package.json ]; then
  echo "[entrypoint] 填充 frontend/node_modules（来自镜像预装）..."
  mkdir -p /app/frontend/node_modules
  cp -rn /opt/frontend_node_modules/. /app/frontend/node_modules/
fi

# 后端：与原来一致（uvicorn 跑 main_sqlite，支持 --reload）
echo "[entrypoint] 启动后端 0.0.0.0:8000 (main_sqlite)..."
uvicorn services.ai-processing.main_sqlite:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 前端：与原来一致 cd frontend && npm run dev
echo "[entrypoint] 启动前端 0.0.0.0:3000 (next dev)..."
cd /app/frontend && npm run dev &
FRONTEND_PID=$!

# 任一进程退出则整容器退出
wait -n
exit $?

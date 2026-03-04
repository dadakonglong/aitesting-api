#!/bin/bash
set -e
# 若挂载后 frontend/node_modules 为空，用镜像内预装的依赖填充，避免每次装包
if [ ! -d /app/frontend/node_modules/.bin ] || [ ! -f /app/frontend/node_modules/package.json ]; then
  echo "[entrypoint] 填充 frontend/node_modules（来自镜像预装）..."
  mkdir -p /app/frontend/node_modules
  cp -rn /opt/frontend_node_modules/. /app/frontend/node_modules/
fi

# 后端：必须在 services/ai-processing 下启动，否则 main_sqlite 里 from services.xxx 会解析到顶层 services
echo "[entrypoint] 启动后端 0.0.0.0:8000 (main_sqlite)..."
(cd /app/services/ai-processing && PYTHONPATH=/app uvicorn main_sqlite:app --host 0.0.0.0 --port 8000 --reload) &

# 前端：其他服务器/资源受限时用生产模式可避免 Node 线程断言崩溃，设 FRONTEND_MODE=prod 即可
if [ "${FRONTEND_MODE}" = "prod" ]; then
  echo "[entrypoint] 启动前端 0.0.0.0:3000 (next build + start)..."
  cd /app/frontend
  [ ! -f .next/BUILD_ID ] && npm run build
  npm start &
else
  echo "[entrypoint] 启动前端 0.0.0.0:3000 (next dev)..."
  cd /app/frontend && npm run dev &
fi

# 任一进程退出则整容器退出
wait -n
exit $?

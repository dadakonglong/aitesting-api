# 启动脚本 (Windows)
@echo off
echo 🚀 启动AI智能接口测试平台...

REM 检查环境变量
if not exist .env (
    echo ⚠️  未找到.env文件，从.env.example复制...
    copy .env.example .env
    echo ❗ 请编辑.env文件，配置OPENAI_API_KEY等必要参数
    pause
    exit /b 1
)

REM 检查Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 请先安装Docker
    pause
    exit /b 1
)

REM 启动基础设施服务
echo 📦 启动基础设施服务（PostgreSQL, Neo4j, Qdrant, Redis, RabbitMQ）...
docker-compose up -d postgres neo4j qdrant redis rabbitmq

REM 等待服务就绪
echo ⏳ 等待服务启动...
timeout /t 15 /nobreak >nul

REM 启动AI服务
echo 🤖 启动AI处理服务...
docker-compose up -d ai-service

REM 等待AI服务就绪
timeout /t 10 /nobreak >nul

REM 启动场景编排服务
echo 📋 启动场景编排服务...
docker-compose up -d scenario-service

REM 启动测试执行服务
echo 🚀 启动测试执行服务...
docker-compose up -d execution-service

REM 等待服务就绪
timeout /t 10 /nobreak >nul

echo.
echo ✅ 服务启动完成！
echo.
echo 📊 服务访问地址：
echo   - AI服务API文档: http://localhost:8000/docs
echo   - Neo4j浏览器: http://localhost:7474 (用户名: neo4j, 密码: password)
echo   - RabbitMQ管理: http://localhost:15672 (用户名: admin, 密码: password)
echo.
echo 🔍 查看日志：
echo   docker-compose logs -f ai-service
echo.
echo 🛑 停止服务：
echo   docker-compose down
echo.
pause

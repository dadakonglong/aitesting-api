# AI Testing API (AI 测试平台)

这是一个现代化、AI 驱动的自动化测试平台。本项目采用微服务架构，包含前端展示、AI 处理服务、场景编排、测试执行引擎以及各类数据库与中间件。

## 运行环境与版本要求

为了保证项目的顺利运行，请确保您的部署环境满足以下版本要求。项目支持使用 **Docker (推荐)** 部署，也支持在符合条件的宿主机上进行**原生部署**。

### 1. 核心运行环境

*   **Docker & Docker Compose** (推荐部署方式)
    *   **Docker**: 版本 >= 20.10.0
    *   **Docker Compose**: 版本 >= v2.0.0 (支持 `docker-compose.yml` version 3.8)

*   **前端环境 (Frontend - Next.js)**
    *   **Node.js**: >= 18.17.0 (推荐使用 LTS 版本，如 18.x 或 20.x，Next.js 14 依赖 Node.js 18.17+)
    *   **包管理器**: npm, yarn 或 pnpm

*   **后端微服务核心环境**
    *   **Python**: >= 3.8 (AI 处理服务 `ai-processing` 使用 FastAPI 0.115.0+ 和 LangChain 框架。*注：若是特定的老旧系统原生环境级联部署，针对某些脚本可勉强兼容 Python 3.6.8*)
    *   **Go**: >= 1.20 (用于高并发调度服务：场景编排 `scenario-orchestration`、测试执行 `test-execution`、知识图谱 `kg-service`)

### 2. 数据存储与中间件服务 (基础设施)

如果您不使用 Docker 而是手动原生安装以下服务，请务必保证版本一致性：

*   **关系型数据库 (PostgreSQL)**
    *   **版本要求**: 15.x
    *   **说明**: 平台的主力业务数据库。
*   **知识图谱数据库 (Neo4j)**
    *   **版本要求**: 5.12
    *   **说明**: **必须**安装并开启 `APOC` 插件。
*   **向量数据库 (Qdrant)**
    *   **版本要求**: v1.7.4
    *   **说明**: 用于存储测试资产的向量数据，支撑 AI 的相似度检索和 RAG (检索增强生成)。
*   **缓存与分布式状态 (Redis)**
    *   **版本要求**: 7.x
*   **消息队列中间件 (RabbitMQ)**
    *   **版本要求**: 3.x
    *   **说明**: 推荐使用带 `management` 管理界面的版本。

## 部署概览

### 方式一：Docker Compose 推荐部署
在项目根目录，复制并配置 `.env` 文件后，可以直接通过以下命令启动全栈服务：
```bash
docker-compose up -d
```

### 方式二：前后端一体开发镜像（只换代码、不重复装包）
适合日常开发：**依赖在镜像内预装**，运行时只挂载代码；以后每次只更新代码文件即可，无需重新执行 `npm install` / `pip install`。

- **前端**：`cd frontend && npm run dev`（端口 3000）
- **后端**：`python services/ai-processing/main_sqlite.py`（即 uvicorn main_sqlite，端口 8000）

```bash
# 构建并启动（首次会构建镜像，之后只需 up）
docker-compose -f docker-compose.dev.full.yml up -d --build

# 以后只改代码时，直接重启或依赖 --reload 热更即可
docker-compose -f docker-compose.dev.full.yml restart
```

镜像由 `Dockerfile.dev.full` 构建，编排文件为 `docker-compose.dev.full.yml`。构建为增量友好：仅当 `requirements.txt` 或 `package.json`/`package-lock.json` 变更时才会重新装包；启用 BuildKit 时 pip/npm 会复用缓存，重复构建更快（Docker 23+ 默认开启，旧版可 `export DOCKER_BUILDKIT=1`）。

#### 打包成镜像文件并在其他服务器还原

在当前机器（已能正常运行的环境）打包镜像：

```bash
# 若尚未构建过，先构建
docker-compose -f docker-compose.dev.full.yml build

# 导出镜像为 tar 文件（可拷到 U 盘或 scp 到目标机）
docker save aitesting-api-dev-full -o aitesting-api-dev-full.tar
```

在**其他服务器**上还原并运行：

1. 将 `aitesting-api-dev-full.tar` 和**项目代码**（整个仓库或至少包含 `docker-compose.offline.yml`、`frontend/`、`services/` 等）拷到目标机同一目录。
2. 在该目录执行：

```bash
# 加载镜像
docker load -i aitesting-api-dev-full.tar

# 使用离线 compose 启动（不构建，只跑已有镜像）
docker-compose -f docker-compose.offline.yml up -d
```

目标机只需安装 Docker 和 Docker Compose，无需 Node/Python 环境。端口 3000（前端）、8000（后端）会与当前机器一致。

### 方式三：定制化脚本部署
项目根目录下包含众多的运维脚本（如 `deploy_docker_backend.py`, `deploy_aliyun.py`, `deploy_native_ultimate.py`），可根据您的实际宿主机环境和基础系统（如阿里云机房、本地原生 Python/Nodejs 混合裸机）运行对应脚本进行适配部署或环境清理修复。

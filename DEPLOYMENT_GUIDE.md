# 项目部署指南 - 在其他电脑上运行本项目

## 📋 目录
- [环境要求](#环境要求)
- [快速部署（推荐）](#快速部署推荐)
- [手动部署](#手动部署)
- [常见问题](#常见问题)

---

## 🔧 环境要求

### 必需软件
1. **Node.js** 18.0 或更高版本
   - 下载地址: https://nodejs.org/
   - 验证安装: `node --version`

2. **Python** 3.11 或更高版本
   - 下载地址: https://www.python.org/downloads/
   - 验证安装: `python --version`

3. **Git** (用于克隆项目)
   - 下载地址: https://git-scm.com/
   - 验证安装: `git --version`

### 可选软件（用于完整功能）
- **Docker Desktop** (如需使用 Neo4j、Qdrant 等完整功能)
- **Go** 1.21+ (如需运行 Go 微服务)

---

## 🚀 快速部署（推荐）

### 方式一：轻量级部署（仅核心功能）

这种方式**不需要 Docker**，适合快速体验核心功能。

#### 步骤 1: 获取项目代码

```bash
# 如果从 GitHub 克隆
git clone <你的仓库地址>
cd aitesting-api

# 或者直接复制整个项目文件夹到新电脑
```

#### 步骤 2: 安装前端依赖

```bash
cd frontend
npm install
```

#### 步骤 3: 安装 Python 依赖

```bash
cd ..
cd services/ai-processing
pip install -r requirements.txt
```

#### 步骤 4: 配置环境变量

在项目根目录创建 `.env` 文件（或复制 `.env.example`）:

```env
# AI 配置
OPENAI_API_KEY=你的API密钥
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 数据库配置（轻量级模式使用 SQLite，无需配置）
```

#### 步骤 5: 启动服务

**打开两个终端窗口：**

**终端 1 - 启动后端服务:**
```bash
# 在项目根目录
python services/ai-processing/main_sqlite.py
```

**终端 2 - 启动前端服务:**
```bash
cd frontend
npm run dev
```

#### 步骤 6: 访问应用

打开浏览器访问: **http://localhost:3000**

---

### 方式二：完整部署（包含所有功能）

这种方式需要 Docker，可以使用完整的知识图谱和向量检索功能。

#### 步骤 1: 安装 Docker Desktop

- Windows: https://docs.docker.com/desktop/install/windows-install/
- Mac: https://docs.docker.com/desktop/install/mac-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

#### 步骤 2: 获取项目代码

```bash
git clone <你的仓库地址>
cd aitesting-api
```

#### 步骤 3: 配置环境变量

复制并编辑环境变量文件:

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENAI_API_KEY
```

#### 步骤 4: 启动所有服务

**Windows:**
```bash
.\scripts\start.bat
```

**Linux/Mac:**
```bash
chmod +x ./scripts/start.sh
./scripts/start.sh
```

#### 步骤 5: 访问各个服务

- **前端应用**: http://localhost:3000
- **AI 服务 API**: http://localhost:8000/docs
- **Neo4j 浏览器**: http://localhost:7474 (用户名: neo4j, 密码: password)
- **RabbitMQ 管理**: http://localhost:15672 (用户名: guest, 密码: guest)

---

## 🛠️ 手动部署

### 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev

# 或生产模式构建
npm run build
npm start
```

### Python 后端部署

```bash
cd services/ai-processing

# 安装依赖
pip install -r requirements.txt

# 轻量级模式（使用 SQLite + 内存向量库）
python main_sqlite.py

# 或完整模式（需要 PostgreSQL + Qdrant）
python main.py
```

### Go 微服务部署（可选）

```bash
# 场景编排服务
cd services/scenario-orchestration
go mod download
go run main.go

# 测试执行服务
cd services/test-execution
go mod download
go run main.go

# 知识图谱服务
cd services/kg-service
go mod download
go run main.go
```

---

## 📦 项目打包与传输

### 方法 1: 使用 Git

```bash
# 在原电脑上
git add .
git commit -m "项目备份"
git push origin main

# 在新电脑上
git clone <仓库地址>
```

### 方法 2: 直接复制文件夹

**需要复制的文件夹:**
```
aitesting-api/
├── frontend/          # 前端代码
├── services/          # 后端服务
├── .env              # 环境变量（记得修改敏感信息）
├── .env.example      # 环境变量模板
├── package.json      # 项目配置
└── README.md         # 说明文档
```

**可以忽略的文件夹（会自动生成）:**
```
frontend/node_modules/     # npm install 会重新生成
frontend/.next/            # npm run dev 会重新生成
services/**/__pycache__/   # Python 运行时生成
services/**/*.pyc          # Python 编译文件
.git/                      # Git 历史（可选）
```

**压缩打包命令:**
```bash
# 排除 node_modules 等大文件夹
tar -czf aitesting-api.tar.gz \
  --exclude=node_modules \
  --exclude=.next \
  --exclude=__pycache__ \
  --exclude=.git \
  aitesting-api/
```

---

## ⚙️ 环境变量配置说明

在新电脑上，你需要配置 `.env` 文件:

```env
# ============ AI 配置 ============
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx        # 必填：你的 OpenAI API 密钥
OPENAI_API_BASE=https://api.openai.com/v1 # API 地址
OPENAI_MODEL=gpt-4                         # 使用的模型

# ============ 数据库配置 ============
# 轻量级模式（默认）- 使用 SQLite，无需配置
# 完整模式需要配置以下内容：

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aitesting

# Neo4j (知识图谱)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant (向量数据库)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

---

## 🔍 验证部署是否成功

### 1. 检查前端服务

打开浏览器访问 http://localhost:3000，应该能看到登录页面或主界面。

### 2. 检查后端服务

访问 http://localhost:8000/docs，应该能看到 API 文档页面（Swagger UI）。

### 3. 测试 AI 功能

在前端界面中尝试：
- 导入 Swagger 文档
- 生成测试场景
- 执行测试用例

---

## ❓ 常见问题

### Q1: 提示 "找不到模块" 或 "ModuleNotFoundError"

**解决方案:**
```bash
# 重新安装 Python 依赖
cd services/ai-processing
pip install -r requirements.txt

# 或使用虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Q2: 前端启动失败，提示端口被占用

**解决方案:**
```bash
# 方法 1: 修改端口
# 编辑 frontend/package.json，修改 dev 脚本:
"dev": "next dev -p 3001"

# 方法 2: 杀掉占用端口的进程
# Windows
netstat -ano | findstr :3000
taskkill /PID <进程ID> /F

# Linux/Mac
lsof -ti:3000 | xargs kill -9
```

### Q3: Python 后端启动失败

**检查步骤:**
1. 确认 Python 版本 >= 3.11: `python --version`
2. 确认已安装依赖: `pip list`
3. 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
4. 查看错误日志，确认具体错误信息

### Q4: Docker 服务启动失败

**解决方案:**
```bash
# 检查 Docker 是否运行
docker --version
docker ps

# 重启 Docker 服务
# Windows: 右键 Docker Desktop 图标 -> Restart

# 查看服务日志
docker-compose logs

# 重新启动所有服务
docker-compose down
docker-compose up -d
```

### Q5: 数据库连接失败

**轻量级模式（推荐）:**
使用 `main_sqlite.py`，无需配置数据库，自动使用 SQLite。

**完整模式:**
确保 Docker 中的数据库服务已启动:
```bash
docker-compose ps
# 应该看到 postgres, neo4j, qdrant, redis 等服务在运行
```

### Q6: 如何在生产环境部署？

**前端构建:**
```bash
cd frontend
npm run build
npm start  # 或使用 PM2、Nginx 等
```

**后端部署:**
```bash
# 使用 gunicorn 或 uvicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main_sqlite:app
```

---

## 📞 获取帮助

如果遇到问题:
1. 查看项目根目录的 `README.md`
2. 查看 `QUICKSTART.md` 快速开始指南
3. 检查 `docs/` 目录下的详细文档
4. 查看项目的 GitHub Issues

---

## 📝 部署检查清单

在新电脑上部署前，请确认：

- [ ] 已安装 Node.js (>= 18.0)
- [ ] 已安装 Python (>= 3.11)
- [ ] 已安装 Git
- [ ] 已获取项目代码
- [ ] 已配置 `.env` 文件（特别是 `OPENAI_API_KEY`）
- [ ] 已安装前端依赖 (`npm install`)
- [ ] 已安装 Python 依赖 (`pip install -r requirements.txt`)
- [ ] 已启动后端服务 (`python main_sqlite.py`)
- [ ] 已启动前端服务 (`npm run dev`)
- [ ] 可以访问 http://localhost:3000

---

**祝你部署顺利！🎉**

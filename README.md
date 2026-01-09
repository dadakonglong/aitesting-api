# AI智能接口测试平台

基于AI+知识图谱的智能接口自动化测试平台，支持自然语言生成测试场景。

## 核心功能

- 🤖 **AI场景生成** - 自然语言描述 → 自动生成完整测试场景
- 🔍 **智能检索** - 从海量接口中精准检索正确的调用链
- 🧠 **知识图谱** - 存储接口依赖关系，智能推荐
- 📊 **向量检索** - 语义搜索，相似场景推荐
- 🔗 **多数据源** - 支持Swagger、Postman、HAR等多种格式
- 📤 **MeterSphere集成** - 导出测试用例到MeterSphere

## 技术栈

### 后端服务
- Go 1.21+ (场景编排、测试执行、知识图谱服务)
- Python 3.11+ (AI处理、向量化服务)
- Neo4j 5.12 (知识图谱数据库)
- Qdrant 1.7+ (向量数据库)
- PostgreSQL 15 (业务数据库)
- Redis 7 (缓存)
- RabbitMQ 3 (消息队列)

### 前端
- Next.js 14
- React 18
- TypeScript
- Ant Design

## 项目结构

```
aitesting-api/
├── services/                    # 微服务
│   ├── scenario-orchestration/  # 场景编排服务 (Go)
│   ├── ai-processing/           # AI处理服务 (Python)
│   ├── knowledge-graph/         # 知识图谱服务 (Go)
│   ├── test-execution/          # 测试执行服务 (Go)
│   ├── data-collection/         # 数据采集服务 (Go)
│   └── vector-rag/              # 向量RAG服务 (Python)
├── frontend/                    # 前端应用
├── docker-compose.yml           # Docker编排
├── docs/                        # 文档
└── scripts/                     # 脚本工具
```

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Python 3.11+ (用于运行测试脚本)

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 OPENAI_API_KEY
```

### 3. 启动服务

```bash
# Windows
.\scripts\start.bat

# Linux/Mac
chmod +x ./scripts/start.sh
./scripts/start.sh
```

### 4. 运行端到端测试

```bash
# 安装测试依赖
pip install httpx

# 运行完整测试
python scripts/test_e2e.py
```

### 5. 访问应用

- AI服务API文档: http://localhost:8000/docs
- 场景编排服务: http://localhost:8081/health
- 测试执行服务: http://localhost:8083/health
- Neo4j浏览器: http://localhost:7474
- RabbitMQ管理: http://localhost:15672

## 开发指南

详见 [开发文档](./docs/development.md)

## License

MIT

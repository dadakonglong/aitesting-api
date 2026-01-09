# 开发指南

## 快速开始

### 1. 环境准备

**必需软件：**
- Docker Desktop
- Git
- Python 3.11+ (本地开发)
- Go 1.21+ (本地开发)
- Node.js 18+ (前端开发)

### 2. 克隆项目

```bash
git clone <repository-url>
cd aitesting-api
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，配置必要参数
# 特别是OPENAI_API_KEY
```

### 4. 启动服务

**Windows:**
```bash
.\scripts\start.bat
```

**Linux/Mac:**
```bash
chmod +x ./scripts/start.sh
./scripts/start.sh
```

### 5. 访问服务

- **AI服务API文档**: http://localhost:8000/docs
- **Neo4j浏览器**: http://localhost:7474
- **RabbitMQ管理**: http://localhost:15672

## 本地开发

### AI处理服务（Python）

```bash
cd services/ai-processing

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload --port 8000
```

## API使用示例

### 1. 导入Swagger文档

```bash
curl -X POST "http://localhost:8000/api/v1/import/swagger" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "swagger",
    "source": "https://petstore.swagger.io/v2/swagger.json",
    "project_id": "test-project"
  }'
```

### 2. AI场景生成

```bash
curl -X POST "http://localhost:8000/api/v1/rag/enhance-scenario" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "测试用户登录后下单购买商品",
    "project_id": "test-project"
  }'
```

### 3. 语义搜索接口

```bash
curl -X POST "http://localhost:8000/api/v1/vector/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "用户登录",
    "limit": 5,
    "filter_type": "api",
    "project_id": "test-project"
  }'
```

## 项目结构

```
aitesting-api/
├── services/
│   └── ai-processing/          # AI处理服务
│       ├── adapters/           # 数据源适配器
│       ├── services/           # 核心服务
│       ├── routers/            # API路由
│       ├── main.py             # 主入口
│       └── requirements.txt    # Python依赖
├── scripts/                    # 脚本工具
├── docker-compose.yml          # Docker编排
└── README.md                   # 项目说明
```

## 常见问题

### Q: 如何查看服务日志？

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f ai-service
```

### Q: 如何重启服务？

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart ai-service
```

### Q: 如何停止服务？

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 下一步

- [ ] 开发场景编排服务（Go）
- [ ] 开发知识图谱服务（Go）
- [ ] 开发前端界面（Next.js）
- [ ] 集成MeterSphere导出功能

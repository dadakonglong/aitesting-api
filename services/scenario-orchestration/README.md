# 场景编排服务

## 功能

- 创建测试场景（自然语言输入）
- 生成测试用例
- 管理场景和用例
- 与AI服务集成

## API端点

### 场景管理

```
POST   /api/v1/scenarios              创建场景
GET    /api/v1/scenarios              列出场景
GET    /api/v1/scenarios/{id}         获取场景详情
POST   /api/v1/scenarios/{id}/generate-case  生成测试用例
```

## 本地开发

```bash
cd services/scenario-orchestration

# 下载依赖
go mod download

# 运行服务
go run cmd/server/main.go
```

## Docker运行

```bash
docker-compose up -d scenario-service
```

## 环境变量

- `SCENARIO_SERVICE_PORT`: 服务端口（默认8081）
- `DATABASE_URL`: PostgreSQL连接字符串
- `REDIS_URL`: Redis连接字符串
- `RABBITMQ_URL`: RabbitMQ连接字符串
- `AI_SERVICE_URL`: AI服务地址
- `KG_SERVICE_URL`: 知识图谱服务地址

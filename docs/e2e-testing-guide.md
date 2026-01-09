# 端到端测试指南

## 快速开始

### 1. 启动所有服务

```bash
# Windows
.\scripts\start.bat

# Linux/Mac
./scripts/start.sh
```

这将启动以下服务：
- PostgreSQL (数据库)
- Neo4j (知识图谱)
- Qdrant (向量数据库)
- Redis (缓存)
- RabbitMQ (消息队列)
- AI处理服务 (端口8000)
- 场景编排服务 (端口8081)
- 测试执行服务 (端口8083)

### 2. 运行端到端测试

```bash
# 安装依赖
pip install httpx

# 运行测试
python scripts/test_e2e.py
```

## 测试流程

端到端测试脚本会自动执行以下流程：

### 步骤1: 导入Swagger文档
- 从Petstore API导入接口定义
- 自动向量化并索引到Qdrant

### 步骤2: 创建测试场景
- 输入自然语言描述
- AI理解并解析场景
- 生成测试步骤序列

### 步骤3: 生成测试用例
- 为每个步骤生成测试数据
- 自动生成断言规则
- 配置参数映射

### 步骤4: 执行测试
- 发送HTTP请求
- 验证响应断言
- 记录执行结果

### 步骤5: 展示结果
- 执行摘要
- 步骤详情
- 断言结果

## 预期输出

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
AI智能接口测试平台 - 端到端测试
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

🔍 检查服务状态...
✅ AI服务 就绪
✅ 场景编排服务 就绪
✅ 测试执行服务 就绪

============================================================
步骤1: 导入Swagger文档
============================================================
✅ 导入成功: 20 个接口
   项目ID: e2e-test-project

============================================================
步骤2: 创建测试场景
============================================================
📝 场景描述: 测试查询宠物信息
✅ 场景创建成功
   场景ID: xxx-xxx-xxx
   场景名称: 查询宠物信息
   
   📋 解析出 2 个测试步骤:
      1. GET /pet/{petId}
         根据ID查询宠物信息

============================================================
步骤3: 生成测试用例
============================================================
🎲 数据策略: smart
✅ 测试用例生成成功
   用例ID: xxx-xxx-xxx
   步骤数: 2

============================================================
步骤4: 执行测试
============================================================
✅ 测试已提交执行
   执行ID: xxx-xxx-xxx
   
⏳ 等待执行完成...
✅ 执行完成

============================================================
步骤5: 测试结果
============================================================

📊 执行摘要:
   状态: ✅ 成功
   耗时: 1234ms
   总步骤数: 2
   成功步骤: 2
   失败步骤: 0
   总断言数: 5
   通过断言: 5
   失败断言: 0
   成功率: 100.00%

📋 步骤详情:
   ✅ 步骤 1
      状态码: 200
      响应时间: 456ms
      断言: 3/3 通过

============================================================
✅ 端到端测试完成！
============================================================
```

## 手动测试

也可以手动调用API进行测试：

### 1. 导入接口
```bash
curl -X POST "http://localhost:8000/api/v1/import/swagger" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "swagger",
    "source": "https://petstore.swagger.io/v2/swagger.json",
    "project_id": "my-project"
  }'
```

### 2. 创建场景
```bash
curl -X POST "http://localhost:8081/api/v1/scenarios" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "natural_language_input": "测试查询宠物信息"
  }'
```

### 3. 生成测试用例
```bash
curl -X POST "http://localhost:8081/api/v1/scenarios/{scenario_id}/generate-case" \
  -H "Content-Type: application/json" \
  -d '{
    "data_strategy": "smart"
  }'
```

### 4. 执行测试
```bash
curl -X POST "http://localhost:8083/api/v1/executions" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "{test_case_id}",
    "environment": "test",
    "base_url": "https://petstore.swagger.io/v2"
  }'
```

### 5. 查看结果
```bash
curl "http://localhost:8083/api/v1/executions/{execution_id}"
```

## 故障排查

### 问题1: 服务启动失败
```bash
# 查看日志
docker-compose logs -f ai-service
docker-compose logs -f scenario-service
docker-compose logs -f execution-service

# 重启服务
docker-compose restart
```

### 问题2: OpenAI API错误
- 检查`.env`文件中的`OPENAI_API_KEY`
- 确认API Key有效且有余额
- 检查网络连接

### 问题3: 测试执行失败
- 检查目标API是否可访问
- 验证base_url是否正确
- 查看执行日志了解详细错误

## 自定义测试场景

你可以修改`test_e2e.py`中的场景描述来测试不同的场景：

```python
scenarios = [
    "测试查询宠物信息",
    "测试添加新宠物后查询",
    "测试更新宠物状态",
    # 添加你自己的场景
]
```

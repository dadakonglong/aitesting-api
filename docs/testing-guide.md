# 快速测试指南

## 前置条件

1. 确保已配置 `.env` 文件中的 `OPENAI_API_KEY`
2. 启动服务：`.\scripts\start.bat` (Windows) 或 `./scripts/start.sh` (Linux/Mac)

## 运行测试

```bash
# 安装测试依赖
pip install httpx

# 运行测试脚本
python scripts/test_core_features.py
```

## 测试内容

测试脚本会依次验证以下功能：

### 1. 导入Swagger文档
- 从 Petstore API 导入接口定义
- 验证接口解析和向量化索引

### 2. 语义搜索
- 测试向量相似度搜索
- 验证能否准确找到相关接口

### 3. AI场景理解
- 测试自然语言理解能力
- 提取测试意图、实体、动作

### 4. RAG增强理解
- 测试检索增强生成
- 验证上下文检索和推荐

### 5. 智能数据生成
- 测试多种数据生成策略
- 验证数据符合schema

### 6. 智能断言生成
- 测试断言规则生成
- 验证断言覆盖度

## 预期输出

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
AI智能接口测试平台 - 核心功能测试
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

✅ 服务状态: healthy

==================================================
测试1: 导入Swagger文档
==================================================
✅ 导入成功: 20 个接口
   项目ID: test-project

==================================================
测试2: 语义搜索接口
==================================================
🔍 搜索: 查询宠物信息
   找到 3 个相关接口:
   1. GET /pet/{petId} - Find pet by ID
      相似度: 0.856
...

==================================================
✅ 所有测试完成！
==================================================
```

## 手动测试

也可以通过API文档手动测试：http://localhost:8000/docs

### 示例：完整的AI场景生成流程

1. **导入接口**
```bash
curl -X POST "http://localhost:8000/api/v1/import/swagger" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "swagger",
    "source": "https://petstore.swagger.io/v2/swagger.json",
    "project_id": "my-project"
  }'
```

2. **RAG增强理解**
```bash
curl -X POST "http://localhost:8000/api/v1/rag/enhance-scenario" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "测试查询宠物信息后更新宠物状态",
    "project_id": "my-project"
  }'
```

3. **生成测试数据**
```bash
curl -X POST "http://localhost:8000/api/v1/ai/generate-data" \
  -H "Content-Type: application/json" \
  -d '{
    "param_schema": {
      "name": {"type": "string"},
      "status": {"type": "string"}
    },
    "strategy": "smart",
    "count": 3
  }'
```

## 故障排查

### 问题1: 服务未启动
```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs ai-service
```

### 问题2: OpenAI API错误
- 检查 `.env` 中的 `OPENAI_API_KEY` 是否正确
- 检查网络连接
- 查看服务日志确认错误信息

### 问题3: 向量搜索无结果
- 确保已导入接口数据
- 等待几秒让索引完成
- 检查 Qdrant 服务是否正常运行

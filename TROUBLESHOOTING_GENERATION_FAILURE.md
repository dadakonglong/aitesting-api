# 生成用例失败 - 故障排查指南

## 🔍 问题现象

前端显示："生成测试用例失败"

## 📋 可能的原因

### 1. 后端服务未启动

**检查方法：**
```bash
# 检查Docker容器
docker ps | findstr ai-service

# 或检查进程
curl http://localhost:8000/health
```

**解决方法：**
```bash
# 启动服务
docker-compose up -d ai-service

# 或直接运行
cd services/ai-processing
python main_sqlite.py
```

### 2. AI API Key未配置或无效

**检查方法：**
```bash
# 查看.env文件
type .env | findstr API_KEY
```

**解决方法：**
在`.env`文件中配置：
```
OPENAI_API_KEY=your_key_here
# 或
DEEPSEEK_API_KEY=your_key_here
AI_PROVIDER=deepseek
```

### 3. 项目中没有API数据

**检查方法：**
```bash
python check_db.py
```

**解决方法：**
- 先导入API数据（Swagger/Postman）
- 确保选择了正确的项目

### 4. AI生成的JSON格式错误

**检查方法：**
查看后端日志：
```bash
docker logs aitesting-ai-service
```

**解决方法：**
- 检查system_prompt格式
- 确保AI返回的是有效的JSON

### 5. 数据库连接问题

**检查方法：**
```bash
# 检查数据库文件是否存在
dir data\apis.db
```

**解决方法：**
- 确保数据库文件存在
- 检查文件权限

## 🔧 快速诊断步骤

### 步骤1: 测试AI服务

```bash
python test_ai_generation.py
```

**预期输出：**
```
✅ AI响应成功:
{'test': 'success'}
```

### 步骤2: 检查数据库

```bash
python check_db.py
```

**预期输出：**
```
API总数量: 34
汇金ERP: 17个API
```

### 步骤3: 测试完整流程

```bash
python test_scenario_generation.py
```

**预期输出：**
```
✅ 场景生成测试成功!
```

### 步骤4: 查看后端日志

如果使用Docker：
```bash
docker logs -f aitesting-ai-service
```

如果直接运行：
查看控制台输出

## 💡 常见错误及解决方案

### 错误1: "AI 服务不可用"

**原因：** API Key无效或网络问题

**解决：**
1. 检查API Key是否正确
2. 检查网络连接
3. 如果使用代理，检查代理配置

### 错误2: "场景不存在"

**原因：** 场景ID不正确

**解决：**
1. 检查场景是否已创建
2. 确认场景ID正确

### 错误3: "数据库中没有API数据"

**原因：** 项目中没有导入API

**解决：**
1. 先导入Swagger或Postman数据
2. 确保选择了正确的项目

### 错误4: JSON解析失败

**原因：** AI返回的不是有效JSON

**解决：**
1. 检查system_prompt
2. 确保使用了`response_format={"type": "json_object"}`
3. 尝试使用更强的模型（GPT-4）

## 🎯 当前问题的可能原因

根据你的情况，最可能的原因是：

1. **后端服务未正确启动**
   - Docker Desktop未运行
   - 容器未启动

2. **项目选择问题**
   - 前端选择的项目中没有API数据
   - 需要先导入API

## ✅ 解决步骤

### 1. 启动Docker Desktop

确保Docker Desktop正在运行

### 2. 启动服务

```bash
cd D:\testc\aitesting-api
docker-compose up -d
```

### 3. 检查服务状态

```bash
docker ps
```

应该看到：
- aitesting-ai-service
- aitesting-postgres
- aitesting-redis
等容器在运行

### 4. 测试AI服务

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"healthy"}
```

### 5. 重新尝试生成

在前端重新点击"生成测试用例"

## 📞 仍然失败？

如果以上步骤都完成了还是失败，请：

1. 查看后端日志：
   ```bash
   docker logs aitesting-ai-service
   ```

2. 查看浏览器控制台的错误信息

3. 运行完整测试：
   ```bash
   python test_scenario_generation.py
   ```

4. 提供错误信息以便进一步诊断

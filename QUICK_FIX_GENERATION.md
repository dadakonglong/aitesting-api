# 场景生成失败 - 快速修复指南

## 🔍 问题现象

点击"一键生成测试用例"后，提示"生成测试用例失败"

## ✅ 快速检查清单

### 1. 检查后端服务是否运行

```bash
# 检查AI服务
curl http://localhost:8000/health

# 应该返回: {"status":"healthy"}
```

如果服务未运行，启动服务：
```bash
# 使用Docker
docker-compose up -d ai-service

# 或直接运行
cd services/ai-processing
python main_sqlite.py
```

### 2. 检查环境变量

查看`.env`文件：
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

或使用DeepSeek：
```bash
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here
```

### 3. 检查项目数据

```bash
python diagnose_generation_failure.py
```

确认：
- ✅ 汇金ERP项目有API数据
- ✅ AI服务配置正确

### 4. 检查浏览器控制台

打开浏览器开发者工具（F12），查看：
- Network标签：查看API请求是否成功
- Console标签：查看是否有JavaScript错误

## 🔧 常见问题

### 问题1: 服务未运行

**症状：** 请求失败，无法连接

**解决：**
```bash
# 启动AI服务
cd services/ai-processing
python main_sqlite.py
```

### 问题2: API Key未配置

**症状：** AI调用失败

**解决：**
1. 编辑`.env`文件
2. 添加`OPENAI_API_KEY=your_key`
3. 重启服务

### 问题3: 网络问题

**症状：** AI调用超时

**解决：**
- 检查网络连接
- 如果在国内，可能需要配置代理
- 或使用DeepSeek（国内服务）

### 问题4: 项目中没有API

**症状：** AI无法生成步骤

**解决：**
1. 先导入API数据
2. 确认选择了正确的项目

## 📝 详细错误信息

修改后的前端会显示详细错误，包括：
- 具体的错误原因
- 后端返回的错误信息

## 🚀 测试AI服务

运行测试脚本：
```bash
python test_ai_generation.py
```

应该看到：
```
✅ AI响应成功:
{'test': 'success'}
```

## 💡 建议

1. **先测试简单场景**
   - 输入："测试登录"
   - 看是否能成功生成

2. **查看后端日志**
   - 如果使用Docker：`docker logs aitesting-ai-service`
   - 如果直接运行：查看终端输出

3. **检查数据库**
   ```bash
   python check_db.py
   ```

## ✅ 成功标志

生成成功后会显示：
- ✅ 场景名称
- ✅ 测试步骤数量
- ✅ "去执行场景"按钮

## 📞 仍然失败？

1. 运行完整诊断：
   ```bash
   python diagnose_generation_failure.py
   ```

2. 查看详细错误信息（浏览器控制台）

3. 检查后端日志

4. 确认AI服务可以访问外网

# 启动AI服务 - 简单指南

## 🎯 问题

前端显示"生成测试用例失败"，因为**后端AI服务没有运行**。

## ✅ 解决方案

### 方式1: 直接启动（推荐）

打开一个新的终端窗口，运行：

```bash
cd services/ai-processing
python main_sqlite.py
```

**预期输出：**
```
✅ 数据库架构已就绪
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**保持这个终端窗口打开！**

### 方式2: 使用Docker

```bash
docker-compose up -d ai-service
```

### 方式3: 后台运行

Windows:
```bash
start /B python services/ai-processing/main_sqlite.py
```

Linux/Mac:
```bash
nohup python services/ai-processing/main_sqlite.py &
```

## 🔍 验证服务运行

打开浏览器访问：
```
http://localhost:8000/docs
```

应该看到Swagger API文档页面。

或使用命令：
```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"healthy"}
```

## 🚀 启动后

1. **保持服务运行**
2. **刷新前端页面**
3. **重新尝试生成场景**

现在应该能看到详细的错误信息（如果还有问题）。

## 📝 注意事项

1. **端口占用**
   - 如果8000端口被占用，修改`.env`中的端口
   - 或停止占用8000端口的程序

2. **环境变量**
   - 确保`.env`文件中配置了`OPENAI_API_KEY`
   - 或配置`DEEPSEEK_API_KEY`和`AI_PROVIDER=deepseek`

3. **依赖安装**
   - 如果提示缺少模块，运行：
     ```bash
     cd services/ai-processing
     pip install -r requirements.txt
     ```

## 🎉 成功标志

服务启动成功后：
- ✅ 终端显示"Uvicorn running on http://0.0.0.0:8000"
- ✅ 访问http://localhost:8000/docs能看到API文档
- ✅ 前端能成功生成场景

## ❓ 仍然失败？

1. 检查终端的错误信息
2. 确认8000端口没有被占用
3. 确认环境变量配置正确
4. 查看浏览器控制台的详细错误

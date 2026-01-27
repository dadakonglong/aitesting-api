# 快速配置指南 - 新电脑部署

## 问题说明
在新电脑上配置项目时，可能会遇到依赖安装缓慢或卡顿的问题。本指南提供了优化的安装方案。

## 解决方案

### 方案一：分步安装（推荐）

#### 1. 创建并激活虚拟环境
```powershell
cd D:\wjy\aitesting-api
python -m venv venv
.\venv\Scripts\activate
```

#### 2. 升级 pip（重要！）
```powershell
python -m pip install --upgrade pip
```

#### 3. 安装核心依赖
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi==0.109.0 uvicorn[standard]==0.27.0
```

#### 4. 安装其他基础依赖
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pydantic==2.5.3 pydantic-settings==2.1.0 httpx==0.26.0 python-dotenv==1.0.0 python-multipart==0.0.6 faker==22.6.0
```

#### 5. 安装 AI 相关依赖（可选，如果需要 AI 功能）
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai langchain langchain-openai langchain-community
```

#### 6. 安装向量数据库客户端（可选）
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple qdrant-client==1.7.1
```

### 方案二：使用最小化依赖文件

```powershell
cd D:\wjy\aitesting-api
.\venv\Scripts\activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r services/ai-processing/requirements-minimal.txt
```

如果需要 AI 功能，再安装：
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r services/ai-processing/requirements-ai.txt
```

### 方案三：使用国内镜像源（如果方案一仍然很慢）

#### 配置 pip 使用清华镜像源
```powershell
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

然后安装：
```powershell
pip install -r services/ai-processing/requirements-minimal.txt
```

## 验证安装

安装完成后，运行以下命令验证：

```powershell
python services/ai-processing/main_sqlite.py
```

如果看到类似以下输出，说明安装成功：
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

## 常见问题

### 1. 安装卡在 "preparing metadata"
- **原因**：网络问题或包依赖解析慢
- **解决**：使用国内镜像源（清华、阿里云等）

### 2. 缺少某些模块
- **原因**：某些依赖没有安装
- **解决**：根据错误提示单独安装缺失的包

### 3. SSL 证书错误
- **解决**：
  ```powershell
  pip install --trusted-host pypi.tuna.tsinghua.edu.cn --trusted-host pypi.org --trusted-host files.pythonhosted.org <package-name>
  ```

## 最小运行要求

如果只是想快速测试项目是否能运行，只需安装以下核心包：
- fastapi
- uvicorn
- pydantic
- httpx
- python-dotenv

AI 功能可以后续按需安装。

## 前端配置

别忘了配置前端：

```powershell
cd frontend
npm install
npm run dev
```

## 环境变量配置

创建 `.env` 文件（如果需要 AI 功能）：
```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 数据库

项目使用 SQLite，无需额外配置。数据库文件会自动创建在：
```
services/ai-processing/ai_test_platform.db
```

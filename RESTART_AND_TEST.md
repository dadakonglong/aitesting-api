# 重启服务并测试

## 🔧 已添加调试日志

在执行引擎中添加了详细的调试日志，用于追踪token提取过程。

## 🚀 下一步操作

### 1. 重启AI服务

**停止当前服务** (如果在运行)：
- 按 Ctrl+C 停止

**重新启动服务：**
```bash
cd services/ai-processing
python main_sqlite.py
```

### 2. 执行场景测试

在前端：
1. 选择"汇金ERP"项目
2. 进入"测试场景"页面
3. 选择一个场景
4. 点击"执行测试"

### 3. 查看调试日志

在AI服务的终端窗口中，你会看到类似的日志：

```
DEBUG: Starting step 1 [POST /shouyin/api/login/phone]
DEBUG: Step 1 response status: 200
DEBUG: Saving step 1 to context
DEBUG: Response contains token: P7UtZfctMCjYTWyXNGawXblR4T...

DEBUG: Starting step 2 [POST /api/v3/order/open-pay]
DEBUG: Extracting from step 1
DEBUG: from_field = data.token
DEBUG: extracted value = P7UtZfctMCjYTWyXNGawXblR4T...
DEBUG: Set header Authorization = Bearer P7UtZfctMCjYTWyXNGawXblR4T...
DEBUG: Step 2 response status: 200
```

### 4. 分析日志

**关键检查点：**

1. **步骤1保存token**
   ```
   DEBUG: Response contains token: xxx...
   ```
   - 如果没有这行，说明响应中没有token

2. **步骤2提取token**
   ```
   DEBUG: extracted value = xxx...
   ```
   - 检查提取的token是否和步骤1返回的一致

3. **步骤2设置header**
   ```
   DEBUG: Set header Authorization = Bearer xxx...
   ```
   - 检查Authorization header的值

### 5. 可能的问题

#### 问题1: Token不一致

如果看到：
```
步骤1: token = ABC...
步骤2: extracted = XYZ...  (不同!)
```

**原因：** Context没有正确保存或提取

#### 问题2: 提取失败

如果看到：
```
DEBUG: WARNING - Could not extract data.token from step 1
```

**原因：** 
- Token路径不对
- 或响应结构不同

#### 问题3: Token为空

如果看到：
```
DEBUG: extracted value = None...
```

**原因：**
- 步骤1没有返回token
- 或token字段名不对

## 📊 预期结果

**正常情况：**
```
步骤1: 返回token ABC...
步骤2: 提取token ABC... (相同)
步骤2: 设置Authorization = Bearer ABC...
步骤2: 请求成功
```

**异常情况：**
```
步骤1: 返回token ABC...
步骤2: 提取token XYZ... (不同) ← 问题在这里
步骤2: 请求失败 (401或4200)
```

## 💡 根据日志调整

看到日志后，我们可以：
1. 确认token是否正确提取
2. 确认from_field路径是否正确
3. 找到真正的问题所在

请重启服务并执行测试，然后把调试日志发给我！

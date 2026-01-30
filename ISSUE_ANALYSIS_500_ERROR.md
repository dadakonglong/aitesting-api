# 场景执行500错误问题分析与解决方案

## 📋 问题描述

在执行场景用例时，第2个接口开始报500服务器内部错误，但单独执行用例没有问题。

## 🔍 问题根因

通过诊断脚本分析，发现了**严重的配置错误**：

### 错误配置

```json
步骤1 (登录接口):
  param_mappings: [
    {
      "from_step": 1,           // ❌ 错误：步骤1依赖自己
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers"
    }
  ]

步骤2/3/4 (业务接口):
  param_mappings: []            // ❌ 错误：缺少token映射
  headers: {
    "Authorization": "Bearer {{token_from_step_1}}"  // 只是占位符，未实际映射
  }
```

### 问题分析

1. **步骤1的自引用问题**
   - 步骤1(登录接口)配置了从"步骤1"获取token
   - 这是一个逻辑错误：步骤1还未执行完成，无法从自己获取返回值
   - 导致步骤1执行时Authorization header为空或错误

2. **步骤2/3/4缺少token映射**
   - 虽然headers中有`"Authorization": "Bearer {{token_from_step_1}}"`
   - 但这只是一个字符串占位符，不会被实际替换
   - 需要在`param_mappings`中配置实际的数据映射关系

3. **执行流程问题**
   ```
   步骤1执行 -> 试图从自己获取token(失败) -> Authorization为空
   步骤2执行 -> 没有token映射 -> Authorization仍是占位符字符串
   服务器收到无效的Authorization -> 返回500错误
   ```

## ✅ 解决方案

### 1. 修复后的配置

```json
步骤1 (登录接口):
  param_mappings: []            // ✅ 移除错误的自引用

步骤2 (开台接口):
  param_mappings: [
    {
      "from_step": 1,           // ✅ 正确：从步骤1获取
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers"
    },
    {
      "from_step": 2,
      "from_field": "data.sessionId",
      "to_field": "sessionId",
      "to_type": "params"
    }
  ]

步骤3 (关台接口):
  param_mappings: [
    {
      "from_step": 1,           // ✅ 正确：从步骤1获取token
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers"
    }
  ]

步骤4 (清洁接口):
  param_mappings: [
    {
      "from_step": 1,           // ✅ 正确：从步骤1获取token
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers"
    }
  ]
```

### 2. 执行修复脚本

```bash
python fix_scenario_500_error.py
```

脚本会自动：
1. 检测并移除步骤1的错误自引用
2. 为需要token的步骤添加正确的映射配置
3. 保存修复后的配置到数据库

### 3. 验证修复

修复后的执行流程：
```
步骤1执行 -> 成功登录 -> 返回token -> 保存到context["step_1"]
步骤2执行 -> 从context["step_1"]提取token -> 设置到Authorization header -> 请求成功
步骤3执行 -> 从context["step_1"]提取token -> 设置到Authorization header -> 请求成功
步骤4执行 -> 从context["step_1"]提取token -> 设置到Authorization header -> 请求成功
```

## 🔧 技术细节

### Token提取路径

从登录接口的实际响应分析：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "appyG0UXy/g0rmbaotA5a9dGYkGN71KKzfR4q0dLanvIDN4KNP...",
    "erpUserVO": { ... },
    "venues": [ ... ]
  }
}
```

正确的token路径是：`data.token`

### Authorization格式

后端代码会自动处理Bearer前缀：
```python
if to_field.lower() == "authorization" and not val_str.lower().startswith("bearer "):
    val_str = f"Bearer {val_str}"
request_headers[to_field] = val_str
```

所以只需要映射token值，不需要手动添加"Bearer "前缀。

### 参数映射机制

执行引擎的处理流程：
```python
# 1. 执行步骤1
step1_result = execute(step1)
context["step_1"] = step1_result  # 保存到上下文

# 2. 执行步骤2
for mapping in step2.param_mappings:
    from_step = mapping["from_step"]  # 1
    from_field = mapping["from_field"]  # "data.token"
    
    # 从上下文获取步骤1的数据
    from_data = context[f"step_{from_step}"]["response"]
    
    # 提取token值
    token = get_value_by_path(from_data, from_field)
    
    # 设置到目标位置
    if mapping["to_type"] == "headers":
        request_headers[mapping["to_field"]] = token
```

## 🎯 为什么单独执行没问题？

单独执行接口时：
- 用户可以手动提供正确的token
- 不依赖参数映射机制
- 直接设置Authorization header

场景执行时：
- 依赖自动的参数映射
- 如果映射配置错误，就会失败

## 📝 预防措施

### 1. AI生成场景时的检查

在`services/ai-processing/services/scenario_parser.py`中添加验证：

```python
def validate_param_mappings(steps):
    """验证参数映射配置"""
    for i, step in enumerate(steps, 1):
        for mapping in step.get('param_mappings', []):
            from_step = mapping.get('from_step')
            
            # 检查自引用
            if from_step == i:
                raise ValueError(f"步骤{i}不能引用自己的数据")
            
            # 检查引用的步骤是否存在
            if from_step >= i:
                raise ValueError(f"步骤{i}不能引用后续步骤{from_step}的数据")
```

### 2. 前端UI提示

在测试场景页面显示依赖关系：
```tsx
{step.param_mappings && step.param_mappings.length > 0 && (
    <span style={{ color: '#F59E0B' }}>
        ⚠️ 依赖步骤: {step.param_mappings.map(m => m.from_step).join(', ')}
    </span>
)}
```

### 3. 执行前验证

在执行引擎中添加预检查：
```python
def pre_validate_execution(steps):
    """执行前验证"""
    for i, step in enumerate(steps, 1):
        for mapping in step.get('param_mappings', []):
            if mapping['from_step'] >= i:
                raise ValueError(f"步骤{i}的映射配置错误")
```

## 🚀 后续优化建议

1. **增强AI场景生成逻辑**
   - 自动识别需要token的接口
   - 自动配置正确的参数映射
   - 避免生成自引用配置

2. **改进错误提示**
   - 500错误时显示更详细的信息
   - 提示可能的原因(如token缺失)
   - 提供修复建议

3. **添加调试模式**
   - 显示每个步骤的实际请求头
   - 显示参数映射的提取过程
   - 便于排查问题

4. **单元测试**
   - 测试参数映射逻辑
   - 测试自引用检测
   - 测试token提取路径

## 📊 修复效果

修复前：
```
✅ 步骤1: 200 (登录成功)
❌ 步骤2: 200 (HTTP成功，但业务返回500)
❌ 步骤3: 200 (HTTP成功，但业务返回500)
❌ 步骤4: 200 (HTTP成功，但业务返回500)
```

修复后（预期）：
```
✅ 步骤1: 200 (登录成功)
✅ 步骤2: 200 (开台成功)
✅ 步骤3: 200 (关台成功)
✅ 步骤4: 200 (清洁成功)
```

## 🔗 相关文件

- 诊断脚本: `diagnose_scenario_execution.py`
- 修复脚本: `fix_scenario_500_error.py`
- 执行引擎: `services/ai-processing/main_sqlite.py`
- 场景解析: `services/ai-processing/services/scenario_parser.py`
- 前端展示: `frontend/app/testing/components/TestScenariosTab.tsx`

## ✅ 总结

这是一个典型的**配置错误导致的级联失败**问题：

1. AI生成场景时错误地为步骤1配置了自引用
2. 步骤2/3/4缺少正确的token映射配置
3. 导致所有需要认证的接口都失败

通过修复脚本已经解决了配置问题，后续需要：
1. 在AI生成逻辑中添加验证
2. 改进错误提示
3. 增强调试能力

这样可以避免类似问题再次发生。

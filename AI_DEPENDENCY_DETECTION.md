# AI自动识别参数依赖 - 实现方案

## 🎯 目标

使用大模型自动识别和配置接口间的参数依赖关系，如：
- Token认证依赖
- SessionId业务依赖
- OrderId/UserId等ID依赖

## ✅ 已实现的功能

### 1. 增强的AI Prompt

已更新`services/ai-processing/main_sqlite.py`中的system_prompt：

**核心改进：**
- ✅ 明确教AI识别登录接口和token依赖
- ✅ 教AI识别业务ID依赖（sessionId, orderId等）
- ✅ 明确禁止自引用规则
- ✅ 明确to_type的使用场景
- ✅ 提供清晰的配置示例

### 2. 执行时动态提取

执行引擎已支持：
- ✅ 从前面步骤的响应中提取数据
- ✅ 支持深层路径（data.token, data.user.id）
- ✅ 自动添加Bearer前缀
- ✅ 区分headers/params/url_params

## 🔧 工作流程

```
用户输入意图
    ↓
AI理解意图（NLU）
    ↓
检索相关API（向量搜索）
    ↓
AI分析依赖关系 ← 增强的Prompt
    ↓
生成param_mappings配置
    ↓
保存测试用例
    ↓
执行时动态提取和传递参数
```

## 📝 AI识别依赖的逻辑

### 1. Token依赖识别

AI会检查：
- 第1个接口路径是否包含login/signin/auth
- 后续接口参数是否需要Authorization
- 自动配置：
  ```json
  {
    "from_step": 1,
    "from_field": "data.token",
    "to_field": "Authorization",
    "to_type": "headers"
  }
  ```

### 2. 业务ID依赖识别

AI会检查：
- 创建接口（POST）通常返回新对象的ID
- 后续接口参数名包含xxxId
- 自动配置：
  ```json
  {
    "from_step": 2,
    "from_field": "data.sessionId",
    "to_field": "sessionId",
    "to_type": "params"
  }
  ```

## 🧪 测试示例

### 示例1：登录+业务操作

**用户输入：**
```
测试开关台的完整流程
```

**AI生成（理想情况）：**
```json
{
  "scenario_name": "测试开关台流程",
  "steps": [
    {
      "step_order": 1,
      "api_path": "/api/login",
      "api_method": "POST",
      "param_mappings": []
    },
    {
      "step_order": 2,
      "api_path": "/api/order/open-pay",
      "api_method": "POST",
      "param_mappings": [
        {
          "from_step": 1,
          "from_field": "data.token",
          "to_field": "Authorization",
          "to_type": "headers"
        }
      ]
    },
    {
      "step_order": 3,
      "api_path": "/api/order/close-room",
      "api_method": "POST",
      "param_mappings": [
        {
          "from_step": 1,
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
    }
  ]
}
```

## 🔍 验证AI生成的质量

使用验证工具：
```bash
python improve_scenario_validation.py
```

会自动检查：
- ✅ 是否有自引用错误
- ✅ 是否缺少必要的token映射
- ✅ 是否引用了不存在的步骤
- ✅ 自动修复发现的问题

## 💡 提升AI识别准确率的方法

### 1. 提供更多API信息

在user_prompt中包含：
- API的请求参数详情
- API的响应结构示例
- API的业务描述

### 2. 使用更强的模型

- GPT-4: 更好的理解能力
- GPT-4-turbo: 更快的响应
- Claude-3: 更长的上下文

### 3. Few-shot学习

在prompt中提供成功案例：
```python
system_prompt += """

成功案例参考：
场景：用户登录后创建订单
步骤1（登录）: param_mappings = []
步骤2（创建订单）: param_mappings = [
  {"from_step": 1, "from_field": "data.token", "to_field": "Authorization", "to_type": "headers"}
]
"""
```

## 🚀 未来优化方向

### 1. 响应结构学习

记录每个API的实际响应结构：
```python
# 执行后保存
api_response_patterns = {
  "/api/login": {
    "token_path": "data.token",
    "user_id_path": "data.user.id"
  }
}
```

下次生成时提供给AI参考。

### 2. 依赖关系图谱

构建知识图谱：
```
登录接口 --返回--> token
token --用于--> 所有业务接口的Authorization
开台接口 --返回--> sessionId
sessionId --用于--> 关台接口
```

### 3. 自动修复机制

如果执行失败：
- 分析失败原因
- 自动调整param_mappings
- 重新执行

## 📊 当前效果评估

基于你的项目测试：

**修复前：**
- ❌ AI生成了错误的自引用
- ❌ 缺少必要的token映射
- ❌ 导致500错误

**修复后：**
- ✅ Token正确提取和传递
- ✅ Authorization header正确设置
- ✅ HTTP请求成功（200）
- ⚠️  业务错误（4200）是另一个问题

## ✅ 总结

**Token提取是在执行时动态进行的：**

1. **生成阶段**：AI配置映射关系
2. **执行阶段**：引擎根据映射动态提取

**AI的作用：**
- 分析API列表
- 识别依赖关系
- 生成param_mappings配置

**执行引擎的作用：**
- 执行步骤1，保存响应到context
- 执行步骤2时，从context提取token
- 设置到Authorization header
- 发送请求

这样的设计既灵活又强大！

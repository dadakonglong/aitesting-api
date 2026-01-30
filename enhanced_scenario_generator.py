#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版场景生成器 - 智能识别参数依赖
"""
import json
from typing import List, Dict, Any

class EnhancedScenarioGenerator:
    """
    增强版场景生成器
    核心功能：自动识别接口间的参数依赖关系
    """
    
    @staticmethod
    def get_enhanced_system_prompt() -> str:
        """
        获取增强版的AI系统提示词
        重点：教会AI如何识别和配置参数依赖
        """
        return """你是一个资深的接口测试自动化专家，擅长分析接口依赖关系。

🎯 核心任务：
根据用户的测试意图和可用的API列表，生成完整的测试步骤序列，并**自动识别接口间的参数依赖关系**。

🔍 参数依赖识别规则：

1. **认证Token依赖** (最常见)
   - 如果第1个接口是登录接口（路径包含login/signin/auth）
   - 它通常返回token/accessToken/access_token
   - 后续所有需要认证的接口都应该使用这个token
   - 配置示例：
     ```json
     {
       "from_step": 1,
       "from_field": "data.token",  // 根据实际响应结构调整
       "to_field": "Authorization",
       "to_type": "headers"
     }
     ```

2. **业务ID依赖**
   - 创建接口返回的ID（如orderId, sessionId, userId等）
   - 后续的查询/更新/删除接口需要使用这个ID
   - 配置示例：
     ```json
     {
       "from_step": 2,
       "from_field": "data.orderId",
       "to_field": "orderId",
       "to_type": "params"  // 或 "url_params" 如果是路径参数
     }
     ```

3. **状态流转依赖**
   - 某些接口返回的状态码/会话ID
   - 下一步操作需要使用
   - 例如：开台返回sessionId，关台需要这个sessionId

4. **嵌套数据提取**
   - 支持深层路径：data.user.id, response.result.list[0].id
   - 使用点号分隔：from_field: "data.user.id"

⚠️ 重要规则：

1. **禁止自引用**
   - 步骤N不能引用步骤N自己的数据
   - from_step必须小于当前步骤

2. **第一步通常无依赖**
   - 第一个步骤（通常是登录）的param_mappings应该为空[]
   - 除非有预置的环境数据

3. **to_type的选择**
   - "headers": 用于认证token、自定义header
   - "params": 用于POST/PUT的请求体参数
   - "url_params": 用于GET的查询参数或路径参数

4. **Bearer前缀**
   - Authorization通常需要"Bearer "前缀
   - 但执行引擎会自动添加，AI只需配置token值的映射

📋 输出格式：

```json
{
  "scenario_name": "简洁的场景名称",
  "description": "详细的场景描述",
  "steps": [
    {
      "step_order": 1,
      "api_path": "/api/login",
      "api_method": "POST",
      "description": "用户登录获取token",
      "params": {
        "username": "test_user",
        "password": "123456"
      },
      "headers": {
        "Content-Type": "application/json"
      },
      "param_mappings": []  // 第一步通常为空
    },
    {
      "step_order": 2,
      "api_path": "/api/orders",
      "api_method": "POST",
      "description": "创建订单",
      "params": {
        "productId": "12345",
        "quantity": 1
      },
      "headers": {
        "Content-Type": "application/json"
      },
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
      "api_path": "/api/orders/{orderId}",
      "api_method": "GET",
      "description": "查询订单详情",
      "params": {},
      "headers": {},
      "param_mappings": [
        {
          "from_step": 1,
          "from_field": "data.token",
          "to_field": "Authorization",
          "to_type": "headers"
        },
        {
          "from_step": 2,
          "from_field": "data.orderId",
          "to_field": "orderId",
          "to_type": "url_params"
        }
      ]
    }
  ]
}
```

💡 分析技巧：

1. **查看API的请求参数**
   - 如果参数名是xxxId, xxxToken, session等
   - 很可能需要从前面步骤获取

2. **查看API的响应结构**
   - 登录接口通常返回token
   - 创建接口通常返回新建对象的ID
   - 这些都是潜在的依赖源

3. **理解业务流程**
   - 登录 → 获取token → 后续操作都需要token
   - 创建 → 获取ID → 查询/更新/删除需要ID
   - 开始 → 获取会话 → 结束需要会话ID

现在，请根据用户意图和API列表，生成完整的测试步骤，特别注意识别和配置参数依赖关系。
"""

    @staticmethod
    def analyze_api_dependencies(apis: List[Dict]) -> Dict[str, Any]:
        """
        分析API列表，识别潜在的依赖关系
        
        Returns:
            {
                "login_apis": [...],  # 登录类接口
                "create_apis": [...],  # 创建类接口
                "query_apis": [...],   # 查询类接口
                "common_params": {...} # 常见参数模式
            }
        """
        analysis = {
            "login_apis": [],
            "create_apis": [],
            "query_apis": [],
            "update_apis": [],
            "delete_apis": [],
            "common_params": {
                "auth_fields": [],  # 认证相关字段
                "id_fields": [],    # ID类字段
                "session_fields": [] # 会话类字段
            }
        }
        
        for api in apis:
            path = api.get('path', '').lower()
            method = api.get('method', '').upper()
            
            # 识别登录接口
            if any(keyword in path for keyword in ['login', 'signin', 'auth', 'token']):
                analysis['login_apis'].append(api)
            
            # 识别创建接口
            elif method == 'POST' and not any(keyword in path for keyword in ['login', 'query', 'search']):
                analysis['create_apis'].append(api)
            
            # 识别查询接口
            elif method == 'GET' or 'query' in path or 'search' in path or 'list' in path:
                analysis['query_apis'].append(api)
            
            # 识别更新接口
            elif method in ['PUT', 'PATCH']:
                analysis['update_apis'].append(api)
            
            # 识别删除接口
            elif method == 'DELETE':
                analysis['delete_apis'].append(api)
            
            # 分析参数
            params = api.get('parameters', [])
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = []
            
            for param in params:
                if isinstance(param, dict):
                    param_name = param.get('name', '').lower()
                    
                    # 识别认证字段
                    if any(keyword in param_name for keyword in ['token', 'auth', 'authorization']):
                        if param_name not in analysis['common_params']['auth_fields']:
                            analysis['common_params']['auth_fields'].append(param_name)
                    
                    # 识别ID字段
                    elif 'id' in param_name:
                        if param_name not in analysis['common_params']['id_fields']:
                            analysis['common_params']['id_fields'].append(param_name)
                    
                    # 识别会话字段
                    elif any(keyword in param_name for keyword in ['session', 'ticket', 'code']):
                        if param_name not in analysis['common_params']['session_fields']:
                            analysis['common_params']['session_fields'].append(param_name)
        
        return analysis
    
    @staticmethod
    def build_user_prompt(intent: str, apis: List[Dict], analysis: Dict = None) -> str:
        """
        构建用户提示词，包含依赖分析结果
        """
        prompt = f"""📝 用户测试意图：
{intent}

📚 可用的API列表：
{json.dumps(apis[:30], ensure_ascii=False, indent=2)}
"""
        
        if analysis:
            prompt += f"""

🔍 API依赖分析结果：

登录类接口 ({len(analysis['login_apis'])}个)：
{json.dumps([f"{api.get('method')} {api.get('path')}" for api in analysis['login_apis'][:5]], ensure_ascii=False, indent=2)}

创建类接口 ({len(analysis['create_apis'])}个)：
{json.dumps([f"{api.get('method')} {api.get('path')}" for api in analysis['create_apis'][:5]], ensure_ascii=False, indent=2)}

常见参数模式：
- 认证字段: {', '.join(analysis['common_params']['auth_fields'][:5])}
- ID字段: {', '.join(analysis['common_params']['id_fields'][:5])}
- 会话字段: {', '.join(analysis['common_params']['session_fields'][:5])}

💡 建议：
1. 如果场景需要认证，优先使用登录接口获取token
2. 创建接口通常返回新对象的ID，后续操作可能需要
3. 注意配置param_mappings来传递这些依赖数据
"""
        
        prompt += """

请根据以上信息，生成完整的测试步骤序列，特别注意：
1. 识别哪些接口需要token认证
2. 识别哪些接口需要前面步骤返回的ID
3. 正确配置param_mappings来传递这些依赖数据
4. 确保from_step不会引用自己或后续步骤
"""
        
        return prompt


# 使用示例
if __name__ == "__main__":
    generator = EnhancedScenarioGenerator()
    
    # 示例API列表
    sample_apis = [
        {
            "path": "/api/login",
            "method": "POST",
            "summary": "用户登录",
            "parameters": [
                {"name": "username", "in": "body"},
                {"name": "password", "in": "body"}
            ]
        },
        {
            "path": "/api/orders",
            "method": "POST",
            "summary": "创建订单",
            "parameters": [
                {"name": "Authorization", "in": "header"},
                {"name": "productId", "in": "body"}
            ]
        },
        {
            "path": "/api/orders/{orderId}",
            "method": "GET",
            "summary": "查询订单",
            "parameters": [
                {"name": "Authorization", "in": "header"},
                {"name": "orderId", "in": "path"}
            ]
        }
    ]
    
    # 分析依赖
    analysis = generator.analyze_api_dependencies(sample_apis)
    
    print("=" * 80)
    print("🔍 API依赖分析结果")
    print("=" * 80)
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("📝 增强版System Prompt")
    print("=" * 80)
    print(generator.get_enhanced_system_prompt()[:500] + "...")
    
    print("\n" + "=" * 80)
    print("📝 User Prompt示例")
    print("=" * 80)
    user_prompt = generator.build_user_prompt(
        "测试用户登录后创建订单并查询订单详情",
        sample_apis,
        analysis
    )
    print(user_prompt[:500] + "...")

"""
智能断言生成器
根据接口信息和业务上下文生成断言规则
"""
from openai import AsyncOpenAI
from typing import Dict, List
import json

class AssertionGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate_assertions(
        self,
        api_info: Dict,
        business_context: Dict = None,
        test_data: Dict = None
    ) -> Dict:
        """
        生成断言规则
        
        Args:
            api_info: API信息
            business_context: 业务上下文
            test_data: 测试数据
            
        Returns:
            断言规则列表
        """
        system_prompt = """你是一个专业的接口测试断言设计专家。
根据API信息和业务上下文，生成全面的断言规则。

断言类型包括：
1. **status_code**: 状态码断言
2. **response_schema**: 响应结构断言
3. **business_logic**: 业务逻辑断言

每个断言包含：
- type: 断言类型
- field: 字段路径（如 response.data.user_id）
- operator: 操作符（==, !=, >, <, contains, matches, exists）
- expected_value: 期望值
- description: 断言描述

以JSON格式返回：
{
  "assertions": [
    {
      "type": "status_code",
      "field": "",
      "operator": "==",
      "expected_value": 200,
      "description": "状态码应为200"
    },
    {
      "type": "response_schema",
      "field": "response.data.user_id",
      "operator": "exists",
      "expected_value": null,
      "description": "响应中应包含user_id"
    }
  ]
}
"""
        
        user_prompt = f"""API信息：
{json.dumps(api_info, ensure_ascii=False, indent=2)}

业务上下文：
{json.dumps(business_context or {}, ensure_ascii=False, indent=2)}

测试数据：
{json.dumps(test_data or {}, ensure_ascii=False, indent=2)}

请生成全面的断言规则。
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            raise Exception(f"断言生成失败: {str(e)}")

"""
场景解析器 - 生成接口调用序列
基于NLU结果和知识图谱，生成完整的测试步骤
"""
from openai import AsyncOpenAI
from typing import Dict, List
import json

class ScenarioParser:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def parse_scenario(
        self,
        nlu_result: Dict,
        project_id: str,
        api_candidates: List[Dict] = None
    ) -> Dict:
        """
        解析场景，生成测试步骤
        
        Args:
            nlu_result: NLU理解结果
            project_id: 项目ID
            api_candidates: 候选API列表（从向量检索获取）
            
        Returns:
            结构化的测试场景
        """
        system_prompt = """你是一个专业的接口测试场景编排专家。
你的任务是根据用户的测试意图和可用的API，生成完整的测试步骤序列。

请生成以下内容：
1. **场景名称** (scenario_name): 简洁的场景名称
2. **场景描述** (description): 详细的场景描述
3. **测试步骤** (steps): 按顺序排列的API调用步骤

每个步骤包含：
- step_order: 步骤序号
- api_id: API标识
- api_name: API名称
- api_path: API路径
- api_method: HTTP方法
- description: 步骤描述
- param_mappings: 参数映射关系（如果需要从前一步获取数据）

以JSON格式返回：
{
  "scenario_name": "场景名称",
  "description": "场景描述",
  "steps": [
    {
      "step_order": 1,
      "api_id": "POST:/api/login",
      "api_name": "用户登录",
      "api_path": "/api/login",
      "api_method": "POST",
      "description": "用户登录获取token",
      "param_mappings": []
    },
    {
      "step_order": 2,
      "api_id": "POST:/api/orders",
      "api_name": "创建订单",
      "api_path": "/api/orders",
      "api_method": "POST",
      "description": "创建订单",
      "param_mappings": [
        {
          "from_step": 1,
          "from_field": "response.token",
          "to_field": "headers.Authorization"
        }
      ]
    }
  ],
  "confidence": 0.9
}
"""
        
        user_prompt = f"""测试意图：
{json.dumps(nlu_result, ensure_ascii=False, indent=2)}

可用的API列表：
{json.dumps(api_candidates or [], ensure_ascii=False, indent=2)}

请根据测试意图，从可用API中选择合适的接口，编排成完整的测试步骤序列。
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
            result['project_id'] = project_id
            return result
            
        except Exception as e:
            raise Exception(f"场景解析失败: {str(e)}")

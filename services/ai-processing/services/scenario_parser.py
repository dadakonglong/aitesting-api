"""
场景解析器 - 生成接口调用序列
基于NLU结果和知识图谱，生成完整的测试步骤
"""
from openai import AsyncOpenAI
from typing import Dict, List, Any
import json
import sqlite3

class ScenarioParser:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def parse_scenario(
        self,
        nlu_result: Dict,
        project_id: str,
        api_candidates: List[Dict] = None,
        db_path: str = None
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
        # 如果没有提供 api_candidates 且提供了 db_path，则从数据库加载
        if not api_candidates and db_path:
             try:
                 conn = sqlite3.connect(db_path)
                 conn.row_factory = sqlite3.Row
                 cursor = conn.cursor()
                 # 简单策略：加载项目下所有 API (如果数量太多可能需要 RAG 优化，但此处先保证功能)
                 cursor.execute("SELECT * FROM apis WHERE project_id = ?", (project_id,))
                 rows = cursor.fetchall()
                 conn.close()
                 api_candidates = [dict(row) for row in rows]
             except Exception as e:
                 print(f"Warning: Failed to load APIs from DB: {e}")
                 api_candidates = []

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

            # 增强: 注入 API Schema (params_schema, body_schema)
            if api_candidates:
                # 建立 api_id / path 映射
                api_map = {}
                for api in api_candidates:
                    # key1: method:path (e.g. "POST:/api/login")
                    key1 = f"{api.get('method', '').upper()}:{api.get('path', '')}"
                    api_map[key1] = api
                    # key2: path (fallback)
                    api_map[api.get('path', '')] = api
                    # key3: id (if available)
                    if api.get('id'):
                        api_map[str(api['id'])] = api

                for step in result.get('steps', []):
                    # 尝试匹配 API
                    found_api = None
                    # 1. 尝试 api_id
                    if step.get('api_id') and str(step['api_id']) in api_map:
                         found_api = api_map[str(step['api_id'])]
                    # 2. 尝试 api_id 作为 method:path
                    elif step.get('api_id') and str(step['api_id']) in api_map:
                         found_api = api_map[str(step['api_id'])]
                    # 3. 尝试 method:path 组合
                    elif step.get('api_path') and step.get('api_method'):
                        key = f"{step['api_method'].upper()}:{step['api_path']}"
                        if key in api_map:
                            found_api = api_map[key]
                    
                    if found_api:
                        # 注入 schema
                        try:
                             params = found_api.get('parameters')
                             if isinstance(params, str):
                                 params = json.loads(params)
                             step['params_schema'] = params
                        except:
                             step['params_schema'] = []

                        try:
                             body = found_api.get('request_body')
                             if isinstance(body, str):
                                 body = json.loads(body)
                             step['body_schema'] = body
                        except:
                             step['body_schema'] = {}

            return result
            
        except Exception as e:
            raise Exception(f"场景解析失败: {str(e)}")

"""
NLU服务 - 自然语言理解
将用户的自然语言描述转换为结构化的场景理解
"""
from openai import AsyncOpenAI
from typing import Dict, Optional
import json

class NLUService:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def understand_scenario(
        self,
        description: str,
        knowledge_context: Optional[Dict] = None
    ) -> Dict:
        """
        理解测试场景
        
        Args:
            description: 用户的自然语言描述
            knowledge_context: 知识图谱提供的上下文信息
            
        Returns:
            结构化的场景理解结果
        """
        system_prompt = """你是一个专业的接口测试场景分析专家。
你的任务是理解用户用自然语言描述的测试场景，并提取关键信息。

请分析用户的描述，提取以下信息：
1. **测试意图** (intent): 用一句话概括测试目标
2. **业务实体** (entities): 涉及的业务对象，如User、Order、Product等
3. **测试动作** (actions): 需要执行的操作序列
4. **约束条件** (constraints): 测试的前置条件或限制
5. **期望结果** (expected_results): 期望的测试结果

以JSON格式返回，格式如下：
{
  "intent": "测试意图描述",
  "entities": [
    {"name": "实体名", "type": "实体类型", "attributes": ["属性1", "属性2"]}
  ],
  "actions": [
    {"name": "动作名", "type": "动作类型", "target": "目标实体", "order": 1}
  ],
  "constraints": [
    {"type": "约束类型", "description": "约束描述"}
  ],
  "expected_results": [
    {"description": "期望结果描述"}
  ],
  "confidence": 0.95
}
"""
        
        user_prompt = f"用户描述的测试场景：\n{description}"
        
        if knowledge_context:
            user_prompt += f"\n\n可用的上下文信息：\n{json.dumps(knowledge_context, ensure_ascii=False, indent=2)}"
        
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
            raise Exception(f"NLU处理失败: {str(e)}")

"""
智能数据生成器
根据参数schema和业务规则生成测试数据
"""
from openai import AsyncOpenAI
from typing import Dict, List
import json
# from faker import Faker  # 临时注释，网络问题无法安装

class DataGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        # self.faker = Faker('zh_CN')  # 临时注释
    
    async def generate_data(
        self,
        param_schema: Dict,
        business_rules: List[Dict] = None,
        strategy: str = "smart",
        count: int = 1
    ) -> Dict:
        """
        生成测试数据
        
        Args:
            param_schema: 参数schema定义
            business_rules: 业务规则
            strategy: 生成策略 (smart, valid, boundary, invalid, random)
            count: 生成数量
            
        Returns:
            生成的测试数据
        """
        if strategy == "smart":
            return await self._generate_smart_data(param_schema, business_rules, count)
        elif strategy == "valid":
            return await self._generate_valid_data(param_schema, count)
        elif strategy == "boundary":
            return await self._generate_boundary_data(param_schema, count)
        elif strategy == "invalid":
            return await self._generate_invalid_data(param_schema, count)
        else:
            return await self._generate_random_data(param_schema, count)
    
    async def _generate_smart_data(
        self,
        param_schema: Dict,
        business_rules: List[Dict],
        count: int
    ) -> Dict:
        """使用AI生成智能测试数据"""
        system_prompt = """你是一个专业的测试数据生成专家。
根据参数schema和业务规则，生成真实、合理的测试数据。

要求：
1. 数据要符合参数类型和约束
2. 数据要符合业务规则
3. 数据要真实可信，不要使用明显的测试数据
4. 考虑边界情况

以JSON格式返回数据数组。
"""
        
        user_prompt = f"""参数Schema：
{json.dumps(param_schema, ensure_ascii=False, indent=2)}

业务规则：
{json.dumps(business_rules or [], ensure_ascii=False, indent=2)}

请生成{count}组测试数据。
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "strategy": "smart",
                "data": result.get("data", [result]),
                "count": len(result.get("data", [result]))
            }
            
        except Exception as e:
            raise Exception(f"智能数据生成失败: {str(e)}")
    
    async def _generate_valid_data(self, param_schema: Dict, count: int) -> Dict:
        """生成有效数据"""
        data = []
        for _ in range(count):
            item = {}
            for param_name, param_def in param_schema.items():
                item[param_name] = self._generate_valid_value(param_def)
            data.append(item)
        
        return {
            "strategy": "valid",
            "data": data,
            "count": len(data)
        }
    
    def _generate_valid_value(self, param_def: Dict):
        """生成有效值（简化版，不使用 faker）"""
        import random
        param_type = param_def.get('type', 'string')
        
        if param_type == 'string':
            if 'email' in param_def.get('name', '').lower():
                return "test@example.com"
            elif 'phone' in param_def.get('name', '').lower():
                return "13800138000"
            elif 'name' in param_def.get('name', '').lower():
                return "测试用户"
            else:
                return "test_value"
        elif param_type == 'integer' or param_type == 'number':
            min_val = param_def.get('minimum', 1)
            max_val = param_def.get('maximum', 100)
            return random.randint(min_val, max_val)
        elif param_type == 'boolean':
            return random.choice([True, False])
        elif param_type == 'array':
            return [self._generate_valid_value(param_def.get('items', {}))]
        else:
            return None
    
    async def _generate_boundary_data(self, param_schema: Dict, count: int) -> Dict:
        """生成边界数据"""
        # 简化实现，实际应该生成最小值、最大值、空值等边界情况
        return {
            "strategy": "boundary",
            "data": [],
            "count": 0
        }
    
    async def _generate_invalid_data(self, param_schema: Dict, count: int) -> Dict:
        """生成无效数据"""
        # 简化实现，实际应该生成类型错误、超出范围等无效数据
        return {
            "strategy": "invalid",
            "data": [],
            "count": 0
        }
    
    async def _generate_random_data(self, param_schema: Dict, count: int) -> Dict:
        """生成随机数据"""
        return await self._generate_valid_data(param_schema, count)

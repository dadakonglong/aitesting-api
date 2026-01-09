"""
本地测试脚本 - 不需要Docker
直接测试AI核心功能
"""
import asyncio
from services.ai-processing.services.nlu_service import NLUService
from services.ai-processing.services.scenario_parser import ScenarioParser
from services.ai-processing.services.data_generator import DataGenerator
from services.ai-processing.services.assertion_generator import AssertionGenerator
import os
import json

# 设置OpenAI API Key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_nlu():
    """测试自然语言理解"""
    print("\n" + "="*60)
    print("测试1: 自然语言理解（NLU）")
    print("="*60)
    
    nlu_service = NLUService(os.getenv('OPENAI_API_KEY'))
    
    scenarios = [
        "测试用户登录功能",
        "测试查询商品列表后添加到购物车",
    ]
    
    for scenario in scenarios:
        print(f"\n📝 场景: {scenario}")
        result = await nlu_service.understand(scenario)
        print(f"   意图: {result.get('intent', 'N/A')}")
        print(f"   实体数: {len(result.get('entities', []))}")
        print(f"   动作数: {len(result.get('actions', []))}")

async def test_data_generation():
    """测试数据生成"""
    print("\n" + "="*60)
    print("测试2: 智能数据生成")
    print("="*60)
    
    generator = DataGenerator(os.getenv('OPENAI_API_KEY'))
    
    schema = {
        "username": {"type": "string", "description": "用户名"},
        "password": {"type": "string", "description": "密码"},
        "email": {"type": "string", "format": "email"}
    }
    
    print("\n📊 生成测试数据（smart策略）...")
    data = await generator.generate(schema, strategy="smart", count=2)
    
    for i, item in enumerate(data, 1):
        print(f"\n   数据{i}: {json.dumps(item, ensure_ascii=False, indent=2)}")

async def test_assertion_generation():
    """测试断言生成"""
    print("\n" + "="*60)
    print("测试3: 智能断言生成")
    print("="*60)
    
    generator = AssertionGenerator(os.getenv('OPENAI_API_KEY'))
    
    api_info = {
        "name": "用户登录",
        "method": "POST",
        "path": "/api/login",
        "responses": {
            "200": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "username": {"type": "string"}
                    }
                }
            }
        }
    }
    
    print("\n✅ 生成断言...")
    assertions = await generator.generate(api_info)
    
    for i, assertion in enumerate(assertions, 1):
        print(f"\n   断言{i}: [{assertion['type']}] {assertion['description']}")
        print(f"          字段: {assertion.get('field', 'N/A')}")
        print(f"          操作符: {assertion['operator']}")

async def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("AI智能接口测试平台 - 本地核心功能测试")
    print("🚀"*30)
    
    # 检查API Key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("\n❌ 错误: 未配置OPENAI_API_KEY")
        print("请在.env文件中设置OPENAI_API_KEY")
        return
    
    print(f"\n✅ OpenAI API Key已配置")
    
    try:
        await test_nlu()
        await test_data_generation()
        await test_assertion_generation()
        
        print("\n" + "="*60)
        print("✅ 所有核心功能测试完成！")
        print("="*60)
        print("\n💡 说明:")
        print("   - NLU服务可以理解自然语言测试场景")
        print("   - 数据生成器可以智能生成测试数据")
        print("   - 断言生成器可以自动生成验证规则")
        print("\n🎯 这些是AI测试平台的核心能力！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

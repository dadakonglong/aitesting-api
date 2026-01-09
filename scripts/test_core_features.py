"""
测试脚本 - 验证AI场景生成核心功能
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_import_swagger():
    """测试1: 导入Swagger文档"""
    print("\n" + "="*50)
    print("测试1: 导入Swagger文档")
    print("="*50)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/import/swagger",
            json={
                "source_type": "swagger",
                "source": "https://petstore.swagger.io/v2/swagger.json",
                "project_id": "test-project"
            },
            timeout=60.0
        )
        
        result = response.json()
        print(f"✅ 导入成功: {result['indexed']} 个接口")
        print(f"   项目ID: {result['project_id']}")
        return result

async def test_semantic_search():
    """测试2: 语义搜索接口"""
    print("\n" + "="*50)
    print("测试2: 语义搜索接口")
    print("="*50)
    
    queries = [
        "查询宠物信息",
        "创建订单",
        "用户登录"
    ]
    
    async with httpx.AsyncClient() as client:
        for query in queries:
            print(f"\n🔍 搜索: {query}")
            response = await client.post(
                f"{BASE_URL}/api/v1/vector/search",
                json={
                    "query": query,
                    "limit": 3,
                    "filter_type": "api",
                    "project_id": "test-project"
                },
                timeout=30.0
            )
            
            results = response.json()['results']
            print(f"   找到 {len(results)} 个相关接口:")
            for i, result in enumerate(results, 1):
                payload = result['payload']
                print(f"   {i}. {payload['method']} {payload['path']} - {payload['name']}")
                print(f"      相似度: {result['score']:.3f}")

async def test_scenario_understanding():
    """测试3: AI场景理解"""
    print("\n" + "="*50)
    print("测试3: AI场景理解")
    print("="*50)
    
    scenarios = [
        "测试查询宠物信息后更新宠物状态",
        "测试创建订单的完整流程",
    ]
    
    async with httpx.AsyncClient() as client:
        for scenario in scenarios:
            print(f"\n📝 场景: {scenario}")
            response = await client.post(
                f"{BASE_URL}/api/v1/ai/understand-scenario",
                json={
                    "description": scenario,
                    "project_id": "test-project"
                },
                timeout=60.0
            )
            
            result = response.json()
            print(f"   意图: {result.get('intent', 'N/A')}")
            print(f"   实体: {len(result.get('entities', []))} 个")
            print(f"   动作: {len(result.get('actions', []))} 个")
            print(f"   置信度: {result.get('confidence', 0):.2f}")

async def test_rag_enhance():
    """测试4: RAG增强场景理解"""
    print("\n" + "="*50)
    print("测试4: RAG增强场景理解")
    print("="*50)
    
    scenario = "测试查询宠物信息后更新宠物状态"
    
    print(f"\n📝 场景: {scenario}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/rag/enhance-scenario",
            json={
                "description": scenario,
                "project_id": "test-project"
            },
            timeout=60.0
        )
        
        result = response.json()
        
        print("\n🤖 AI理解结果:")
        understanding = result.get('understanding', {})
        print(f"   意图: {understanding.get('intent', 'N/A')}")
        
        print("\n📚 检索到的上下文:")
        context = result.get('context', {})
        
        relevant_apis = context.get('relevant_apis', [])
        print(f"   相关接口: {len(relevant_apis)} 个")
        for i, api in enumerate(relevant_apis[:3], 1):
            print(f"   {i}. {api['method']} {api['path']} - {api['name']}")
        
        similar_scenarios = context.get('similar_scenarios', [])
        if similar_scenarios:
            print(f"\n   相似场景: {len(similar_scenarios)} 个")
            for i, s in enumerate(similar_scenarios, 1):
                print(f"   {i}. {s['name']}")

async def test_data_generation():
    """测试5: 智能数据生成"""
    print("\n" + "="*50)
    print("测试5: 智能数据生成")
    print("="*50)
    
    param_schema = {
        "name": {"type": "string", "description": "宠物名称"},
        "status": {"type": "string", "enum": ["available", "pending", "sold"]},
        "category": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }
    }
    
    strategies = ["smart", "valid"]
    
    async with httpx.AsyncClient() as client:
        for strategy in strategies:
            print(f"\n📊 策略: {strategy}")
            response = await client.post(
                f"{BASE_URL}/api/v1/ai/generate-data",
                json={
                    "param_schema": param_schema,
                    "strategy": strategy,
                    "count": 2
                },
                timeout=60.0
            )
            
            result = response.json()
            print(f"   生成 {result['count']} 组数据:")
            for i, data in enumerate(result['data'][:2], 1):
                print(f"   {i}. {json.dumps(data, ensure_ascii=False, indent=6)}")

async def test_assertion_generation():
    """测试6: 智能断言生成"""
    print("\n" + "="*50)
    print("测试6: 智能断言生成")
    print("="*50)
    
    api_info = {
        "name": "查询宠物信息",
        "method": "GET",
        "path": "/pet/{petId}",
        "responses": {
            "200": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "status": {"type": "string"}
                    }
                }
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/ai/generate-assertions",
            json={
                "api_info": api_info
            },
            timeout=60.0
        )
        
        result = response.json()
        assertions = result.get('assertions', [])
        
        print(f"\n✅ 生成 {len(assertions)} 个断言:")
        for i, assertion in enumerate(assertions, 1):
            print(f"   {i}. [{assertion['type']}] {assertion['description']}")
            print(f"      字段: {assertion.get('field', 'N/A')}")
            print(f"      操作符: {assertion['operator']}")
            print(f"      期望值: {assertion.get('expected_value', 'N/A')}")

async def main():
    """运行所有测试"""
    print("\n" + "🚀"*25)
    print("AI智能接口测试平台 - 核心功能测试")
    print("🚀"*25)
    
    try:
        # 检查服务是否运行
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"\n✅ 服务状态: {response.json()['status']}")
    except Exception as e:
        print(f"\n❌ 服务未启动，请先运行: docker-compose up -d ai-service")
        print(f"   错误: {str(e)}")
        return
    
    try:
        # 运行测试
        await test_import_swagger()
        await asyncio.sleep(2)  # 等待索引完成
        
        await test_semantic_search()
        await test_scenario_understanding()
        await test_rag_enhance()
        await test_data_generation()
        await test_assertion_generation()
        
        print("\n" + "="*50)
        print("✅ 所有测试完成！")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

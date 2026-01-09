"""
端到端测试脚本
完整测试从自然语言输入到测试执行的全流程
"""
import asyncio
import httpx
import json
import time

# 服务地址
AI_SERVICE_URL = "http://localhost:8000"
SCENARIO_SERVICE_URL = "http://localhost:8081"
EXECUTION_SERVICE_URL = "http://localhost:8083"

# 测试配置
PROJECT_ID = "e2e-test-project"
SWAGGER_URL = "https://petstore.swagger.io/v2/swagger.json"
BASE_URL = "https://petstore.swagger.io/v2"

async def wait_for_services():
    """等待所有服务就绪"""
    print("\n🔍 检查服务状态...")
    
    services = [
        ("AI服务", f"{AI_SERVICE_URL}/health"),
        ("场景编排服务", f"{SCENARIO_SERVICE_URL}/health"),
        ("测试执行服务", f"{EXECUTION_SERVICE_URL}/health"),
    ]
    
    async with httpx.AsyncClient() as client:
        for name, url in services:
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        print(f"✅ {name} 就绪")
                        break
                except Exception as e:
                    if i == max_retries - 1:
                        print(f"❌ {name} 启动失败: {str(e)}")
                        return False
                    await asyncio.sleep(2)
    
    return True

async def step1_import_swagger():
    """步骤1: 导入Swagger文档"""
    print("\n" + "="*60)
    print("步骤1: 导入Swagger文档")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/api/v1/import/swagger",
            json={
                "source_type": "swagger",
                "source": SWAGGER_URL,
                "project_id": PROJECT_ID
            },
            timeout=120.0
        )
        
        result = response.json()
        print(f"✅ 导入成功: {result['indexed']} 个接口")
        print(f"   项目ID: {result['project_id']}")
        
        # 等待索引完成
        print("⏳ 等待向量索引完成...")
        await asyncio.sleep(3)
        
        return result

async def step2_create_scenario(scenario_description):
    """步骤2: 创建测试场景"""
    print("\n" + "="*60)
    print("步骤2: 创建测试场景")
    print("="*60)
    print(f"📝 场景描述: {scenario_description}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SCENARIO_SERVICE_URL}/api/v1/scenarios",
            json={
                "project_id": PROJECT_ID,
                "natural_language_input": scenario_description
            },
            timeout=120.0
        )
        
        if response.status_code != 200:
            print(f"❌ 创建场景失败: {response.text}")
            return None
        
        scenario = response.json()
        print(f"✅ 场景创建成功")
        print(f"   场景ID: {scenario['id']}")
        print(f"   场景名称: {scenario['name']}")
        print(f"   描述: {scenario['description']}")
        
        # 显示解析的步骤
        if 'parsed_structure' in scenario and 'steps' in scenario['parsed_structure']:
            steps = scenario['parsed_structure']['steps']
            print(f"\n   📋 解析出 {len(steps)} 个测试步骤:")
            for i, step in enumerate(steps, 1):
                print(f"      {i}. {step.get('api_method', 'N/A')} {step.get('api_path', 'N/A')}")
                print(f"         {step.get('description', 'N/A')}")
        
        return scenario

async def step3_generate_test_case(scenario_id, data_strategy="smart"):
    """步骤3: 生成测试用例"""
    print("\n" + "="*60)
    print("步骤3: 生成测试用例")
    print("="*60)
    print(f"🎲 数据策略: {data_strategy}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SCENARIO_SERVICE_URL}/api/v1/scenarios/{scenario_id}/generate-case",
            json={
                "data_strategy": data_strategy
            },
            timeout=120.0
        )
        
        if response.status_code != 200:
            print(f"❌ 生成测试用例失败: {response.text}")
            return None
        
        test_case = response.json()
        print(f"✅ 测试用例生成成功")
        print(f"   用例ID: {test_case['id']}")
        print(f"   用例名称: {test_case['name']}")
        print(f"   步骤数: {len(test_case.get('steps', []))}")
        
        # 显示每个步骤的详情
        if 'steps' in test_case:
            print(f"\n   📋 测试步骤详情:")
            for step in test_case['steps']:
                print(f"\n      步骤 {step['step_order']}: {step['api_name']}")
                print(f"      请求: {step['api_method']} {step['api_path']}")
                print(f"      参数: {json.dumps(step.get('params', {}), ensure_ascii=False)[:100]}...")
                print(f"      断言数: {len(step.get('assertions', []))}")
        
        return test_case

async def step4_execute_test(test_case_id):
    """步骤4: 执行测试"""
    print("\n" + "="*60)
    print("步骤4: 执行测试")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # 提交执行请求
        response = await client.post(
            f"{EXECUTION_SERVICE_URL}/api/v1/executions",
            json={
                "test_case_id": test_case_id,
                "environment": "test",
                "base_url": BASE_URL
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ 提交执行失败: {response.text}")
            return None
        
        execution = response.json()
        execution_id = execution['id']
        print(f"✅ 测试已提交执行")
        print(f"   执行ID: {execution_id}")
        print(f"   状态: {execution['status']}")
        
        # 轮询执行结果
        print("\n⏳ 等待执行完成...")
        max_wait = 60  # 最多等待60秒
        for i in range(max_wait):
            await asyncio.sleep(2)
            
            result_response = await client.get(
                f"{EXECUTION_SERVICE_URL}/api/v1/executions/{execution_id}",
                timeout=10.0
            )
            
            if result_response.status_code != 200:
                continue
            
            execution_result = result_response.json()
            status = execution_result['status']
            
            if status in ['success', 'failed']:
                print(f"\n✅ 执行完成")
                return execution_result
            
            print(f"   状态: {status} ({i*2}s)")
        
        print("⚠️  执行超时")
        return None

async def step5_display_results(execution_result):
    """步骤5: 展示测试结果"""
    print("\n" + "="*60)
    print("步骤5: 测试结果")
    print("="*60)
    
    status = execution_result['status']
    duration = execution_result.get('duration_ms', 0)
    
    print(f"\n📊 执行摘要:")
    print(f"   状态: {'✅ 成功' if status == 'success' else '❌ 失败'}")
    print(f"   耗时: {duration}ms")
    
    if 'result' in execution_result:
        result = execution_result['result']
        
        if 'summary' in result:
            summary = result['summary']
            print(f"\n   总步骤数: {summary.get('total_steps', 0)}")
            print(f"   成功步骤: {summary.get('success_steps', 0)}")
            print(f"   失败步骤: {summary.get('failed_steps', 0)}")
            print(f"   总断言数: {summary.get('total_assertions', 0)}")
            print(f"   通过断言: {summary.get('passed_assertions', 0)}")
            print(f"   失败断言: {summary.get('failed_assertions', 0)}")
            print(f"   成功率: {summary.get('success_rate', 0):.2f}%")
        
        if 'steps' in result:
            print(f"\n📋 步骤详情:")
            for step in result['steps']:
                status_icon = "✅" if step['success'] else "❌"
                print(f"\n   {status_icon} 步骤 {step['step_order']}")
                print(f"      状态码: {step.get('status_code', 'N/A')}")
                print(f"      响应时间: {step.get('response_time_ms', 0)}ms")
                
                if 'assertions' in step:
                    passed = sum(1 for a in step['assertions'] if a['passed'])
                    total = len(step['assertions'])
                    print(f"      断言: {passed}/{total} 通过")
                    
                    # 显示失败的断言
                    for assertion in step['assertions']:
                        if not assertion['passed']:
                            print(f"         ❌ {assertion['assertion']['description']}")
                            if 'error_msg' in assertion:
                                print(f"            {assertion['error_msg']}")

async def run_e2e_test():
    """运行完整的端到端测试"""
    print("\n" + "🚀"*30)
    print("AI智能接口测试平台 - 端到端测试")
    print("🚀"*30)
    
    # 检查服务
    if not await wait_for_services():
        print("\n❌ 服务未就绪，请先启动服务")
        print("   运行: docker-compose up -d")
        return
    
    try:
        # 步骤1: 导入接口
        await step1_import_swagger()
        
        # 步骤2: 创建场景
        scenarios = [
            "测试查询宠物信息",
            "测试添加新宠物后查询",
        ]
        
        for scenario_desc in scenarios:
            print(f"\n{'='*60}")
            print(f"测试场景: {scenario_desc}")
            print(f"{'='*60}")
            
            scenario = await step2_create_scenario(scenario_desc)
            if not scenario:
                continue
            
            # 步骤3: 生成测试用例
            test_case = await step3_generate_test_case(scenario['id'])
            if not test_case:
                continue
            
            # 步骤4: 执行测试
            execution_result = await step4_execute_test(test_case['id'])
            if not execution_result:
                continue
            
            # 步骤5: 展示结果
            await step5_display_results(execution_result)
        
        print("\n" + "="*60)
        print("✅ 端到端测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_e2e_test())

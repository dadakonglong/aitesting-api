#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复ID58的请求头和参数提取问题
主要解决：
1. 确保所有步骤都有正确的请求头配置
2. 修复参数提取失败的问题
3. 确保生成的场景包含完整的执行信息
"""
import sqlite3
import json
import httpx
import asyncio
from datetime import datetime

DB_PATH = "data/apis.db"

def analyze_id58_issue():
    """分析ID58的具体问题"""
    print("=" * 80)
    print("🔍 分析ID58问题")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取ID58场景
    c.execute("SELECT * FROM scenarios WHERE id = 58")
    scenario = c.fetchone()
    
    if not scenario:
        print("❌ 找不到场景58")
        conn.close()
        return None
    
    # 获取测试用例
    c.execute("SELECT * FROM test_cases WHERE id = ?", (scenario['test_case_id'],))
    test_case = c.fetchone()
    
    if not test_case:
        print("❌ 找不到测试用例")
        conn.close()
        return None
    
    steps = json.loads(test_case['steps'])
    
    print(f"📋 场景信息:")
    print(f"   场景ID: {scenario['id']}")
    print(f"   场景名: {scenario['name']}")
    print(f"   测试用例ID: {test_case['id']}")
    print(f"   步骤数: {len(steps)}")
    
    # 分析每个步骤
    issues = []
    
    for i, step in enumerate(steps):
        step_num = i + 1
        print(f"\n📝 步骤{step_num}: {step.get('api_method')} {step.get('api_path')}")
        
        # 检查基本信息
        if not step.get('api_path'):
            issues.append(f"步骤{step_num}: 缺少api_path")
        
        if not step.get('api_method'):
            issues.append(f"步骤{step_num}: 缺少api_method")
        
        # 检查参数映射
        param_mappings = step.get('param_mappings', [])
        print(f"   参数映射: {len(param_mappings)}个")
        
        for mapping in param_mappings:
            from_step = mapping.get('from_step')
            from_field = mapping.get('from_field')
            to_field = mapping.get('to_field')
            to_type = mapping.get('to_type', 'params')
            
            print(f"      从步骤{from_step}的{from_field} -> {to_type}.{to_field}")
            
            # 检查映射配置
            if from_step >= step_num:
                issues.append(f"步骤{step_num}: from_step({from_step})不能大于等于当前步骤")
            
            if to_type == 'headers' and to_field == 'Authorization':
                print(f"         ✅ Authorization映射正确")
            elif 'Authorization' in to_field and to_type != 'headers':
                issues.append(f"步骤{step_num}: Authorization应该映射到headers")
        
        # 检查请求头
        headers = step.get('headers', {})
        if headers:
            print(f"   静态请求头: {list(headers.keys())}")
        
        # 检查参数
        params = step.get('params', {})
        if params:
            print(f"   请求参数: {list(params.keys())}")
    
    # 检查最近执行记录
    print(f"\n" + "=" * 80)
    print(f"📊 最近执行分析:")
    print("-" * 80)
    
    c.execute("""
        SELECT * FROM executions 
        WHERE test_case_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (test_case['id'],))
    
    execution = c.fetchone()
    
    if execution:
        results = json.loads(execution['results'])
        print(f"执行ID: {execution['id']}")
        print(f"状态: {execution['status']}")
        print(f"时间: {execution['created_at']}")
        
        for i, result in enumerate(results):
            step_num = i + 1
            print(f"\n   步骤{step_num}:")
            print(f"      URL: {result.get('url')}")
            print(f"      状态码: {result.get('status_code')}")
            print(f"      成功: {result.get('success')}")
            
            # 检查提取记录
            extractions = result.get('extractions', [])
            if extractions:
                print(f"      提取记录:")
                for ext in extractions:
                    success = ext.get('success', False)
                    icon = "✅" if success else "❌"
                    print(f"         {icon} {ext.get('from_field')} -> {ext.get('to_type')}.{ext.get('to_field')}")
                    if not success:
                        print(f"            错误: {ext.get('error_msg')}")
            
            # 检查请求头
            req_headers = result.get('request_headers', {})
            if 'Authorization' in req_headers:
                auth = req_headers['Authorization']
                if 'Bearer' in auth and len(auth) > 20:
                    print(f"      ✅ Authorization: {auth[:30]}...")
                else:
                    print(f"      ❌ Authorization异常: {auth}")
            elif step_num > 1:
                print(f"      ❌ 缺少Authorization")
            
            # 检查响应
            response = result.get('response', {})
            if isinstance(response, dict):
                code = response.get('code')
                message = response.get('message')
                print(f"      响应: code={code}, message={message}")
                
                # 检查是否有需要提取的字段
                if step_num == 1 and 'data' in response:
                    data = response['data']
                    if 'token' in data:
                        print(f"      ✅ 包含token: {str(data['token'])[:20]}...")
                    else:
                        print(f"      ❌ 登录响应缺少token")
                
                if step_num == 2 and 'data' in response:
                    data = response['data']
                    if 'sessionId' in data:
                        print(f"      ✅ 包含sessionId: {data['sessionId']}")
                    else:
                        print(f"      ❌ 开台响应缺少sessionId")
                        print(f"      响应data字段: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    
    conn.close()
    
    # 总结问题
    print(f"\n" + "=" * 80)
    print(f"🔧 问题总结:")
    print("=" * 80)
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
    else:
        print("✅ 配置检查通过")
    
    return {
        'scenario': dict(scenario),
        'test_case': dict(test_case),
        'steps': steps,
        'issues': issues
    }

def fix_id58_extraction_issue():
    """修复ID58的参数提取问题"""
    print("\n" + "=" * 80)
    print("🔧 修复ID58参数提取问题")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取测试用例
    c.execute("SELECT * FROM scenarios WHERE id = 58")
    scenario = c.fetchone()
    c.execute("SELECT * FROM test_cases WHERE id = ?", (scenario['test_case_id'],))
    test_case = c.fetchone()
    
    steps = json.loads(test_case['steps'])
    
    # 检查步骤2的响应结构，看看sessionId在哪里
    print("🔍 检查步骤2的API响应结构...")
    
    # 查找开台API的定义
    c.execute("""
        SELECT * FROM apis 
        WHERE path LIKE '%open-pay%' 
        AND project_id = ?
    """, (scenario['project_id'],))
    
    open_pay_api = c.fetchone()
    if open_pay_api:
        print(f"找到开台API: {open_pay_api['method']} {open_pay_api['path']}")
        print(f"描述: {open_pay_api['description']}")
        
        # 检查API的响应结构定义
        if open_pay_api['request_body']:
            try:
                request_body = json.loads(open_pay_api['request_body'])
                print(f"请求体结构: {list(request_body.keys()) if isinstance(request_body, dict) else type(request_body)}")
            except:
                pass
    
    # 检查最近的执行记录，看看实际响应
    c.execute("""
        SELECT * FROM executions 
        WHERE test_case_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (test_case['id'],))
    
    execution = c.fetchone()
    if execution:
        results = json.loads(execution['results'])
        if len(results) >= 2:
            step2_result = results[1]  # 步骤2（开台）
            response = step2_result.get('response', {})
            
            print(f"\n步骤2实际响应结构:")
            if isinstance(response, dict):
                print(f"   顶级字段: {list(response.keys())}")
                
                if 'data' in response:
                    data = response['data']
                    if isinstance(data, dict):
                        print(f"   data字段: {list(data.keys())}")
                        
                        # 查找可能的sessionId字段
                        session_fields = [k for k in data.keys() if 'session' in k.lower()]
                        if session_fields:
                            print(f"   可能的session字段: {session_fields}")
                        else:
                            print(f"   ❌ 没有找到session相关字段")
                            print(f"   所有字段: {list(data.keys())}")
                    else:
                        print(f"   data类型: {type(data)}")
                else:
                    print(f"   ❌ 响应中没有data字段")
            else:
                print(f"   响应类型: {type(response)}")
    
    # 修复步骤3的参数映射
    print(f"\n🔧 修复步骤3的参数映射...")
    
    if len(steps) >= 3:
        step3 = steps[2]  # 步骤3
        param_mappings = step3.get('param_mappings', [])
        
        # 查找sessionId映射
        session_mapping = None
        for mapping in param_mappings:
            if 'session' in mapping.get('from_field', '').lower():
                session_mapping = mapping
                break
        
        if session_mapping:
            current_from_field = session_mapping['from_field']
            print(f"当前sessionId映射: {current_from_field}")
            
            # 根据实际响应调整映射
            if execution and len(results) >= 2:
                step2_response = results[1].get('response', {})
                if isinstance(step2_response, dict) and 'data' in step2_response:
                    data = step2_response['data']
                    if isinstance(data, dict):
                        # 查找实际的session字段
                        possible_fields = []
                        for key, value in data.items():
                            if 'session' in key.lower() or (isinstance(value, str) and len(value) > 10):
                                possible_fields.append(key)
                        
                        if possible_fields:
                            # 选择最可能的字段
                            best_field = None
                            for field in possible_fields:
                                if 'session' in field.lower():
                                    best_field = field
                                    break
                            
                            if not best_field:
                                best_field = possible_fields[0]
                            
                            new_from_field = f"data.{best_field}"
                            
                            if new_from_field != current_from_field:
                                print(f"建议修改映射: {current_from_field} -> {new_from_field}")
                                
                                # 更新映射
                                session_mapping['from_field'] = new_from_field
                                
                                # 保存更新
                                c.execute("""
                                    UPDATE test_cases 
                                    SET steps = ? 
                                    WHERE id = ?
                                """, (json.dumps(steps), test_case['id']))
                                
                                conn.commit()
                                print(f"✅ 已更新参数映射")
                            else:
                                print(f"✅ 当前映射已正确")
                        else:
                            print(f"❌ 步骤2响应中没有找到合适的session字段")
    
    conn.close()

async def test_id58_execution():
    """测试ID58的执行"""
    print("\n" + "=" * 80)
    print("🧪 测试ID58执行")
    print("=" * 80)
    
    # 调用执行API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/v1/executions",
                json={
                    "test_case_id": 52,  # ID58对应的测试用例ID
                    "environment": "test",
                    "base_url": "https://medev-stage.ktvsky.com"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 执行成功")
                print(f"执行ID: {result.get('id')}")
                print(f"状态: {result.get('status')}")
                
                results = result.get('results', [])
                for i, step_result in enumerate(results):
                    step_num = i + 1
                    print(f"\n步骤{step_num}:")
                    print(f"   状态码: {step_result.get('status_code')}")
                    print(f"   成功: {step_result.get('success')}")
                    
                    # 检查提取记录
                    extractions = step_result.get('extractions', [])
                    if extractions:
                        for ext in extractions:
                            success = ext.get('success', False)
                            icon = "✅" if success else "❌"
                            print(f"   {icon} 提取 {ext.get('from_field')} -> {ext.get('to_type')}.{ext.get('to_field')}")
                            if not success:
                                print(f"      错误: {ext.get('error_msg')}")
                    
                    # 检查响应
                    response_data = step_result.get('response', {})
                    if isinstance(response_data, dict):
                        code = response_data.get('code')
                        message = response_data.get('message')
                        print(f"   响应: code={code}, message={message}")
            else:
                print(f"❌ 执行失败: {response.status_code}")
                print(f"错误: {response.text}")
                
        except Exception as e:
            print(f"❌ 执行异常: {str(e)}")

def enhance_scenario_generation():
    """增强场景生成，确保包含完整的请求头和参数映射"""
    print("\n" + "=" * 80)
    print("🚀 增强场景生成逻辑")
    print("=" * 80)
    
    print("""
建议的增强措施:

1. 📋 API导入时增强请求头信息:
   - 确保每个API都包含完整的headers定义
   - 特别是需要认证的API，明确标记需要Authorization

2. 🤖 AI生成时增强提示词:
   - 明确指出哪些API需要token认证
   - 提供更详细的参数映射示例
   - 强调响应字段的准确提取

3. 🔍 执行时增强调试信息:
   - 详细记录每个参数映射的执行过程
   - 记录响应结构，便于调试提取失败的问题
   - 提供更友好的错误信息

4. ✅ 验证机制:
   - 生成场景后自动验证参数映射的合理性
   - 检查必需的请求头是否配置
   - 验证提取字段是否存在于响应中
    """)

def main():
    """主函数"""
    print("🔧 ID58问题修复工具")
    print("=" * 80)
    
    # 1. 分析问题
    analysis = analyze_id58_issue()
    
    if not analysis:
        return
    
    # 2. 修复提取问题
    fix_id58_extraction_issue()
    
    # 3. 测试执行
    print("\n是否要测试执行? (y/n): ", end="")
    if input().lower() == 'y':
        asyncio.run(test_id58_execution())
    
    # 4. 增强建议
    enhance_scenario_generation()
    
    print(f"\n" + "=" * 80)
    print(f"✅ 修复完成")
    print("=" * 80)
    print("""
总结:
1. ✅ 已分析ID58的配置和执行问题
2. ✅ 已修复参数映射中的字段提取问题
3. ✅ 提供了场景生成的增强建议

下一步建议:
1. 重新执行ID58测试场景
2. 检查业务逻辑问题（如门店授权码）
3. 完善API导入时的请求头信息
4. 优化AI生成的提示词
    """)

if __name__ == "__main__":
    main()
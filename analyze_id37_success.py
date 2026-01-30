#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析ID 37成功的原因
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def analyze_id37():
    print("=" * 80)
    print("🔍 分析ID 37成功的原因")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 查找ID 37相关的数据
    print("\n📋 查找ID 37相关数据:")
    
    # 检查是否是场景ID 37
    c.execute("SELECT * FROM scenarios WHERE id = 37")
    scenario37 = c.fetchone()
    
    if scenario37:
        print(f"   ✅ 找到场景37: {scenario37['name']}")
        print(f"   测试用例ID: {scenario37['test_case_id']}")
        test_case_id = scenario37['test_case_id']
    else:
        # 检查是否是测试用例ID 37
        c.execute("SELECT * FROM test_cases WHERE id = 37")
        case37 = c.fetchone()
        
        if case37:
            print(f"   ✅ 找到测试用例37: {case37['name']}")
            test_case_id = 37
        else:
            print("   ❌ 找不到ID 37的场景或测试用例")
            
            # 显示所有可能的ID
            print("\n   可用的场景ID:")
            c.execute("SELECT id, name FROM scenarios ORDER BY id DESC LIMIT 10")
            scenarios = c.fetchall()
            for s in scenarios:
                print(f"      场景{s['id']}: {s['name']}")
            
            print("\n   可用的测试用例ID:")
            c.execute("SELECT id, name FROM test_cases ORDER BY id DESC LIMIT 10")
            cases = c.fetchall()
            for case in cases:
                print(f"      用例{case['id']}: {case['name']}")
            
            conn.close()
            return
    
    # 2. 获取ID 37的测试用例配置
    c.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,))
    case37 = c.fetchone()
    
    if not case37:
        print(f"   ❌ 找不到测试用例{test_case_id}")
        conn.close()
        return
    
    steps37 = json.loads(case37['steps'])
    
    print(f"\n📝 ID 37的测试用例配置:")
    print(f"   名称: {case37['name']}")
    print(f"   步骤数: {len(steps37)}")
    
    # 显示前3步的详细配置
    for i in range(min(3, len(steps37))):
        step = steps37[i]
        print(f"\n   步骤{i+1}: {step.get('api_method')} {step.get('api_path')}")
        
        # 显示所有参数
        params = step.get('params', {})
        if params:
            print(f"   请求参数:")
            for key, value in params.items():
                print(f"      {key}: {value}")
        
        # 显示所有请求头
        headers = step.get('headers', {})
        if headers:
            print(f"   请求头:")
            for key, value in headers.items():
                print(f"      {key}: {value}")
        
        # 显示参数映射
        param_mappings = step.get('param_mappings', [])
        if param_mappings:
            print(f"   参数映射:")
            for mapping in param_mappings:
                print(f"      {json.dumps(mapping, ensure_ascii=False)}")
    
    # 3. 查找ID 37的成功执行记录
    print(f"\n" + "=" * 80)
    print(f"📊 ID 37的执行记录:")
    print("-" * 80)
    
    c.execute("""
        SELECT * FROM executions 
        WHERE test_case_id = ? 
        ORDER BY id DESC 
        LIMIT 3
    """, (test_case_id,))
    
    executions = c.fetchall()
    
    if executions:
        for exec_rec in executions:
            print(f"\n执行{exec_rec['id']} ({exec_rec['created_at']}):")
            print(f"   状态: {exec_rec['status']}")
            
            results = json.loads(exec_rec['results'])
            
            for j, result in enumerate(results[:3], 1):
                print(f"\n   步骤{j}: {result.get('method')} {result.get('url')}")
                print(f"      状态码: {result.get('status_code')}")
                print(f"      成功: {result.get('success')}")
                
                # 显示请求头（特别是Authorization）
                req_headers = result.get('request_headers', {})
                if req_headers:
                    print(f"      请求头:")
                    for key, value in req_headers.items():
                        if key.lower() in ['authorization', 'x-venue-id', 'x-employee-id', 'x-mac']:
                            print(f"         {key}: {value}")
                
                # 显示响应
                response = result.get('response', {})
                if isinstance(response, dict):
                    code = response.get('code')
                    message = response.get('message')
                    print(f"      响应: code={code}, message={message}")
                    
                    # 如果是步骤1，显示返回的关键数据
                    if j == 1 and isinstance(response, dict):
                        data = response.get('data', {})
                        if 'token' in data:
                            token = data['token']
                            print(f"      返回token: {str(token)[:30]}...")
                        
                        # 显示其他可能重要的字段
                        if 'loginEmployeeVO' in data:
                            employee = data['loginEmployeeVO']
                            print(f"      员工ID: {employee.get('id')}")
                            print(f"      员工姓名: {employee.get('name')}")
                            print(f"      权限角色: {employee.get('permissionRole')}")
    else:
        print(f"   ❌ 没有找到ID 37的执行记录")
    
    # 4. 对比最新的失败执行
    print(f"\n" + "=" * 80)
    print(f"🔍 对比最新的失败执行:")
    print("-" * 80)
    
    c.execute("""
        SELECT * FROM executions 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    latest_exec = c.fetchone()
    
    if latest_exec:
        print(f"\n最新执行{latest_exec['id']} ({latest_exec['created_at']}):")
        print(f"   状态: {latest_exec['status']}")
        
        latest_results = json.loads(latest_exec['results'])
        
        if len(latest_results) >= 2:
            step1 = latest_results[0]
            step2 = latest_results[1]
            
            print(f"\n   步骤1: {step1.get('status_code')} - {step1.get('success')}")
            print(f"   步骤2: {step2.get('status_code')} - {step2.get('success')}")
            
            # 对比步骤2的请求头
            print(f"\n   步骤2请求头对比:")
            
            if executions and len(json.loads(executions[0]['results'])) >= 2:
                success_step2 = json.loads(executions[0]['results'])[1]
                success_headers = success_step2.get('request_headers', {})
                
                print(f"\n   成功的执行 (ID 37):")
                for key, value in success_headers.items():
                    if key.lower() in ['authorization', 'x-venue-id', 'x-employee-id', 'x-mac']:
                        print(f"      {key}: {value}")
            
            fail_headers = step2.get('request_headers', {})
            print(f"\n   失败的执行 (最新):")
            for key, value in fail_headers.items():
                if key.lower() in ['authorization', 'x-venue-id', 'x-employee-id', 'x-mac']:
                    print(f"      {key}: {value}")
    
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"💡 分析建议:")
    print("=" * 80)
    print("""
1. 对比成功和失败执行的请求头差异
2. 检查是否缺少必需的header（如X-Employee-Id, X-Venue-Id等）
3. 检查token格式是否一致
4. 检查请求参数是否有差异
5. 检查员工权限和门店权限
    """)

if __name__ == "__main__":
    analyze_id37()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景执行500错误诊断脚本
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def diagnose():
    print("=" * 80)
    print("🔍 场景执行500错误诊断")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 查看最近的场景
    print("\n📋 最近的测试场景:")
    c.execute("""
        SELECT id, name, test_case_id, created_at 
        FROM scenarios 
        ORDER BY id DESC 
        LIMIT 5
    """)
    scenarios = c.fetchall()
    for s in scenarios:
        print(f"  场景 {s['id']}: {s['name']} (用例ID: {s['test_case_id']})")
    
    if not scenarios:
        print("  ❌ 没有找到场景")
        conn.close()
        return
    
    # 选择最新的场景
    scenario = scenarios[0]
    scenario_id = scenario['id']
    test_case_id = scenario['test_case_id']
    
    print(f"\n🎯 分析场景: {scenario['name']} (ID: {scenario_id})")
    
    # 2. 查看测试用例步骤
    c.execute("SELECT steps FROM test_cases WHERE id = ?", (test_case_id,))
    case = c.fetchone()
    
    if not case:
        print(f"  ❌ 找不到测试用例 {test_case_id}")
        conn.close()
        return
    
    steps = json.loads(case['steps'])
    print(f"\n📝 测试步骤数量: {len(steps)}")
    
    # 3. 分析每个步骤
    print("\n🔬 步骤详细分析:")
    print("-" * 80)
    
    issues_found = []
    
    for i, step in enumerate(steps, 1):
        print(f"\n步骤 {i}:")
        print(f"  方法: {step.get('api_method', 'N/A')}")
        print(f"  路径: {step.get('api_path', 'N/A')}")
        print(f"  描述: {step.get('description', 'N/A')}")
        
        # 检查请求头
        headers = step.get('headers', {})
        print(f"  请求头: {json.dumps(headers, ensure_ascii=False, indent=4)}")
        
        # 检查参数映射
        param_mappings = step.get('param_mappings', [])
        if param_mappings:
            print(f"  参数映射:")
            for mapping in param_mappings:
                from_step = mapping.get('from_step')
                from_field = mapping.get('from_field')
                to_field = mapping.get('to_field')
                to_type = mapping.get('to_type', 'params')
                print(f"    - 从步骤{from_step}的{from_field} -> {to_type}.{to_field}")
                
                # 检查是否映射到headers
                if to_type == 'headers':
                    print(f"      ⚠️  发现headers映射: {to_field}")
                    if to_field.lower() == 'authorization':
                        issues_found.append({
                            'step': i,
                            'issue': 'Authorization header映射',
                            'detail': f'步骤{i}依赖步骤{from_step}的{from_field}作为Authorization'
                        })
        
        # 检查请求参数
        params = step.get('params', {})
        if params:
            print(f"  请求参数: {json.dumps(params, ensure_ascii=False, indent=4)}")
    
    # 4. 查看最近的执行记录
    print("\n" + "=" * 80)
    print("📊 最近的执行记录:")
    print("-" * 80)
    
    c.execute("""
        SELECT id, test_case_id, status, results, created_at 
        FROM executions 
        WHERE test_case_id = ?
        ORDER BY id DESC 
        LIMIT 3
    """, (test_case_id,))
    
    executions = c.fetchall()
    
    if not executions:
        print("  ℹ️  还没有执行记录")
    else:
        for exec_rec in executions:
            print(f"\n执行 {exec_rec['id']} ({exec_rec['created_at']}):")
            print(f"  状态: {exec_rec['status']}")
            
            results = json.loads(exec_rec['results'])
            for result in results:
                step_order = result.get('step_order', '?')
                status_code = result.get('status_code', 'N/A')
                success = result.get('success', False)
                error = result.get('error', '')
                
                status_icon = "✅" if success else "❌"
                print(f"  {status_icon} 步骤{step_order}: {status_code}")
                
                if error:
                    print(f"      错误: {error}")
                
                # 检查响应
                response = result.get('response', {})
                if isinstance(response, dict):
                    if 'code' in response and response['code'] == 500:
                        print(f"      ⚠️  服务器返回500错误")
                        print(f"      消息: {response.get('message', 'N/A')}")
                        issues_found.append({
                            'step': step_order,
                            'issue': '服务器500错误',
                            'detail': response.get('message', '未知错误')
                        })
    
    # 5. 总结问题
    print("\n" + "=" * 80)
    print("🎯 问题总结:")
    print("=" * 80)
    
    if issues_found:
        print(f"\n发现 {len(issues_found)} 个潜在问题:\n")
        for idx, issue in enumerate(issues_found, 1):
            print(f"{idx}. 步骤{issue['step']}: {issue['issue']}")
            print(f"   详情: {issue['detail']}\n")
    else:
        print("\n✅ 未发现明显问题")
    
    # 6. 常见原因分析
    print("\n💡 场景执行第2个接口开始报500的常见原因:")
    print("-" * 80)
    print("""
1. **请求头丢失或错误** (最常见)
   - 第1个接口(登录)成功返回token
   - 第2个接口需要使用token作为Authorization header
   - 但token没有正确传递或格式错误(如缺少"Bearer "前缀)
   
2. **参数映射问题**
   - 第2个接口依赖第1个接口的返回数据
   - 但参数映射路径错误或数据提取失败
   
3. **会话状态问题**
   - 每个步骤使用独立的HTTP客户端
   - Cookie或Session没有在步骤间传递
   
4. **Base URL配置错误**
   - 不同接口可能需要不同的域名
   - 但使用了统一的base_url
   
5. **请求体格式问题**
   - Content-Type设置错误
   - JSON序列化问题
    """)
    
    print("\n🔧 建议的排查步骤:")
    print("-" * 80)
    print("""
1. 检查第1个接口的响应,确认token字段名称和位置
2. 检查第2个接口的param_mappings,确认token映射配置
3. 查看执行日志中的request_headers,确认Authorization是否正确
4. 单独执行第2个接口,手动提供token,验证接口本身是否正常
5. 检查后端API是否有token验证逻辑,以及错误返回格式
    """)
    
    conn.close()

if __name__ == "__main__":
    diagnose()
